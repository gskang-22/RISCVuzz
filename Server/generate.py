import subprocess
import json
import random, time
import ctypes

def call_base_instruction(input_str, node_proc):
    # Send instruction to Node.js
    node_proc.stdin.write(input_str + "\n")
    node_proc.stdin.flush()
    
    # Read one line of JSON response
    output = node_proc.stdout.readline()
    data = json.loads(output)
    
    if 'error' in data:
        raise RuntimeError(data['error'])
    
    return data

def call_thead_instruction(opcode, libthead) -> int:
    result = libthead.encode_thead(opcode.encode("utf-8"))
    return result & 0xffffffff

def call_rust_asm(asm_line: str) -> str:
    # Replace with the path to your compiled Rust binary
    rust_bin = "/home/szekang/Documents/RISCVuzz/Server/rvv-as"
    
    # Call the Rust program with the instruction as an argument
    result = subprocess.run(
        [rust_bin, asm_line],
        capture_output=True,  # Capture stdout and stderr
        text=True             # Return output as string instead of bytes
    )

    if result.returncode != 0:
        print("Rust program failed:", result.stderr)
        return ""
    
    return result.stdout

def flip_bits(inst_word, cfg):
    # With flip_prob chance, flip some bits
    if random.random() >= cfg["FLIP_PROBABILITY"]:
        return inst_word  # no flip

    num_flips = random.randint(1, cfg["MAX_FLIPS"])  # how many bits to flip
    bits_to_flip = random.sample(range(32), num_flips)  # pick unique bit positions
    
    mask = 0
    for bit in bits_to_flip:
        mask |= (1 << bit)
    
    flipped = inst_word ^ mask  # XOR flips the bits
    return flipped

def flip_endian_32(w):
    b0 = (w & 0x000000FF) << 24
    b1 = (w & 0x0000FF00) << 8
    b2 = (w & 0x00FF0000) >> 8
    b3 = (w & 0xFF000000) >> 24
    return (b0 | b1 | b2 | b3) & 0xFFFFFFFF

def check_flip(instructions, result, cfg):
    if random.random() < cfg["FLIP_PROBABILITY"]:
        # randomly flip bits, increasing number and randomness of instructions generated
        result_flipped = flip_bits(result, cfg)
        instructions.append(result_flipped & 0xffffffff)
        # output.append("0x{:08x}".format(result & 0xffffffff))

    if random.random() < cfg["ENDIAN_PROBABILITY"]:
        # flip endianess of instruction
        result_endian = flip_endian_32(result)
        # output.append("0x{:08x}".format(result & 0xffffffff))
        instructions.append(result_endian & 0xffffffff)

BASE_INSTRUCTIONS = [
    "ADD", "SUB", "SLL", "XOR", "SRL", "SRA", "OR", "AND", "ADDI", "XORI",
    "ORI", "ANDI", "ADDIW", "MUL", "MULH", "MULHSU", "MULHU", "DIV", "DIVU", "REM",
    "REMU", "SLLI", "SRLI", "SRAI", "SLLIW", "SRLIW", "SRAIW", "ADDW", "SUBW", "SLLW",
    "SRLW", "SRAW", "MULW", "DIVW", "DIVUW", "REMW", "REMUW", "SLTI", "SLTIU", "SLT",
    "SLTU", "LB", "LH", "LW", "LBU", "LHU", "LWU", "LD", "SB", "SH",
    "SW", "SD", "BEQ", "BNE", "BLT", "BGE", "BLTU", "BGEU", "JAL", "JALR",
    "LUI", "AUIPC", "FENCE", "ECALL", "EBREAK", "AMOSWAP.W", "AMOADD.W", "AMOXOR.W", "AMOAND.W", "AMOOR.W",
    "AMOMIN.W", "AMOMAX.W", "AMOMINU.W", "AMOMAXU.W", "AMOADD.D", "AMOSWAP.D", "AMOXOR.D", "AMOAND.D", "AMOOR.D", "AMOMIN.D",
    "AMOMAX.D", "AMOMINU.D", "AMOMAXU.D", "FADD.S", "FSUB.S", "FMUL.S", "FDIV.S", "FADD.D", "FSUB.D", "FMUL.D",
    "FDIV.D", "FLW", "FLD", "FSW", "FSD", "FSQRT.S", "FMIN.S", "FMAX.S", "FSGNJ.S", "FSGNJN.S",
    "FSGNJX.S", "FSQRT.D", "FMIN.D", "FMAX.D", "FSGNJ.D", "FSGNJN.D", "FSGNJX.D",
]

