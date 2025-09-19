/* In RISCVuzz, a server is connected to many clients.
Since in this case we only have one C910 board (AKA 1 client), all code will be
run on the board instead.
However, the code will still be split into two sections (client and server) for
ease of futher expansion.
*/

#include "client.h"

#include <errno.h>
#include <signal.h>
#include <stdatomic.h>
#include <sys/time.h>

#include "../main.h"
#include "sandbox.h"

// extern functions
extern void run_sandbox();
extern void test_start();
extern void print_xreg_changes();
extern void print_freg_changes();

// function declarations
static void diffs_push(void *addr, uint8_t oldv, uint8_t newv);
static bool probe_read_byte(uint8_t *addr, uint8_t *out);
static void report_diffs(uint8_t expected);
static bool region_exists(void *addr);
static inline void *page_align_down(void *p);
static void map_two_pages(void *base, uint8_t fill_byte);
static void fill_all_pages(uint8_t fill_byte);
void unmap_all_regions(void);
static void run_until_quiet(int8_t fill_byte);
void *alloc_sandbox_stack(size_t stack_size);
void free_sandbox_stack(void *stack_top, size_t stack_size);
void arm_timeout_timer(void);
void disarm_timeout_timer(void);
int run_client(uint32_t *instructions, size_t n_instructions);

// extern variables
extern sigjmp_buf jump_buffer;

extern uint64_t xreg_init_data[];
extern uint64_t xreg_output_data[];

extern size_t sandbox_pages;
extern size_t page_size;

// private definitions
#define SANDBOX_STACK_SIZE (64 * 1024)  // e.g. 64KB
#define STACK_GUARD_PAGES 1

// private variables
uint8_t *sandbox_ptr;

volatile sig_atomic_t g_faults_this_run = 0;
volatile atomic_uintptr_t g_fault_addr = 0;
mapped_region_t *g_regions = NULL;
size_t g_regions_len = 0;  // global counter variable (number of valid entries
                           // currently stored in the g_regions array)

memdiff_t *g_diffs = NULL;
static size_t g_diffs_len = 0;
static size_t g_diffs_cap = 0;

// Example: vse128.v v0, 0(t0) encoded as 0x10028027
uint32_t instrs[] = {
    0x00000013,  // nop to be replaced

    0x00048067  // jalr x0, 0(x9)
};

int run_client(uint32_t *instructions, size_t n_instructions) {
  setup_signal_handlers();
  unmap_vdso_vvar();

  // for (size_t i = 0; i < sizeof(fuzz_buffer) / sizeof(uint32_t); i++)
  for (size_t i = 0; i < n_instructions; i++) {
    void *sandbox_sp = alloc_sandbox_stack(SANDBOX_STACK_SIZE);
    xreg_init_data[2] = (uint64_t)sandbox_sp;

    // uint8_t sandbox_stack[SANDBOX_STACK_SIZE];
    // void *sandbox_sp = sandbox_stack + SANDBOX_STACK_SIZE;
    // xreg_init_data[2] = (uint64_t)sandbox_sp;

    log_append("=== Running fuzz %zu: 0x%08x ===\n", i, instructions[i]);

    // prepare sandbox
    prepare_sandbox(sandbox_ptr);
    // instrs[0] = fuzz_buffer[i];
    instrs[0] = instructions[i];
    inject_instructions(sandbox_ptr, instrs, sizeof(instrs) / sizeof(uint32_t));

    // unmap using munmap
    unmap_all_regions();  // unmap g_regions

    int jump_rc = sigsetjmp(jump_buffer, 1);
    if (jump_rc == 0) {
      arm_timeout_timer();
      run_sandbox(sandbox_ptr);
      disarm_timeout_timer();
      continue;  // no faults raised
    } else {
      disarm_timeout_timer();

      if (jump_rc == 1 || jump_rc == 4 || jump_rc == 5) {
        // 1. non SIGSEGV fault raised
        // 4. SIGSEGV fault in sandbox memory
        // 5. timer timeout: sandbox stuck
        continue;
      }
    }
    // SIGSEGV if code reaches here
    run_until_quiet(0x00);
    report_diffs(0x00);

    // log_append("Mapped regions:\n");
    // for (size_t i = 0; i < g_regions_len; i++)
    // {
    //     log_append("region %zu: addr=%p, len=%zu\n", i,
    //     g_regions[i].addr, g_regions[i].len);
    // }

    prepare_sandbox(sandbox_ptr);
    instrs[0] = instructions[i];

    inject_instructions(sandbox_ptr, instrs, sizeof(instrs) / sizeof(uint32_t));

    fill_all_pages(0xFF);
    run_until_quiet(0xFF);
    report_diffs(0xFF);

    // printf("DEBUG: g_regions_len=%zu g_diffs_cap=%zu g_diffs_len=%zu\n",
    //        g_regions_len, g_diffs_cap, g_diffs_len);
    // fflush(stdout);
    if (xreg_init_data == NULL || xreg_output_data == NULL) {
      log_append("WARNING: xreg pointers NULL; skipping print_xreg_changes\n");
    } else {
      print_xreg_changes();
    }

    print_xreg_changes();
    print_freg_changes();

    free_sandbox_stack(sandbox_sp, SANDBOX_STACK_SIZE);
  }
  return 0;
}

