.section .text                                                                                      
.global run_sandbox                                                                                 
                                                                                                    
.extern regs_before                                                                                 
.extern regs_after 
.extern sandbox                                                                                 
                                                                                                    
run_sandbox:                                                                        
    la t6, regs_before                                                                               
                                                                                                    
    sd zero,  0(t6)      # x0 = 0 (hardwired zero)                                                  
    sd ra,    8(t6)      # x1 = ra                                                                  
    sd sp,   16(t6)      # x2 = t6                                                                  
    sd gp,   24(t6)      # x3 = gp                                                                  
    sd tp,   32(t6)      # x4 = tp                                                                  
    sd t0,   40(t6)      # x5 = t0                                                                  
    sd t1,   48(t6)      # x6 = t1                                                                  
   sd t2,   56(t6)      # x7 = t2                                                                   
   sd s0,   64(t6)      # x8 = s0/fp                                                                
   sd s1,   72(t6)      # x9 = s1                                                                   
   sd a0,   80(t6)      # x10 = a0                                                                  
   sd a1,   88(t6)      # x11 = a1                                                                  
   sd a2,   96(t6)      # x12 = a2                                                                  
   sd a3,  104(t6)      # x13 = a3                                                                  
   sd a4,  112(t6)      # x14 = a4                                                                  
   sd a5,  120(t6)      # x15 = a5                                                                  
   sd a6,  128(t6)      # x16 = a6                                                                  
   sd a7,  136(t6)      # x17 = a7                                                                  
   sd s2,  144(t6)      # x18 = s2                                                                  
   sd s3,  152(t6)      # x19 = s3                                                                  
   sd s4,  160(t6)      # x20 = s4                                                                  
   sd s5,  168(t6)      # x21 = s5                                                                  
   sd s6,  176(t6)      # x22 = s6                                                                  
    sd s7,  184(t6)      # x23 = s7                                                                 
    sd s8,  192(t6)      # x24 = s8                                                                 
   sd s9,  200(t6)      # x25 = s9                                                                  
   sd s10, 208(t6)      # x26 = s10                                                                 
   sd s11, 216(t6)      # x27 = s11                                                                 
   sd t3,  224(t6)      # x28 = t3                                                                  
   sd t4,  232(t6)      # x29 = t4                                                                  
   sd t5,  240(t6)      # x30 = t5                                                                  
   sd t6,  248(t6)      # x31 = t6                                                                  
                                                                                                    

                                                                                              
########################################################                                                                                                                                            
    la ra, return_label                                    
                                                                                                    
    # Jump absolutely to sandbox start (jalr zero, 0(s0))                                           
    jalr zero, 4(a0) # offset 4 to skip the first ebreak
                                                                                                    
########################################################                                            
return_label:                                                                                                    
    # After sandbox returns...    
    addi sp, sp, -8
    sd t6, 0(sp)                                                                  
    la t6, regs_after                                                                               
                                                                                                    
    # Save current registers to regs_after                                                          
                                                                                                    
   sd zero,  0(t6)      # x0 = 0                                                                    
   sd ra,    8(t6)                                                                                  
   sd sp,   16(t6)                                                                                  
   sd gp,   24(t6)                                                                                  
   sd tp,   32(t6)                                                                                  
   sd t0,   40(t6)                                                                                  
   sd t1,   48(t6)                                                                                  
   sd t2,   56(t6)                                                                                  
   sd s0,   64(t6)                                                                                  
   sd s1,   72(t6)                                                                                  
   sd a0,   80(t6)                                                                                  
   sd a1,   88(t6)                                                                                  
   sd a2,   96(t6)                                                                                  
   sd a3,  104(t6)                                                                                  
   sd a4,  112(t6)                                                                                  
   sd a5,  120(t6)                                                                                  
   sd a6,  128(t6)                                                                                  
   sd a7,  136(t6)                                                                                  
   sd s2,  144(t6)                                                                                  
   sd s3,  152(t6)                                                                                  
   sd s4,  160(t6)                                                                                  
   sd s5,  168(t6)                                                                                  
   sd s6,  176(t6)                                                                                  
   sd s7,  184(t6)                                                                                  
   sd s8,  192(t6)                                                                                  
   sd s9,  200(t6)                                                                                  
   sd s10, 208(t6)                                                                                  
   sd s11, 216(t6)                                                                                  
   sd t3,  224(t6)                                                                                  
   sd t4,  232(t6)                                                                                  
   sd t5,  240(t6)

    ld t5, 0(sp)          # Temporarily load old t6 into t5
    sd t5, 248(t6)        # Store original t6 (from stack) into offset 248

    addi sp, sp, 8                                                                                  
    #sd t6,  248(t6)                                                                                  
                                                                                                    
##############################################################################                      
                                                                                                    
# Restore registers from regs_before                                                                
   la t6, regs_before                                                                               
                                                                                                    
   ld zero,  0(t6)      # x0 - no effect, can skip or do nop                                        
   ld ra,    8(t6)                                                                                  
   ld sp,   16(t6)                                                                                  
   ld gp,   24(t6)                                                                                  
   ld tp,   32(t6)                                                                                  
   ld t0,   40(t6)                                                                                  
   ld t1,   48(t6)                                                                                  
   ld t2,   56(t6)                                                                                  
   ld s0,   64(t6)                                                                                  
   ld s1,   72(t6)                                                                                  
   ld a0,   80(t6)                                                                                  
   ld a1,   88(t6)                                                                                  
   ld a2,   96(t6)                                                                                  
   ld a3,  104(t6)                                                                                  
   ld a4,  112(t6)                                                                                  
   ld a5,  120(t6)                                                                                  
   ld a6,  128(t6)                                                                                  
   ld a7,  136(t6)                                                                                  
   ld s2,  144(t6)                                                                                  
   ld s3,  152(t6)                                                                                  
   ld s4,  160(t6)                                                                                  
   ld s5,  168(t6)                                                                                  
   ld s6,  176(t6)                                                                                  
   ld s7,  184(t6)                                                                                  
   ld s8,  192(t6)                                                                                  
   ld s9,  200(t6)                                                                                  
   ld s10, 208(t6)                                                                                  
   ld s11, 216(t6)                                                                                  
   ld t3,  224(t6)                                                                                  
   ld t4,  232(t6)                                                                                  
   ld t5,  240(t6)                                                                                  
   ld t6,  248(t6)                                                                                  
                                                                                                    
   ret   
