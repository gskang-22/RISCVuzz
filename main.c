#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <arpa/inet.h>  // for htonl/ntohl
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdarg.h>

#define UART_DEV "/dev/ttyS4"   // adjust for your board
#define UART_BAUD B115200

#define LOG_BUF_SIZE 4096

int uart_fd;  // file descriptor for UART
char log_buffer[LOG_BUF_SIZE];
size_t log_len = 0;


int main() {
    int fd = open(UART_DEV, O_RDWR);
    if(fd < 0) { perror("open"); return 1; }

    char *msg = "Hello from board!\n";
    write(fd, msg, 18);

    char buf[100];
    int n = read(fd, buf, sizeof(buf));
    if(n > 0) {
        write(1, buf, n); // print to console
    }

    close(fd);
    return 0;
}
