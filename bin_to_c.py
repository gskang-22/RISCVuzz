#!/usr/bin/env python3
import sys
import struct

def bin_to_c_array(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()

    if len(data) % 4 != 0:
        print("Error: file size is not a multiple of 4 bytes", file=sys.stderr)
        sys.exit(1)

    words = struct.unpack("<" + "I" * (len(data) // 4), data)

    print("uint32_t fuzz_buffer[] = {")
    for w in words:
        print(f"    0x{w:08x},")
    print("};")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} input.bin", file=sys.stderr)
        sys.exit(1)
    bin_to_c_array(sys.argv[1])

