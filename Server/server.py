# Aim: 
#     1. Generate test cases for the client to run 
#     2. Analyze the results sent back by client, and compare them (if there are multiple boards) 

import asyncio
import struct

INSTRUCTIONS = [
    0x00000013,  # NOP
    0x00100093,  # ADDI x1, x0, 1
    0x00200113,  # ADDI x2, x0, 2
    0x00308193,  # ADDI x3, x1, 3
] * 10  # fake fuzz batch

async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"Client connected: {addr}")

    # Send batch
    batch = INSTRUCTIONS
    header = struct.pack("<I", len(batch))
    payload = b"".join(struct.pack("<I", inst) for inst in batch)
    writer.write(header + payload)
    await writer.drain()

    # Read results
    header = await reader.readexactly(4)
    (count,) = struct.unpack("<I", header)
    results = []
    for _ in range(count):
        data = await reader.readexactly(4)
        (res,) = struct.unpack("<I", data)
        results.append(res)

    print(f"Got {len(results)} results from {addr}")
    print(results[:10], "...")

    writer.close()
    await writer.wait_closed()
    print(f"Client {addr} disconnected")

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 9000)
    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Server listening on {addrs}")

    async with server:
        await server.serve_forever()

asyncio.run(main())
