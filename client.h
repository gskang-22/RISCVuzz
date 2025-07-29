#include <stdint.h>
#include <stdio.h>

void setup_signal_handlers();
void initialise();
uint8_t *allocate_executable_buffer(size_t size);
void inject_instructions(uint8_t *buf, const uint32_t *instrs, size_t num_instrs);
void print_reg_changes();
void unmap_vdso_vvar();
void compare_reg_changes(uint64_t regs_before[32], uint64_t regs_after[32]);
