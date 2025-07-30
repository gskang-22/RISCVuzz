    .section .text
    .global test_start
    .extern regs_before
    .extern regs_after
    .extern sandbox


test_start:

freg_init:
freg_s_init:
	la x1, freg_init_data
	flw f2, 16(x1)
	flw f3, 24(x1)
	flw f4, 32(x1)
	flw f5, 40(x1)
	flw f6, 48(x1)
	flw f7, 56(x1)
	flw f8, 64(x1)
	flw f10, 80(x1)
	flw f13, 104(x1)
	flw f14, 112(x1)
	flw f15, 120(x1)
	flw f16, 128(x1)
	flw f17, 136(x1)
	flw f20, 160(x1)
	flw f22, 176(x1)
	flw f25, 200(x1)
	flw f29, 232(x1)
	flw f30, 240(x1)

freg_d_init:
	la x1, freg_init_data
	fld f0, 0(x1)
	fld f1, 8(x1)
	fld f9, 72(x1)
	fld f11, 88(x1)
	fld f12, 96(x1)
	fld f18, 144(x1)
	fld f19, 152(x1)
	fld f21, 168(x1)
	fld f23, 184(x1)
	fld f24, 192(x1)
	fld f26, 208(x1)
	fld f27, 216(x1)
	fld f28, 224(x1)
	fld f31, 248(x1)


xreg_init:
	la x31, xreg_init_data
	ld x0, 0(x31)
	ld x1, 8(x31)
	ld x2, 16(x31)
	ld x3, 24(x31)
	ld x4, 32(x31)
	ld x5, 40(x31)
	ld x6, 48(x31)
	ld x7, 56(x31)
	ld x8, 64(x31)
	ld x9, 72(x31)
	ld x10, 80(x31)
	ld x11, 88(x31)
	ld x12, 96(x31)
	ld x13, 104(x31)
	ld x14, 112(x31)
	ld x15, 120(x31)
	ld x16, 128(x31)
	ld x17, 136(x31)
	ld x18, 144(x31)
	ld x19, 152(x31)
	ld x20, 160(x31)
	ld x21, 168(x31)
	ld x22, 176(x31)
	ld x23, 184(x31)
	ld x24, 192(x31)
	ld x25, 200(x31)
	ld x26, 208(x31)
	ld x27, 216(x31)
	ld x28, 224(x31)
	ld x29, 232(x31)
	ld x30, 240(x31)
	ld x31, 248(x31)

	j pseg_0

pseg_0:
	addi x16, x0, -1502
	j reg_dump

reg_dump:
	la x1, xreg_output_data
	sd x0, 0(x1)
	sd x2, 16(x1)
	sd x3, 24(x1)
	sd x4, 32(x1)
	sd x5, 40(x1)
	sd x6, 48(x1)
	sd x7, 56(x1)
	sd x8, 64(x1)
	sd x9, 72(x1)
	sd x10, 80(x1)
	sd x11, 88(x1)
	sd x12, 96(x1)
	sd x13, 104(x1)
	sd x14, 112(x1)
	sd x15, 120(x1)
	sd x16, 128(x1)
	sd x17, 136(x1)
	sd x18, 144(x1)
	sd x19, 152(x1)
	sd x20, 160(x1)
	sd x21, 168(x1)
	sd x22, 176(x1)
	sd x23, 184(x1)
	sd x24, 192(x1)
	sd x25, 200(x1)
	sd x26, 208(x1)
	sd x27, 216(x1)
	sd x28, 224(x1)
	sd x29, 232(x1)
	sd x30, 240(x1)
	sd x31, 248(x1)

freg_save:
	la x1, freg_output_data
	fsw f2, 16(x1)
	fsw f3, 24(x1)
	fsw f4, 32(x1)
	fsw f5, 40(x1)
	fsw f6, 48(x1)
	fsw f7, 56(x1)
	fsw f8, 64(x1)
	fsw f10, 80(x1)
	fsw f13, 104(x1)
	fsw f14, 112(x1)
	fsw f15, 120(x1)
	fsw f16, 128(x1)
	fsw f17, 136(x1)
	fsw f20, 160(x1)
	fsw f22, 176(x1)
	fsw f25, 200(x1)
	fsw f29, 232(x1)
	fsw f30, 240(x1)

	la x1, freg_output_data
	fsd f0, 0(x1)
	fsd f1, 8(x1)
	fsd f9, 72(x1)
	fsd f11, 88(x1)
	fsd f12, 96(x1)
	fsd f18, 144(x1)
	fsd f19, 152(x1)
	fsd f21, 168(x1)
	fsd f23, 184(x1)
	fsd f24, 192(x1)
	fsd f26, 208(x1)
	fsd f27, 216(x1)
	fsd f28, 224(x1)
	fsd f31, 248(x1)


	j test_end

