# Python code to generate RISC-V instruction words (hex) for fuzzing.
# This script supports:
# - R, I, S, B, U, J encodings for a subset of RV32I instructions (no CSR/system instructions)
# - Optional simple Vector-extension-like R-type encodings (toggleable)
# - Randomly-generated 32-bit instructions (controlled by random_ratio percent)
# - Immediate edge-cases: 0 or -1 most of the time; 1/8 chance of random immediate
# - Register selection random but never x31 (i.e., numbers 0..30)
#
# Example usage at the bottom: generates 16 instruction words and prints hex bytes little-endian.

import random
from typing import List, Tuple

# Helper utils for bit manipulation
def mask(x, bits):
    return x & ((1 << bits) - 1)

def sign_mask(x, bits):
    # get two's complement representation within bits
    return mask(x, bits)

def encode_r(func2, rs2, rs1, func1, rd, opcode):
    word = (mask(func2,7) << 25) | (mask(rs2,5) << 20) | (mask(rs1,5) << 15) | (mask(func1,3) << 12) | (mask(rd,5) << 7) | mask(opcode,7)
    return word

def encode_i(imm, rs1, func1, rd, opcode):
    imm12 = sign_mask(imm, 12)
    word = (imm12 << 20) | (mask(rs1,5) << 15) | (mask(func1,3) << 12) | (mask(rd,5) << 7) | mask(opcode,7)
    return word

def encode_s(imm, rs2, rs1, func1, opcode):
    imm12 = sign_mask(imm, 12)
    imm_11_5 = (imm12 >> 5) & 0x7F
    imm_4_0  = imm12 & 0x1F
    word = (imm_11_5 << 25) | (mask(rs2,5) << 20) | (mask(rs1,5) << 15) | (mask(func1,3) << 12) | (imm_4_0 << 7) | mask(opcode,7)
    return word

def encode_b(imm, rs2, rs1, func1, opcode):
    # Branch immediate is 13-bit signed, but LSB is zero (imm[12|10:5|4:1|11] << 1)
    imm13 = sign_mask(imm, 13)
    imm12 = (imm13 >> 12) & 0x1
    imm10_5 = (imm13 >> 5) & 0x3F
    imm4_1 = (imm13 >> 1) & 0xF
    imm11 = (imm13 >> 11) & 0x1
    word = (imm12 << 31) | (imm10_5 << 25) | (mask(rs2,5) << 20) | (mask(rs1,5) << 15) | (mask(func1,3) << 12) | (imm4_1 << 8) | (imm11 << 7) | mask(opcode,7)
    return word

def encode_u(imm, rd, opcode):
    imm20 = sign_mask(imm, 32) & 0xFFFFF000
    # imm passed is expected to be already aligned (lower 12 bits zero)
    word = (imm20) | (mask(rd,5) << 7) | mask(opcode,7)
    return word

def encode_j(imm, rd, opcode):
    # J-type immediate 21-bit (imm[20|10:1|11|19:12]) with LSB zero
    imm21 = sign_mask(imm, 21)
    imm20 = (imm21 >> 20) & 0x1
    imm10_1 = (imm21 >> 1) & 0x3FF
    imm11 = (imm21 >> 11) & 0x1
    imm19_12 = (imm21 >> 12) & 0xFF
    word = (imm20 << 31) | (imm19_12 << 12) | (imm11 << 20) | (imm10_1 << 21) | (mask(rd,5) << 7) | mask(opcode,7)
    return word

# Prevent use of x31 per user request
def rand_reg(exclude31=True):
    r = random.randint(0, 30) if exclude31 else random.randint(0, 31)
    return r

def choose_imm(edge_bias=True):
    # by default choose 0 or -1 as edge cases; 1/8 of time choose random immediate in allowed range
    if random.randint(1,8) == 1:
        return random.randint(- (1<<20), (1<<20)-1)  # reasonably wide random immediate
    return 0 if random.choice([True, False]) else -1