static void run_until_quiet(int8_t fill_byte) {
  g_fault_addr = 0;
  int retries = 0;
  const int MAX_RETRIES = 20;  // set limit

  while (1) {
    if (++retries > MAX_RETRIES) {
      log_append("ERROR: Max retries exceeded, aborting run_until_quiet\n");
      // fflush(stdout);
      break;
    }

    int jump_rc = sigsetjmp(jump_buffer, 1);

    if (jump_rc == 0) {
      arm_timeout_timer();
      run_sandbox(sandbox_ptr);
      disarm_timeout_timer();
      break;
    } else {
      disarm_timeout_timer();
      if (jump_rc == 2) {
        // segv happened; map and retry
        void *base = page_align_down((void *)g_fault_addr);
        map_two_pages(base, fill_byte);
      } else if (jump_rc == 1 || jump_rc == 3 || jump_rc == 4 || jump_rc == 5) {
        log_append("non-recoverable jump_rc=%i, exiting loop\n", jump_rc);
        break;
      }
    }
  }
  log_append("run_until_quiet finished\n");
}

// Maps two pages of memory (base and base + pagesize)
static void map_two_pages(void *base, uint8_t fill_byte) {
  if (g_regions_len >= MAX_MAPPED_PAGES) return;

  if (base == NULL) {
    log_append("map_two_pages: refusing to map at NULL base\n");
    siglongjmp(jump_buffer, 4);
  }

  /* avoid mapping very low addresses (NULL page) */
  if ((uintptr_t)base < (uintptr_t)page_size) {
    log_append("map_two_pages: refusing to map at low address %p\n", base);
    siglongjmp(jump_buffer, 4);
  }

  /* if region exists at exactly this base, skip */
  if (region_exists(base)) return;

  void *r =
      mmap(base, 2 * page_size, PROT_READ | PROT_WRITE,
           MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE,  // MAP_FIXED
           -1, 0);
  log_append("mapping: %p\n", r);
  if (r == MAP_FAILED) {
    int e = errno;
    log_append("mmap failed (requested %p): errno=%d (%s)\n", base, e,
               strerror(e));

    // perror("mmap failed for lazy mapping");
    siglongjmp(jump_buffer, 4);  // abort / skip this test case
  }

  log_append("Requested base: 0x%016lx, mapped at: 0x%016lx\n",
             (unsigned long)(uintptr_t)base, (unsigned long)(uintptr_t)r);

  /* Store the actual returned address (r), not the requested base */
  if (g_regions_len < MAX_MAPPED_PAGES) {
    g_regions[g_regions_len].addr = r;
    g_regions[g_regions_len].len = 2 * page_size;
    g_regions_len++;
  } else {
    log_append("WARNING: region capacity exhausted\n");
    /* still write to the mapping to initialize it */
  }

  // fill region with fill_byte
  memset(r, fill_byte, 2 * page_size);
}

static void diffs_push(void *addr, uint8_t oldv, uint8_t newv) {
  if (g_diffs_len == g_diffs_cap) {
    size_t ncap = g_diffs_cap ? g_diffs_cap * 2 : 256;
    memdiff_t *tmp = realloc(g_diffs, ncap * sizeof(*g_diffs));
    if (!tmp) {
      perror("realloc");
      exit(1);
    }
    g_diffs = tmp;
    g_diffs_cap = ncap;
  }
  g_diffs[g_diffs_len++] = (memdiff_t){addr, oldv, newv};
}

