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
I_SHIFTS = {
    "slli": (0x1,0x00), 
    "srli": (0x5,0x00), 
    "srai": (0x5,0x20)}

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
