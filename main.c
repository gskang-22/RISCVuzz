#include "main.h"
#include "client.h"
#include "sandbox.h"

extern uint8_t *sandbox_ptr;
extern mapped_region_t *g_regions;

#define SERVER_IP "192.168.10.1" 
#define SERVER_PORT 9000

#define LOG_BUF_SIZE 4096

int sock;
char log_buffer[LOG_BUF_SIZE];
size_t log_len = 0;  // current length of string in buffer

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

    // Send length prefix (network byte order)
    uint32_t len_net = htonl((uint32_t)log_len);
    if (write(sock, &len_net, sizeof(len_net)) != sizeof(len_net)) return -1;
    // Send the buffer itself
    if (write(sock, log_buffer, log_len) != (ssize_t)log_len) return -1;

    log_len = 0;  // reset after sending
    log_buffer[0] = '\0';
    printf("log sent; resetting log\n");
    fflush(stdout);
    return 0;
    // example usage
    // send_log(sock);  // send accumulated logs to server
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

ssize_t write_n(int fd, const void *buf, size_t n) {
    size_t total = 0;
    while (total < n) {
        ssize_t ret = write(fd, (char*)buf + total, n - total);
        if (ret <= 0) return ret;
        total += ret;
    }
    return total;
}

int send_string(int sock, const char *msg) {
    uint32_t len = htonl(strlen(msg));   // 4-byte length prefix
    if (write(sock, &len, sizeof(len)) != sizeof(len)) return -1;  // send length
    if (write(sock, msg, strlen(msg)) != (ssize_t)strlen(msg)) return -1; // send string
    return 0;
}

int main() {

    g_regions = calloc(MAX_MAPPED_PAGES, sizeof(*g_regions));
    setup_signal_handlers();
    unmap_vdso_vvar();
    sandbox_ptr = allocate_executable_buffer();
    log_append("sandbox ptr: %p\n", sandbox_ptr);

    run_client();
    return 0;
    // creates a new socket (IPv4, TCP)
    // sock: file descriptor used to send/receive
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) { perror("socket"); exit(1); }

    struct sockaddr_in server_addr = {0};
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(SERVER_PORT);
    inet_pton(AF_INET, SERVER_IP, &server_addr.sin_addr);
    
    // attempt to establish TCP connection
    if (connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("connect"); close(sock); exit(1);
    }

    // connection successful
    printf("Connected to server\n");
    
    // write() on client --> reader on server
    // writer.write() on server --> read() on client

    // send client name for identification
    const char *name = "beagle";
    uint32_t len = htonl(strlen(name));
    write(sock, &len, sizeof(len));   // send length
    write(sock, name, strlen(name));  // send name

    // loop: receive instructions, send back results 
    while (1) {
        uint32_t batch_size_net;
        // closes client if server closed connection
        if (read_n(sock, &batch_size_net, sizeof(batch_size_net)) != sizeof(batch_size_net)) {
            printf("Server closed connection\n");
            break;
        }
        
        // alternative way to close client: send batch size of 0
        uint32_t batch_size = ntohl(batch_size_net);
        if (batch_size == 0) {
            printf("No more instructions\n");
            break;
        }

        uint32_t *instructions = malloc(batch_size * sizeof(uint32_t));
        read_n(sock, instructions, batch_size * sizeof(uint32_t));
        printf("Got %u instructions\n", batch_size);

        run_client(); // runs sandbox 

        // Then send results back
        send_log();
        // uint32_t result_count_net = htonl(batch_size);
        // write_n(sock, &result_count_net, sizeof(result_count_net));
        // for (uint32_t i = 0; i < batch_size; i++) {
        //     uint32_t val = htonl(instructions[i]);
        //     write_n(sock, &val, sizeof(uint32_t));
        // }    

    free(instructions);
    }

    close(sock);
    printf("Done\n");
    return 0;
}
