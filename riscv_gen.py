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
OP_FMA    = 0x5b   # (fused multiply-add)

GPRs = list(range(31)) # 31 since x31 shld not be touched
VREGS = list(range(32))
FREGS = list(range(32))
fence_called = False

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

# helpers for imm selection
# random signed immediate generator
def rand_simm(bits):
    if random.randint(0, 7) != 0:  # 7 out of 8 times
        return random.choice([-1, 0])
    lo = -(1 << (bits-1))
    hi = (1 << (bits-1)) - 1
    return random.randint(lo, hi)
# random unsigned immediate generator 
def rand_uimm(bits):
    if random.randint(0, 7) != 0:  # 7 out of 8 times
        return random.choice([0, (1 << bits) - 1])  # 0 or max unsigned (like all-1s)
    return random.randint(0, (1 << bits) - 1)



# mapping instruction -> (type, funct3, funct7/opcode fam)
# We'll implement many common mnemonics below. CSR mnemonics are intentionally omitted.

RV32I_TEMPLATES = [
    # R-type (opcode 0x33)
    ("ADD", "R", {"opcode":OP_R, "funct3":0x0, "funct7":0x00}),
    ("SUB", "R", {"opcode":OP_R, "funct3":0x0, "funct7":0x20}),
    ("SLL", "R", {"opcode":OP_R, "funct3":0x1, "funct7":0x00}),
    ("SLT", "R", {"opcode":OP_R, "funct3":0x2, "funct7":0x00}),
    ("SLTU","R", {"opcode":OP_R, "funct3":0x3, "funct7":0x00}),
    ("XOR", "R", {"opcode":OP_R, "funct3":0x4, "funct7":0x00}),
    ("SRL", "R", {"opcode":OP_R, "funct3":0x5, "funct7":0x00}),
    ("SRA", "R", {"opcode":OP_R, "funct3":0x5, "funct7":0x20}),
    ("OR",  "R", {"opcode":OP_R, "funct3":0x6, "funct7":0x00}),
    ("AND", "R", {"opcode":OP_R, "funct3":0x7, "funct7":0x00}),

    # I-type (opcode 0x13)
    ("ADDI","I", {"opcode":OP_IMM, "funct3":0x0}),
    ("SLTI","I", {"opcode":OP_IMM, "funct3":0x2}),
    ("SLTIU","I",{"opcode":OP_IMM, "funct3":0x3}),
    ("XORI","I", {"opcode":OP_IMM, "funct3":0x4}),
    ("ORI", "I", {"opcode":OP_IMM, "funct3":0x6}),
    ("ANDI","I", {"opcode":OP_IMM, "funct3":0x7}),

    # I_SHIFTS (I-type, opcode 0x13)
    ("SLLI", "SHIFT", {"opcode":OP_IMM, "funct3":0x1, "funct7":0x00}),    
    ("SRLI", "SHIFT", {"opcode":OP_IMM, "funct3":0x5, "funct7":0x00}),    
    ("SRAI", "SHIFT", {"opcode":OP_IMM, "funct3":0x5, "funct7":0x20}),  

    # Loads (I-type, opcode 0x03)
    ("LB",  "I", {"opcode":OP_LOAD, "funct3":0x0}),
    ("LH",  "I", {"opcode":OP_LOAD, "funct3":0x1}),
    ("LW",  "I", {"opcode":OP_LOAD, "funct3":0x2}),
    ("LBU", "I", {"opcode":OP_LOAD, "funct3":0x4}),   # missing in your list
    ("LHU", "I", {"opcode":OP_LOAD, "funct3":0x5}),   # missing in your list
    ("LWU", "I", {"opcode":OP_LOAD, "funct3":0x6}),   # RV64 only
    ("LD",  "I", {"opcode":OP_LOAD, "funct3":0x3}),   # RV64 only

    # Stores (S-type, opcode 0x23)
    ("SB", "S", {"opcode":OP_STORE, "funct3":0x0}),
    ("SH", "S", {"opcode":OP_STORE, "funct3":0x1}),
    ("SW", "S", {"opcode":OP_STORE, "funct3":0x2}),
    ("SD", "S", {"opcode":OP_STORE, "funct3":0x3}),     # RV64 only

    # Branches (B-type, opcode 0x63)
    ("BEQ",  "B", {"opcode":OP_BRANCH, "funct3":0x0}),
    ("BNE",  "B", {"opcode":OP_BRANCH, "funct3":0x1}),
    ("BLT",  "B", {"opcode":OP_BRANCH, "funct3":0x4}),
    ("BGE",  "B", {"opcode":OP_BRANCH, "funct3":0x5}),
    ("BLTU", "B", {"opcode":OP_BRANCH, "funct3":0x6}),
    ("BGEU", "B", {"opcode":OP_BRANCH, "funct3":0x7}),

    # Jumps and upper immediates
    ("JAL",   "J",  {"opcode":OP_JAL}),
    ("JALR",  "I", {"opcode":OP_JALR, "funct3":0x0}),  # I-type
    ("LUI",   "U",  {"opcode":OP_LUI}),
    ("AUIPC", "U",  {"opcode":OP_AUIPC}),

    # fences and misc
    ("FENCE",  "FENCE", {"opcode":OP_MISC,   "funct3":0x00}),
    ("ECALL",  "SYS",   {"opcode":OP_SYSTEM, "imm":0x00}),
    ("EBREAK", "SYS",   {"opcode":OP_SYSTEM, "imm":0x01}),
]