crash_forward:
#	RVTEST_FAIL

test_end:
#	RVTEST_PASS

#RVTEST_CODE_END


	.data

hidden_data:
	.align 8
xreg_init_data:
reg_x0_init:	.dword 0xd8b2fb3fc35cd94a
reg_x1_init:	.dword 0xf045bfd112f01034
reg_x2_init:	.dword 0x4030112c8b28dedf
reg_x3_init:	.dword 0xd5c1e2fb3cfa9478
reg_x4_init:	.dword 0x0000000000000005
reg_x5_init:	.dword 0x2f1ef2878a4061f2
reg_x6_init:	.dword 0xd081eac10119e7bb
reg_x7_init:	.dword 0xf71b2c213b634e1f
reg_x8_init:	.dword 0xffffffffffffffff
reg_x9_init:	.dword 0x0000000000000000
reg_x10_init:	.dword 0xeb25c2dc1baf2109
reg_x11_init:	.dword 0xffffffffffffffff
reg_x12_init:	.dword 0x3684f30b4a7bd296
reg_x13_init:	.dword 0xc6e26af78413e5e3
reg_x14_init:	.dword 0x67ffe336dab40344
reg_x15_init:	.dword 0xffffffff80000000
reg_x16_init:	.dword 0xe15d72430a808d01
reg_x17_init:	.dword 0xffffffffffffffff
reg_x18_init:	.dword 0xbf059713fff21466
reg_x19_init:	.dword 0x9fadd2fb99a2d49f
reg_x20_init:	.dword 0x0000000000000000
reg_x21_init:	.dword 0x0000000000000000
reg_x22_init:	.dword 0xffffffffffffff83
reg_x23_init:	.dword 0xffffffffffffff89
reg_x24_init:	.dword 0xffffffffffffffef
reg_x25_init:	.dword 0xffffffff80000009
reg_x26_init:	.dword 0x0000000000000000
reg_x27_init:	.dword 0xffffffffffffffff
reg_x28_init:	.dword 0xffffffffffffff81
reg_x29_init:	.dword 0xffffffffffffffff
reg_x30_init:	.dword 0xe06e046a2ea1534d
reg_x31_init:	.dword 0x1142ddc2cc63c27e

	.align 8
freg_init_data:
reg_f0_init:	.dword 0x0800000000000001
reg_f1_init:	.dword 0xd8986f418f85eb19
reg_f2_init:	.dword 0x74b3977385b267fd
reg_f3_init:	.dword 0xb8092bb3cafdea73
reg_f4_init:	.dword 0x0000000000000001
reg_f5_init:	.dword 0x489e03954350cb80
reg_f6_init:	.dword 0xb8912e1ade5ff3cd
reg_f7_init:	.dword 0x27ca1d145b08a7be
reg_f8_init:	.dword 0xffffffff80000003
reg_f9_init:	.dword 0xc4f37893da038603
reg_f10_init:	.dword 0x0da567778ba48f39
reg_f11_init:	.dword 0x0800000000000007
reg_f12_init:	.dword 0x2c0120da9d457e2f
reg_f13_init:	.dword 0x0000000000000000
reg_f14_init:	.dword 0x0000000000000000
reg_f15_init:	.dword 0x0800000000000006
reg_f16_init:	.dword 0x0c6cd25bf8dd32a5
reg_f17_init:	.dword 0x7fe92f0d96e9cb5a
reg_f18_init:	.dword 0x1e6d935acb7b0b56
reg_f19_init:	.dword 0xc925177a790671d8
reg_f20_init:	.dword 0xc29b73b407a253b6
reg_f21_init:	.dword 0xffffffffffff8004
reg_f22_init:	.dword 0xffffffffffffffff
reg_f23_init:	.dword 0xffffffffffffff81
reg_f24_init:	.dword 0x0000000000000000
reg_f25_init:	.dword 0x0000000000000000
reg_f26_init:	.dword 0x1e3060b94b9951a9
reg_f27_init:	.dword 0x4bb03d2aa911120c
reg_f28_init:	.dword 0x0000000000000002
reg_f29_init:	.dword 0xffffffff80000008
reg_f30_init:	.dword 0xffffffffffff8008
reg_f31_init:	.dword 0x5ee8301b4d8fc709

#RVTEST_DATA_BEGIN

	.align 8
