#!/usr/bin/env python3
"""
riscv_bin_gen.py — Random RISC-V binary instruction generator.

Outputs 32-bit instruction words (little-endian) to stdout.

Features:
- Base RV32/64 instructions (R/I/S/B/U/J formats)
- Optional M-extension, AMO, FP instructions
- Optional RVV-ish vector instruction encodings (best-effort)
- CSR ops removed entirely
- Configurable RNG seed and count

Limitations:
- RVV encodings are approximate (funct6 + vm + vs2 + vs1 + funct3 + vd + opcode)
- Does not emit ELF or assemble; raw 4-byte instruction words only.
"""

from config import *
import random, argparse, time
fence_called = False

# random signed immediate generator
def rand_simm(bits):
    if random.random() < IMM_SPECIAL:
        return random.choice(SPECIAL_SIMMS)
    lo = -(1 << (bits-1))
    hi = (1 << (bits-1)) - 1
    return random.randint(lo, hi)
# random unsigned immediate generator 
def rand_uimm(bits):
    if random.random() < IMM_SPECIAL:
        return random.choice(SPECIAL_UIMMS)
    return random.randint(0, (1 << bits) - 1)

# Random generators producing registers:
def pick_gpr(avoid_zero=False, exclude=None):
    if random.random() < GPR_SPECIAL:  # n% special
        return random.choice(SPECIAL_GPRS)
    
    base_exclude = {9}    # Start with x9 always excluded

    if exclude:
        base_exclude.update(exclude)  # add any extra exclusions
    if avoid_zero:
        base_exclude.add(0)

    candidates = [r for r in range(32) if r not in base_exclude]
    return random.choice(candidates)
def pick_fpr():
    if random.random() < FPR_SPECIAL:
        return random.choice(SPECIAL_FPRS)
    return random.choice(FREGS)
def pick_vreg():
    if random.random() < VREG_SPECIAL:
        return random.choice(SPECIAL_VREGS)    
    return random.choice(VREGS)


def rd_bits(rd): return (rd & 0x1f) << 7
def rs1_bits(rs1): return (rs1 & 0x1f) << 15
def rs2_bits(rs2): return (rs2 & 0x1f) << 20
def funct3_bits(f3): return (f3 & 0x7) << 12
def funct7_bits(f7): return (f7 & 0x7f) << 25
def opcode_bits(op): return op & 0x7f

def encode_r(funct7, rs2, rs1, funct3, rd, opcode):
    return (funct7_bits(funct7) | rs2_bits(rs2) | rs1_bits(rs1) |
            funct3_bits(funct3) | rd_bits(rd) | opcode_bits(opcode))

def encode_i(imm12, rs1, funct3, rd, opcode):
    imm = imm12 & 0xfff
    return ( (imm << 20) | rs1_bits(rs1) | funct3_bits(funct3) |
             rd_bits(rd) | opcode_bits(opcode) )

def encode_s(imm12, rs2, rs1, funct3, opcode):
    imm = imm12 & 0xfff
    imm_lo = imm & 0x1f
    imm_hi = (imm >> 5) & 0x7f
    return ( (imm_hi << 25) | rs2_bits(rs2) | rs1_bits(rs1) |
             funct3_bits(funct3) | (imm_lo << 7) | opcode_bits(opcode) )

def encode_b(imm13, rs2, rs1, funct3, opcode):
    # imm13 is signed branch immediate (lowest bit zero). encode as imm[12|10:5][4:1|11]
    imm = imm13 & 0x1fff
    imm_bit11 = (imm >> 11) & 0x1    # bit 11 -> imm[11]
    imm_lo = (imm >> 1) & 0xf        # bits 1..4 -> imm[4:1]
    imm_hi = (imm >> 5) & 0x3f       # bits 5..10 -> imm[10:5]
    imm_top = (imm >> 12) & 0x1      # bit12 -> imm[12]
    encoded = ( (imm_top << 31) |
                (imm_hi << 25) |
                rs2_bits(rs2) |
                rs1_bits(rs1) |
                funct3_bits(funct3) |
                (imm_lo << 8) |
                (imm_bit11 << 7) |
                opcode_bits(opcode) )
    return encoded

def encode_u(imm20, rd, opcode):
    imm = imm20 & 0xfffff
    return ( (imm << 12) | rd_bits(rd) | opcode_bits(opcode) )