VECTOR_INSTRUCTIONS = [
    # "vaadd.vv", "vaadd.vx", "vaaddu.vv", "vaaddu.vx", "vadc.vim", "vadc.vvm", "vadc.vxm", "vadd.vi", "vadd.vv", "vadd.vx",
    # "vand.vi", "vand.vv", "vand.vx", "vasub.vv", "vasub.vx", "vasubu.vv", "vasubu.vx", "vcompress.vm", "vcpop.m", "vdiv.vv",
    # "vdiv.vx", "vdivu.vv", "vdivu.vx", "vfadd.vf", "vfadd.vv", "vfclass.v", "vfcvt.f.x.v", "vfcvt.f.xu.v", "vfcvt.rtz.x.f.v", "vfcvt.rtz.xu.f.v",
    # "vfcvt.x.f.v", "vfcvt.xu.f.v", "vfdiv.vf", "vfdiv.vv", "vfirst.m", "vfmacc.vf", "vfmacc.vv", "vfmadd.vf", "vfmadd.vv", "vfmax.vf",
    # "vfmax.vv", "vfmerge.vfm", "vfmin.vf", "vfmin.vv", "vfmsac.vf", "vfmsac.vv", "vfmsub.vf", "vfmsub.vv", "vfmul.vf", "vfmul.vv",
    # "vfmv.f.s", "vfmv.s.f", "vfmv.v.f", "vfncvt.f.f.w", "vfncvt.f.x.w", "vfncvt.f.xu.w", "vfncvt.rod.f.f.w", "vfncvt.rtz.x.f.w", "vfncvt.rtz.xu.f.w", "vfncvt.x.f.w",
    # "vfncvt.xu.f.w", "vfnmacc.vf", "vfnmacc.vv", "vfnmadd.vf", "vfnmadd.vv", "vfnmsac.vf", "vfnmsac.vv", "vfnmsub.vf", "vfnmsub.vv", "vfrdiv.vf",
    # "vfrec7.v", "vfredmax.vs", "vfredmin.vs", "vfredosum.vs", "vfredusum.vs", "vfrsqrt7.v", "vfrsub.vf", "vfsgnj.vf", "vfsgnj.vv", "vfsgnjn.vf",
    # "vfsgnjn.vv", "vfsgnjx.vf", "vfsgnjx.vv", "vfslide1down.vf", "vfslide1up.vf", "vfsqrt.v", "vfsub.vf", "vfsub.vv", "vfwadd.vf", "vfwadd.vv",
    # "vfwadd.wf", "vfwadd.wv", "vfwcvt.f.f.v", "vfwcvt.f.x.v", "vfwcvt.f.xu.v", "vfwcvt.rtz.x.f.v", "vfwcvt.rtz.xu.f.v", "vfwcvt.x.f.v", "vfwcvt.xu.f.v", "vfwmacc.vf",
    # "vfwmacc.vv", "vfwmsac.vf", "vfwmsac.vv", "vfwmul.vf", "vfwmul.vv", "vfwnmacc.vf", "vfwnmacc.vv", "vfwnmsac.vf", "vfwnmsac.vv", "vfwredosum.vs",
    # "vfwredusum.vs", "vfwsub.vf", "vfwsub.vv", "vfwsub.wf", "vfwsub.wv", "vid.v", "viota.m", "vl1re16.v", "vl1re32.v", "vl1re64.v",
    # "vl1re8.v", "vl2re16.v", "vl2re32.v", "vl2re64.v", "vl2re8.v", "vl4re16.v", "vl4re32.v", "vl4re64.v", "vl4re8.v", "vl8re16.v",
    # "vl8re32.v", "vl8re64.v", "vl8re8.v", "vle1024.v", "vle1024ff.v", "vle128.v", "vle128ff.v", "vle16.v", "vle16ff.v", "vle256.v",
    # "vle256ff.v", "vle32.v", "vle32ff.v", "vle512.v", "vle512ff.v", "vle64.v", "vle64ff.v", "vle8.v", "vle8ff.v", "vlm.v",
    # "vloxei1024.v", "vloxei128.v", "vloxei16.v", "vloxei256.v", "vloxei32.v", "vloxei512.v", "vloxei64.v", "vloxei8.v", "vlse1024.v", "vlse128.v",
    # "vlse16.v", "vlse256.v", "vlse32.v", "vlse512.v", "vlse64.v", "vlse8.v", "vluxei1024.v", "vluxei128.v", "vluxei16.v", "vluxei256.v",
    # "vluxei32.v", "vluxei512.v", "vluxei64.v", "vluxei8.v", "vmacc.vv", "vmacc.vx", "vmadc.vi", "vmadc.vim", "vmadc.vv", "vmadc.vvm",
    # "vmadc.vx", "vmadc.vxm", "vmadd.vv", "vmadd.vx", "vmand.mm", "vmandn.mm", "vmax.vv", "vmax.vx", "vmaxu.vv", "vmaxu.vx",
    # "vmerge.vim", "vmerge.vvm", "vmerge.vxm", "vmfeq.vf", "vmfeq.vv", "vmfge.vf", "vmfgt.vf", "vmfle.vf", "vmfle.vv", "vmflt.vf",
    # "vmflt.vv", "vmfne.vf", "vmfne.vv", "vmin.vv", "vmin.vx", "vminu.vv", "vminu.vx", "vmnand.mm", "vmnor.mm", "vmor.mm",
    # "vmorn.mm", "vmsbc.vv", "vmsbc.vvm", "vmsbc.vx", "vmsbc.vxm", "vmsbf.m", "vmseq.vi", "vmseq.vv", "vmseq.vx", "vmsgt.vi",
    # "vmsgt.vx", "vmsgtu.vi", "vmsgtu.vx", "vmsif.m", "vmsle.vi", "vmsle.vv", "vmsle.vx", "vmsleu.vi", "vmsleu.vv", "vmsleu.vx",
    # "vmslt.vv", "vmslt.vx", "vmsltu.vv", "vmsltu.vx", "vmsne.vi", "vmsne.vv", "vmsne.vx", "vmsof.m", "vmul.vv", "vmul.vx",
    # "vmulh.vv", "vmulh.vx", "vmulhsu.vv", "vmulhsu.vx", "vmulhu.vv", "vmulhu.vx", "vmv1r.v", "vmv2r.v", "vmv4r.v", "vmv8r.v",
    # "vmv.s.x", "vmv.v.i", "vmv.v.v", "vmv.v.x", "vmv.x.s", "vmxnor.mm", "vmxor.mm", "vnclip.wi", "vnclip.wv", "vnclip.wx",
    # "vnclipu.wi", "vnclipu.wv", "vnclipu.wx", "vnmsac.vv", "vnmsac.vx", "vnmsub.vv", "vnmsub.vx", "vnsra.wi", "vnsra.wv", "vnsra.wx",
    # "vnsrl.wi", "vnsrl.wv", "vnsrl.wx", "vor.vi", "vor.vv", "vor.vx", "vredand.vs", "vredmax.vs", "vredmaxu.vs", "vredmin.vs",
    # "vredminu.vs", "vredor.vs", "vredsum.vs", "vredxor.vs", "vrem.vv", "vrem.vx", "vremu.vv", "vremu.vx", "vrgather.vi", "vrgather.vv",
    # "vrgather.vx", "vrgatherei16.vv", "vrsub.vi", "vrsub.vx", "vs1r.v", "vs2r.v", "vs4r.v", "vs8r.v", "vsadd.vi", "vsadd.vv",
    # "vsadd.vx", "vsaddu.vi", "vsaddu.vv", "vsaddu.vx", "vsbc.vvm", "vsbc.vxm", "vse1024.v", "vse128.v", "vse16.v", "vse256.v",
    # "vse32.v", "vse512.v", "vse64.v", "vse8.v", "vsetivli", "vsetvl", "vsetvli", "vsext.vf2", "vsext.vf4", "vsext.vf8",
    # "vslide1down.vx", "vslide1up.vx", "vslidedown.vi", "vslidedown.vx", "vslideup.vi", "vslideup.vx", "vsll.vi", "vsll.vv", "vsll.vx", "vsm.v",
    # "vsmul.vv", "vsmul.vx", "vsoxei1024.v", "vsoxei128.v", "vsoxei16.v", "vsoxei256.v", "vsoxei32.v", "vsoxei512.v", "vsoxei64.v", "vsoxei8.v",
    # "vsra.vi", "vsra.vv", "vsra.vx", "vsrl.vi", "vsrl.vv", "vsrl.vx", "vsse1024.v", "vsse128.v", "vsse16.v", "vsse256.v",
    # "vsse32.v", "vsse512.v", "vsse64.v", "vsse8.v", "vssra.vi", "vssra.vv", "vssra.vx", "vssrl.vi", "vssrl.vv", "vssrl.vx",
    # "vssub.vv", "vssub.vx", "vssubu.vv", "vssubu.vx", "vsub.vv", "vsub.vx", "vsuxei1024.v", "vsuxei128.v", "vsuxei16.v", "vsuxei256.v",
    # "vsuxei32.v", "vsuxei512.v", "vsuxei64.v", "vsuxei8.v", "vwadd.vv", "vwadd.vx", "vwadd.wv", "vwadd.wx", "vwaddu.vv", "vwaddu.vx",
    # "vwaddu.wv", "vwaddu.wx", "vwmacc.vv", "vwmacc.vx", "vwmaccsu.vv", "vwmaccsu.vx", "vwmaccu.vv", "vwmaccu.vx", "vwmaccus.vx", "vwmul.vv",
    # "vwmul.vx", "vwmulsu.vv", "vwmulsu.vx", "vwmulu.vv", "vwmulu.vx", "vwredsum.vs", "vwredsumu.vs", "vwsub.vv", "vwsub.vx", "vwsub.wv",
    # "vwsub.wx", "vwsubu.vv", "vwsubu.vx", "vwsubu.wv", "vwsubu.wx", "vxor.vi", "vxor.vv", "vxor.vx", "vzext.vf2", "vzext.vf4", "vzext.vf8",
    "vse128.v"
]

