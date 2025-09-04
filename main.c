#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#define SERVER_IP "192.168.10.1" 
#define SERVER_PORT 9000

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
    // creates a new socket (IPv4, TCP)
    // sock: file descriptor used to send/receive
    int sock = socket(AF_INET, SOCK_STREAM, 0);
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

        // Todo: make this actually run the instructions.
        // For now, just echo them back as "results".
        uint32_t result_count_net = htonl(batch_size);
        write_n(sock, &result_count_net, sizeof(result_count_net));
        for (uint32_t i = 0; i < batch_size; i++) {
            uint32_t val = htonl(instructions[i]);
            write_n(sock, &val, sizeof(uint32_t));
        }    

    free(instructions);
    }

    close(sock);
    printf("Done\n");
    return 0;
}
