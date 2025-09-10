# Aim: 
#     1. Generate test cases for the client to run 
#     2. Analyze the results sent back by client, and compare them (if there are multiple boards) 

import asyncio
import struct
from generate import generate_instructions

instructions = [
    # instructions to be injected
    0x00000013, # nop
    0x10028027, # ghostwrite
    0xFFFFFFFF, # illegal instruction
    0x00008067, # ret
    0x00050067, # jump to x10
    0x00048067, # jump to x9
    0x00058067, # jump to x11
    0x0000a103, # lw x2, 0(x1)
    0x0142b183, # ld x3, 20(x5)
    0x00dd31af,
]

clients = {}  # name -> writer

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

def handle_beagle_results(message):
    # Read results

    # print(f"[beagle] Got {len(results)} results")
    # print(results[:10], "...")
    return

def handle_lichee_results(message):
    return

# reads data from client and handles it 
async def read_results(reader, name):
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
    # todo: raise error and terminate
        return  # client disconnected

async def handle_client(reader, writer, instructions, cfg):
    # reader --> used to receive from client
    # writer --> used to send to client

    # Handshake: read client name
    name_len_data = await reader.readexactly(4)
    (name_len,) = struct.unpack("!I", name_len_data)
    name = (await reader.readexactly(name_len)).decode()

    clients[name] = writer  # store writer by name
    print(f"Client connected: {name}")

    # # sending a string 
    # msg = "Hello, Beagle!"
    # msg_bytes = msg.encode()              # convert to bytes
    # header = struct.pack("!I", len(msg_bytes))  # 4-byte length
    # writer.write(header + msg_bytes)
    # await writer.drain()

    # Each client independently runs the whole list
    instr_index = 0
    try:
        while instr_index < len(instructions):
            # Slice next N instructions
            batch = instructions[instr_index:instr_index + cfg["BATCH_SIZE"]]
            instr_index += len(batch)
            print(f"instr_index: {instr_index}")
            # Send batch
            header = struct.pack("!I", len(batch))
            payload = b"".join(struct.pack("!I", inst) for inst in batch)
            writer.write(header + payload)
            await writer.drain()

            # Wait for results before sending next batch
            # await read_results(reader, name)
            response1 = await read_results(reader, name)
            response2 = await read_results(reader, name)

            # Compare responses
            if response1 != response2:
                print(f"[ERROR] Responses differ for client {name} on batch starting at index {instr_index - len(batch)}")
                print(f"Instruction set 1:")
                print(response1)
                print(f"Instruction set 2:")
                print(response2)
            else:
                print(f"{name}: responses are the same")
                print(response1)

        print(f"All instructions sent to {name}")

    except asyncio.IncompleteReadError:
        print(f"Client {name} disconnected unexpectedly")

    writer.close()
    await writer.wait_closed()
    print(f"Client {name} disconnected")

async def main():

    # open config file
    cfg = read_cfg("/home/szekang/Documents/RISCVuzz/config.cfg")
    global instructions
    # instructions = generate_instructions(cfg)
    # print([f"0x{inst:08x}" for inst in instructions])

    # creates a listening socket (TCP server)
    # handle_client: callback function
    async def client_handler(reader, writer):
        await handle_client(reader, writer, instructions, cfg)

    server = await asyncio.start_server(client_handler, "0.0.0.0", 9000)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Server listening on {addrs}")

    # runs server forever
    async with server:
        await server.serve_forever()

# spawns handle_client() per connection
asyncio.run(main())