xreg_output_data:
reg_x0_output:	.dword 0xcc0cc0f2fb1da24f
reg_x1_output:	.dword 0xb8ee4e5cd912e6b9
reg_x2_output:	.dword 0x3b17c0671a73d71c
reg_x3_output:	.dword 0x2f095caa184fd077
reg_x4_output:	.dword 0x5117d99573ca5da5
reg_x5_output:	.dword 0x2215f96f49c5ecff
reg_x6_output:	.dword 0xdedf7c5d847caa4e
reg_x7_output:	.dword 0xe3964edc539167fe
reg_x8_output:	.dword 0xc437697ae55700a3
reg_x9_output:	.dword 0x30f417ed5882e255
reg_x10_output:	.dword 0xfb02a0ad00d59778
reg_x11_output:	.dword 0x100b5bb9cceeacd8
reg_x12_output:	.dword 0xc6f67e388def5b50
reg_x13_output:	.dword 0x2e550a0bf4ee6b52
reg_x14_output:	.dword 0x2fb2bb92dadff302
reg_x15_output:	.dword 0xb8464d3282eb63cc
reg_x16_output:	.dword 0xcf8c4758c47aea99
reg_x17_output:	.dword 0xa272a515ade7fe0e
reg_x18_output:	.dword 0x5f1928825acc287c
reg_x19_output:	.dword 0x204c1f8a39633766
reg_x20_output:	.dword 0x1bbae0d7396810ce
reg_x21_output:	.dword 0x963e41e765190ea7
reg_x22_output:	.dword 0xc94802a0b30ffb17
reg_x23_output:	.dword 0x9b9577d7ad8f2c74
reg_x24_output:	.dword 0x23cceda33375de23
reg_x25_output:	.dword 0x956e1b734f8d4bbe
reg_x26_output:	.dword 0xd966e749e134562a
reg_x27_output:	.dword 0x64036a890495268a
reg_x28_output:	.dword 0xc4bc022233be6930
reg_x29_output:	.dword 0x6867fd3dd565eaf7
reg_x30_output:	.dword 0x01c5888c1f5cadae
reg_x31_output:	.dword 0x873691dad5d37c7f

	.align 8
freg_output_data:
reg_f0_output:	.dword 0x6fc9deadd283b772
reg_f1_output:	.dword 0x866341e252fa057c
reg_f2_output:	.dword 0x4fbe0faa0e29eec3
reg_f3_output:	.dword 0x56427462665a9cee
reg_f4_output:	.dword 0x6d167a10948135c8
reg_f5_output:	.dword 0x315c218cf5f6047b
reg_f6_output:	.dword 0xd3914f9950db0029
reg_f7_output:	.dword 0x88f73b872746c2b6
reg_f8_output:	.dword 0xa5fcdc0deec3c0f6
reg_f9_output:	.dword 0x06b2507ff14c1da3
reg_f10_output:	.dword 0x93a6c785efccd2c8
reg_f11_output:	.dword 0x733bba044cebb97b
reg_f12_output:	.dword 0x7b40c7d7ad4a3e25
reg_f13_output:	.dword 0x908ced910b07dfab
reg_f14_output:	.dword 0x85da754e77bc0228
reg_f15_output:	.dword 0x4031c2696104b222
reg_f16_output:	.dword 0xe257369976f0c361
reg_f17_output:	.dword 0x0d5dc0aa1756cecc
reg_f18_output:	.dword 0xf4c27805766a04f9
reg_f19_output:	.dword 0x241ecd9b065a2759
reg_f20_output:	.dword 0x6453a1ed3768501a
reg_f21_output:	.dword 0x341dc9474c581142
reg_f22_output:	.dword 0xca16826fa787ed8d
reg_f23_output:	.dword 0xdb52f14fc08fd20c
reg_f24_output:	.dword 0xa0441e63ce3d15a4
reg_f25_output:	.dword 0x351d1cfc7a852bce
reg_f26_output:	.dword 0x72a31d89df08ba59
reg_f27_output:	.dword 0x99882693770cadf1
reg_f28_output:	.dword 0xa2064602802d4fb7
reg_f29_output:	.dword 0x988015ed1dc5ce37
reg_f30_output:	.dword 0x7372bb02803d3678
reg_f31_output:	.dword 0xc273e045962f0dfe

// Memory Blocks
	.align 8
