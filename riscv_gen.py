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

import random, argparse, sys, time, struct

# Opcodes (7-bit) — canonical major opcode values
OP_R      = 0x33   # 0110011
OP_IMM    = 0x13   # 0010011
OP_LUI    = 0x37   # 0110111
OP_AUIPC  = 0x17   # 0010111
OP_JAL    = 0x6f   # 1101111
OP_JALR   = 0x67   # 1100111
OP_BRANCH = 0x63   # 1100011
OP_LOAD   = 0x03   # 0000011
OP_STORE  = 0x23   # 0100011
OP_MISC   = 0x0f   # 0001111 (fence)
OP_SYSTEM = 0x73   # 1110011
OP_AMO    = 0x2f   # 0101111 (AMO/Atomic)
OP_FPU    = 0x53   # 1010011 (FP)
OP_VECTOR = 0x57   # 1010111 (RVV, OP-V/OPIVV space)

GPRs = list(range(32))
VREGS = list(range(32))
FREGS = list(range(32))

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
    imm_bit11 = (imm >> 11) & 0x1     # bit 11 -> imm[11]
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

# helpers for imm selection (signed)
def rand_simm(bits):
    lo = -(1 << (bits-1))
    hi = (1 << (bits-1)) - 1
    return random.randint(lo, hi)

def rand_uimm(bits):
    return random.randint(0, (1<<bits)-1)

# mapping instruction -> (type, funct3, funct7/opcode fam)
# We'll implement many common mnemonics below. CSR mnemonics are intentionally omitted.

R_ALU = {
    "add":  (0x0, 0x00),
    "sub":  (0x0, 0x20),
    "sll":  (0x1, 0x00),
    "slt":  (0x2, 0x00),
    "sltu": (0x3, 0x00),
    "xor":  (0x4, 0x00),
    "srl":  (0x5, 0x00),
    "sra":  (0x5, 0x20),
    "or":   (0x6, 0x00),
    "and":  (0x7, 0x00),
}

I_ALU = {
    "addi": 0x0,
    "slti": 0x2,
    "sltiu":0x3,
    "xori": 0x4,
    "ori":  0x6,
    "andi": 0x7,
}

# shift-immediate use funct3 = 1 or 5 and shamt in imm field, funct7 may be 0 or 0x20
I_SHIFTS = {"slli": (0x1,0x00), "srli":(0x5,0x00), "srai":(0x5,0x20)}

LOADS = {
    "lb": 0x0,
    "lh": 0x1,
    "lw": 0x2,
    "lwu": 0x6,    # for RV64
    "ld": 0x3      # for RV64
}

STORES = {
    "sb": 0x0,
    "sh": 0x1,
    "sw": 0x2,
    "sd": 0x3
}

BRANCHES = {
    "beq": 0x0,
    "bne": 0x1,
    "blt": 0x4,
    "bge": 0x5,
    "bltu":0x6,
    "bgeu":0x7
}

M_OPS = {
    "mul": (0x0, 0x01),
    "mulh":(0x1, 0x01),
    "mulhsu":(0x2,0x01),
    "mulhu":(0x3,0x01),
    "div":(0x4,0x01),
    "divu":(0x5,0x01),
    "rem":(0x6,0x01),
    "remu":(0x7,0x01)
}

# Atomic AMO: use opcode OP_AMO (0x2f) and funct3 usually 0x2 (word/dword)
AMO_OPS = [
    # We'll emit common template AMOs with funct5 or funct? encoded in funct7's upper bits; simplified
    ("amoswap.w", 0x2, 0x01),
    ("amoadd.w", 0x2, 0x00),
    ("amoxor.w",  0x2, 0x04),
    ("amoand.w",  0x2, 0x0c),
    ("amoor.w",   0x2, 0x08),
    ("amomin.w",  0x2, 0x10),
    ("amomax.w",  0x2, 0x14),
    ("amominu.w", 0x2, 0x18),
    ("amomaxu.w", 0x2, 0x1c),
]

