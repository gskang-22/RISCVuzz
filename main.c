#include "main.h"
#include "client.h"
#include "sandbox.h"
#include <termios.h>
#include <fcntl.h>
#include <unistd.h>

extern uint8_t *sandbox_ptr;
extern mapped_region_t *g_regions;
extern memdiff_t *g_diffs;
extern void unmap_all_regions();

#define SERVER_IP "192.168.10.1" 
#define SERVER_PORT 9000

#define LOG_BUF_SIZE 4096

// int sock;
int serial_fd;
char log_buffer[LOG_BUF_SIZE];
size_t log_len = 0;  // current length of string in buffer

int open_serial(const char *device, int baud) {
    int fd = open(device, O_RDWR | O_NOCTTY | O_SYNC);
    if (fd < 0) { perror("open"); return -1; }

    struct termios tty;
    if (tcgetattr(fd, &tty) != 0) { perror("tcgetattr"); close(fd); return -1; }

    cfsetospeed(&tty, B115200);
    cfsetispeed(&tty, B115200);

    tty.c_cflag = (tty.c_cflag & ~CSIZE) | CS8;     // 8-bit chars
    tty.c_iflag &= ~IGNBRK;         // disable break processing
    tty.c_lflag = 0;                // no signaling chars, no echo, no canonical
    tty.c_oflag = 0;                // no remapping, no delays
    tty.c_cc[VMIN]  = 1;            // read doesn't block
    tty.c_cc[VTIME] = 5;            // 0.5s timeout

    tty.c_iflag &= ~(IXON | IXOFF | IXANY); // shut off xon/xoff ctrl

    tty.c_cflag |= (CLOCAL | CREAD);// ignore modem controls, enable reading
    tty.c_cflag &= ~(PARENB | PARODD);      // shut off parity
    tty.c_cflag &= ~CSTOPB;
    tty.c_cflag &= ~CRTSCTS;

    if (tcsetattr(fd, TCSANOW, &tty) != 0) { perror("tcsetattr"); close(fd); return -1; }
    return fd;
}

ssize_t read_n(int fd, void *buf, size_t n) {
    size_t total = 0;
    while (total < n) {
        ssize_t ret = read(fd, (char*)buf + total, n - total);
        if (ret <= 0) return ret;  // error or disconnect
        total += ret;
    }
    return total;
}

ssize_t read_exact(int fd, void *buf, size_t n) {
    size_t total = 0;
    char *p = buf;
    while (total < n) {
        ssize_t r = read(fd, p + total, n - total);
        if (r < 0) { perror("read"); return -1; }
        if (r == 0) { usleep(1000); continue; } // no data yet
        total += r;
    }
    return total;
}

ssize_t write_n(int fd, const void *buf, size_t n) {
    size_t total = 0;
    while (total < n) {
        ssize_t ret = write(fd, (char*)buf + total, n - total);
        if (ret <= 0) return ret;
        total += ret;
    }
    return total;
}

void log_append(const char *fmt, ...) {
    if (log_len >= LOG_BUF_SIZE - 1) return;  // buffer full

    va_list args;
    va_start(args, fmt);
    int n = vsnprintf(log_buffer + log_len, LOG_BUF_SIZE - log_len, fmt, args);

    va_end(args);

    if (n > 0) {
        log_len += (size_t)n;
        if (log_len >= LOG_BUF_SIZE) {
            log_len = LOG_BUF_SIZE - 1;
            log_buffer[log_len] = '\0';
        }
    }
    // example usage
//     log_append("Batch %d executed\n", batch_number);
//     log_append("Register x1 = 0x%x\n", regs_after[1]);
}

int send_log() {
    if (log_len == 0) return 0;

    // Print log locally first
    printf("=== CLIENT LOG START ===\n");
    fwrite(log_buffer, 1, log_len, stdout);  // print raw buffer
    printf("\n=== CLIENT LOG END ===\n");
    fflush(stdout);

    // Send length prefix (network byte order)
    uint32_t len_net = htonl((uint32_t)log_len);
    if (write_n(serial_fd, &len_net, sizeof(len_net)) != sizeof(len_net)) return -1;
    // Send the buffer itself
    if (write_n(serial_fd, log_buffer, log_len) != (ssize_t)log_len) return -1;

    log_len = 0;  // reset after sending
    log_buffer[0] = '\0';
    printf("log sent; resetting log\n");
    fflush(stdout);
    return 0;
    // example usage
    // send_log(sock);  // send accumulated logs to server
}

int send_string(int serial_fd, const char *msg) {
    uint32_t len = htonl(strlen(msg));   // 4-byte length prefix
    if (write(serial_fd, &len, sizeof(len)) != sizeof(len)) return -1;  // send length
    if (write(serial_fd, msg, strlen(msg)) != (ssize_t)strlen(msg)) return -1; // send string
    return 0;
}

int main() {

    g_regions = calloc(MAX_MAPPED_PAGES, sizeof(*g_regions));
    sandbox_ptr = allocate_executable_buffer();
#ifdef TESTING
    uint32_t instructions[] = {
    // instructions to be injected
    0x00000013, // nop
};

    printf("Running sandbox 1...\n");
    fflush(stdout);
    run_client(instructions, sizeof(instructions) / sizeof(instructions[0]));  
#endif
#ifndef TESTING
    serial_fd = open_serial("/dev/ttyS0", 115200);
    if (serial_fd < 0) exit(1);
    
    // connection successful
    printf("Connected to server\n");
    fflush(stdout);

    // loop: receive instructions, send back results 
    while (1) {
        uint32_t batch_size_net;
        write_n(serial_fd, &batch_size_net, sizeof(batch_size_net));

        uint32_t batch_size = ntohl(batch_size_net);
        printf("Batch size: %u\n", batch_size);
        fflush(stdout);

        // alternative way to close client: send batch size of 0
        if (batch_size == 0) {
            printf("No more instructions\n");
            fflush(stdout);
            break;
        }

        uint32_t *instructions = malloc(batch_size * sizeof(uint32_t));
        if (!instructions) { 
            perror("malloc"); 
            break; 
        }               
        if (read_exact(serial_fd, instructions, batch_size * sizeof(uint32_t)) != 
            (ssize_t)(batch_size * sizeof(uint32_t))) {
            fprintf(stderr, "short read or disconnect while reading instructions\n");
            fflush(stdout);
            free(instructions);
            break;
        }
        printf("Got %u instructions\n", batch_size);
        fflush(stdout);

        // convert each network-order word instruction with ntohl
        for (uint32_t i = 0; i < batch_size; i++) {
            instructions[i] = ntohl(instructions[i]);
            // printf("Instruction[%u] = 0x%08x\n", i, instructions[i]); // prints instructions received
        }
        // run sandbox 1
        printf("Running sandbox 1...\n");
        fflush(stdout);
        log_append("sandbox ptr: %p\n", sandbox_ptr);
        run_client(instructions, batch_size);    
        send_log(); // send results back
        // run sandbox 2
        printf("Running sandbox 2..\n");
        fflush(stdout);
        log_append("sandbox ptr: %p\n", sandbox_ptr);
        run_client(instructions, batch_size);    
        send_log(); // send results back
        free(instructions);
    }

    close(serial_fd);
#endif
    free_executable_buffer(sandbox_ptr); // unmap sandbox region
    unmap_all_regions();                 // unmap g_regions

    free(g_regions);
    g_regions = NULL;
    free(g_diffs);
    g_diffs = NULL;

    printf("Done\n");
    return 0;
}
