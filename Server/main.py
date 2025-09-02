import subprocess
import json
import random, time

# Function to read your cfg file
def read_cfg(filename):
    cfg = {}
    with open(filename) as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            if '=' in line:
                key, value = line.split('=', 1)
            else:
                # Allow whitespace separator too
                parts = line.split(None, 1)
                if len(parts) != 2:
                    continue
                key, value = parts

            key = key.strip()
            value = value.strip()

            # Convert lists (comma-separated)
            if ',' in value:
                value = [int(x) if x.strip().isdigit() or (x.strip()[0] == '-' and x.strip()[1:].isdigit()) else x.strip() for x in value.split(',')]
            else:
                # Convert numbers if possible
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except ValueError:
                    # Convert booleans
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False

            # Store in dictionary
            cfg[key] = value

    return cfg

def call_instruction(input_str, node_proc):
    # Send instruction to Node.js
    node_proc.stdin.write(input_str + "\n")
    node_proc.stdin.flush()
    
    # Read one line of JSON response
    output = node_proc.stdout.readline()
    data = json.loads(output)
    
    if 'error' in data:
        raise RuntimeError(data['error'])
    
    return data

def call_rust_asm(asm_line: str) -> str:
    # Replace with the path to your compiled Rust binary
    rust_bin = "/home/szekang/Documents/RISCVuzz/Server/vector_generator/target/release/rvv-as"
    
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

