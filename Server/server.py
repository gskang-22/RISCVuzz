import struct
import asyncio
import serial_asyncio
from generate import generate_instructions

# Map UART ports to board names
UART_PORTS = {
    # "/dev/ttyUSB0": "lichee",
    "/dev/ttyUSB1": "beagle",
}
BAUD = 115200

instructions = [
    # instructions to be injected
    # 0x00000013, # nop
    # 0x10028027, # ghostwrite
    # 0xFFFFFFFF, # illegal instruction
    # 0x00008067, # ret
    # 0x00050067, # jump to x10
    # 0x00048067, # jump to x9
    # 0x00058067, # jump to x11
    # 0x0000a103, # lw x2, 0(x1)
    # 0x0142b183, # ld x3, 20(x5)
    0x00dd31af,
]

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

def write_msg(writer, payload: bytes):
    header = struct.pack("!I", len(payload))
    writer.write(header + payload)

def handle_beagle_results(message):
    # Read results

    # print(f"[beagle] Got {len(results)} results")
    # print(results[:10], "...")
    return

def handle_lichee_results(message):
    return

# reads data from client and handles it 
async def read_results(reader, name, port):
    try:
        # Step 1: read 4-byte length
        length_data = await reader.readexactly(4)
        (msg_len,) = struct.unpack("!I", length_data)
        # Step 2: read message bytes
        data = await reader.readexactly(msg_len)
        # Step 3: decode and print
        message = data.decode(errors="replace")  # safe decode
        # print(f"{message}")

        # Handle results differently based on client name
        if name == "beagle":
            handle_beagle_results(message)
        elif name == "lichee":
            handle_lichee_results(message)
        return message

    except asyncio.IncompleteReadError:
        print(f"[{port}] disconnected")
        return None  # client disconnected

async def handle_uart(port, board_name, instructions, cfg):
    # reader --> used to receive from client
    # writer --> used to send to client

    print(f"[{board_name} on {port}] Opening UART...")
    reader, writer = await serial_asyncio.open_serial_connection(
        url=port, baudrate=BAUD
    )

    instr_index = 0
    try:
        while instr_index < len(instructions):
            batch = instructions[instr_index:instr_index + cfg["BATCH_SIZE"]]
            instr_index += len(batch)

            # Send
            payload = b"".join(struct.pack("!I", inst) for inst in batch)
            write_msg(writer, payload)
            await writer.drain()
            print(f"[{port}] Sent batch (index {instr_index})")

            # Wait for 2 replies
            response1 = await read_results(reader, board_name, port)
            response2 = await read_results(reader, board_name, port)

            if response1 is None or response2 is None:
                break

            if response1 != response2:
                print(f"[{board_name}] ERROR: responses differ")
                #todo: print differences
            else:
                print(f"[{board_name}] OK: responses match")

        print(f"[{port}] All instructions sent")
        writer.write(struct.pack("!I", 0))  # 4-byte length of 0

    finally:
        writer.close()
        await writer.wait_closed()
        print(f"[{board_name} on {port}] closed")

async def main():
    cfg = read_cfg("/home/szekang/Documents/RISCVuzz/config.cfg")

    tasks = [handle_uart(port, name, instructions, cfg) for port, name in UART_PORTS.items()]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())