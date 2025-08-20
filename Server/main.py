import subprocess
import json

# Start Node.js process once
node_proc = subprocess.Popen(
    ['node', '/home/szekang/Documents/RISCVuzz/Server/generator/main.mjs'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

def call_instruction(input_str):
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

# Example usages

instructions = ["add", "fadd.s", "jal"]
for instr in instructions:
    result = call_instruction(instr)
    print("Input:", instr)
    print(result["asm"])
    print("0x" + result["hex"])
    print("---")

instructions = ["vadd.vx", "vfadd.vf"]
for asm_input in instructions:
    output = call_rust_asm(asm_input)
    print(output)
    print("---")