# Instruction templates (subset of RV32I)
# Each entry: (name, fmt, params)
# fmt: 'R','I','S','B','U','J'
# params: values or patterns we need (opcode, func1, func2)
# opcodes are 7-bit numbers
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

    # M_OPS (R-type, opcode 0x33)
    ("MUL",    "R", {"opcode":OP_R, "funct3":0x0, "funct7":0x01}),   
    ("MULH",   "R", {"opcode":OP_R, "funct3":0x1, "funct7":0x01}),   
    ("MULHSU", "R", {"opcode":OP_R, "funct3":0x2, "funct7":0x01}),   
    ("MULHU",  "R", {"opcode":OP_R, "funct3":0x3, "funct7":0x01}),   
    ("DIV",    "R", {"opcode":OP_R, "funct3":0x4, "funct7":0x01}),   
    ("DIVU",   "R", {"opcode":OP_R, "funct3":0x5, "funct7":0x01}),   
    ("REM",    "R", {"opcode":OP_R, "funct3":0x6, "funct7":0x01}),   
    ("REMU",   "R", {"opcode":OP_R, "funct3":0x7, "funct7":0x01}),     

    # Jumps and upper immediates
    ("JAL",   "J",  {"opcode":OP_JAL}),
    ("JALR",  "I", {"opcode":OP_JALR, "funct3":0x0}),  # I-type
    ("LUI",   "U",  {"opcode":OP_LUI}),
    ("AUIPC", "U",  {"opcode":OP_AUIPC}),

    # fences and misc
    ("FENCE",  "FENCE", {"opcode":OP_MISC,   "funct3":0x00}),
    ("ECALL",  "SYS",   {"opcode":OP_SYSTEM, "funct3":0x00}),
    ("EBREAK", "SYS",   {"opcode":OP_SYSTEM, "funct3":0x01}),
    
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

def generate_instruction_from_template(tpl, allow_vectors=False):
    name, fmt, p = tpl
    if fmt == "R":
        rd = rand_reg()
        rs1 = rand_reg()
        rs2 = rand_reg()
        func1 = p.get("func1", random.randint(0,7))
        func2 = p.get("func2", random.randint(0,0x7F))
        opcode = p["opcode"]
        return encode_r(func2, rs2, rs1, func1, rd, opcode)
    elif fmt == "I":
        rd = rand_reg()
        rs1 = rand_reg()
        imm = choose_imm()
        func1 = p.get("func1", random.randint(0,7))
        opcode = p["opcode"]
        return encode_i(imm, rs1, func1, rd, opcode)
    elif fmt == "S":
        rs1 = rand_reg()
        rs2 = rand_reg()
        imm = choose_imm()
        func1 = p.get("func1", random.randint(0,7))
        opcode = p["opcode"]
        return encode_s(imm, rs2, rs1, func1, opcode)
    elif fmt == "B":
        rs1 = rand_reg()
        rs2 = rand_reg()
        # Branch immediates should be multiples of 2; we'll generate small offsets
        imm = choose_imm()
        # ensure imm is aligned (LSB 0)
        imm = (imm & ~1)
        func1 = p.get("func1", random.randint(0,7))
        opcode = p["opcode"]
        return encode_b(imm, rs2, rs1, func1, opcode)
    elif fmt == "U":
        rd = rand_reg()
        # U-type immediate should be 32-bit with lower 12 bits zero; choose edgecases 0 or 0xFFFFF000 for -1 at top
        imm_choice = random.choice([0, -0x1000])
        opcode = p["opcode"]
        return encode_u(imm_choice, rd, opcode)
    elif fmt == "J":
        rd = rand_reg()
        imm = choose_imm()
        imm = (imm & ~1)  # align
        opcode = p["opcode"]
        return encode_j(imm, rd, opcode)
    else:
        # unknown format - return totally random 32-bit
        return random.getrandbits(32)

def generate_fuzz_instructions(count:int=100, include_vectors:bool=False, random_ratio:float=0.05)->List[str]:
    """
    Generate `count` instructions and return list of hex strings like '0x01234567' (32-bit little endian words).
    include_vectors: whether to include vector-like templates
    random_ratio: fraction (0..1) of totally random 32-bit words to include
    """
    templates = list(RV32I_TEMPLATES)
    if include_vectors:
        templates += VECTOR_TEMPLATES

    out = []
    for i in range(count):
        if random.random() < random_ratio:
            w = random.getrandbits(32)
        else:
            tpl = random.choice(templates)
            w = generate_instruction_from_template(tpl, allow_vectors=include_vectors)
        # present as 32-bit hex (target machine endian when injecting depends on sandbox; we show both little-endian byte order and word-hex)
        word_hex = "0x{:08x}".format(mask(w, 0xFFFFFFFF))
        # little-endian byte sequence often is used when writing bytes in memory; show also bytes
        b0 = mask(w,0xFF)
        b1 = mask(w>>8,0xFF)
        b2 = mask(w>>16,0xFF)
        b3 = mask(w>>24,0xFF)
        le_bytes = " ".join(f"{x:02x}" for x in (b0,b1,b2,b3))
        out.append(f"{word_hex}  ; LE bytes: {le_bytes}")
    return out

# Example: generate 16 fuzz instructions (vectors enabled, 10% totally random instructions)
if __name__ == "__main__":
    samples = generate_fuzz_instructions(16, include_vectors=True, random_ratio=0.10)
    for s in samples:
        print(s)