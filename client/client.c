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
static void diffs_push(void* addr, uint8_t oldv, uint8_t newv);
static bool probe_read_byte(uint8_t* addr, uint8_t* out);
static void report_diffs(uint8_t expected);
static bool region_exists(void* addr);
static inline void* page_align_down(void* p);
static void map_two_pages(void* base, uint8_t fill_byte);
static void fill_all_pages(uint8_t fill_byte);
void unmap_all_regions(void);
static void run_until_quiet(int8_t fill_byte);
void* alloc_sandbox_stack(size_t stack_size);
void free_sandbox_stack(void* stack_top, size_t stack_size);
void arm_timeout_timer(void);
void disarm_timeout_timer(void);
void fill_instrs(uint32_t* instructions, size_t n_instructions);
int run_client(uint32_t* instructions, size_t n_instructions);

// extern variables
extern sigjmp_buf jump_buffer;

extern uint64_t xreg_init_data[];
extern uint64_t xreg_output_data[];

extern size_t sandbox_pages;
extern size_t page_size;

// private definitions
#define SANDBOX_STACK_SIZE (64 * 1024)  // e.g. 64KB
#define STACK_GUARD_PAGES 1
#define STACK_BASE_ADDR 0x2000000000UL  // 128 GB

// private variables
uint8_t* sandbox_ptr;

volatile sig_atomic_t g_faults_this_run = 0;
volatile atomic_uintptr_t g_fault_addr = 0;
mapped_region_t* g_regions = NULL;
size_t g_regions_len = 0;  // global counter variable (number of valid entries
                           // currently stored in the g_regions array)

memdiff_t* g_diffs = NULL;
static size_t g_diffs_len = 0;
static size_t g_diffs_cap = 0;

static const uint32_t instrs_template[] = {0x00000013, 0x00000013, 0x00000013,
                                           0x00000013, 0x00000013, 0x00048067};

// Example: vse128.v v0, 0(t0) encoded as 0x10028027
uint32_t instrs[sizeof(instrs_template) / sizeof(instrs_template[0])];

/**
 * @brief Run a single fuzzing test case inside the RISC-V sandbox.
 *
 * Sets up the sandbox environment, injects the provided instructions, and runs
 * them with signal-based recovery for SIGSEGV and timeouts.
 * If a segmentation fault occurs, the test is re-run using lazy page mapping to
 * capture architectural differences.
 * Finally, prints register deltas and restores all host state.
 *
 * Execution flow:
 * 1. Unmap VDSO/VVAR pages to prevent unintended interactions.
 * 2. Install custom signal handlers to catch SIGSEGV/timeouts.
 * 3. Allocate a private stack for the sandbox and initialise xregs.
 * 4. Prepare the sandbox environment and inject instructions.
 * 5. Attempt to run the sandbox:
 *    - If it completes normally: collect register diffs.
 *    - If a SIGSEGV occurs: run a second pass where missing pages are
 *      lazily mapped and re-run to capture differences.
 * 6. Print architectural register deltas.
 * 7. Free all allocated resources and restore host signal state.
 *
 * @param instructions     Array of RISC-V instructions to fuzz.
 * @param n_instructions   Number of instructions supplied.
 * @return 0
 */
int run_client(uint32_t* instructions, size_t n_instructions) {
  unmap_vdso_vvar();
  setup_signal_handlers();
  void* sandbox_sp = alloc_sandbox_stack(SANDBOX_STACK_SIZE);
  xreg_init_data[2] = (uint64_t)sandbox_sp;

  // prepare sandbox
  prepare_sandbox(sandbox_ptr);
  memcpy(instrs, instrs_template, sizeof(instrs));
  fill_instrs(instructions, n_instructions);
  inject_instructions(sandbox_ptr, instrs, sizeof(instrs) / sizeof(uint32_t));
  unmap_all_regions();  // unmap g_regions

  log_append("===Running fuzz:");
  for (size_t i = 0; i < sizeof(instrs) / sizeof(instrs[0]); ++i) {
    if (i == 0)
      log_append(" 0x%08x", instrs[i]);
    else
      log_append(", 0x%08x", instrs[i]);
  }
  log_append("====\n");

  bool had_seg_fault = false;
  int jump_rc = sigsetjmp(jump_buffer, 1);

  if (jump_rc == 0) {
    arm_timeout_timer();
    run_sandbox(sandbox_ptr);
    disarm_timeout_timer();

  } else {
    disarm_timeout_timer();
    if (jump_rc == 2) {
      had_seg_fault = true;
    }
  }

  if (had_seg_fault) {
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
    fill_instrs(instructions, n_instructions);

    inject_instructions(sandbox_ptr, instrs, sizeof(instrs) / sizeof(uint32_t));

    fill_all_pages(0xFF);
    run_until_quiet(0xFF);
    report_diffs(0xFF);

    // printf("DEBUG: g_regions_len=%zu g_diffs_cap=%zu g_diffs_len=%zu\n",
    //        g_regions_len, g_diffs_cap, g_diffs_len);
    // fflush(stdout);
  }

  print_xreg_changes();
  print_freg_changes();

  free_sandbox_stack(sandbox_sp, SANDBOX_STACK_SIZE);
  restore_signal_handlers();

  return 0;
}