M_TEMPLATES = [
    # M_OPS (R-type, opcode 0x33)
    ("MUL",    "R", {"opcode":OP_R, "funct3":0x0, "funct7":0x01}),   
    ("MULH",   "R", {"opcode":OP_R, "funct3":0x1, "funct7":0x01}),   
    ("MULHSU", "R", {"opcode":OP_R, "funct3":0x2, "funct7":0x01}),   
    ("MULHU",  "R", {"opcode":OP_R, "funct3":0x3, "funct7":0x01}),   
    ("DIV",    "R", {"opcode":OP_R, "funct3":0x4, "funct7":0x01}),   
    ("DIVU",   "R", {"opcode":OP_R, "funct3":0x5, "funct7":0x01}),   
    ("REM",    "R", {"opcode":OP_R, "funct3":0x6, "funct7":0x01}),   
    ("REMU",   "R", {"opcode":OP_R, "funct3":0x7, "funct7":0x01}),     
]

AMO_TEMPLATES = [
    # Atomic AMO
    ("AMOSWAP.W", "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x01}),
    ("AMOADD.W",  "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x00}),
    ("AMOXOR.W",  "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x04}),
    ("AMOAND.W",  "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x0c}),
    ("AMOOR.W",   "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x08}),
    ("AMOMIN.W",  "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x10}),
    ("AMOMAX.W",  "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x14}),
    ("AMOMINU.W", "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x18}),
    ("AMOMAXU.W", "AMO", {"opcode": OP_AMO, "funct3":0x2,  "funct7":0x1c}),
]

FLOATING_TEMPLATES = [
    # Floating-point operations (F and D precision)
    ("FADD.S", "F", {"opcode": OP_FPU, "funct3": 0x0, "funct7": 0x00}),
    ("FSUB.S", "F", {"opcode": OP_FPU, "funct3": 0x0, "funct7": 0x08}),
    ("FMUL.S", "F", {"opcode": OP_FPU, "funct3": 0x0, "funct7": 0x10}),
    ("FDIV.S", "F", {"opcode": OP_FPU, "funct3": 0x0, "funct7": 0x18}),

    ("FADD.D", "F", {"opcode": OP_FPU, "funct3": 0x1, "funct7": 0x00}),
    ("FSUB.D", "F", {"opcode": OP_FPU, "funct3": 0x1, "funct7": 0x08}),
    ("FMUL.D", "F", {"opcode": OP_FPU, "funct3": 0x1, "funct7": 0x10}),
    ("FDIV.D", "F", {"opcode": OP_FPU, "funct3": 0x1, "funct7": 0x18}),
]

# Minimal vector-like templates (R-type with opcode 0x57). These are simple approximations to include vector encodings.
VECTOR_TEMPLATES = [
    ("VADD_VV",  "RV",  {"opcode": OP_VECTOR, "funct6": 0x00, "funct3": 0x0}),
    ("VSUB_VV",  "RV",  {"opcode": OP_VECTOR, "funct6": 0x04, "funct3": 0x0}),
    ("VMUL_VV",  "RV",  {"opcode": OP_VECTOR, "funct6": 0x01, "funct3": 0x0}),
    ("VDIV_VV",  "RV",  {"opcode": OP_VECTOR, "funct6": 0x02, "funct3": 0x0}),
    ("VAND_VV",  "RV",  {"opcode": OP_VECTOR, "funct6": 0x07, "funct3": 0x0}),
    ("VOR_VV",   "RV",  {"opcode": OP_VECTOR, "funct6": 0x06, "funct3": 0x0}),
    ("VXOR_VV",  "RV",  {"opcode": OP_VECTOR, "funct6": 0x05, "funct3": 0x0}),

    # R4-type (e.g. fused multiply-add)
    ("VFMADD_VV",  "R4", {"opcode": OP_FMA, "funct6": 0x00, "funct3": 0x0}),
    ("VFNMADD_VV", "R4", {"opcode": OP_FMA, "funct6": 0x01, "funct3": 0x0}),
    ("VFMSUB_VV",  "R4", {"opcode": OP_FMA, "funct6": 0x02, "funct3": 0x0}),
    ("VFNMSUB_VV", "R4", {"opcode": OP_FMA, "funct6": 0x03, "funct3": 0x0}),

    # I-type vector instructions (shifts)
    ("VSLL_VI", "I", {"opcode": OP_VECTOR, "funct6": 0x08, "funct3": 0x1}),
    ("VSRL_VI", "I", {"opcode": OP_VECTOR, "funct6": 0x09, "funct3": 0x1}),
    ("VSRA_VI", "I", {"opcode": OP_VECTOR, "funct6": 0x0a, "funct3": 0x1}),

    # M-type (vector mask instructions)
    ("VMAND_MM",   "M", {"opcode": OP_VECTOR, "funct6": 0x20, "funct3": 0x7}),
    ("VMNAND_MM",  "M", {"opcode": OP_VECTOR, "funct6": 0x21, "funct3": 0x7}),
    ("VMOR_MM",    "M", {"opcode": OP_VECTOR, "funct6": 0x22, "funct3": 0x7}),
    ("VMNOR_MM",   "M", {"opcode": OP_VECTOR, "funct6": 0x23, "funct3": 0x7}),
    ("VMXOR_MM",   "M", {"opcode": OP_VECTOR, "funct6": 0x24, "funct3": 0x7}),
    ("VMXNOR_MM",  "M", {"opcode": OP_VECTOR, "funct6": 0x25, "funct3": 0x7}),
    ("VMORNOT_MM", "M", {"opcode": OP_VECTOR, "funct6": 0x26, "funct3": 0x7}),

    ("VADD.VX",  "VECTOR", {"opcode": OP_VECTOR, "funct3":0x0, "funct6":0x01}),
    ("VSUB.VX",  "VECTOR", {"opcode": OP_VECTOR, "funct3":0x0, "funct6":0x05}),
    ("VMUL.VX",  "VECTOR", {"opcode": OP_VECTOR, "funct3":0x1, "funct6":0x01}),       
]

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

    return entry

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

def emit_jal(xlen):
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

def emit_fence(entry, xlen):
    rd=0
    rs1=0
    f3 = 0  # for both fence and fence.i

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
    # Best-effort OP_VECTOR encoding:
    vd = pick_vreg()
    vs1 = pick_vreg()
    vs2 = pick_vreg()
    vm = random.randint(0,1)

    name, instr_type, fields = entry
    opcode = fields["opcode"]
    f3 = fields.get("funct3")
    f6 = fields.get("funct6")

    # place bits:
    # funct6 -> bits 26..31
    # vm -> bit 25
    # rs2 -> bits20..24 (vs2)
    # rs1 -> bits15..19 (vs1)
    # funct3 -> bits12..14
    # rd -> bits7..11 (vd)
    encoded = ( (f6 & 0x3f) << 26 ) | ((vm & 0x1) << 25) | ( (vs2 & 0x1f) << 20) | ( (vs1 & 0x1f) << 15) | ((f3 & 0x7) << 12) | ((vd & 0x1f) << 7) | (opcode & 0x7f)
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
        if typ == "R" or "AMO":
            w = emit_r_ins(op, xlen)
        elif typ == "I":
            w = emit_i_ins(op, xlen)
        elif typ == "SHIFT":
            w = emit_shift_ins(op, xlen)
        elif typ == "S":
            w = emit_store(op, xlen)
        elif typ == "B":
            w = emit_branch(op, xlen)
        elif typ == "J":
            w = emit_jal(xlen)
        elif typ == "U":
            w = emit_u(op, xlen)
        elif typ == "M":
            # todo 
            break
        elif typ == "F":
            w = emit_fp(op, xlen)
        elif typ == "FLOAD":
            w = emit_fload(op, xlen)
            # todo: add FLW, FLD (FLOAD) FSW, FSD (FSTORE)
        elif typ == "FSTORE":
            w = emit_fstore(op, xlen)
        elif typ == "FENCE":
            w = emit_fence()
        elif typ == "SYS":
            w = emit_sys(op)
        elif typ == "RV":
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

