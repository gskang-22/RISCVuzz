/* In RISCVuzz, a server is connected to many clients.
Since in this case we only have one C910 board (AKA 1 client), all code will be
run on the board instead.
However, the code will still be split into two sections (client and server) for ease of
futher expansion.
*/

#include "client.h"
#include "sandbox.h"
#include "../main.h"

extern void run_sandbox();
extern void test_start();
extern void print_xreg_changes();
extern void print_freg_changes();

extern sigjmp_buf jump_buffer;
extern uint64_t regs_before[32];
extern uint64_t regs_after[32];

extern uint32_t fuzz_buffer2[];
extern size_t fuzz_buffer_len;

#define BUFFER_SIZE 64 // Number of elements in the random buffer
uint32_t fuzz_buffer3[BUFFER_SIZE];
uint8_t *sandbox_ptr;

extern size_t sandbox_pages;
extern size_t page_size;

volatile sig_atomic_t g_faults_this_run = 0;
volatile uintptr_t g_fault_addr = 0;
mapped_region_t *g_regions = NULL;
static size_t g_regions_len = 0; // global counter variable (number of valid entries currently stored in the g_regions array)

memdiff_t *g_diffs = NULL;
static size_t g_diffs_len = 0;
static size_t g_diffs_cap = 0;

uint32_t rand32()
{
    // rand() typically returns 15-bit values, so combine to get 32 bits
    uint32_t r = ((uint32_t)rand() & 0x7FFF);
    r |= ((uint32_t)rand() & 0x7FFF) << 15;
    r |= ((uint32_t)rand() & 0x3) << 30; // Only need 2 more bits
    return r;
}

uint32_t fuzz_buffer[] = {
    // instructions to be injected
    0x00000013, // nop
    0x10028027, // ghostwrite
    0xFFFFFFFF, // illegal instruction
    0x00008067, // ret
    0x00050067, // jump to x10
    0x00048067, // jump to x9
    0x00058067, // jump to x11
    0x0000a103, // lw x2, 0(x1)
    0x0142b183, // ld x3, 20(x5)
    0x01423183, // ld x3, 20(x4)
};

// Example: vse128.v v0, 0(t0) encoded as 0x10028027
uint32_t instrs[] = {
    0x00000013, // nop to be replaced

    0x00048067 // jalr x0, 0(x9)
};

void print_registers(const char *label, uint64_t regs[32])
{
    // log_append("=== %s ===\n", label);
    for (int i = 0; i < 32; i++)
    {
        log_append("%-10s: 0x%016lx\n", reg_names[i], regs[i]);
    }
}

static void diffs_push(void *addr, uint8_t oldv, uint8_t newv)
{
    if (g_diffs_len == g_diffs_cap)
    {
        size_t ncap = g_diffs_cap ? g_diffs_cap * 2 : 256;
        g_diffs = realloc(g_diffs, ncap * sizeof(*g_diffs));
        if (!g_diffs)
        {
            perror("realloc");
            exit(1);
        }
        g_diffs_cap = ncap;
    }
    g_diffs[g_diffs_len++] = (memdiff_t){addr, oldv, newv};
}

static void report_diffs(uint8_t expected)
{
    g_diffs_len = 0;
    for (size_t i = 0; i < g_regions_len; i++)
    {
        uint8_t *p = (uint8_t *)g_regions[i].addr;
        size_t n = g_regions[i].len;
        for (size_t j = 0; j < n; j++)
        {
            uint8_t newv = p[j];
            if (newv != expected)
            {
                void *absaddr = (uint8_t *)g_regions[i].addr + j;
                diffs_push(absaddr, expected, newv);
            }
        }
    }

    for (size_t k = 0; k < g_diffs_len; k++)
    {
        log_append("CHG: addr=%p old=0x%02x new=0x%02x\n",
                g_diffs[k].addr, g_diffs[k].old_val, g_diffs[k].new_val);

    }
}

static bool region_exists(void *addr)
{
    for (size_t i = 0; i < g_regions_len; i++)
        if (g_regions[i].addr == addr)
            return true;
    return false;
}

// Takes an arbitrary address (p, which caused the segfault) and rounds it down to the start of the containing page
// Since mmap() only works at page-aligned addresses
static inline void *page_align_down(void *p)
{
    uintptr_t u = (uintptr_t)p;
    return (void *)(u & ~(uintptr_t)(page_size - 1));
}