/**
 * @brief Retry sandbox execution until it finishes without SIGSEGV.
 *
 * Each time a segmentation fault occurs, maps in the missing memory page using
 * `map_two_pages()` and retries. Stops when execution completes, a
 * non-recoverable signal occurs, or the retry limit is exceeded.
 *
 * @param fill_byte  Value used to initialise newly mapped pages.
 */
static void run_until_quiet(int8_t fill_byte) {
  g_fault_addr = 0;
  int retries = 0;
  const int MAX_RETRIES = 20;  // set limit

  while (1) {
    if (++retries > MAX_RETRIES) {
      log_append("ERROR: Max retries exceeded, aborting run_until_quiet\n");
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
        void* base = page_align_down((void*)g_fault_addr);
        map_two_pages(base, fill_byte);
      } else if (jump_rc == 1 || jump_rc == 3 || jump_rc == 4 || jump_rc == 5) {
        log_append("non-recoverable jump_rc=%i, exiting loop\n", jump_rc);
        break;
      }
    }
  }
  log_append("run_until_quiet finished\n");
}

/**
 * @brief Map two pages at the given base address for lazy fault recovery.
 *
 * Used after SIGSEGV to supply missing memory. Performs safety checks, maps
 * exactly two pages at `base` if not already mapped, records the region, and
 * fills it with `fill_byte`. On error, exits via siglongjmp.
 *
 * @param base        Page-aligned address to map.
 * @param fill_byte   Value to fill the mapped pages with.
 */