def encode_j(imm21, rd, opcode):
    # J-type imm[20|10:1|11|19:12]
    imm = imm21 & 0x1fffff
    imm_20 = (imm >> 20) & 0x1
    imm_10_1 = (imm >> 1) & 0x3ff
    imm_11 = (imm >> 11) & 0x1
    imm_19_12 = (imm >> 12) & 0xff
    encoded = ( (imm_20 << 31) |
                (imm_19_12 << 12) |
                (imm_11 << 20) |
                (imm_10_1 << 21) |
                rd_bits(rd) |
                opcode_bits(opcode) )
    return encoded
 
# build instruction pool based on flags
def build_pool(xlen, enable_m, enable_amo, enable_f, enable_vector):
    pool = []
    for entry in RV32I_TEMPLATES:
        pool.append(entry)

    # M extension
    if enable_m:
        for entry in M_TEMPLATES:
            pool.append(entry)
    # AMO
    if enable_amo:
        for entry in AMO_TEMPLATES:
            pool.append(entry)
    # Floating
    if enable_f:
        for entry in FLOATING_TEMPLATES:
            pool.append(entry)
    # vector
    if enable_vector:
        for entry in VECTOR_TEMPLATES:
            pool.append(entry)

    return pool

def emit_r_ins(entry, xlen):
    # For R entries 
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    rs2 = pick_gpr()

    name, instr_type, fields = entry
    f3 = fields["funct3"]
    f7 = fields["funct7"]
    opcode = fields["opcode"]

    enc = encode_r(f7, rs2, rs1, f3, rd, opcode)
    return enc

def emit_i_ins(entry, xlen):
    # For I entries
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    imm = rand_simm(12)

    name, instr_type, fields = entry
    f3 = fields["funct3"]
    opcode = fields["opcode"]

    return encode_i(imm, rs1, f3, rd, opcode)

def emit_shift_ins(entry, xlen):
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    shamt_max = 31 if xlen==32 else 63
    shamt = random.randint(0, shamt_max)

    name, instr_type, fields = entry
    f3 = fields["funct3"]
    f7 = fields["funct7"]
    opcode = fields["opcode"]

    # encode shamt in imm[5:0] or imm[4:0] for RV32; when f7 != 0, set in funct7's low bits
    if xlen == 32:
        shamt_masked = shamt & 0x1f
    else:
        shamt_masked = shamt & 0x3f
        
    imm12 = (f7 << 5) | shamt_masked
    return encode_i(imm12, rs1, f3, rd, opcode)

def emit_store(entry, xlen):
    # For S entries (Store)
    rs2 = pick_gpr()
    rs1 = pick_gpr()
    imm = rand_simm(12)

    name, instr_type, fields = entry
    f3 = fields["funct3"]
    opcode = fields["opcode"]

    return encode_s(imm, rs2, rs1, f3, opcode)

def emit_branch(entry, xlen):
    # For B entries (Branch)
    rs1 = pick_gpr()
    rs2 = pick_gpr()
    # choose branch offset aligned to 2 (lowest bit zero); limit magnitude
    imm = random.choice([4,8,12,16,-4,-8,-12,-16, random.randint(-2048,2048)])

    name, instr_type, fields = entry
    f3 = fields["funct3"]
    opcode = fields["opcode"]

    return encode_b(imm, rs2, rs1, f3, opcode)

def emit_jal(entry, xlen):
    rd = pick_gpr(avoid_zero=True)
    imm = random.randint(- (1<<20), (1<<20)-1)

    return encode_j(imm, rd, OP_JAL)

def emit_u(entry, xlen):
    # For U entries 
    rd = pick_gpr(avoid_zero=True)
    imm = rand_simm(20)

    name, instr_type, fields = entry
    opcode = fields["opcode"]

    return encode_u(imm, rd, opcode)

def emit_fp(entry, xlen):
    # For F entries (requires FP regs)
    rd = pick_fpr()
    rs1 = pick_fpr()
    rs2 = pick_fpr()

    name, instr_type, fields = entry
    f3 = fields["funct3"]
    f7 = fields["funct7"]
    opcode = fields["opcode"]

    # for fp we use rd/rs1/rs2 mapped into integer fields (assembler treats them specially)
    return encode_r(f7, rs2, rs1, f3, rd, opcode)

def emit_fload(entry, xlen):
    # For floating-point I-type loads (e.g. FLW, FLD)
    rd = pick_fpr()
    rs1 = pick_gpr()
    imm = rand_simm(12)

    name, instr_type, fields = entry
    f3 = fields["funct3"]
    opcode = fields["opcode"]

    return encode_i(imm & 0xfff, rs1, f3, rd, opcode)