// Maps two pages of memory (base and base + pagesize) starting at the faulting page
static void map_two_pages(void *base, uint8_t fill_byte)
{
    if (g_regions_len >= MAX_MAPPED_PAGES)
        return;

    if (!region_exists(base))
    {
        void *r = mmap(base, 2 * page_size,
                       PROT_READ | PROT_WRITE,
                       MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, // MAP_FIXED_NOREPLACE
                       -1, 0);
        // log_append("mapping: %p\n", r);
        if (r == MAP_FAILED)
        {
            perror("mmap failed for lazy mapping");
            siglongjmp(jump_buffer, 4); // abort / skip this test case
        }
        else
        {
            // log_append("Requested base: 0x%016lx, mapped at: 0x%016lx\n",
            //        (unsigned long)(uintptr_t)base,
            //        (unsigned long)(uintptr_t)r);

            // add region to g_regions array
            if (g_regions_len < MAX_MAPPED_PAGES)
            {
                g_regions[g_regions_len].addr = base;
                g_regions[g_regions_len].len = 2 * page_size;
                g_regions_len++;
            }
            // fill region with fill_byte
            memset(r, fill_byte, 2 * page_size);
        }
    }
}

// fills all pages in g_region with fill_byte
static void fill_all_pages(uint8_t fill_byte)
{
    for (size_t i = 0; i < g_regions_len; i++)
    {
        memset(g_regions[i].addr, fill_byte, g_regions[i].len);
    }
}

// Unmap all mapped regions and reset g_regions_len
void unmap_all_regions(void)
{
    for (size_t i = 0; i < g_regions_len; i++)
    {
        // log_append("munmapping: %p\n", g_regions[i].addr);
        if ((uintptr_t)g_regions[i].addr % page_size != 0) {
            fprintf(stderr, "munmap addr not page-aligned: %p\n", g_regions[i].addr);
        }
        if (g_regions[i].len % page_size != 0) {
            fprintf(stderr, "munmap len not page-size aligned: %zu\n", g_regions[i].len);
        }

        if (munmap(g_regions[i].addr, g_regions[i].len) != 0)
        {
            perror("munmap failed");
        }
    }

    g_faults_this_run = 0;
    g_regions_len = 0;
}

static void run_until_quiet(int8_t fill_byte)
{
    g_fault_addr = 0;

    while (1)
    {
        int jump_rc = sigsetjmp(jump_buffer, 1);

        if (jump_rc == 0)
        {
            run_sandbox(sandbox_ptr);
            break;
        }
        else if (jump_rc == 2)
        {
            // segv happened; map and retry
            void *base = page_align_down((void *)g_fault_addr);
            map_two_pages(base, fill_byte);
            continue;
        }
        else if (jump_rc == 1 || jump_rc == 3 || jump_rc == 4)
        {
            // log_append("non-recoverable jump_rc=%i, exiting loop\n", jump_rc);
            break;
        }
    }
    // log_append("run_until_quiet finished\n");
}

int run_client(uint32_t *instructions, size_t n_instructions)
{
    setup_signal_handlers();
    unmap_vdso_vvar();

    // for (size_t i = 0; i < sizeof(fuzz_buffer) / sizeof(uint32_t); i++)
    for (size_t i = 0; i < n_instructions; i++)
    {
        // log_append("=== Running fuzz %zu: 0x%08x ===\n", i, fuzz_buffer[i]);
        log_append("=== Running fuzz %zu: 0x%08x ===\n", i, instructions[i]);

        // prepare sandbox
        prepare_sandbox(sandbox_ptr);
        // instrs[0] = fuzz_buffer[i];
        instrs[0] = instructions[i];
        inject_instructions(sandbox_ptr, instrs, sizeof(instrs) / sizeof(uint32_t));

        // unmap using munmap
        unmap_all_regions(); // unmap g_regions

        int jump_rc = sigsetjmp(jump_buffer, 1);
        if (jump_rc == 0)
        {
            run_sandbox(sandbox_ptr);
            continue; // no faults raised
        }
        else if (jump_rc == 1 || jump_rc == 4)
        {
            // non SIGSEGV fault raised OR SIGSEGV fault in sandbox memory
            continue;
        }

        // SIGSEGV if code reaches here
        run_until_quiet(0x00);
        report_diffs(0x00);

        // log_append("Mapped regions:\n");
        // for (size_t i = 0; i < g_regions_len; i++)
        // {
        //     log_append("region %zu: addr=%p, len=%zu\n", i, g_regions[i].addr, g_regions[i].len);
        // }

        prepare_sandbox(sandbox_ptr);
        // instrs[0] = fuzz_buffer[i];
        instrs[0] = instructions[i];

        inject_instructions(sandbox_ptr, instrs, sizeof(instrs) / sizeof(uint32_t));

        fill_all_pages(0xFF);
        run_until_quiet(0xFF);
        report_diffs(0xFF);

        print_xreg_changes();
        print_freg_changes();
    }


    return 0;
}
