/* In RISCVuzz, a server is connected to many clients.
Since in this case we only have one C910 board (AKA 1 client), all code will be
run on the board instead.
However, the code will still be split into two sections (client and server) for ease of
futher expansion.
*/

#include "client.h"
#include <stdint.h>
#include <unistd.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

extern void run_sandbox();
extern void test_start();
extern sigjmp_buf jump_buffer;
extern uint64_t regs_before[32];
extern uint64_t regs_after[32];

size_t sandbox_size = 0x1000;
uint8_t *sandbox_ptr;
size_t start_offset = 0x20;

uint32_t fuzz_buffer[] = {
    // instructions to be injected
    0x00000013, // nop
    0x10028027, // ghostwrite
    0x00008067, // ret
};

// Example: vse128.v v0, 0(t0) encoded as 0x10028027
uint32_t instrs[] = {
    0x00000013, // nop to be replaced
    // 0xFFFF8F67,
    0x000F8067, // jalr x0, 0(t6)
};

const char *reg_names[] = {
    "x0 (zero)", "x1 (ra)", "x2 (sp)", "x3 (gp)", "x4 (tp)",
    "x5 (t0)", "x6 (t1)", "x7 (t2)", "x8 (s0/fp)", "x9 (s1)",
    "x10 (a0)", "x11 (a1)", "x12 (a2)", "x13 (a3)", "x14 (a4)",
    "x15 (a5)", "x16 (a6)", "x17 (a7)", "x18 (s2)", "x19 (s3)",
    "x20 (s4)", "x21 (s5)", "x22 (s6)", "x23 (s7)", "x24 (s8)",
    "x25 (s9)", "x26 (s10)", "x27 (s11)", "x28 (t3)", "x29 (t4)",
    "x30 (t5)", "x31 (t6)"};

void print_registers(const char *label, uint64_t regs[32])
{
    printf("=== %s ===\n", label);
    for (int i = 0; i < 32; i++)
    {
        printf("%-10s: 0x%016lx\n", reg_names[i], regs[i]);
    }
}

int main()
{
    uint64_t store_regs_before[32];
    uint64_t store_regs_after[32];
    setup_signal_handlers();
    unmap_vdso_vvar();
    printf("\n");
    sandbox_ptr = allocate_executable_buffer(sandbox_size);
    printf("sandbox ptr: %p\n", sandbox_ptr);

    for (size_t i = 0; i < sizeof(fuzz_buffer) / sizeof(uint32_t); i++)
    {

        printf("=== Running fuzz %zu: 0x%08x ===\n", i, fuzz_buffer[i]);
        memset(sandbox_ptr, 0, sandbox_size);
        pid_t pid = fork();
        if (pid == 0)
        {
            // replace nop with fuzzed instruction
            instrs[0] = fuzz_buffer[i];
            // inject instruction
            inject_instructions(sandbox_ptr, instrs, sizeof(instrs) / sizeof(uint32_t), start_offset, sandbox_size);
            run_sandbox(sandbox_ptr);
            _exit(0);
        }
        else
        {
            int status;
            waitpid(pid, &status, 0);
            if (WIFSIGNALED(status))
                printf("Child crashed with signal %d\n", WTERMSIG(status));
            else
                printf("Child exited %d\n", WEXITSTATUS(status));
        }

        /*
        printf("=== Running fuzz %zu: 0x%08x ===\n", i, fuzz_buffer[i]);

        // loops twice to check for differing results
        for (size_t x = 0; x < 2; x++)
        {
            // clears sandbox memory
            memset(sandbox_ptr, 0, sandbox_size);

            if (sigsetjmp(jump_buffer, 1) == 0)
            {
                // replace nop with fuzzed instruction
                instrs[0] = fuzz_buffer[i];

                // inject instruction
                inject_instructions(sandbox_ptr, instrs, sizeof(instrs) / sizeof(uint32_t), start_offset, sandbox_size);

                run_sandbox(sandbox_ptr);
                
                print_registers("Registers Before", regs_before);
                print_registers("Registers After", regs_after);
                
                // print_reg_changes(regs_before, regs_after);

                
                // memcpy(store_regs_before, regs_before, 32 * sizeof(uint64_t));
                // memcpy(store_regs_after, regs_after, 32 * sizeof(uint64_t));
                
            }
            else
            {
                printf("Recovered from crash\n");
            }

            // compare_reg_changes(store_regs_before, regs_before);
            // compare_reg_changes(store_regs_after, regs_after);
        }
        printf("\n");
        */
    }
    return 0;
}
