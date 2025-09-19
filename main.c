#include "main.h"

#include <fcntl.h>
#include <termios.h>
#include <unistd.h>

#include "client.h"
#include "sandbox.h"

extern uint8_t *sandbox_ptr;
extern mapped_region_t *g_regions;
extern memdiff_t *g_diffs;
extern void unmap_all_regions();
extern size_t g_regions_len;

#define SERVER_IP "192.168.10.1"
#define SERVER_PORT 9000
#define LOG_BUF_SIZE 4096

// #define TESTING
#define DEBUG_MODE

int sock;
char log_buffer[LOG_BUF_SIZE];
size_t log_len = 0;  // current length of string in buffer

int main() {
  g_regions = calloc(MAX_MAPPED_PAGES, sizeof(*g_regions));
  if (!g_regions) {
    perror("calloc g_regions");
    exit(1);
  }
  g_regions_len = 0;

  sandbox_ptr = allocate_executable_buffer();

#ifdef TESTING
  uint32_t instructions[] = {
      // instructions to be injected
      0x00dd31af,  // amoadd.d gp,a3,(s10)
      0x00dcb1af,  // amoadd.d gp,a3,(s9)
      0x00dc31af,  // amoadd.d gp,a3,(s8)
  };

  printf("Running sandbox 1...\n");
  fflush(stdout);
  run_client(instructions, sizeof(instructions) / sizeof(instructions[0]));
#else
  set_up_tcp();

  // send client name for identification
  const char *name = "beagle";
  uint32_t len = htonl(strlen(name));
  write_n(sock, &len, sizeof(len));   // send length
  write_n(sock, name, strlen(name));  // send name

  // loop: receive instructions, send back results
  while (1) {
    uint32_t batch_size_net;
    // closes client if server closed connection
    if (read_n(sock, &batch_size_net, sizeof(batch_size_net)) !=
        sizeof(batch_size_net)) {
      printf("Server closed connection\n");
      break;
    }

    // alternative way to close client: send batch size of 0
    uint32_t batch_size = ntohl(batch_size_net);
    if (batch_size == 0) {
      printf("No more instructions\n");
      break;
    }

    if (batch_size > (UINT32_MAX / sizeof(uint32_t)) ||
        batch_size > SOME_REASONABLE_LIMIT) {  // e.g., 1<<20
      fprintf(stderr, "batch_size too large: %u\n", batch_size);
      break;
    }

    uint32_t *instructions = malloc(batch_size * sizeof(uint32_t));
    if (!instructions) {
      perror("malloc");
      break;
    }

    if (read_n(sock, instructions, batch_size * sizeof(uint32_t)) !=
        (ssize_t)(batch_size * sizeof(uint32_t))) {
      fprintf(stderr, "short read or disconnect while reading instructions\n");
      free(instructions);
      break;
    }
    printf("Got %u instructions\n", batch_size);

    // convert each network-order word instruction with ntohl
    for (uint32_t i = 0; i < batch_size; i++) {
      instructions[i] = ntohl(instructions[i]);
      // printf("Instruction[%u] = 0x%08x\n", i, instructions[i]); //
      // prints instructions received
    }

    // run sandbox 1
    printf("Running sandbox 1...\n");
    fflush(stdout);
    log_append("sandbox ptr: %p\n", sandbox_ptr);
    run_client(instructions, batch_size);
    send_log();  // send results back

    // run sandbox 2
    printf("Running sandbox 2..\n");
    fflush(stdout);
    log_append("sandbox ptr: %p\n", sandbox_ptr);
    run_client(instructions, batch_size);
    send_log();  // send results back

    free(instructions);
    memset(g_regions, 0, MAX_MAPPED_PAGES * sizeof(*g_regions));
  }

  close(sock);

#endif

  free_executable_buffer(sandbox_ptr);  // unmap sandbox region
  unmap_all_regions();                  // unmap g_regions

  free(g_regions);
  g_regions = NULL;
  free(g_diffs);
  g_diffs = NULL;

  // clear mapped regions
  if (g_regions) {
    for (size_t i = 0; i < MAX_MAPPED_PAGES; i++) {
      if (g_regions[i].addr) {
        munmap(g_regions[i].addr, g_regions[i].len);
        g_regions[i].addr = NULL;
        g_regions[i].len = 0;
      }
    }
    memset(g_regions, 0, MAX_MAPPED_PAGES * sizeof(*g_regions));
  }

  printf("Done\n");
  return 0;
}

// read exactly n bytes, retry until all bytes received
ssize_t read_n(int fd, void *buf, size_t n) {
  size_t total = 0;
  while (total < n) {
    ssize_t ret = read(fd, (char *)buf + total, n - total);
    if (ret <= 0) return ret;  // error or disconnect
    total += ret;
  }
  return total;
}

ssize_t write_n(int fd, const void *buf, size_t n) {
  size_t total = 0;
  while (total < n) {
    ssize_t ret = write(fd, (char *)buf + total, n - total);
    if (ret <= 0) return ret;
    total += ret;
  }
  return total;
}

void log_append(const char *fmt, ...) {
  va_list args;
#ifdef DEBUG_MODE
  // Print immediately to stdout
  va_start(args, fmt);
  vprintf(fmt, args);
  fflush(stdout);
  va_end(args);
#endif

  // append to log buffer
  if (log_len >= LOG_BUF_SIZE - 1) return;  // buffer full

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
}

int send_log() {
  if (log_len == 0) return 0;

  // Send length prefix (network byte order)
  uint32_t len_net = htonl((uint32_t)log_len);
  if (write_n(sock, &len_net, sizeof(len_net)) != sizeof(len_net)) return -1;
  // Send the buffer itself
  if (write_n(sock, log_buffer, log_len) != (ssize_t)log_len) return -1;

  // Clear the buffer memory
  memset(log_buffer, 0, LOG_BUF_SIZE);  // <-- zero entire buffer
  log_len = 0;                          // reset length

  printf("log sent; resetting log\n");
  fflush(stdout);
  return 0;
  // example usage
  // send_log(sock);  // send accumulated logs to server
}

void set_up_tcp() {
  // write() on client --> reader on server
  // writer.write() on server --> read() on client

  // creates a new socket (IPv4, TCP)
  // sock: file descriptor used to send/receive
  sock = socket(AF_INET, SOCK_STREAM, 0);
  if (sock < 0) {
    perror("socket");
    exit(1);
  }

  struct sockaddr_in server_addr = {0};
  server_addr.sin_family = AF_INET;
  server_addr.sin_port = htons(SERVER_PORT);
  inet_pton(AF_INET, SERVER_IP, &server_addr.sin_addr);

  // attempt to establish TCP connection
  if (connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
    perror("connect");
    close(sock);
    exit(1);
  }

  // connection successful
  printf("Connected to server\n");
}