# FP ops (OP_FPU=0x53) simple subset
F_OPS = {
    "fadd.s": (0x0, 0x00), "fsub.s": (0x0, 0x08), "fmul.s": (0x0, 0x10), "fdiv.s": (0x0, 0x18),
    "fadd.d": (0x1, 0x00), "fsub.d": (0x1, 0x08), "fmul.d": (0x1, 0x10), "fdiv.d": (0x1, 0x18),
}

# vector ops: best-effort list (we will produce encodings in OP_VECTOR space)
V_OPS = [
    "vadd.vv", "vsub.vv", "vand.vv", "vor.vv", "vxor.vv",
    "vmul.vv", "vdiv.vv"  # vmul/vdiv are high-level placeholders (RVV real encodings differ)
]

# build instruction pool based on flags
def build_pool(xlen, enable_m, enable_amo, enable_f, enable_vector):
    pool = []
    # base R types
    for op in R_ALU.keys():
        pool.append(("R", op))
    for op in I_ALU.keys():
        pool.append(("I", op))
    # shifts
    for op in I_SHIFTS.keys():
        pool.append(("SHIFT", op))
    # loads/stores
    load_ops = ["lb","lh","lw"]
    store_ops = ["sb","sh","sw"]
    if xlen == 64:
        load_ops += ["lwu","ld"]
        store_ops += ["sd"]
    for op in load_ops:
        pool.append(("LOAD", op))
    for op in store_ops:
        pool.append(("STORE", op))
    # branches, jal, jalr, lui, auipc
    for op in BRANCHES.keys():
        pool.append(("BR", op))
    pool += [("J","jal"), ("JR","jalr"), ("U","lui"), ("U","auipc")]
    # M extension
    if enable_m:
        for op in M_OPS.keys():
            pool.append(("M", op))
    # AMO
    if enable_amo:
        for name, f3, f5 in AMO_OPS:
            pool.append(("AMO", name))
    # Floating
    if enable_f:
        for op in F_OPS.keys():
            pool.append(("F", op))
        # simple fp loads/stores
        if xlen==32:
            pool += [("FLOAD","flw"), ("FSTORE","fsw")]
        else:
            pool += [("FLOAD","flw"), ("FSTORE","fsw"), ("FLOAD","fld"), ("FSTORE","fsd")]
    # vector
    if enable_vector:
        for op in V_OPS:
            pool.append(("V", op))
    # fences and misc
    pool += [("FENCE","fence"), ("SYS","ecall"), ("SYS","ebreak")]
    return pool

# Random generators producing immediates and registers then encoding:
def pick_gpr(avoid_zero=False):
    r = random.choice(GPRs)
    if avoid_zero:
        while r == 0:
            r = random.choice(GPRs)
    return r

def pick_fpr():
    return random.choice(FREGS)

def pick_vreg():
    return random.choice(VREGS)

def emit_r_ins(op, xlen):
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    rs2 = pick_gpr()
    if op in R_ALU:
        f3, f7 = R_ALU[op]
        enc = encode_r(f7, rs2, rs1, f3, rd, OP_R)
        return enc
    # fallback as add
    return encode_r(0x00, rs2, rs1, 0x0, rd, OP_R)

def emit_i_ins(op, xlen):
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    if op in I_ALU:
        f3 = I_ALU[op]
        imm = rand_simm(12)
        return encode_i(imm, rs1, f3, rd, OP_IMM)
    # fallback
    imm = rand_simm(12)
    return encode_i(imm, rs1, 0, rd, OP_IMM)