THEAD_INSTRUCTIONS = [
    "th.addsl",         "th.srri",
    "th.srriw",         "th.ext",
    "th.extu",          "th.ff0",
    "th.ff1",           "th.rev",
    "th.revw",          "th.tstnbz",
    "th.tst",           "th.dcache.call",
    "th.dcache.ciall",  "th.dcache.iall",
    "th.dcache.cpa",    "th.dcache.cipa",
    "th.dcache.ipa",    "th.dcache.cva",
    "th.dcache.civa",   "th.dcache.iva",
    "th.dcache.csw",    "th.dcache.cisw",
    "th.dcache.isw",    "th.dcache.cpal1",
    "th.dcache.cval1",  "th.icache.iall",
    "th.icache.ialls",  "th.icache.ipa",
    "th.icache.iva",    "th.l2cache.call",
    "th.l2cache.ciall", "th.l2cache.iall",
    "th.mveqz",         "th.mvnez",
    "th.flrd",          "th.flrw",
    "th.flurd",         "th.flurw",
    "th.fsrd",          "th.fsrw",
    "th.fsurd",         "th.fsurw",
    "th.fmv.hw.x",      "th.fmv.x.hw",
    "th.ipop",          "th.ipush",
    "th.ldia",          "th.ldib",
    "th.lwia",          "th.lwib",
    "th.lwuia",         "th.lwuib",
    "th.lhia",          "th.lhib",
    "th.lhuia",         "th.lhuib",
    "th.lbia",          "th.lbib",
    "th.lbuia",         "th.lbuib",
    "th.sdia",          "th.sdib",
    "th.swia",          "th.swib",
    "th.shia",          "th.shib",
    "th.sbia",          "th.sbib",
    "th.lrd",           "th.lrw",
    "th.lrwu",          "th.lrh",
    "th.lrhu",          "th.lrb",
    "th.lrbu",          "th.srd",
    "th.srw",           "th.srh",
    "th.srb",           "th.lurd",
    "th.lurw",          "th.lurwu",
    "th.lurh",          "th.lurhu",
    "th.lurb",          "th.lurbu",
    "th.surd",          "th.surw",
    "th.surh",          "th.surb",
    "th.ldd",           "th.lwd",
    "th.lwud",          "th.sdd",
    "th.swd",           "th.mula",
    "th.mulah",         "th.mulaw",
    "th.muls",          "th.mulsh",
    "th.mulsw",         "th.sfence.vmas",
    "th.sync",          "th.sync.i",
    "th.sync.is",       "th.sync.s",
    "th.vsetvl",        "th.vsetvli",
    "th.vlb.v",         "th.vlh.v",
    "th.vlw.v",         "th.vlbu.v",
    "th.vlhu.v",        "th.vlwu.v",
    "th.vle.v",         "th.vsb.v",
    "th.vsh.v",         "th.vsw.v",
    "th.vse.v",         "th.vlsb.v",
    "th.vlsh.v",        "th.vlsw.v",
    "th.vlsbu.v",       "th.vlshu.v",
    "th.vlswu.v",       "th.vlse.v",
    "th.vssb.v",        "th.vssh.v",
    "th.vssw.v",        "th.vsse.v",
    "th.vlxb.v",        "th.vlxh.v",
    "th.vlxw.v",        "th.vlxbu.v",
    "th.vlxhu.v",       "th.vlxwu.v",
    "th.vlxe.v",        "th.vsxb.v",
    "th.vsxh.v",        "th.vsxw.v",
    "th.vsxe.v",        "th.vsuxb.v",
    "th.vsuxh.v",       "th.vsuxw.v",
    "th.vsuxe.v",       "th.vlbff.v",
    "th.vlhff.v",       "th.vlwff.v",
    "th.vlbuff.v",      "th.vlhuff.v",
    "th.vlwuff.v",      "th.vleff.v",
    "th.vlseg2b.v",     "th.vlseg2h.v",
    "th.vlseg2w.v",     "th.vlseg2bu.v",
    "th.vlseg2hu.v",    "th.vlseg2wu.v",
    "th.vlseg2e.v",     "th.vsseg2b.v",
    "th.vsseg2h.v",     "th.vsseg2w.v",
    "th.vsseg2e.v",     "th.vlseg3b.v",
    "th.vlseg3h.v",     "th.vlseg3w.v",
    "th.vlseg3bu.v",    "th.vlseg3hu.v",
    "th.vlseg3wu.v",    "th.vlseg3e.v",
    "th.vsseg3b.v",     "th.vsseg3h.v",
    "th.vsseg3w.v",     "th.vsseg3e.v",
    "th.vlseg4b.v",     "th.vlseg4h.v",
    "th.vlseg4w.v",     "th.vlseg4bu.v",
    "th.vlseg4hu.v",    "th.vlseg4wu.v",
    "th.vlseg4e.v",     "th.vsseg4b.v",
    "th.vsseg4h.v",     "th.vsseg4w.v",
    "th.vsseg4e.v",     "th.vlseg5b.v",
    "th.vlseg5h.v",     "th.vlseg5w.v",
    "th.vlseg5bu.v",    "th.vlseg5hu.v",
    "th.vlseg5wu.v",    "th.vlseg5e.v",
    "th.vsseg5b.v",     "th.vsseg5h.v",
    "th.vsseg5w.v",     "th.vsseg5e.v",
    "th.vlseg6b.v",     "th.vlseg6h.v",
    "th.vlseg6w.v",     "th.vlseg6bu.v",
    "th.vlseg6hu.v",    "th.vlseg6wu.v",
    "th.vlseg6e.v",     "th.vsseg6b.v",
    "th.vsseg6h.v",     "th.vsseg6w.v",
    "th.vsseg6e.v",     "th.vlseg7b.v",
    "th.vlseg7h.v",     "th.vlseg7w.v",
    "th.vlseg7bu.v",    "th.vlseg7hu.v",
    "th.vlseg7wu.v",    "th.vlseg7e.v",
    "th.vsseg7b.v",     "th.vsseg7h.v",
    "th.vsseg7w.v",     "th.vsseg7e.v",
    "th.vlseg8b.v",     "th.vlseg8h.v",
    "th.vlseg8w.v",     "th.vlseg8bu.v",
    "th.vlseg8hu.v",    "th.vlseg8wu.v",
    "th.vlseg8e.v",     "th.vsseg8b.v",
    "th.vsseg8h.v",     "th.vsseg8w.v",
    "th.vsseg8e.v",     "th.vlsseg2b.v",
    "th.vlsseg2h.v",    "th.vlsseg2w.v",
    "th.vlsseg2bu.v",   "th.vlsseg2hu.v",
    "th.vlsseg2wu.v",   "th.vlsseg2e.v",
    "th.vssseg2b.v",    "th.vssseg2h.v",
    "th.vssseg2w.v",    "th.vssseg2e.v",
    "th.vlsseg3b.v",    "th.vlsseg3h.v",
    "th.vlsseg3w.v",    "th.vlsseg3bu.v",
    "th.vlsseg3hu.v",   "th.vlsseg3wu.v",
    "th.vlsseg3e.v",    "th.vssseg3b.v",
    "th.vssseg3h.v",    "th.vssseg3w.v",
    "th.vssseg3e.v",    "th.vlsseg4b.v",
    "th.vlsseg4h.v",    "th.vlsseg4w.v",
    "th.vlsseg4bu.v",   "th.vlsseg4hu.v",
    "th.vlsseg4wu.v",   "th.vlsseg4e.v",
    "th.vssseg4b.v",    "th.vssseg4h.v",
    "th.vssseg4w.v",    "th.vssseg4e.v",
    "th.vlsseg5b.v",    "th.vlsseg5h.v",
    "th.vlsseg5w.v",    "th.vlsseg5bu.v",
    "th.vlsseg5hu.v",   "th.vlsseg5wu.v",
    "th.vlsseg5e.v",    "th.vssseg5b.v",
    "th.vssseg5h.v",    "th.vssseg5w.v",
    "th.vssseg5e.v",    "th.vlsseg6b.v",
    "th.vlsseg6h.v",    "th.vlsseg6w.v",
    "th.vlsseg6bu.v",   "th.vlsseg6hu.v",
    "th.vlsseg6wu.v",   "th.vlsseg6e.v",
    "th.vssseg6b.v",    "th.vssseg6h.v",
    "th.vssseg6w.v",    "th.vssseg6e.v",
    "th.vlsseg7b.v",    "th.vlsseg7h.v",
    "th.vlsseg7w.v",    "th.vlsseg7bu.v",
    "th.vlsseg7hu.v",   "th.vlsseg7wu.v",
    "th.vlsseg7e.v",    "th.vssseg7b.v",
    "th.vssseg7h.v",    "th.vssseg7w.v",
    "th.vssseg7e.v",    "th.vlsseg8b.v",
    "th.vlsseg8h.v",    "th.vlsseg8w.v",
    "th.vlsseg8bu.v",   "th.vlsseg8hu.v",
    "th.vlsseg8wu.v",   "th.vlsseg8e.v",
    "th.vssseg8b.v",    "th.vssseg8h.v",
    "th.vssseg8w.v",    "th.vssseg8e.v",
    "th.vlxseg2b.v",    "th.vlxseg2h.v",
    "th.vlxseg2w.v",    "th.vlxseg2bu.v",
    "th.vlxseg2hu.v",   "th.vlxseg2wu.v",
    "th.vlxseg2e.v",    "th.vsxseg2b.v",
    "th.vsxseg2h.v",    "th.vsxseg2w.v",
    "th.vsxseg2e.v",    "th.vlxseg3b.v",
    "th.vlxseg3h.v",    "th.vlxseg3w.v",
    "th.vlxseg3bu.v",   "th.vlxseg3hu.v",
    "th.vlxseg3wu.v",   "th.vlxseg3e.v",
    "th.vsxseg3b.v",    "th.vsxseg3h.v",
    "th.vsxseg3w.v",    "th.vsxseg3e.v",
    "th.vlxseg4b.v",    "th.vlxseg4h.v",
    "th.vlxseg4w.v",    "th.vlxseg4bu.v",
    "th.vlxseg4hu.v",   "th.vlxseg4wu.v",
    "th.vlxseg4e.v",    "th.vsxseg4b.v",
    "th.vsxseg4h.v",    "th.vsxseg4w.v",
    "th.vsxseg4e.v",    "th.vlxseg5b.v",
    "th.vlxseg5h.v",    "th.vlxseg5w.v",
    "th.vlxseg5bu.v",   "th.vlxseg5hu.v",
    "th.vlxseg5wu.v",   "th.vlxseg5e.v",
    "th.vsxseg5b.v",    "th.vsxseg5h.v",
    "th.vsxseg5w.v",    "th.vsxseg5e.v",
    "th.vlxseg6b.v",    "th.vlxseg6h.v",
    "th.vlxseg6w.v",    "th.vlxseg6bu.v",
    "th.vlxseg6hu.v",   "th.vlxseg6wu.v",
    "th.vlxseg6e.v",    "th.vsxseg6b.v",
    "th.vsxseg6h.v",    "th.vsxseg6w.v",
    "th.vsxseg6e.v",    "th.vlxseg7b.v",
    "th.vlxseg7h.v",    "th.vlxseg7w.v",
    "th.vlxseg7bu.v",   "th.vlxseg7hu.v",
    "th.vlxseg7wu.v",   "th.vlxseg7e.v",
    "th.vsxseg7b.v",    "th.vsxseg7h.v",
    "th.vsxseg7w.v",    "th.vsxseg7e.v",
    "th.vlxseg8b.v",    "th.vlxseg8h.v",
    "th.vlxseg8w.v",    "th.vlxseg8bu.v",
    "th.vlxseg8hu.v",   "th.vlxseg8wu.v",
    "th.vlxseg8e.v",    "th.vsxseg8b.v",
    "th.vsxseg8h.v",    "th.vsxseg8w.v",
    "th.vsxseg8e.v",    "th.vlseg2bff.v",
    "th.vlseg2hff.v",   "th.vlseg2wff.v",
    "th.vlseg2buff.v",  "th.vlseg2huff.v",
    "th.vlseg2wuff.v",  "th.vlseg2eff.v",
    "th.vlseg3bff.v",   "th.vlseg3hff.v",
    "th.vlseg3wff.v",   "th.vlseg3buff.v",
    "th.vlseg3huff.v",  "th.vlseg3wuff.v",
    "th.vlseg3eff.v",   "th.vlseg4bff.v",
    "th.vlseg4hff.v",   "th.vlseg4wff.v",
    "th.vlseg4buff.v",  "th.vlseg4huff.v",
    "th.vlseg4wuff.v",  "th.vlseg4eff.v",
    "th.vlseg5bff.v",   "th.vlseg5hff.v",
    "th.vlseg5wff.v",   "th.vlseg5buff.v",
    "th.vlseg5huff.v",  "th.vlseg5wuff.v",
    "th.vlseg5eff.v",   "th.vlseg6bff.v",
    "th.vlseg6hff.v",   "th.vlseg6wff.v",
    "th.vlseg6buff.v",  "th.vlseg6huff.v",
    "th.vlseg6wuff.v",  "th.vlseg6eff.v",
    "th.vlseg7bff.v",   "th.vlseg7hff.v",
    "th.vlseg7wff.v",   "th.vlseg7buff.v",
    "th.vlseg7huff.v",  "th.vlseg7wuff.v",
    "th.vlseg7eff.v",   "th.vlseg8bff.v",
    "th.vlseg8hff.v",   "th.vlseg8wff.v",
    "th.vlseg8buff.v",  "th.vlseg8huff.v",
    "th.vlseg8wuff.v",  "th.vlseg8eff.v",
    "th.vamoaddw.v",    "th.vamoaddd.v",
    "th.vamoswapw.v",   "th.vamoswapd.v",
    "th.vamoxorw.v",    "th.vamoxord.v",
    "th.vamoandw.v",    "th.vamoandd.v",
    "th.vamoorw.v",     "th.vamoord.v",
    "th.vamominw.v",    "th.vamomind.v",
    "th.vamomaxw.v",    "th.vamomaxd.v",
    "th.vamominuw.v",   "th.vamominud.v",
    "th.vamomaxuw.v",   "th.vamomaxud.v",
    "th.vneg.v",        "th.vadd.vv",
    "th.vadd.vx",       "th.vadd.vi",
    "th.vsub.vv",       "th.vsub.vx",
    "th.vrsub.vx",      "th.vrsub.vi",
    "th.vwcvt.x.x.v",   "th.vwcvtu.x.x.v",
    "th.vwaddu.vv",     "th.vwaddu.vx",
    "th.vwsubu.vv",     "th.vwsubu.vx",
    "th.vwadd.vv",      "th.vwadd.vx",
    "th.vwsub.vv",      "th.vwsub.vx",
    "th.vwaddu.wv",     "th.vwaddu.wx",
    "th.vwsubu.wv",     "th.vwsubu.wx",
    "th.vwadd.wv",      "th.vwadd.wx",
    "th.vwsub.wv",      "th.vwsub.wx",
    "th.vadc.vvm",      "th.vadc.vxm",
    "th.vadc.vim",      "th.vmadc.vvm",
    "th.vmadc.vxm",     "th.vmadc.vim",
    "th.vsbc.vvm",      "th.vsbc.vxm",
    "th.vmsbc.vvm",     "th.vmsbc.vxm",
    "th.vnot.v",        "th.vand.vv",
    "th.vand.vx",       "th.vand.vi",
    "th.vor.vv",        "th.vor.vx",
    "th.vor.vi",        "th.vxor.vv",
    "th.vxor.vx",       "th.vxor.vi",
    "th.vsll.vv",       "th.vsll.vx",
    "th.vsll.vi",       "th.vsrl.vv",
    "th.vsrl.vx",       "th.vsrl.vi",
    "th.vsra.vv",       "th.vsra.vx",
    "th.vsra.vi",       "th.vncvt.x.x.v",
    "th.vnsrl.vv",      "th.vnsrl.vx",
    "th.vnsrl.vi",      "th.vnsra.vv",
    "th.vnsra.vx",      "th.vnsra.vi",
    "th.vmseq.vv",      "th.vmseq.vx",
    "th.vmseq.vi",      "th.vmsne.vv",
    "th.vmsne.vx",      "th.vmsne.vi",
    "th.vmsltu.vv",     "th.vmsltu.vx",
    "th.vmslt.vv",      "th.vmslt.vx",
    "th.vmsleu.vv",     "th.vmsleu.vx",
    "th.vmsleu.vi",     "th.vmsle.vv",
    "th.vmsle.vx",      "th.vmsle.vi",
    "th.vmsgtu.vx",     "th.vmsgtu.vi",
    "th.vmsgt.vx",      "th.vmsgt.vi",
    "th.vmsgt.vv",      "th.vmsgtu.vv",
    "th.vmsge.vv",      "th.vmsgeu.vv",
    "th.vmslt.vi",      "th.vmsltu.vi",
    "th.vmsge.vi",      "th.vmsgeu.vi",
    "th.vmsge.vx",      "th.vmsge.vx",
    "th.vmsgeu.vx",     "th.vmsgeu.vx",
    "th.vminu.vv",      "th.vminu.vx",
    "th.vmin.vv",       "th.vmin.vx",
    "th.vmaxu.vv",      "th.vmaxu.vx",
    "th.vmax.vv",       "th.vmax.vx",
    "th.vmul.vv",       "th.vmul.vx",
    "th.vmulh.vv",      "th.vmulh.vx",
    "th.vmulhu.vv",     "th.vmulhu.vx",
    "th.vmulhsu.vv",    "th.vmulhsu.vx",
    "th.vwmul.vv",      "th.vwmul.vx",
    "th.vwmulu.vv",     "th.vwmulu.vx",
    "th.vwmulsu.vv",    "th.vwmulsu.vx",
    "th.vmacc.vv",      "th.vmacc.vx",
    "th.vnmsac.vv",     "th.vnmsac.vx",
    "th.vmadd.vv",      "th.vmadd.vx",
    "th.vnmsub.vv",     "th.vnmsub.vx",
    "th.vwmaccu.vv",    "th.vwmaccu.vx",
    "th.vwmacc.vv",     "th.vwmacc.vx",
    "th.vwmaccsu.vv",   "th.vwmaccsu.vx",
    "th.vwmaccus.vx",   "th.vdivu.vv",
    "th.vdivu.vx",      "th.vdiv.vv",
    "th.vdiv.vx",       "th.vremu.vv",
    "th.vremu.vx",      "th.vrem.vv",
    "th.vrem.vx",       "th.vmerge.vvm",
    "th.vmerge.vxm",    "th.vmerge.vim",
    "th.vmv.v.v",       "th.vmv.v.x",
    "th.vmv.v.i",       "th.vsaddu.vv",
    "th.vsaddu.vx",     "th.vsaddu.vi",
    "th.vsadd.vv",      "th.vsadd.vx",
    "th.vsadd.vi",      "th.vssubu.vv",
    "th.vssubu.vx",     "th.vssub.vv",
    "th.vssub.vx",      "th.vaadd.vv",
    "th.vaadd.vx",      "th.vaadd.vi",
    "th.vasub.vv",      "th.vasub.vx",
    "th.vsmul.vv",      "th.vsmul.vx",
    "th.vwsmaccu.vv",   "th.vwsmaccu.vx",
    "th.vwsmacc.vv",    "th.vwsmacc.vx",
    "th.vwsmaccsu.vv",  "th.vwsmaccsu.vx",
    "th.vwsmaccus.vx",  "th.vssrl.vv",
    "th.vssrl.vx",      "th.vssrl.vi",
    "th.vssra.vv",      "th.vssra.vx",
    "th.vssra.vi",      "th.vnclipu.vv",
    "th.vnclipu.vx",    "th.vnclipu.vi",
    "th.vnclip.vv",     "th.vnclip.vx",
    "th.vnclip.vi",     "th.vfadd.vv",
    "th.vfadd.vf",      "th.vfsub.vv",
    "th.vfsub.vf",      "th.vfrsub.vf",
    "th.vfwadd.vv",     "th.vfwadd.vf",
    "th.vfwsub.vv",     "th.vfwsub.vf",
    "th.vfwadd.wv",     "th.vfwsub.wv",
    "th.vfwadd.wf",     "th.vfwsub.wf",
    "th.vfmul.vv",      "th.vfmul.vf",
    "th.vfdiv.vv",      "th.vfdiv.vf",
    "th.vfrdiv.vf",     "th.vfwmul.vv",
    "th.vfwmul.vf",     "th.vfmadd.vv",
    "th.vfmadd.vf",     "th.vfnmadd.vv",
    "th.vfnmadd.vf",    "th.vfmsub.vv",
    "th.vfmsub.vf",     "th.vfnmsub.vv",
    "th.vfnmsub.vf",    "th.vfmacc.vv",
    "th.vfmacc.vf",     "th.vfnmacc.vv",
    "th.vfnmacc.vf",    "th.vfmsac.vv",
    "th.vfmsac.vf",     "th.vfnmsac.vv",
    "th.vfnmsac.vf",    "th.vfwmacc.vv",
    "th.vfwmacc.vf",    "th.vfwnmacc.vv",
    "th.vfwnmacc.vf",   "th.vfwmsac.vv",
    "th.vfwmsac.vf",    "th.vfwnmsac.vv",
    "th.vfwnmsac.vf",   "th.vfsqrt.v",
    "th.vfmin.vv",      "th.vfmin.vf",
    "th.vfmax.vv",      "th.vfmax.vf",
    "th.vfneg.v",       "th.vfabs.v",
    "th.vfsgnj.vv",     "th.vfsgnj.vf",
    "th.vfsgnjn.vv",    "th.vfsgnjn.vf",
    "th.vfsgnjx.vv",    "th.vfsgnjx.vf",
    "th.vmfeq.vv",      "th.vmfeq.vf",
    "th.vmfne.vv",      "th.vmfne.vf",
    "th.vmflt.vv",      "th.vmflt.vf",
    "th.vmfle.vv",      "th.vmfle.vf",
    "th.vmfgt.vf",      "th.vmfge.vf",
    "th.vmfgt.vv",      "th.vmfge.vv",
    "th.vmford.vv",     "th.vmford.vf",
    "th.vfclass.v",     "th.vfmerge.vfm",
    "th.vfmv.v.f",      "th.vfcvt.xu.f.v",
    "th.vfcvt.x.f.v",   "th.vfcvt.f.xu.v",
    "th.vfcvt.f.x.v",   "th.vfwcvt.xu.f.v",
    "th.vfwcvt.x.f.v",  "th.vfwcvt.f.xu.v",
    "th.vfwcvt.f.x.v",  "th.vfwcvt.f.f.v",
    "th.vfncvt.xu.f.v", "th.vfncvt.x.f.v",
    "th.vfncvt.f.xu.v", "th.vfncvt.f.x.v",
    "th.vfncvt.f.f.v",  "th.vredsum.vs",
    "th.vredmaxu.vs",   "th.vredmax.vs",
    "th.vredminu.vs",   "th.vredmin.vs",
    "th.vredand.vs",    "th.vredor.vs",
    "th.vredxor.vs",    "th.vwredsumu.vs",
    "th.vwredsum.vs",   "th.vfredosum.vs",
    "th.vfredsum.vs",   "th.vfredmax.vs",
    "th.vfredmin.vs",   "th.vfwredosum.vs",
    "th.vfwredsum.vs",  "th.vmcpy.m",
    "th.vmmv.m",        "th.vmclr.m",
    "th.vmset.m",       "th.vmnot.m",
    "th.vmand.mm",      "th.vmnand.mm",
    "th.vmandnot.mm",   "th.vmxor.mm",
    "th.vmor.mm",       "th.vmnor.mm",
    "th.vmornot.mm",    "th.vmxnor.mm",
    "th.vmpopc.m",      "th.vmfirst.m",
    "th.vmsbf.m",       "th.vmsif.m",
    "th.vmsof.m",       "th.viota.m",
    "th.vid.v",         "th.vmv.x.s",
    "th.vext.x.v",      "th.vmv.s.x",
    "th.vfmv.f.s",      "th.vfmv.s.f",
    "th.vslideup.vx",   "th.vslideup.vi",
    "th.vslidedown.vx", "th.vslidedown.vi",
    "th.vslide1up.vx",  "th.vslide1down.vx",
    "th.vrgather.vv",   "th.vrgather.vx",
    "th.vrgather.vi",   "th.vcompress.vm",
    "th.vmaqa.vv",      "th.vmaqau.vv",
    "th.vmaqasu.vv",    "th.vmaqa.vx",
    "th.vmaqau.vx",     "th.vmaqasu.vx",
    "th.vmaqaus.vx",
]

