	.text
	.global run_sandbox
	.global temp_storage
	.global xreg_init_data
	.global freg_init_data
	.global xreg_output_data
	.global freg_output_data

	.extern sandbox_ptr

run_sandbox:

# saves important registers to restore at the end
	la      s1, temp_storage
	sd      ra, 0(s1)
	sd      sp, 8(s1)
	sd      gp, 16(s1)
	sd      tp, 24(s1)
	sd      fp, 32 (s1)

##############################################################

# preset registers to set up environment
freg_init:
freg_s_init:
	la      s1, freg_init_data

	flw     f2, 16(s1)
	flw     f3, 24(s1)
	flw     f4, 32(s1)
	flw     f5, 40(s1)
	flw     f6, 48(s1)
	flw     f7, 56(s1)
	flw     f8, 64(s1)
	flw     f10, 80(s1)
	flw     f13, 104(s1)
	flw     f14, 112(s1)
	flw     f15, 120(s1)
	flw     f16, 128(s1)
	flw     f17, 136(s1)
	flw     f20, 160(s1)
	flw     f22, 176(s1)
	flw     f25, 200(s1)
	flw     f29, 232(s1)
	flw     f30, 240(s1)

freg_d_init:
	fld     f0, 0(s1)
	fld     f1, 8(s1)
	fld     f9, 72(s1)
	fld     f11, 88(s1)
	fld     f12, 96(s1)
	fld     f18, 144(s1)
	fld     f19, 152(s1)
	fld     f21, 168(s1)
	fld     f23, 184(s1)
	fld     f24, 192(s1)
	fld     f26, 208(s1)
	fld     f27, 216(s1)
	fld     f28, 224(s1)
	fld     f31, 248(s1)

xreg_init:
	la      s1, xreg_init_data

	ld      x0, 0(s1)
	ld      ra, 8(s1)
	ld      sp, 16(s1)
	ld      gp, 24(s1)
	ld      tp, 32(s1)
	ld      t0, 40(s1)
	ld      t1, 48(s1)
	ld      t2, 56(s1)
	ld      s0, 64(s1)
# ld s1, 72(s1)
	ld      a0, 80(s1) // x8 - s0/fp
	ld      a1, 88(s1)
	ld      a2, 96(s1)
	ld      a3, 104(s1)
	ld      a4, 112(s1)
	ld      a5, 120(s1)
	ld      a6, 128(s1)
	ld      a7, 136(s1)
	ld      s2, 144(s1)
	ld      s3, 152(s1)
	ld      s4, 160(s1)
	ld      s5, 168(s1)
	ld      s6, 176(s1)
	ld      s7, 184(s1)
	ld      s8, 192(s1)
	ld      s9, 200(s1)
	ld      s10, 208(s1)
	ld      s11, 216(s1)
	ld      t3, 224(s1)
	ld      t4, 232(s1)
	ld      t5, 240(s1)
	ld      t6, 248(s1)

########################################################

# load address of sandbox_ptr to s1
	la      s1, sandbox_ptr
	ld      s1, 0(s1)

# Jump absolutely to sandbox start
# (skipping 0x00000000 and ebreak instructions in front)
# 0x20 (start offset) == 32
	jalr    s1, 32(s1)

########################################################

return_label:
# After sandbox returns...
# save register values to xreg_output_data and freg_output_data
reg_dump:
	la      s1, xreg_output_data
	sd      x0, 0(s1)
	sd      x2, 8(s1)
	sd      x2, 16(s1)
	sd      x3, 24(s1)
	sd      x4, 32(s1)
	sd      x5, 40(s1)
	sd      x6, 48(s1)
	sd      x7, 56(s1)
	sd      x8, 64(s1)
	sd      x9, 72(s1)
	sd      x10, 80(s1)
	sd      x11, 88(s1)
	sd      x12, 96(s1)
	sd      x13, 104(s1)
	sd      x14, 112(s1)
	sd      x15, 120(s1)
	sd      x16, 128(s1)
	sd      x17, 136(s1)
	sd      x18, 144(s1)
	sd      x19, 152(s1)
	sd      x20, 160(s1)
	sd      x21, 168(s1)
	sd      x22, 176(s1)
	sd      x23, 184(s1)
	sd      x24, 192(s1)
	sd      x25, 200(s1)
	sd      x26, 208(s1)
	sd      x27, 216(s1)
	sd      x28, 224(s1)
	sd      x29, 232(s1)
	sd      x30, 240(s1)
	sd      x31, 248(s1)