static void report_diffs(uint8_t expected) {
  g_diffs_len = 0;

  /* sanity checks */
  if (g_regions == NULL) {
    log_append("report_diffs_safe: no g_regions\n");
    return;
  }

  for (size_t i = 0; i < g_regions_len; i++) {
    void *base = g_regions[i].addr;
    size_t len = g_regions[i].len;

    if (base == NULL || len == 0) {
      printf("Skipping invalid region %zu\n", i);
      fflush(stdout);
      continue;
    }

    uint8_t *p = (uint8_t *)g_regions[i].addr;
    size_t n = g_regions[i].len;

    if ((uintptr_t)p % page_size != 0 || n % page_size != 0) {
      printf("WARNING: misaligned region %zu: addr=%p len=%zu\n", i, p, n);
      fflush(stdout);
      if (((uintptr_t)base % page_size) != 0 || (len % page_size) != 0) {
        printf("Skipping misaligned region %zu: addr=%p len=%zu\n", i, base,
               len);
        fflush(stdout);
        continue;
      }

      uint8_t *p = (uint8_t *)g_regions[i].addr;
      size_t pages = len / page_size;

      for (size_t pg = 0; pg < pages; ++pg) {
        uint8_t sample = 0;
        uint8_t *page_addr = p + pg * page_size;

        /* probe the first byte of the page before scanning */
        if (!probe_read_byte(page_addr, &sample)) {
          printf(
              "Skipping page %zu of region %zu at %p (probe "
              "failed)\n",
              pg, i, page_addr);
          fflush(stdout);
          continue;
        }

        /* If probe succeeded, scan that page safely in a loop.
           If scanning the rest of the page faults, probe_read_byte will
           catch that on the next page loop (we still try to be
           conservative).
         */
        for (size_t off = 0; off < page_size; ++off) {
          uint8_t newv;
          /* small optimization: we already read page_addr[0] */
          if (off == 0) {
            newv = sample;
          } else {
            int rc2 = sigsetjmp(jump_buffer, 1);
            if (rc2 == 0) {
              volatile uint8_t v = page_addr[off];
              newv = (uint8_t)v;
            } else {
              log_append(
                  "Fault while scanning page %zu offset %zu; "
                  "skipping "
                  "rest of page\n",
                  pg, off);
              break;
            }
          }

          if (newv != expected) {
            void *absaddr = page_addr + off;
            diffs_push(absaddr, expected, newv);
          }
        }
      }
    }

    /* Print diffs */
    for (size_t k = 0; k < g_diffs_len; k++) {
      printf("CHG: addr=%p old=0x%02x new=0x%02x\n", g_diffs[k].addr,
             g_diffs[k].old_val, g_diffs[k].new_val);
      fflush(stdout);
    }
  }
}

static bool probe_read_byte(uint8_t *addr, uint8_t *out) {
  int rc = sigsetjmp(jump_buffer, 1);
  if (rc == 0) {
    /* Attempt read: volatile to force the actual memory read */
    volatile uint8_t v = *addr;
    *out = (uint8_t)v;
    /* normal path */
    return true;
  } else {
    /* siglongjmp landed here — read faulted or handler asked to skip */
    return false;
  }
}

static bool region_exists(void *addr) {
  for (size_t i = 0; i < g_regions_len; i++)
    if (g_regions[i].addr == addr) return true;
  return false;
}

// Takes an arbitrary address (p, which caused the segfault) and rounds it down
// to the start of the containing page Since mmap() only works at page-aligned
// addresses
static inline void *page_align_down(void *p) {
  uintptr_t u = (uintptr_t)p;
  return (void *)(u & ~(uintptr_t)(page_size - 1));
}

// fills all pages in g_region with fill_byte
static void fill_all_pages(uint8_t fill_byte) {
  for (size_t i = 0; i < g_regions_len; i++) {
    memset(g_regions[i].addr, fill_byte, g_regions[i].len);
  }
}

// Unmap all mapped regions and reset g_regions_len
void unmap_all_regions(void) {
  for (size_t i = 0; i < g_regions_len; i++) {
    log_append("munmapping: %p\n", g_regions[i].addr);
    if ((uintptr_t)g_regions[i].addr % page_size != 0) {
      fprintf(stderr, "munmap addr not page-aligned: %p\n", g_regions[i].addr);
      fflush(stdout);
    }
    if (g_regions[i].len % page_size != 0) {
      fprintf(stderr, "munmap len not page-size aligned: %zu\n",
              g_regions[i].len);
      fflush(stdout);
    }

    if (munmap(g_regions[i].addr, g_regions[i].len) != 0) {
      perror("munmap failed");
    }
  }

  g_faults_this_run = 0;
  g_regions_len = 0;
}

void *alloc_sandbox_stack(size_t stack_size) {
  size_t ps = 4096;  // call sysconf(_SC_PAGESIZE) during init
  size_t total = stack_size + STACK_GUARD_PAGES * ps;
  void *base = mmap(NULL, total, PROT_READ | PROT_WRITE,
                    MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
  if (base == MAP_FAILED) {
    perror("mmap sandbox stack");
    exit(1);
  }
  // Protect the bottom page as guard
  if (mprotect(base, STACK_GUARD_PAGES * ps, PROT_NONE) != 0) {
    perror("mprotect guard");
    exit(1);
  }
  // Return pointer to stack top (grow-down stack)
  return (uint8_t *)base + total;
}

void free_sandbox_stack(void *stack_top, size_t stack_size) {
  size_t ps = page_size;
  void *base = (uint8_t *)stack_top - (stack_size + STACK_GUARD_PAGES * ps);
  size_t total = stack_size + STACK_GUARD_PAGES * ps;
  munmap(base, total);
}

void arm_timeout_timer(void) {
  struct itimerval timer;
  timer.it_value.tv_sec = 1;  // 1 second timeout
  timer.it_value.tv_usec = 0;
  timer.it_interval.tv_sec = 0;
  timer.it_interval.tv_usec = 0;
  setitimer(ITIMER_REAL, &timer, NULL);
}

void disarm_timeout_timer(void) {
  struct itimerval timer = {0};
  setitimer(ITIMER_REAL, &timer, NULL);
}