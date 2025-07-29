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
                                                                                                    
extern void run_sandbox();                                                        
extern sigjmp_buf jump_buffer;                                                                      
extern uint64_t regs_before[32];                                                                    
extern uint64_t regs_after[32];                                                                     
                                                                                                    
size_t sandbox_size;                                                                                
uint8_t *sandbox;                                                                                   
                                                                                                    
uint32_t fuzz_buffer[] = {                                                                          
    // instructions to be injected                                                                  
    0x10028027,                                                                                     
    0x00008067,                                                                                     
    0x00000013                                                                                      
};                                                                                                  
// Example: vse128.v v0, 0(t0) encoded as 0x10028027                                                
uint32_t instrs[] = {                                                                               
            0x00100073, // ebreak                                                                   
                                                                                                    
            0x00000013, // to be replaced                                                           
                                                                                                    
            0x00008067, // return                                                                   
            0x00100073, // ebreak                                                                   
            0x00100073  // ebreak again jic                                                         
};                                                                                                  
                                                                                                    
const char* reg_names[] = {                                                                         
"x0 (zero)", "x1 (ra)",   "x2 (sp)",  "x3 (gp)",  "x4 (tp)",                                        
"x5 (t0)",   "x6 (t1)",   "x7 (t2)",  "x8 (s0/fp)", "x9 (s1)",                                      
"x10 (a0)",  "x11 (a1)",  "x12 (a2)", "x13 (a3)", "x14 (a4)",                                       
"x15 (a5)",  "x16 (a6)",  "x17 (a7)", "x18 (s2)", "x19 (s3)",                                       
"x20 (s4)",  "x21 (s5)",  "x22 (s6)", "x23 (s7)", "x24 (s8)",                                       
"x25 (s9)",  "x26 (s10)", "x27 (s11)", "x28 (t3)", "x29 (t4)",                                      
"x30 (t5)",  "x31 (t6)"                                                                             
};                                                                                                  
                                                                                                    
void print_registers(const char* label, uint64_t regs[32]) {                                        
    printf("=== %s ===\n", label);                                                                  
    for (int i = 0; i < 32; i++) {                                                                  
        printf("%-10s: 0x%016lx\n", reg_names[i], regs[i]);                                         
    }                                                                                               
}                                                                                                   
                                                                                                    
int main() {                                                                                        
    setup_signal_handlers();                                                                        
                                                                                                    
    for (size_t i = 0; i < sizeof(fuzz_buffer) / sizeof(uint32_t); i++) {                           
        if (sigsetjmp(jump_buffer, 1) == 0) {                                                       
            sandbox_size = 0x1000;                                                                  
            sandbox = allocate_executable_buffer(sandbox_size);                                     
                                                                                                    
            // replace nop with fuzzed instruction                                                  
            instrs[1] = fuzz_buffer[i];                                                             
            // inject instruction                                                                   
            inject_instructions(sandbox, instrs, sizeof(instrs)/sizeof(uint32_t));                  
                                                                                                    
            printf("sandbox ptr: %p\n", sandbox);                                                   
            printf("Running fuzz %zu: 0x%08x\n", i, fuzz_buffer[i]);                                
                                                                                                    
            run_sandbox(sandbox);                                                                   
                                                                                                    
/*                                                                                                  
            print_registers("Registers Before", regs_before);                                       
            print_registers("Registers After", regs_after);                                         
*/
	    print_reg_changes(regs_before, regs_after);                                             
                                                                                                  
                                                                                                    
        } else {                                                                                    
            printf("Recovered from crash\n");                                                       
        }                                                                                           
    }                                                                                               
    return 0;                                                                                       
}         