freg_save:
	la      s1, freg_output_data
	fsw     f2, 16(s1)
	fsw     f3, 24(s1)
	fsw     f4, 32(s1)
	fsw     f5, 40(s1)
	fsw     f6, 48(s1)
	fsw     f7, 56(s1)
	fsw     f8, 64(s1)
	fsw     f10, 80(s1)
	fsw     f13, 104(s1)
	fsw     f14, 112(s1)
	fsw     f15, 120(s1)
	fsw     f16, 128(s1)
	fsw     f17, 136(s1)
	fsw     f20, 160(s1)
	fsw     f22, 176(s1)
	fsw     f25, 200(s1)
	fsw     f29, 232(s1)
	fsw     f30, 240(s1)

	la      s1, freg_output_data
	fsd     f0, 0(s1)
	fsd     f1, 8(s1)
	fsd     f9, 72(s1)
	fsd     f11, 88(s1)
	fsd     f12, 96(s1)
	fsd     f18, 144(s1)
	fsd     f19, 152(s1)
	fsd     f21, 168(s1)
	fsd     f23, 184(s1)
	fsd     f24, 192(s1)
	fsd     f26, 208(s1)
	fsd     f27, 216(s1)
	fsd     f28, 224(s1)
	fsd     f31, 248(s1)

#################################################################

# Restore important registers to prevent crash
	la      s1, temp_storage
	ld      ra, 0(s1)
	ld      sp, 8(s1)
	ld      gp, 16(s1)
	ld      tp, 24(s1)
	ld      fp, 32 (s1)

	ret
#################################################################
	.data

hidden_data:
	.align  8
xreg_init_data:
reg_x0_init:
	.dword  0x0000000000000000
reg_x1_init:
	.dword  0xf045bfd112f01034
reg_x2_init:
	.dword  0x4030112c8b28dedf
reg_x3_init:
	.dword  0xd5c1e2fb3cfa9478
reg_x4_init:
	.dword  0x00000000000f0005
reg_x5_init:
	.dword  0x2f1ef2878a4061f2
reg_x6_init:
	.dword  0xd081eac10119e7bb
reg_x7_init:
	.dword  0xf71b2c213b634e1f
reg_x8_init:
	.dword  0xffffffffffffffff
reg_x9_init:
	.dword  0x0000000000000000
reg_x10_init:
	.dword  0xeb25c2dc1baf2109
reg_x11_init:
	.dword  0xffffffffffffffff
reg_x12_init:
	.dword  0x3684f30b4a7bd296
reg_x13_init:
	.dword  0xc6e26af78413e5e3
reg_x14_init:
	.dword  0x67ffe336dab40344
reg_x15_init:
	.dword  0xffffffff80000000
reg_x16_init:
	.dword  0xe15d72430a808d01
reg_x17_init:
	.dword  0xffffffffffffffff
reg_x18_init:
	.dword  0xbf059713fff21466
reg_x19_init:
	.dword  0x9fadd2fb99a2d49f
reg_x20_init:
	.dword  0x0000000000000000
reg_x21_init:
	.dword  0x0000000000000000
reg_x22_init:
	.dword  0xffffffffffffff83
reg_x23_init:
	.dword  0xffffffffffffff89
reg_x24_init:
	.dword  0x00000000002f0508
reg_x25_init:
	.dword  0xffffffff80000008
reg_x26_init:
	.dword  0x0000000000000000
reg_x27_init:
	.dword  0xffffffffffffffff
reg_x28_init:
	.dword  0xffffffffffffff81
reg_x29_init:
	.dword  0xffffffffffffffff
reg_x30_init:
	.dword  0xe06e046a2ea1534d
reg_x31_init:
	.dword  0x1142ddc2cc63c27e

	.align  8
freg_init_data:
reg_f0_init:
	.dword  0x0800000000000001
reg_f1_init:
	.dword  0xd8986f418f85eb19
reg_f2_init:
	.dword  0x74b3977385b267fd
reg_f3_init:
	.dword  0xb8092bb3cafdea73
reg_f4_init:
	.dword  0x0000000000000001
reg_f5_init:
	.dword  0x489e03954350cb80
reg_f6_init:
	.dword  0xb8912e1ade5ff3cd
reg_f7_init:
	.dword  0x27ca1d145b08a7be
reg_f8_init:
	.dword  0xffffffff80000003
reg_f9_init:
	.dword  0xc4f37893da038603
reg_f10_init:
	.dword  0x0da567778ba48f39
reg_f11_init:
	.dword  0x0800000000000007
reg_f12_init:
	.dword  0x2c0120da9d457e2f
reg_f13_init:
	.dword  0x0000000000000000
reg_f14_init:
	.dword  0x0000000000000000
reg_f15_init:
	.dword  0x0800000000000006
reg_f16_init:
	.dword  0x0c6cd25bf8dd32a5
reg_f17_init:
	.dword  0x7fe92f0d96e9cb5a
reg_f18_init:
	.dword  0x1e6d935acb7b0b56
reg_f19_init:
	.dword  0xc925177a790671d8
reg_f20_init:
	.dword  0xc29b73b407a253b6
reg_f21_init:
	.dword  0xffffffffffff8004
reg_f22_init:
	.dword  0xffffffffffffffff
reg_f23_init:
	.dword  0xffffffffffffff81
reg_f24_init:
	.dword  0x0000000000000000
reg_f25_init:
	.dword  0x0000000000000000
reg_f26_init:
	.dword  0x1e3060b94b9951a9
reg_f27_init:
	.dword  0x4bb03d2aa911120c
reg_f28_init:
	.dword  0x0000000000000002