def check_flip(output, result, cfg):
    if random.random() < cfg["FLIP_PROBABILITY"]:
        # randomly flip bits, increasing number and randomness of instructions generated
        result = flip_bits(result, cfg)
        output.append("0x{:08x}".format(result & 0xffffffff))
    if random.random() < cfg["ENDIAN_PROBABILITY"]:
        # flip endianess of instruction
        result = flip_endian_32(result)
        output.append("0x{:08x}".format(result & 0xffffffff))

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
    "vaadd.vv", "vaadd.vx", "vaaddu.vv", "vaaddu.vx", "vadc.vim", "vadc.vvm", "vadc.vxm", "vadd.vi", "vadd.vv", "vadd.vx",
    "vand.vi", "vand.vv", "vand.vx", "vasub.vv", "vasub.vx", "vasubu.vv", "vasubu.vx", "vcompress.vm", "vcpop.m", "vdiv.vv",
    "vdiv.vx", "vdivu.vv", "vdivu.vx", "vfadd.vf", "vfadd.vv", "vfclass.v", "vfcvt.f.x.v", "vfcvt.f.xu.v", "vfcvt.rtz.x.f.v", "vfcvt.rtz.xu.f.v",
    "vfcvt.x.f.v", "vfcvt.xu.f.v", "vfdiv.vf", "vfdiv.vv", "vfirst.m", "vfmacc.vf", "vfmacc.vv", "vfmadd.vf", "vfmadd.vv", "vfmax.vf",
    "vfmax.vv", "vfmerge.vfm", "vfmin.vf", "vfmin.vv", "vfmsac.vf", "vfmsac.vv", "vfmsub.vf", "vfmsub.vv", "vfmul.vf", "vfmul.vv",
    "vfmv.f.s", "vfmv.s.f", "vfmv.v.f", "vfncvt.f.f.w", "vfncvt.f.x.w", "vfncvt.f.xu.w", "vfncvt.rod.f.f.w", "vfncvt.rtz.x.f.w", "vfncvt.rtz.xu.f.w", "vfncvt.x.f.w",
    "vfncvt.xu.f.w", "vfnmacc.vf", "vfnmacc.vv", "vfnmadd.vf", "vfnmadd.vv", "vfnmsac.vf", "vfnmsac.vv", "vfnmsub.vf", "vfnmsub.vv", "vfrdiv.vf",
    "vfrec7.v", "vfredmax.vs", "vfredmin.vs", "vfredosum.vs", "vfredusum.vs", "vfrsqrt7.v", "vfrsub.vf", "vfsgnj.vf", "vfsgnj.vv", "vfsgnjn.vf",
    "vfsgnjn.vv", "vfsgnjx.vf", "vfsgnjx.vv", "vfslide1down.vf", "vfslide1up.vf", "vfsqrt.v", "vfsub.vf", "vfsub.vv", "vfwadd.vf", "vfwadd.vv",
    "vfwadd.wf", "vfwadd.wv", "vfwcvt.f.f.v", "vfwcvt.f.x.v", "vfwcvt.f.xu.v", "vfwcvt.rtz.x.f.v", "vfwcvt.rtz.xu.f.v", "vfwcvt.x.f.v", "vfwcvt.xu.f.v", "vfwmacc.vf",
    "vfwmacc.vv", "vfwmsac.vf", "vfwmsac.vv", "vfwmul.vf", "vfwmul.vv", "vfwnmacc.vf", "vfwnmacc.vv", "vfwnmsac.vf", "vfwnmsac.vv", "vfwredosum.vs",
    "vfwredusum.vs", "vfwsub.vf", "vfwsub.vv", "vfwsub.wf", "vfwsub.wv", "vid.v", "viota.m", "vl1re16.v", "vl1re32.v", "vl1re64.v",
    "vl1re8.v", "vl2re16.v", "vl2re32.v", "vl2re64.v", "vl2re8.v", "vl4re16.v", "vl4re32.v", "vl4re64.v", "vl4re8.v", "vl8re16.v",
    "vl8re32.v", "vl8re64.v", "vl8re8.v", "vle1024.v", "vle1024ff.v", "vle128.v", "vle128ff.v", "vle16.v", "vle16ff.v", "vle256.v",
    "vle256ff.v", "vle32.v", "vle32ff.v", "vle512.v", "vle512ff.v", "vle64.v", "vle64ff.v", "vle8.v", "vle8ff.v", "vlm.v",
    "vloxei1024.v", "vloxei128.v", "vloxei16.v", "vloxei256.v", "vloxei32.v", "vloxei512.v", "vloxei64.v", "vloxei8.v", "vlse1024.v", "vlse128.v",
    "vlse16.v", "vlse256.v", "vlse32.v", "vlse512.v", "vlse64.v", "vlse8.v", "vluxei1024.v", "vluxei128.v", "vluxei16.v", "vluxei256.v",
    "vluxei32.v", "vluxei512.v", "vluxei64.v", "vluxei8.v", "vmacc.vv", "vmacc.vx", "vmadc.vi", "vmadc.vim", "vmadc.vv", "vmadc.vvm",
    "vmadc.vx", "vmadc.vxm", "vmadd.vv", "vmadd.vx", "vmand.mm", "vmandn.mm", "vmax.vv", "vmax.vx", "vmaxu.vv", "vmaxu.vx",
    "vmerge.vim", "vmerge.vvm", "vmerge.vxm", "vmfeq.vf", "vmfeq.vv", "vmfge.vf", "vmfgt.vf", "vmfle.vf", "vmfle.vv", "vmflt.vf",
    "vmflt.vv", "vmfne.vf", "vmfne.vv", "vmin.vv", "vmin.vx", "vminu.vv", "vminu.vx", "vmnand.mm", "vmnor.mm", "vmor.mm",
    "vmorn.mm", "vmsbc.vv", "vmsbc.vvm", "vmsbc.vx", "vmsbc.vxm", "vmsbf.m", "vmseq.vi", "vmseq.vv", "vmseq.vx", "vmsgt.vi",
    "vmsgt.vx", "vmsgtu.vi", "vmsgtu.vx", "vmsif.m", "vmsle.vi", "vmsle.vv", "vmsle.vx", "vmsleu.vi", "vmsleu.vv", "vmsleu.vx",
    "vmslt.vv", "vmslt.vx", "vmsltu.vv", "vmsltu.vx", "vmsne.vi", "vmsne.vv", "vmsne.vx", "vmsof.m", "vmul.vv", "vmul.vx",
    "vmulh.vv", "vmulh.vx", "vmulhsu.vv", "vmulhsu.vx", "vmulhu.vv", "vmulhu.vx", "vmv1r.v", "vmv2r.v", "vmv4r.v", "vmv8r.v",
    "vmv.s.x", "vmv.v.i", "vmv.v.v", "vmv.v.x", "vmv.x.s", "vmxnor.mm", "vmxor.mm", "vnclip.wi", "vnclip.wv", "vnclip.wx",
    "vnclipu.wi", "vnclipu.wv", "vnclipu.wx", "vnmsac.vv", "vnmsac.vx", "vnmsub.vv", "vnmsub.vx", "vnsra.wi", "vnsra.wv", "vnsra.wx",
    "vnsrl.wi", "vnsrl.wv", "vnsrl.wx", "vor.vi", "vor.vv", "vor.vx", "vredand.vs", "vredmax.vs", "vredmaxu.vs", "vredmin.vs",
    "vredminu.vs", "vredor.vs", "vredsum.vs", "vredxor.vs", "vrem.vv", "vrem.vx", "vremu.vv", "vremu.vx", "vrgather.vi", "vrgather.vv",
    "vrgather.vx", "vrgatherei16.vv", "vrsub.vi", "vrsub.vx", "vs1r.v", "vs2r.v", "vs4r.v", "vs8r.v", "vsadd.vi", "vsadd.vv",
    "vsadd.vx", "vsaddu.vi", "vsaddu.vv", "vsaddu.vx", "vsbc.vvm", "vsbc.vxm", "vse1024.v", "vse128.v", "vse16.v", "vse256.v",
    "vse32.v", "vse512.v", "vse64.v", "vse8.v", "vsetivli", "vsetvl", "vsetvli", "vsext.vf2", "vsext.vf4", "vsext.vf8",
    "vslide1down.vx", "vslide1up.vx", "vslidedown.vi", "vslidedown.vx", "vslideup.vi", "vslideup.vx", "vsll.vi", "vsll.vv", "vsll.vx", "vsm.v",
    "vsmul.vv", "vsmul.vx", "vsoxei1024.v", "vsoxei128.v", "vsoxei16.v", "vsoxei256.v", "vsoxei32.v", "vsoxei512.v", "vsoxei64.v", "vsoxei8.v",
    "vsra.vi", "vsra.vv", "vsra.vx", "vsrl.vi", "vsrl.vv", "vsrl.vx", "vsse1024.v", "vsse128.v", "vsse16.v", "vsse256.v",
    "vsse32.v", "vsse512.v", "vsse64.v", "vsse8.v", "vssra.vi", "vssra.vv", "vssra.vx", "vssrl.vi", "vssrl.vv", "vssrl.vx",
    "vssub.vv", "vssub.vx", "vssubu.vv", "vssubu.vx", "vsub.vv", "vsub.vx", "vsuxei1024.v", "vsuxei128.v", "vsuxei16.v", "vsuxei256.v",
    "vsuxei32.v", "vsuxei512.v", "vsuxei64.v", "vsuxei8.v", "vwadd.vv", "vwadd.vx", "vwadd.wv", "vwadd.wx", "vwaddu.vv", "vwaddu.vx",
    "vwaddu.wv", "vwaddu.wx", "vwmacc.vv", "vwmacc.vx", "vwmaccsu.vv", "vwmaccsu.vx", "vwmaccu.vv", "vwmaccu.vx", "vwmaccus.vx", "vwmul.vv",
    "vwmul.vx", "vwmulsu.vv", "vwmulsu.vx", "vwmulu.vv", "vwmulu.vx", "vwredsum.vs", "vwredsumu.vs", "vwsub.vv", "vwsub.vx", "vwsub.wv",
    "vwsub.wx", "vwsubu.vv", "vwsubu.vx", "vwsubu.wv", "vwsubu.wx", "vxor.vi", "vxor.vv", "vxor.vx", "vzext.vf2", "vzext.vf4", "vzext.vf8",
]

