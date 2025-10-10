import struct
import asyncio
from generate import generate_instructions
import difflib

TESTING = False
DEBUG = False

instructions = [
0x8c05eb87, 0xcc05fb87, 0x3c05db87, 
0xa9e00bd7, 0xe280d407, 0x6c05eb87, 
0xfc05db87, 0x001b8063, 0x5e0f0bd7, 
0xb2eb8cd7, 0xd9e01bd7, 0x6815eba7, 
0x4c058b87, 0x6205fba7, 0xe0b0c18b, 
0x70a2ac57, 0x2c05fb87, 0xe2808f87, 
0xfbef9fd7, 0x1c05dba7, 0x03202033, 
0x01e08b80, 0xa7cf4057, 0xe205fb87, 
0x0de01bd7, 0x00000add, 0x31e0bbd7, 
0x61e00bd7, 0xf405ebd7, 0xe205db87, 
0xa9f0bfd7, 0x91e05bd7, 0x05e02bd7, 
0x67f43057, 0xa5e0cbd7, 0x4815db87, 
0x2815db87, 0x46803357, 0x3c05eb87, 
0x8205db87, 0x5815d18b, 0x3bffe1d7, 
0x00015d9b, 0x6015c18b, 0x68158ba7, 
0x6d7340d7, 0x000bb003, 0x42058b87, 
0xd90fa357, 0x09e05bd7, 
]

clients = {}  # name -> writer
log_lock = asyncio.Lock() # global lock 

async def log(msg):
    """Async-safe log function that prints and flushes immediately."""
    async with log_lock:
        print(msg, flush=True)  # prints to console
        with open("/home/szekang/Documents/RISCVuzz/console.log", "a") as logf:  # append to file
            logf.write(msg + "\n")
            logf.flush()

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

        if DEBUG == True:
            await log(f"[DEBUG] Expecting {msg_len} bytes from {name}")
            await log(f"[DEBUG] Actually got {len(data)} bytes")

        return message
    except asyncio.IncompleteReadError:
        return  # client disconnected

async def handle_client(reader, writer, instructions, cfg):
    # reader --> used to receive from client
    # writer --> used to send to client

    # Handshake: read client name
    name_len_data = await reader.readexactly(4)
    (name_len,) = struct.unpack("!I", name_len_data)
    name = (await reader.readexactly(name_len)).decode()
    clients[name] = (reader, writer)
    await log(f"Client connected: {name}")

    # wait until both clients are connected
    if "beagle" in clients and "lichee" in clients:
        await run_batches(instructions, cfg)

async def run_batches(instructions, cfg):
    # Each client independently runs the whole list
    instr_index = 0
    while instr_index < len(instructions):

        # Slice next N instructions
        batch = instructions[instr_index:instr_index + cfg["BATCH_SIZE"]]
        instr_index += len(batch)
        await log(f"instr_index: {instr_index}")

        # Send batch to both clients
        for name, (reader, writer) in clients.items():
            header = struct.pack("!I", len(batch))
            payload = b"".join(struct.pack("!I", inst) for inst in batch)
            writer.write(header + payload)
            await writer.drain()

        # --- First run ---
        tasks1 = {
            name: asyncio.create_task(read_results(reader, name))
            for name, (reader, writer) in clients.items()
        }
        run1_results = {name: await t for name, t in tasks1.items()}

        # --- Second run ---
        tasks2 = {
            name: asyncio.create_task(read_results(reader, name))
            for name, (reader, writer) in clients.items()
        }
        run2_results = {name: await t for name, t in tasks2.items()}

        # Wait for results before sending next batch
        results = {}
        # for name, (reader, writer) in clients.items():
        #     run1 = await read_results(reader, name)
        #     run2 = await read_results(reader, name)
        for name in clients:
            run1 = run1_results[name]
            run2 = run2_results[name]

            if run1 is None or run2 is None:
                return
            
            # Compare runs within client
            if run1 != run2:
                await log(f"[ERROR] Responses differ for client {name} on batch starting at index {instr_index - len(batch)}")
                await log(f"Instruction set 1:")
                await log(run1)
                await log(f"Instruction set 2:")
                await log(run2)

                await log("Diff between runs:")
                input("Paused for debugging. Press Enter to continue...")
                                
                # Split responses into lines and keep line endings
                diff = difflib.unified_diff(
                    run1.splitlines(keepends=True),
                    run2.splitlines(keepends=True),
                    fromfile=f"{name}-run1",
                    tofile=f"{name}-run2",
                )
                await log(''.join(diff))  # print the diff
            else:
                await log(f"[OK] {name} results are internally consistent")
                await log(run1)

            results[name] = run1

            # Cross-compare between clients
        if len(results) == 2:
            beagle, lichee = results.keys()
            if results[beagle] != results[lichee]:
                await log(f"Client{beagle} response 1:")
                await log(results[beagle])
                await log(f"Client{lichee} response 2:")
                await log(results[lichee])

                await log(f"[MISMATCH] Results differ between {beagle} and {lichee}")
                input("Paused for debugging. Press Enter to continue...")

                # Split responses into lines and keep line endings
                diff = difflib.unified_diff(
                    results[beagle].splitlines(keepends=True),
                    results[lichee].splitlines(keepends=True),
                    fromfile=beagle,
                    tofile=lichee,
                )
                await log("".join(diff))
            else:
                await log("[OK] Both clients produced identical results")
                await log(results[beagle])
    
    # All instructions have been sent
    await log(f"All instructions sent")
    for name, (reader, writer) in clients.items():
        writer.close()
        await writer.wait_closed()
        await log(f"Client {name} disconnected")
    clients.clear()
    instr_index = 0


async def main():
    # Clear the log file at startup
    open("/home/szekang/Documents/RISCVuzz/console.log", "w").close()

    # open config file
    cfg = read_cfg("/home/szekang/Documents/RISCVuzz/Server/config.cfg")

    if TESTING:
        global instructions
        await log(str([f"0x{inst:08x}" for inst in instructions]))
    else:
        instructions = generate_instructions(cfg)
        await log(str([f"0x{inst:08x}" for inst in instructions]))

    # creates a listening socket (TCP server)
    # handle_client: callback function
    async def client_handler(reader, writer):
        await handle_client(reader, writer, instructions, cfg)

    server = await asyncio.start_server(client_handler, "0.0.0.0", 9000)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    await log(f"Server listening on {addrs}")

    # runs server forever
    async with server:
        await server.serve_forever()

# spawns handle_client() per connection
asyncio.run(main())