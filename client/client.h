#include <stdint.h>
#include <stdio.h>

typedef struct {
    void  *addr;
    size_t len;
} mapped_region_t;

typedef struct {
    void    *addr;    // absolute address
    uint8_t  old_val; // expected value
    uint8_t  new_val; // actual value
} memdiff_t;

void setup_signal_handlers();
void initialise();
uint8_t *allocate_executable_buffer();
void free_executable_buffer(uint8_t *sandbox);
void prepare_sandbox(uint8_t *sandbox_ptr);
void inject_instructions(uint8_t *sandbox_ptr, const uint32_t *instrs, size_t num_instrs);
void print_reg_changes();
void unmap_vdso_vvar();
void compare_reg_changes(uint64_t regs_before[32], uint64_t regs_after[32]);
