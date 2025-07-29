    .section .text
    .global  run_sandbox

    .extern  regs_before
    .extern  regs_after
    .extern  sandbox

run_sandbox:

# preset registers to set up environment
    li       zero, 0x0000000000000000      # x0 = 0 (hardwired zero)
#    li       ra, 0x000000000008b9fc        # x1 = ra
#    li       sp, 0x0000003fbe31b180       # x2 = sp
#    li       gp, 0x0000003fffe39508       # x3 = gp
#    li       tp, 0x0000000000000040       # x4 = tp
    li       t0, 0x203a32207a7a7566       # x5 = t0
    li       t1, 0x0000003fffe39508       # x6 = t1
    li       t2, 0x0000000000000001       # x7 = t2
#    li       s0, 0x00000000ffffffff       # x8 = s0/fp
    li       s1, 0xffffffffffffffff       # x9 = s1
#    li       a0, 0x0000003fffa63d00       # x10 = a0
    li       a1, 0x0000003fffe39518       # x11 = a1
    li       a2, 0x00000000000814d8       # x12 = a2
    li       a3, 0x0000002accf8b048      # x13 = a3
    li       a4, 0x0000003fffe39400      # x14 = a4
    li       a5, 0x00000000000627c8      # x15 = a5
    li       a6, 0x000000000004f246      # x16 = a6
    li       a7, 0x0000000000000000      # x17 = a7
    li       s2, 0x0000000000000000      # x18 = s2
    li       s3, 0x000000000006cdc0      # x19 = s3
    li       s4, 0x000000000008e180      # x20 = s4
    li       s5, 0x000000000006cdc0      # x21 = s5
    li       s6, 0x0000000000084750      # x22 = s6
    li       s7, 0x0000000000086a00      # x23 = s7
    li       s8, 0x0000003fffe39408      # x24 = s8
    li       s9, 0x00000000000814d8      # x25 = s9
    li       s10, 0x000000000004f246     # x26 = s10
    li       s11, 0x0000003fd4687d70     # x27 = s11
    li       t3, 0xffffffffffffffff      # x28 = t3
    li       t4, 0x000000000004ecd4      # x29 = t4
    li       t5, 0x0000000000000001      # x30 = t5
    li       t6, 0x0000003fffe39408      # x31 = t6

########################################################
    
    la       t6, regs_before

    sd       zero, 0(t6)      # x0 = 0 (hardwired zero)
    sd       ra, 8(t6)        # x1 = ra
    sd       sp, 16(t6)       # x2 = t6
    sd       gp, 24(t6)       # x3 = gp
    sd       tp, 32(t6)       # x4 = tp
    sd       t0, 40(t6)       # x5 = t0
    sd       t1, 48(t6)       # x6 = t1
    sd       t2, 56(t6)       # x7 = t2
    sd       s0, 64(t6)       # x8 = s0/fp
    sd       s1, 72(t6)       # x9 = s1
    sd       a0, 80(t6)       # x10 = a0
    sd       a1, 88(t6)       # x11 = a1
    sd       a2, 96(t6)       # x12 = a2
    sd       a3, 104(t6)      # x13 = a3
    sd       a4, 112(t6)      # x14 = a4
    sd       a5, 120(t6)      # x15 = a5
    sd       a6, 128(t6)      # x16 = a6
    sd       a7, 136(t6)      # x17 = a7
    sd       s2, 144(t6)      # x18 = s2
    sd       s3, 152(t6)      # x19 = s3
    sd       s4, 160(t6)      # x20 = s4
    sd       s5, 168(t6)      # x21 = s5
    sd       s6, 176(t6)      # x22 = s6
    sd       s7, 184(t6)      # x23 = s7
    sd       s8, 192(t6)      # x24 = s8
    sd       s9, 200(t6)      # x25 = s9
    sd       s10, 208(t6)     # x26 = s10
    sd       s11, 216(t6)     # x27 = s11
    sd       t3, 224(t6)      # x28 = t3
    sd       t4, 232(t6)      # x29 = t4
    sd       t5, 240(t6)      # x30 = t5
    sd       t6, 248(t6)      # x31 = t6



########################################################
    la       ra, return_label

# Jump absolutely to sandbox start (jalr zero, 0(s0))
    jalr     zero, 4(a0)      # offset 4 to skip the first ebreak

########################################################
return_label:
# After sandbox returns...
    addi     sp, sp, -8
    sd       t6, 0(sp)
    la       t6, regs_after

# Save current registers to regs_after

    sd       zero, 0(t6)      # x0 = 0
    sd       ra, 8(t6)
    sd       sp, 16(t6)
    sd       gp, 24(t6)
    sd       tp, 32(t6)
    sd       t0, 40(t6)
    sd       t1, 48(t6)
    sd       t2, 56(t6)
    sd       s0, 64(t6)
    sd       s1, 72(t6)
    sd       a0, 80(t6)
    sd       a1, 88(t6)
    sd       a2, 96(t6)
    sd       a3, 104(t6)
    sd       a4, 112(t6)
    sd       a5, 120(t6)
    sd       a6, 128(t6)
    sd       a7, 136(t6)
    sd       s2, 144(t6)
    sd       s3, 152(t6)
    sd       s4, 160(t6)
    sd       s5, 168(t6)
    sd       s6, 176(t6)
    sd       s7, 184(t6)
    sd       s8, 192(t6)
    sd       s9, 200(t6)
    sd       s10, 208(t6)
    sd       s11, 216(t6)
    sd       t3, 224(t6)
    sd       t4, 232(t6)
    sd       t5, 240(t6)

    ld       t5, 0(sp)        # Temporarily load old t6 into t5
    sd       t5, 248(t6)      # Store original t6 (from stack) into offset 248

    addi     sp, sp, 8
#sd t6, 248(t6)

##############################################################################


# Restore registers from regs_before
    la       t6, regs_before

    ld       zero, 0(t6)      # x0 - no effect, can skip or do nop
    ld       ra, 8(t6)
    ld       sp, 16(t6)
    ld       gp, 24(t6)
    ld       tp, 32(t6)
    ld       t0, 40(t6)
    ld       t1, 48(t6)
    ld       t2, 56(t6)
    ld       s0, 64(t6)
    ld       s1, 72(t6)
    ld       a0, 80(t6)
    ld       a1, 88(t6)
    ld       a2, 96(t6)
    ld       a3, 104(t6)
    ld       a4, 112(t6)
    ld       a5, 120(t6)
    ld       a6, 128(t6)
    ld       a7, 136(t6)
    ld       s2, 144(t6)
    ld       s3, 152(t6)
    ld       s4, 160(t6)
    ld       s5, 168(t6)
    ld       s6, 176(t6)
    ld       s7, 184(t6)
    ld       s8, 192(t6)
    ld       s9, 200(t6)
    ld       s10, 208(t6)
    ld       s11, 216(t6)
    ld       t3, 224(t6)
    ld       t4, 232(t6)
    ld       t5, 240(t6)
    ld       t6, 248(t6)

    ret
