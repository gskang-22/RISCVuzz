import struct
import serial
import time

BATCH_SIZE = 10
INSTRUCTIONS = [
    0x00000013,  # NOP
    0x00100093,  # ADDI x1, x0, 1
    0x00200113,  # ADDI x2, x0, 2
    0x00308193,  # ADDI x3, x1, 3
] * 10  # fake fuzz batch

# UART device on the PC side (USB-UART)
UART_DEV = "/dev/ttyUSB0"
BAUD = 115200

clients = {}  # name -> serial.Serial object

def handle_beagle_results(message):
    # Do any analysis you want here
    print(f"[beagle] {message[:200]}...")  # truncate long messages

def handle_lichee_results(message):
    print(f"[lichee] {message[:200]}...")  # truncate long messages

def read_results(ser, name):
    """Reads a length-prefixed string from UART and handles it."""
    # Step 1: read 4 bytes for message length
    length_bytes = ser.read(4)
    if len(length_bytes) != 4:
        return False  # disconnected or timeout

    (msg_len,) = struct.unpack("!I", length_bytes)
    # Step 2: read the actual message
    data = ser.read(msg_len)
    if len(data) != msg_len:
        return False

    message = data.decode(errors="replace")
    print(f"[{name}] {message}")

    # dispatch by client
    if name == "beagle":
        handle_beagle_results(message)
    elif name == "lichee":
        handle_lichee_results(message)
    return True

def send_batch(ser, batch):
    """Sends a batch of instructions over UART (length-prefixed)."""
    header = struct.pack("!I", len(batch))
    payload = b"".join(struct.pack("!I", inst) for inst in batch)
    ser.write(header + payload)
    ser.flush()

def handle_client(name, ser):
    """Handles a single client (blocking)."""
    clients[name] = ser
    print(f"Client connected: {name}")

    instr_index = 0
    while instr_index < len(INSTRUCTIONS):
        batch = INSTRUCTIONS[instr_index:instr_index + BATCH_SIZE]
        instr_index += len(batch)

        send_batch(ser, batch)
        if not read_results(ser, name):
            print(f"Client {name} disconnected")
            break

    print(f"All instructions sent to {name}")

def main():
    # Open UARTs for each board
    beagle_ser = serial.Serial(UART_DEV, BAUD, timeout=1)
    # If you have another board:
    # lichee_ser = serial.Serial("/dev/ttyUSB1", BAUD, timeout=1)

    # Assume first thing each client sends is its name
    name_bytes = beagle_ser.read(4)
    (name_len,) = struct.unpack("!I", name_bytes)
    name = beagle_ser.read(name_len).decode()
    handle_client(name, beagle_ser)

    # Close UARTs
    beagle_ser.close()
    # lichee_ser.close()

if __name__ == "__main__":
    main()
