import struct
import serial

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

def read_n(ser, n):
    """Read exactly n bytes from serial port."""
    data = b''
    while len(data) < n:
        chunk = ser.read(n - len(data))
        if not chunk:
            raise IOError("UART disconnected or timeout")
        data += chunk
    return data

def read_results(ser, name):
    """Reads a length-prefixed string from UART and handles it."""
    # Step 1: read 4 bytes for message length
    length_bytes = read_n(ser, 4)
    if len(length_bytes) != 4:
        return False  # disconnected or timeout

    (msg_len,) = struct.unpack("!I", length_bytes)
    # Step 2: read the actual message
    data = read_n(ser, msg_len)
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
    print("Opening UART and waiting for client...")
    # beagle_ser = serial.Serial(UART_DEV, BAUD, timeout=1)
    beagle_ser = serial.Serial("/dev/ttyUSB0", 115200, timeout=1,
                           parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE,
                           bytesize=serial.EIGHTBITS,
                           xonxoff=False, rtscts=False)
    # If you have another board:
    # lichee_ser = serial.Serial("/dev/ttyUSB1", BAUD, timeout=1)

    # Wait for handshake
    print("Waiting for client name...")
    name_len_bytes = read_n(beagle_ser, 4)
    (name_len,) = struct.unpack("!I", name_len_bytes)
    name = read_n(beagle_ser, name_len).decode()
    print(f"Client connected: {name}")

    # Now you can send instructions or receive logs
    # Example: just read one log string
    log_len_bytes = read_n(beagle_ser, 4)
    (log_len,) = struct.unpack("!I", log_len_bytes)
    log = read_n(beagle_ser, log_len).decode()
    print(f"Received log: {log}")

    # Close UARTs
    beagle_ser.close()
    # lichee_ser.close()

if __name__ == "__main__":
    main()