static void map_two_pages(void* base, uint8_t fill_byte) {
  if (g_regions_len >= MAX_MAPPED_PAGES) return;

  if (base == NULL) {
    // log_append("map_two_pages: refusing to map at NULL base\n");
    siglongjmp(jump_buffer, 4);
  }

  /* avoid mapping very low addresses (NULL page) */
  if ((uintptr_t)base < (uintptr_t)page_size) {
    // log_append("map_two_pages: refusing to map at low address %p\n", base);
    siglongjmp(jump_buffer, 4);
  }

  /* if region exists at exactly this base, skip */
  if (region_exists(base)) return;

  void* r =
      mmap(base, 2 * page_size, PROT_READ | PROT_WRITE,
           MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE,  // MAP_FIXED
           -1, 0);
  // log_append("mapping: %p\n", r);
  if (r == MAP_FAILED) {
    int e = errno;
    log_append("mmap failed (requested %p): errno=%d (%s)\n", base, e,
               strerror(e));

    // perror("mmap failed for lazy mapping");
    siglongjmp(jump_buffer, 4);  // abort / skip this test case
  }

  // log_append("Requested base: 0x%016lx, mapped at: 0x%016lx\n",
  //  (unsigned long)(uintptr_t)base, (unsigned long)(uintptr_t)r);

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

/**
 * @brief Append a memory-difference record to the global diff buffer.
 *
 * @param addr   Address where a memory change was detected.
 * @param oldv   Expected byte value before sandbox execution.
 * @param newv   Actual byte value read after execution.
 */
static void diffs_push(void* addr, uint8_t oldv, uint8_t newv) {
  if (g_diffs_len == g_diffs_cap) {
    size_t ncap = g_diffs_cap ? g_diffs_cap * 2 : 256;
    memdiff_t* tmp = realloc(g_diffs, ncap * sizeof(*g_diffs));
    if (!tmp) {
      perror("realloc");
      exit(1);
    }
    g_diffs = tmp;
    g_diffs_cap = ncap;
  }
  g_diffs[g_diffs_len++] = (memdiff_t){addr, oldv, newv};
}

/**
 * @brief Scan all mapped regions for memory modifications and report diffs.
 *
 * @param expected  The fill-byte that indicates an "unchanged" memory value.
 */
static void report_diffs(uint8_t expected) {
  g_diffs_len = 0;

  /* sanity checks */
  if (g_regions == NULL) {
    // log_append("report_diffs_safe: no g_regions\n");
    return;
  }

  for (size_t i = 0; i < g_regions_len; i++) {
    void* base = g_regions[i].addr;
    size_t len = g_regions[i].len;

    if (base == NULL || len == 0) {
      // printf("Skipping invalid region %zu\n", i);
      fflush(stdout);
      continue;
    }

    uint8_t* p = (uint8_t*)g_regions[i].addr;
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

      uint8_t* p = (uint8_t*)g_regions[i].addr;
      size_t pages = len / page_size;

      for (size_t pg = 0; pg < pages; ++pg) {
        uint8_t sample = 0;
        uint8_t* page_addr = p + pg * page_size;

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
            void* absaddr = page_addr + off;
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

/**
 * @brief Safely attempt to read one byte from a potentially unsafe address.
 *
 * @param addr  Address to read from.
 * @param out   Output pointer for the successfully read byte.
 * @return true if the read was successful; false if a fault occurred.
 */
static bool probe_read_byte(uint8_t* addr, uint8_t* out) {
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

/**
 * @brief Check whether a region starting at the given address is already
 * tracked.
 *
 * @param addr  Base address to compare against stored regions.
 * @return true if a region with this base address exists; false otherwise.
 */
static bool region_exists(void* addr) {
  for (size_t i = 0; i < g_regions_len; i++)
    if (g_regions[i].addr == addr) return true;
  return false;
}

/**
 * @brief Align an arbitrary address down to its page boundary.
 *
 * @param p  Arbitrary address that may not be page aligned.
 * @return The page-aligned base address.
 */
static inline void* page_align_down(void* p) {
  uintptr_t u = (uintptr_t)p;
  return (void*)(u & ~(uintptr_t)(page_size - 1));
}

/**
 * @brief Overwrite every mapped region with a uniform fill_byte.
 *
 * Iterates through all lazily-mapped memory regions tracked in g_regions
 * and fills their entire contents with the given value. Used to detect
 * memory writes by comparing against a known baseline.
 *
 * @param fill_byte  Value to write into all mapped pages.
 */
static void fill_all_pages(uint8_t fill_byte) {
  for (size_t i = 0; i < g_regions_len; i++) {
    memset(g_regions[i].addr, fill_byte, g_regions[i].len);
  }
}

/**
 * @brief Unmap all memory regions previously mapped for lazy fault recovery
 * and reset reset g_regions_len.
 *
 * This is used to clean up before running the next sandboxed instruction
 * sequence.
 */
void unmap_all_regions(void) {
  for (size_t i = 0; i < g_regions_len; i++) {
    // log_append("munmapping: %p\n", g_regions[i].addr);
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

/**
 * @brief Allocate and set up a protected stack region for the sandbox.
 *
 * Allocates a contiguous memory range consisting of:
 *   - one guard page (no access, via mprotect),
 *   - followed by the actual sandbox stack space.
 *
 * @param stack_size  Desired size of the usable stack (excluding guard pages).
 * @return Pointer to the top of the newly allocated sandbox stack.
 */
void* alloc_sandbox_stack(size_t stack_size) {
  size_t total = stack_size + STACK_GUARD_PAGES * page_size;

  void* base =
      mmap((void*)(STACK_BASE_ADDR - total), total, PROT_READ | PROT_WRITE,
           MAP_ANONYMOUS | MAP_PRIVATE | MAP_FIXED_NOREPLACE, -1, 0);
  if (base == MAP_FAILED) {
    perror("mmap sandbox stack");
    exit(1);
  }
  // Protect the bottom page as guard
  if (mprotect(base, STACK_GUARD_PAGES * page_size, PROT_NONE) != 0) {
    perror("mprotect guard");
    exit(1);
  }
  // Return pointer to stack top (grow-down stack)
  return (uint8_t*)base + total;
}

/**
 * @brief Unmap the sandbox stack previously allocated with
 * alloc_sandbox_stack().
 *
 * @param stack_top   Pointer returned by alloc_sandbox_stack() (top of stack).
 * @param stack_size  Size of the usable stack portion (without guard pages).
 */
void free_sandbox_stack(void* stack_top, size_t stack_size) {
  size_t ps = page_size;
  void* base = (uint8_t*)stack_top - (stack_size + STACK_GUARD_PAGES * ps);
  size_t total = stack_size + STACK_GUARD_PAGES * ps;
  munmap(base, total);
}

/**
 * @brief Arm a timer to detect sandbox hangs (infinite loops).
 */
void arm_timeout_timer(void) {
  struct itimerval timer;
  timer.it_value.tv_sec = 0;
  timer.it_value.tv_usec = 100000;
  timer.it_interval.tv_sec = 0;
  timer.it_interval.tv_usec = 0;
  setitimer(ITIMER_REAL, &timer, NULL);
}

/**
 * @brief Disarms the timer detecting sandbox hangs when
 * sandbox (asm code) returns successfully
 */
void disarm_timeout_timer(void) {
  struct itimerval timer = {0};
  setitimer(ITIMER_REAL, &timer, NULL);
}

// Copies user-provided instructions into instrs[]
void fill_instrs(uint32_t* instructions, size_t n_instructions) {
  size_t instrs_len = sizeof(instrs) / sizeof(instrs[0]);

  // don’t touch the last slot (jalr)
  size_t writable = instrs_len - 1;

  // copy only as many as instructions has, capped at writable space
  size_t to_copy = (n_instructions < writable) ? n_instructions : writable;

  for (size_t i = 0; i < to_copy; i++) {
    instrs[i] = instructions[i];
  }
}