test_memory:
	.dword 0xb5def2c34e52acef, 0xe4c3d153eb80afc4
	.dword 0x531697bc1b5b6a28, 0x6184f19b263ec0ed
	.dword 0x605ec91084e0474c, 0x28e3fdfefa3b7bc4
	.dword 0x2d396e4b9d539b4a, 0x5c07c49aebcf45bf
	.dword 0xc95d924c89772cb4, 0x9efbfacfdf9bce06
	.dword 0x21e5f97e5814dde6, 0xc62ae09ea9841036
	.dword 0x3816674b2f53776c, 0x9d7d453b29db3f61
	.dword 0xd52b46d10ba334a5, 0x989dc0d8e768dd59
	.dword 0x35aeaad49dd3f6a3, 0xf65537cb6a00822d
	.dword 0x5f08d8f702a14155, 0x41c3facc385017f4
	.dword 0x8ab1d426241e66e8, 0xb49c189c9c6f8ec8
	.dword 0x5ecc9a56472f8569, 0x32b6b4cfd1e94d15
	.dword 0x934c09702ae23aae, 0xe2a777e31da2e013
	.dword 0x604c9f89ef433276, 0x958e6c8f7081b090
	.dword 0x554d8a56d37bf2cf, 0xa399de61811fbff3
	.dword 0x64a6b9e081d68ab8, 0xcfaf0d8aeba0b17c
	.dword 0x5a40ea74b9fb0706, 0x74c9cbf390f7a3d0
	.dword 0x2b6fd9dc8094d18b, 0x5010579594f29eb4
	.dword 0x8f1e1bd3bdcc5e73, 0xdc9a060774689918
	.dword 0xcc7d41b633e3cbf1, 0x6ebc955777335b57
	.dword 0x52644976ab0b581b, 0x259d361d7c6ec1bd
	.dword 0x4db187d4f16cd113, 0xcfffa2cbcf0b2349
	.dword 0x68a481d11cbb6366, 0x061ed84a5d58e0b3
	.dword 0x2377695a37876ab8, 0xd30043c2a40f5fb0
	.dword 0xc6c7314af66c289f, 0x3d6b79b8acb1f673
	.dword 0xf5d46c98222785cf, 0x10bdca5f3c598b77
	.dword 0x00966cc3620a4178, 0x417247275311ed7b
	.dword 0x973d5393f03132eb, 0xd5ac0d99416627ce
	.dword 0xb1570c0854de8183, 0x1099eb6641a756cc
	.dword 0xd5965e888a53f6c2, 0xcd67afbcd12dc0a8
	.dword 0x637a945f3cfdceba, 0x1ce2bddc238c366b
	.dword 0xb1095e663ecfaaae, 0xcd3cb4e962aa013b
	.dword 0x53b3f3009eab89f8, 0x0eb04100f337dfe0
	.dword 0x8f9b974e2fc4ed2c, 0xc77969915938d884
	.dword 0xeaf9079a1770877d, 0xced3f0e5549fe2ba
	.dword 0x37ad731743f3225f, 0x76c798fe5e8fadc1
	.dword 0xf23afecc72e8976d, 0xe0b361a754da0708
	.dword 0xb6ce03cbc406048d, 0x3e0613ca1f30a4f4
	.dword 0x51df7caa3b889e52, 0x96a3adfeb85159e1
	.dword 0xdd8c562b30d4c4a1, 0x0e5c8664d193f367
	.dword 0xa644973d77df3d96, 0x13d435b550e049de
	.dword 0xa43094284934baa8, 0xe2839f9304774423
	.dword 0x11d9a10313120c0a, 0x6062ac26ed61d39b
	.dword 0x9f86f767a841a654, 0x837b86eb8d052c77
	.dword 0x7c96c36ac5995e62, 0x0d7276c7548bbe39
	.dword 0xa8268bc6df3d7f7c, 0xd82aa35b11c6b077
	.dword 0xdfdd695a317c9fb7, 0x08615b9b6523e7df
	.dword 0xf9ddc1d37069d69a, 0xf69eb19f9b90d77a
	.dword 0x550b79a94b913a03, 0x45737fbbe5e2a234
	.dword 0x5c2ed14d9a7cc54b, 0x8aea2acdc9e0509c
	.dword 0x5c4b61a4197e0ea8, 0xdb90b5d6c7941ee7
	.dword 0x5805ebaf76936ed3, 0xecd7faccc455273a
	.dword 0x386aef8c42857eea, 0x03ed1cae9c4aec28
	.dword 0x1a133ea184c41096, 0x6aef86d8c7408778
	.dword 0x4bc2fd15ef580470, 0x31b70d98ceb5812c
	.dword 0x6472c68465b1a2a0, 0xe6830401357692be
	.dword 0x1979e9eafb7159c7, 0x1f245afdb4e8daac
	.dword 0xdd8bf0e729c3081e, 0xd9c21da96dd64437
	.dword 0xedaae62588c232df, 0x3e78dedbf2322766
	.dword 0x1d530f1450dfcfe3, 0x460aec083f396551
	.dword 0x363c0cd89ca8858c, 0x76e05945bbc1849b
	.dword 0x155698844fd484e4, 0xd5f33aaab9be923f
	.dword 0x456d4e878b786206, 0x76359ee07c3fca8f
	.dword 0xd3423d6632c08ebc, 0xb3c41ef0489f4e7a

.align 8

#RVTEST_DATA_END