def emit_fstore(entry, xlen):
    # For floating-point I-type stores (e.g. FSW, FSD)
    rs2 = pick_fpr()
    rs1 = pick_gpr()
    imm = rand_simm(12)

    name, instr_type, fields = entry
    f3 = fields["funct3"]
    opcode = fields["opcode"]

    imm11_5 = (imm >> 5) & 0x7f
    imm4_0 = imm & 0x1f

    return encode_s(imm11_5, rs2, rs1, f3, imm4_0, opcode)

def emit_fence(entry, xlen):
    rd=0
    rs1=0
    f3 = 0  # for both fence and fence.i
    global fence_called

    # calls fence once, then calls fence.i afterwards 
    if not fence_called:
        # FENCE.I
        imm = 1
        fence_called = True
    else:
        # FENCE: randomize pred and succ (imm[7:4], imm[3:0])
        pred = random.randint(0, 0xF)
        succ = random.randint(0, 0xF)
        imm = (pred << 4) | succ
    
    return encode_i(imm, rs1, f3, rd, OP_MISC)

def emit_sys(entry, xlen):
    # ecall/ebreak with imm numbers 0/1

    name, instr_type, fields = entry
    imm = fields["imm"]
    opcode = fields["opcode"]

    return encode_i(imm, 0, 0, 0, opcode)

def emit_vector(entry, xlen):
    # For M and RV entries (vector encoding):
    vd = pick_vreg()
    vs1 = pick_vreg()
    vs2 = pick_vreg()

    name, instr_type, fields = entry
    opcode = fields["opcode"]
    f3 = fields.get("funct3")
    f6 = fields.get("funct6")

    if instr_type == "M":
        vm = 0
    elif instr_type == "RV":
        vm = random.randint(0,1)

    # place bits:
    # funct6 -> bits 26..31
    # vm -> bit 25
    # rs2 -> bits20..24 (vs2)
    # rs1 -> bits15..19 (vs1)
    # funct3 -> bits12..14
    # rd -> bits7..11 (vd)
    encoded = ( (f6 & 0x3f) << 26 ) | ((vm & 0x1) << 25) | ( (vs2 & 0x1f) << 20) | ( (vs1 & 0x1f) << 15) | ((f3 & 0x7) << 12) | ((vd & 0x1f) << 7) | (opcode & 0x7f)
    
    return encoded

def emit_vector_r4(entry, xlen):
    """
    Emit a vector R4-type instruction (e.g., VFMADD.VV).
    R4-type has 4 vector register operands: vd, vs1, vs2, vs3.
    Encoding based on V-extension spec section on FMA ops.
    """
    vd  = pick_vreg()
    vs1 = pick_vreg()
    vs2 = pick_vreg()
    vs3 = pick_vreg()
    vm = random.randint(0, 1)

    name, instr_type, fields = entry
    opcode = fields["opcode"]
    f3 = fields.get("funct3")
    f6 = fields.get("funct6")

    # Layout:
    # funct6 [31:26]
    # vs3    [24:20]   (extra src)
    # vm     [25]
    # vs2    [19:15]
    # vs1    [14:10]
    # funct3 [9:7]
    # vd     [11:7]
    # opcode [6:0]
    encoded = ((f6 & 0x3f) << 26) | \
              ((vm & 0x1) << 25) | \
              ((vs3 & 0x1f) << 20) | \
              ((vs2 & 0x1f) << 15) | \
              ((vs1 & 0x1f) << 10) | \
              ((f3 & 0x7) << 12) | \
              ((vd & 0x1f) << 7) | \
              (opcode & 0x7f)

    return encoded

def emit_vector_i(entry, xlen):
    """
    Emit a vector I-type (immediate) instruction, e.g., VSLL.VI, VSRL.VI, VSRA.VI.
    Encoding per RISC-V V extension spec (vector immediate shift).
    """
    vd  = pick_vreg()
    vs2 = pick_vreg()
    vm = random.randint(0, 1)

    name, instr_type, fields = entry
    opcode = fields["opcode"]
    f3 = fields.get("funct3")
    f6 = fields.get("funct6")

    # Immediate: shift amount is in 'rs1' field for VI form
    shamt_max = 31 if xlen == 32 else 63
    simm5 = random.randint(0, shamt_max) & 0x1f  # spec: 5-bit immediate for VI shift

    # Layout (VI-type):
    # funct6  [31:26]
    # vm      [25]
    # vs2     [24:20]
    # simm5   [19:15]   (immediate instead of vs1)
    # funct3  [14:12]
    # vd      [11:7]
    # opcode  [6:0]
    encoded = ((f6 & 0x3f) << 26) | \
              ((vm & 0x1) << 25)  | \
              ((vs2 & 0x1f) << 20) | \
              ((simm5 & 0x1f) << 15) | \
              ((f3 & 0x7) << 12) | \
              ((vd & 0x1f) << 7) | \
              (opcode & 0x7f)

    return encoded