def emit_shift_ins(op, xlen):
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    shamt_max = 31 if xlen==32 else 63
    shamt = random.randint(0, shamt_max)
    f3, f7 = I_SHIFTS[op]
    # encode shamt in imm[5:0] or imm[4:0] for RV32; when f7 != 0, set in funct7's low bits
    imm = shamt & 0xfff
    # for srai, need top bits set -> encode funct7 0x20 in place: we will set funct7 in funct7_bits
    # Note: Encoding shifts uses opcode OP_IMM with imm[11:0] containing shamt and possibly funct7 in upper bits for RV64; but we construct accordingly:
    if op == "srai":
        # set bit pattern for arithmetic right -> we put 0x20 in imm high area for RV32; using encode_i suffices because imm <<20 places it
        # But to be safe, craft imm with bit 10 set as per spec for srai on RV32/64: set imm = (f7<<5) | shamt
        imm12 = ((0x20 & 0x7f) << 5) | (shamt & 0x1f)
        return encode_i(imm12, rs1, f3, rd, OP_IMM)
    elif op == "srli":
        imm12 = ((0x00 & 0x7f) << 5) | (shamt & 0x1f)
        return encode_i(imm12, rs1, f3, rd, OP_IMM)
    else: # slli
        imm12 = ((0x00 & 0x7f) << 5) | (shamt & 0x1f)
        return encode_i(imm12, rs1, f3, rd, OP_IMM)

def emit_load(op, xlen):
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    imm = rand_simm(12)
    f3 = LOADS.get(op, 0)
    return encode_i(imm, rs1, f3, rd, OP_LOAD)

def emit_store(op, xlen):
    rs2 = pick_gpr()
    rs1 = pick_gpr()
    imm = rand_simm(12)
    f3 = STORES.get(op, 0)
    return encode_s(imm, rs2, rs1, f3, OP_STORE)

def emit_branch(op, xlen):
    rs1 = pick_gpr()
    rs2 = pick_gpr()
    # choose branch offset aligned to 2 (lowest bit zero); limit magnitude
    imm = random.choice([4,8,12,16,-4,-8,-12,-16, random.randint(-2048,2048)])
    f3 = BRANCHES.get(op, 0)
    return encode_b(imm, rs2, rs1, f3, OP_BRANCH)

def emit_jal(xlen):
    rd = pick_gpr(avoid_zero=True)
    imm = random.randint(- (1<<20), (1<<20)-1)
    return encode_j(imm, rd, OP_JAL)

def emit_jalr(xlen):
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    imm = rand_simm(12)
    return encode_i(imm, rs1, 0x0, rd, OP_JALR)

def emit_u(op, xlen):
    rd = pick_gpr(avoid_zero=True)
    imm = rand_simm(20)
    opc = OP_LUI if op=="lui" else OP_AUIPC
    return encode_u(imm, rd, opc)

def emit_m(op, xlen):
    # use R-type encoding in OP_R space but funct7 = 0x01
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    rs2 = pick_gpr()
    f3, f7_base = M_OPS[op]
    return encode_r(f7_base, rs2, rs1, f3, rd, OP_R)

def emit_amo(name, xlen):
    # simplified: use OP_AMO opcode, funct3 field 0x2 (word/dword), encode an amo funct5 in upper bits of funct7.
    rd = pick_gpr(avoid_zero=True)
    rs1 = pick_gpr()
    rs2 = pick_gpr()
    # pick matching AMO_OPS entry
    entry = random.choice(AMO_OPS)
    name, f3, func5 = entry
    # Put func5 in bits[31:27] (high portion of funct7) and set lowest two bits of funct7 to 0
    funct7 = (func5 & 0x1f) << 2
    return encode_r(funct7, rs2, rs1, f3, rd, OP_AMO)

def emit_fp(op, xlen):
    # emit simple FP op in OP_FPU space (requires FP regs)
    rd = pick_fpr()
    rs1 = pick_fpr()
    rs2 = pick_fpr()
    # map op to (fmt, funct7-like)
    t = F_OPS.get(op, (0x0,0x00))
    fmt, func7 = t
    # encode as R-type in OP_FPU but place fmt in funct3 (approx)
    f3 = fmt & 0x7
    funct7 = func7 & 0x7f
    # for fp we use rd/rs1/rs2 mapped into integer fields (assembler treats them specially)
    return encode_r(funct7, rs2, rs1, f3, rd, OP_FPU)

def emit_fload(op, xlen):
    rd = pick_fpr()
    rs1 = pick_gpr()
    imm = rand_simm(12)
    # map flw/fld -> fpu load (OP_LOAD but assembler maps fp-regs into rd)
    # we'll encode using OP_LOAD but rd bits contain fp reg index.
    f3 = 2 if op in ("flw","fld") else 2
    return encode_i(imm, rs1, f3, rd, OP_LOAD)