def generate_instructions(cfg):
    instructions = []

    # Start Node.js process for base instructions
    node_proc = subprocess.Popen(
        ['node', '/home/szekang/Documents/RISCVuzz/Server/generator/main.mjs'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )

    # for xuantie thead instructions
    libthead = ctypes.CDLL("/home/szekang/Documents/RISCVuzz/Server/thead_generator/libthead.so")
    libthead.encode_thead.argtypes = [ctypes.c_char_p]
    libthead.encode_thead.restype = ctypes.c_uint32
    
    # generate random seed
    seed = int(time.time())
    random.seed(seed)   

    # Combine VECTOR and BASE instructions
    all_instructions =  VECTOR_INSTRUCTIONS

    for _ in range(cfg["TOTAL_INSTRUCTIONS"]):
        # Randomly select one instruction
        asm_input = random.choice(all_instructions)
        # print("Selected Input:", asm_input)
        try:
            # Determine which function to call
            if asm_input in VECTOR_INSTRUCTIONS:
                result = int(call_rust_asm(asm_input), 16)
            elif asm_input in THEAD_INSTRUCTIONS:
                result = call_thead_instruction(asm_input, libthead)
            else:
                result = int((call_base_instruction(asm_input, node_proc))["hex"], 16)

            # formatted_result = "0x{:08x}".format(result & 0xffffffff)
            # instructions.append(formatted_result)
            # print("output:", formatted_result)
            final_result = result & 0xffffffff
            instructions.append(final_result)
            print(asm_input)
            # check_flip(instructions, result, cfg)

        except RuntimeError as e:
            print("Input:", asm_input, " -> Error:", e)

    return instructions

    # print("-----------------------------------")

    # for asm_input in VECTOR_INSTRUCTIONS:
    #     print("Input:" + asm_input)
    #     result = int(call_rust_asm(asm_input), 16)
    #     output.append("0x{:08x}".format(result & 0xffffffff))
    #     print("output:", "0x{:08x}".format(result))
    #     check_flip(output, result, cfg)
    # print("-----------------------------------")
    # for asm_input in BASE_INSTRUCTIONS:
    #     try:
    #         print("Input:", asm_input)
    #         result = int((call_base_instruction(asm_input, node_proc))["hex"], 16)
    #         output.append("0x{:08x}".format(result & 0xffffffff))
    #         print("output:", "0x{:08x}".format(result))
    #         check_flip(output, result, cfg)
    #     except RuntimeError as e:
    #         print("Input:", asm_input, " -> Error:", e)