def emit_vector_vx(entry, xlen):
    vd = pick_vreg()
    rs1 = pick_gpr()
    vs2 = pick_vreg()
    vm = random.randint(0, 1)

    name, instr_type, fields = entry
    opcode = fields["opcode"]
    f3 = fields.get("funct3", 0)
    f6 = fields.get("funct6", 0)

    encoded = ((f6 & 0x3f) << 26) | \
              ((vm & 0x1) << 25) | \
              ((vs2 & 0x1f) << 20) | \
              ((rs1 & 0x1f) << 15) | \
              ((f3 & 0x7) << 12) | \
              ((vd & 0x1f) << 7) | \
              (opcode & 0x7f)

    return encoded


# main generator
def generate(count=200, xlen=64, enable_m=False, enable_amo=False, enable_f=False, enable_vector=False, seed=None):
    if seed is None:
        seed = int(time.time())
    random.seed(seed)
    pool = build_pool(xlen, enable_m, enable_amo, enable_f, enable_vector)
    out_words = []
    for _ in range(count):
        name, instr_type, fields = random.choice(pool)
        if instr_type in ("R", "AMO"):
            w = emit_r_ins((name, instr_type, fields), xlen)
        elif instr_type == "I":
            w = emit_i_ins((name, instr_type, fields), xlen)
        elif instr_type == "SHIFT":
            w = emit_shift_ins((name, instr_type, fields), xlen)
        elif instr_type == "S":
            w = emit_store((name, instr_type, fields), xlen)
        elif instr_type == "B":
            w = emit_branch((name, instr_type, fields), xlen)
        elif instr_type == "J":
            w = emit_jal((name, instr_type, fields), xlen)
        elif instr_type == "U":
            w = emit_u((name, instr_type, fields), xlen)
        elif instr_type == "F":
            w = emit_fp((name, instr_type, fields), xlen)
        elif instr_type == "FLOAD":
            w = emit_fload((name, instr_type, fields), xlen)
        elif instr_type == "FSTORE":
            w = emit_fstore((name, instr_type, fields), xlen)
        elif instr_type == "FENCE":
            w = emit_fence((name, instr_type, fields), xlen)
        elif instr_type == "SYS":
            w = emit_sys((name, instr_type, fields), xlen)
        elif instr_type in ("VR", "VM"):
            w = emit_vector((name, instr_type, fields), xlen)
        elif instr_type == "VR4":
            w = emit_vector_r4((name, instr_type, fields), xlen)
        elif instr_type == "VI":
            w = emit_vector_i((name, instr_type, fields), xlen)
        elif instr_type == "VX":
            w = emit_vector_vx((name, instr_type, fields), xlen)
        else:
            w = 0x00000013  # nop (addi x0,x0,0)
        out_words.append(w & 0xffffffff)
    return out_words

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=200)
    p.add_argument("--xlen", type=int, default=64, choices=[32,64])
    p.add_argument("--seed", type=int, default=None)
    p.add_argument("--enable-m", action="store_true")
    p.add_argument("--enable-amo", action="store_true")
    p.add_argument("--enable-f", action="store_true")
    p.add_argument("--enable-vector", action="store_true")
    args = p.parse_args()

    words = generate(count=args.count,
                     xlen=args.xlen,
                     enable_m=args.enable_m,
                     enable_amo=args.enable_amo,
                     enable_f=args.enable_f,
                     enable_vector=args.enable_vector,
                     seed=args.seed)

    words = generate(count=args.count,
                     xlen=args.xlen,
                     enable_m=args.enable_m,
                     enable_amo=args.enable_amo,
                     enable_f=args.enable_f,
                     enable_vector=args.enable_vector,
                     seed=args.seed)
    
    with open("output.c", "w") as f:
        f.write("// Auto-generated instructions\n\n")
        f.write("#include <stdint.h>\n#include <stddef.h>\n\n")
        f.write("uint32_t fuzz_buffer2[] = {\n")
        for w in words:
            f.write(f"    0x{w:08x},\n")
        f.write("};\n")
        f.write("const size_t fuzz_buffer_len = sizeof(fuzz_buffer2) / sizeof(uint32_t);");


if __name__ == "__main__":
    main()

