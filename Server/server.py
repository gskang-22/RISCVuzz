# Aim: 
#     1. Generate test cases for the client to run 
#     2. Analyze the results sent back by client, and compare them (if there are multiple boards) 

import asyncio
import struct

BATCH_SIZE = 10
INSTRUCTIONS = [
    0x00000013,  # NOP
    0x00100093,  # ADDI x1, x0, 1
    0x00200113,  # ADDI x2, x0, 2
    0x00308193,  # ADDI x3, x1, 3
] * 10  # fake fuzz batch

clients = {}  # name -> writer

def handle_beagle_results(results):
    # Read results

    print(f"[beagle] Got {len(results)} results")
    print(results[:10], "...")

def handle_lichee_results(results):
    return

# reads data from client and handles it 
async def read_results(reader, name):
    try:
        header = await reader.readexactly(4)
        (result_count,) = struct.unpack("!I", header)
        data = await reader.readexactly(result_count * 4)
        results = [int.from_bytes(data[i*4:(i+1)*4], 'big') for i in range(result_count)]

        # Handle results differently based on client name
        if name == "beagle":
            handle_beagle_results(results)
        elif name == "lichee":
            handle_lichee_results(results)

    except asyncio.IncompleteReadError:
    # todo: raise error and terminate
        return  # client disconnected

async def handle_client(reader, writer):
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
        while instr_index < len(INSTRUCTIONS):
            # Slice next N instructions
            batch = INSTRUCTIONS[instr_index:instr_index + BATCH_SIZE]
            instr_index += len(batch)

            # Send batch
            header = struct.pack("!I", len(batch))
            payload = b"".join(struct.pack("!I", inst) for inst in batch)
            writer.write(header + payload)
            await writer.drain()

            # Wait for results before sending next batch
            await read_results(reader, name)
            
        print(f"All instructions sent to {name}")

    except asyncio.IncompleteReadError:
        print(f"Client {name} disconnected unexpectedly")

    writer.close()
    await writer.wait_closed()
    print(f"Client {name} disconnected")

async def main():
    # creates a listening socket (TCP server)
    # handle_client: callback function
    server = await asyncio.start_server(handle_client, "0.0.0.0", 9000)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Server listening on {addrs}")

    # runs server forever
    async with server:
        await server.serve_forever()

# spawns handle_client() per connection
asyncio.run(main())