def emit_fstore(op, xlen):
    rs2 = pick_fpr()
    rs1 = pick_gpr()
    imm = rand_simm(12)
    f3 = 2
    # encode S-type with rs2 field holding fp reg index value
    return encode_s(imm, rs2, rs1, f3, OP_STORE)

def emit_fence():
    # fence (0) and fence.i (0x1??) — we'll use OP_MISC opcode with funct3 zero
    # fence has imm fields but simplest emit 0
    imm = 0
    rd=0; rs1=0
    return encode_i(imm, rs1, 0, rd, OP_MISC)

def emit_sys(name):
    # ecall/ebreak use OP_SYSTEM with funct3=0 and imm numbers 0/1
    if name == "ecall":
        imm = 0
    else:
        imm = 1
    return encode_i(imm, 0, 0, 0, OP_SYSTEM)

def emit_vector(op, xlen):
    # Best-effort OP_VECTOR encoding:
    vd = pick_vreg()
    vs1 = pick_vreg()
    vs2 = pick_vreg()
    # choose random funct6 and vm bit
    funct6 = random.randint(0, 0x3f)
    vm = random.randint(0,1)
    funct3 = 0  # many RVV use funct3=0, but not always — this is a simplified approach
    opcode = OP_VECTOR
    # place bits:
    # funct6 -> bits 26..31
    # vm -> bit 25
    # rs2 -> bits20..24 (vs2)
    # rs1 -> bits15..19 (vs1)
    # funct3 -> bits12..14
    # rd -> bits7..11 (vd)
    encoded = ( (funct6 & 0x3f) << 26 ) | ((vm & 0x1) << 25) | ( (vs2 & 0x1f) << 20) | ( (vs1 & 0x1f) << 15) | ((funct3 & 0x7) << 12) | ((vd & 0x1f) << 7) | (opcode & 0x7f)
    return encoded

# main generator
def generate(count=200, xlen=64, enable_m=False, enable_amo=False, enable_f=False, enable_vector=False, seed=None):
    if seed is None:
        seed = int(time.time())
    random.seed(seed)
    pool = build_pool(xlen, enable_m, enable_amo, enable_f, enable_vector)
    out_words = []
    for _ in range(count):
        typ, op = random.choice(pool)
        if typ == "R":
            w = emit_r_ins(op, xlen)
        elif typ == "I":
            w = emit_i_ins(op, xlen)
        elif typ == "SHIFT":
            w = emit_shift_ins(op, xlen)
        elif typ == "LOAD":
            w = emit_load(op, xlen)
        elif typ == "STORE":
            w = emit_store(op, xlen)
        elif typ == "BR":
            w = emit_branch(op, xlen)
        elif typ == "J":
            w = emit_jal(xlen)
        elif typ == "JR":
            w = emit_jalr(xlen)
        elif typ == "U":
            w = emit_u(op, xlen)
        elif typ == "M":
            w = emit_m(op, xlen)
        elif typ == "AMO":
            w = emit_amo(op, xlen)
        elif typ == "F":
            w = emit_fp(op, xlen)
        elif typ == "FLOAD":
            w = emit_fload(op, xlen)
        elif typ == "FSTORE":
            w = emit_fstore(op, xlen)
        elif typ == "FENCE":
            w = emit_fence()
        elif typ == "SYS":
            w = emit_sys(op)
        elif typ == "V":
            w = emit_vector(op, xlen)
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
    # write little-endian 32-bit words to stdout
    # (use buffer write for speed)
#    out = sys.stdout.buffer
#    for w in words:
#        print(f"{w:08x}")
#        out.write(struct.pack("<I", w))

    print("#include <stdint.h>\n#include <stddef.h>");
    print("uint32_t fuzz_buffer[] = {")
    for w in words:
        print(f"    0x{w:08x},")
    print("};")
    print("const size_t fuzz_buffer_len = sizeof(fuzz_buffer) / sizeof(uint32_t);");

if __name__ == "__main__":
    main()