def main():
    # Start Node.js process once
    node_proc = subprocess.Popen(
        ['node', '/home/szekang/Documents/RISCVuzz/Server/generator/main.mjs'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True
    )
    # open config file
    # with open("/home/szekang/Documents/RISCVuzz/config.json") as f:
    #     cfg = json.load(f)
    cfg = read_cfg("/home/szekang/Documents/RISCVuzz/config.cfg")

    # generate fuzzing instructions for injection into sandbox
    output = []
    seed = int(time.time())
    random.seed(seed)
    # # Combine VECTOR and BASE instructions
    # all_instructions = VECTOR_INSTRUCTIONS + BASE_INSTRUCTIONS

    # # Randomly select one instruction
    # asm_input = random.choice(all_instructions)
    # print("Selected Input:", asm_input)

    # try:
    #     # Determine which function to call
    #     if asm_input in VECTOR_INSTRUCTIONS:
    #         result = int(call_rust_asm(asm_input), 16)
    #     else:
    #         result = int((call_instruction(asm_input, node_proc))["hex"], 16)

    #     formatted_result = "0x{:08x}".format(result & 0xffffffff)
    #     output.append(formatted_result)
    #     print("output:", formatted_result)

    #     # Call check_flip N times
    #     for _ in range(N):
    #         check_flip(output, result, cfg)

    # except RuntimeError as e:
    #     print("Input:", asm_input, " -> Error:", e)

    # print("-----------------------------------")

    for asm_input in VECTOR_INSTRUCTIONS:
        print("Input:" + asm_input)
        result = int(call_rust_asm(asm_input), 16)
        output.append("0x{:08x}".format(result & 0xffffffff))
        print("output:", "0x{:08x}".format(result))
        check_flip(output, result, cfg)
    print("-----------------------------------")
    for asm_input in BASE_INSTRUCTIONS:
        try:
            print("Input:", asm_input)
            result = int((call_instruction(asm_input, node_proc))["hex"], 16)
            output.append("0x{:08x}".format(result & 0xffffffff))
            print("output:", "0x{:08x}".format(result))
            check_flip(output, result, cfg)
        except RuntimeError as e:
            print("Input:", asm_input, " -> Error:", e)

if __name__ == "__main__":
    main()