reg_f29_init:
	.dword  0xffffffff80000008
reg_f30_init:
	.dword  0xffffffffffff8008
reg_f31_init:
	.dword  0x5ee8301b4d8fc709

#RVTEST_DATA_BEGIN

	.align  8
xreg_output_data:
reg_x0_output:
	.dword  0xcc0cc0f2fb1da24f
reg_x1_output:
	.dword  0xb8ee4e5cd912e6b9
reg_x2_output:
	.dword  0x3b17c0671a73d71c
reg_x3_output:
	.dword  0x2f095caa184fd077
reg_x4_output:
	.dword  0x5117d99573ca5da5
reg_x5_output:
	.dword  0x2215f96f49c5ecff
reg_x6_output:
	.dword  0xdedf7c5d847caa4e
reg_x7_output:
	.dword  0xe3964edc539167fe
reg_x8_output:
	.dword  0xc437697ae55700a3
reg_x9_output:
	.dword  0x30f417ed5882e255
reg_x10_output:
	.dword  0xfb02a0ad00d59778
reg_x11_output:
	.dword  0x100b5bb9cceeacd8
reg_x12_output:
	.dword  0xc6f67e388def5b50
reg_x13_output:
	.dword  0x2e550a0bf4ee6b52
reg_x14_output:
	.dword  0x2fb2bb92dadff302
reg_x15_output:
	.dword  0xb8464d3282eb63cc
reg_x16_output:
	.dword  0xcf8c4758c47aea99
reg_x17_output:
	.dword  0xa272a515ade7fe0e
reg_x18_output:
	.dword  0x5f1928825acc287c
reg_x19_output:
	.dword  0x204c1f8a39633766
reg_x20_output:
	.dword  0x1bbae0d7396810ce
reg_x21_output:
	.dword  0x963e41e765190ea7
reg_x22_output:
	.dword  0xc94802a0b30ffb17
reg_x23_output:
	.dword  0x9b9577d7ad8f2c74
reg_x24_output:
	.dword  0x23cceda33375de23
reg_x25_output:
	.dword  0x956e1b734f8d4bbe
reg_x26_output:
	.dword  0xd966e749e134562a
reg_x27_output:
	.dword  0x64036a890495268a
reg_x28_output:
	.dword  0xc4bc022233be6930
reg_x29_output:
	.dword  0x6867fd3dd565eaf7
reg_x30_output:
	.dword  0x01c5888c1f5cadae
reg_x31_output:
	.dword  0x873691dad5d37c7f

	.align  8
freg_output_data:
reg_f0_output:
	.dword  0x6fc9deadd283b772
reg_f1_output:
	.dword  0x866341e252fa057c
reg_f2_output:
	.dword  0x4fbe0faa0e29eec3
reg_f3_output:
	.dword  0x56427462665a9cee
reg_f4_output:
	.dword  0x6d167a10948135c8
reg_f5_output:
	.dword  0x315c218cf5f6047b
reg_f6_output:
	.dword  0xd3914f9950db0029
reg_f7_output:
	.dword  0x88f73b872746c2b6
reg_f8_output:
	.dword  0xa5fcdc0deec3c0f6
reg_f9_output:
	.dword  0x06b2507ff14c1da3
reg_f10_output:
	.dword  0x93a6c785efccd2c8
reg_f11_output:
	.dword  0x733bba044cebb97b
reg_f12_output:
	.dword  0x7b40c7d7ad4a3e25
reg_f13_output:
	.dword  0x908ced910b07dfab
reg_f14_output:
	.dword  0x85da754e77bc0228
reg_f15_output:
	.dword  0x4031c2696104b222
reg_f16_output:
	.dword  0xe257369976f0c361
reg_f17_output:
	.dword  0x0d5dc0aa1756cecc
reg_f18_output:
	.dword  0xf4c27805766a04f9
reg_f19_output:
	.dword  0x241ecd9b065a2759
reg_f20_output:
	.dword  0x6453a1ed3768501a
reg_f21_output:
	.dword  0x341dc9474c581142
reg_f22_output:
	.dword  0xca16826fa787ed8d
reg_f23_output:
	.dword  0xdb52f14fc08fd20c
reg_f24_output:
	.dword  0xa0441e63ce3d15a4
reg_f25_output:
	.dword  0x351d1cfc7a852bce
reg_f26_output:
	.dword  0x72a31d89df08ba59
reg_f27_output:
	.dword  0x99882693770cadf1
reg_f28_output:
	.dword  0xa2064602802d4fb7
reg_f29_output:
	.dword  0x988015ed1dc5ce37
reg_f30_output:
	.dword  0x7372bb02803d3678
reg_f31_output:
	.dword  0xc273e045962f0dfe

	.align  8
temp_storage:
reg_ra_output:
	.dword  0xb8ee4e5cd912e6b9
reg_sp_output:
	.dword  0x3b17c0671a73d71c
reg_gp_output:
	.dword  0x2f095caa184fd077
reg_tp_output:
	.dword  0x5117d99573ca5da5
reg_fp_output:
	.dword  0x2215f96f49c5ecff