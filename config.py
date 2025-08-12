
GPRs = list(range(32))
VREGS = list(range(32))
FREGS = list(range(32))

# Special test registers and immediates to bias toward
SPECIAL_GPRS = [0, 1, 2, 31]  # x0, ra, sp, t6
SPECIAL_FPRS = [0, 1, 31]     # f0, f1, f31
SPECIAL_VREGS = [0, 1, 31]
SPECIAL_SIMMS = [0, 1, -1, (1 << 11) - 1, -(1 << 11)]
SPECIAL_UIMMS = [0, 1, (1 << 12) - 1, (1 << 12), (1 << 10)]

GPR_SPECIAL = 0.2
FPR_SPECIAL = 0.2
VREG_SPECIAL = 0.3
IMM_SPECIAL = 0.875

FLIP_PROBABILITY = 0.5
ENDIAN_PROBABILITY = 0.5

# Opcodes (7-bit) — canonical major opcode values
OP_R        = 0x33   # 0110011
OP_IMM      = 0x13   # 0010011
OP_LUI      = 0x37   # 0110111
OP_AUIPC    = 0x17   # 0010111
OP_JAL      = 0x6f   # 1101111
OP_JALR     = 0x67   # 1100111
OP_BRANCH   = 0x63   # 1100011
OP_LOAD     = 0x03   # 0000011
OP_STORE    = 0x23   # 0100011
OP_MISC     = 0x0f   # 0001111 (fence)
OP_SYSTEM   = 0x73   # 1110011
OP_AMO      = 0x2f   # 0101111 (AMO/Atomic)

OP_FPU      = 0x53   # 1010011 (FP)
OP_LOAD_FP  = 0x07   # floating-point load
OP_STORE_FP = 0x27   # floating-point store

OP_VECTOR   = 0x57   # 1010111 (RVV, OP-V/OPIVV space)
OP_FMA      = 0x5b   # (fused multiply-add)

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
    # Atomic AMO (opcode 0x2f)
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
    # Floating-point operations (F and D precision) (opcode 0x53)
    ("FADD.S", "F", {"opcode": OP_FPU, "funct3": 0x0, "funct7": 0x00}),
    ("FSUB.S", "F", {"opcode": OP_FPU, "funct3": 0x0, "funct7": 0x08}),
    ("FMUL.S", "F", {"opcode": OP_FPU, "funct3": 0x0, "funct7": 0x10}),
    ("FDIV.S", "F", {"opcode": OP_FPU, "funct3": 0x0, "funct7": 0x18}),

    ("FADD.D", "F", {"opcode": OP_FPU, "funct3": 0x1, "funct7": 0x00}),
    ("FSUB.D", "F", {"opcode": OP_FPU, "funct3": 0x1, "funct7": 0x08}),
    ("FMUL.D", "F", {"opcode": OP_FPU, "funct3": 0x1, "funct7": 0x10}),
    ("FDIV.D", "F", {"opcode": OP_FPU, "funct3": 0x1, "funct7": 0x18}),
    
    # Floating-point loads (FLOAD) (opcode 0x07)
    ("FLW", "FLOAD", {"opcode": OP_LOAD_FP, "funct3": 0x2}),
    ("FLD", "FLOAD", {"opcode": OP_LOAD_FP, "funct3": 0x3}),

    # Floating-point stores (FSTORE) (opcode 0x27)
    ("FSW", "FSTORE", {"opcode": OP_STORE_FP, "funct3": 0x2}),
    ("FSD", "FSTORE", {"opcode": OP_STORE_FP, "funct3": 0x3}),
]

# Minimal vector-like templates (R-type with opcode 0x57). These are simple approximations to include vector encodings.
VECTOR_TEMPLATES = [
    ("VADD_VV",  "VR",  {"opcode": OP_VECTOR, "funct6": 0x00, "funct3": 0x0}),
    ("VSUB_VV",  "VR",  {"opcode": OP_VECTOR, "funct6": 0x04, "funct3": 0x0}),
    ("VMUL_VV",  "VR",  {"opcode": OP_VECTOR, "funct6": 0x01, "funct3": 0x0}),
    ("VDIV_VV",  "VR",  {"opcode": OP_VECTOR, "funct6": 0x02, "funct3": 0x0}),
    ("VAND_VV",  "VR",  {"opcode": OP_VECTOR, "funct6": 0x07, "funct3": 0x0}),
    ("VOR_VV",   "VR",  {"opcode": OP_VECTOR, "funct6": 0x06, "funct3": 0x0}),
    ("VXOR_VV",  "VR",  {"opcode": OP_VECTOR, "funct6": 0x05, "funct3": 0x0}),

    # R4-type (e.g. fused multiply-add)
    ("VFMADD_VV",  "VR4", {"opcode": OP_FMA, "funct6": 0x00, "funct3": 0x0}),
    ("VFNMADD_VV", "VR4", {"opcode": OP_FMA, "funct6": 0x01, "funct3": 0x0}),
    ("VFMSUB_VV",  "VR4", {"opcode": OP_FMA, "funct6": 0x02, "funct3": 0x0}),
    ("VFNMSUB_VV", "VR4", {"opcode": OP_FMA, "funct6": 0x03, "funct3": 0x0}),

    # I-type vector instructions (shifts)
    ("VSLL_VI", "VI", {"opcode": OP_VECTOR, "funct6": 0x08, "funct3": 0x1}),
    ("VSRL_VI", "VI", {"opcode": OP_VECTOR, "funct6": 0x09, "funct3": 0x1}),
    ("VSRA_VI", "VI", {"opcode": OP_VECTOR, "funct6": 0x0a, "funct3": 0x1}),

    # M-type (vector mask instructions)
    ("VMAND_MM",   "VM", {"opcode": OP_VECTOR, "funct6": 0x20, "funct3": 0x7}),
    ("VMNAND_MM",  "VM", {"opcode": OP_VECTOR, "funct6": 0x21, "funct3": 0x7}),
    ("VMOR_MM",    "VM", {"opcode": OP_VECTOR, "funct6": 0x22, "funct3": 0x7}),
    ("VMNOR_MM",   "VM", {"opcode": OP_VECTOR, "funct6": 0x23, "funct3": 0x7}),
    ("VMXOR_MM",   "VM", {"opcode": OP_VECTOR, "funct6": 0x24, "funct3": 0x7}),
    ("VMXNOR_MM",  "VM", {"opcode": OP_VECTOR, "funct6": 0x25, "funct3": 0x7}),
    ("VMORNOT_MM", "VM", {"opcode": OP_VECTOR, "funct6": 0x26, "funct3": 0x7}),

    ("VADD_VX",  "VX", {"opcode": OP_VECTOR, "funct3":0x0, "funct6":0x01}),
    ("VSUB_VX",  "VX", {"opcode": OP_VECTOR, "funct3":0x0, "funct6":0x05}),
    ("VMUL_VX",  "VX", {"opcode": OP_VECTOR, "funct3":0x1, "funct6":0x01}),       
]
