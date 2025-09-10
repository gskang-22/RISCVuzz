#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <signal.h>
#include <setjmp.h>
#include <sys/mman.h>
#include <string.h>
#include <unistd.h>

sigjmp_buf jump_buffer;

void signal_handler(int signo) {
    printf("Caught signal %d\n", signo);
    siglongjmp(jump_buffer, 1);
}

int main() {
    // Install signal handlers
    struct sigaction sa;
    sa.sa_handler = signal_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = 0;
    sigaction(SIGILL, &sa, NULL);
    sigaction(SIGSEGV, &sa, NULL);

    // Allocate executable memory
    size_t pagesize = sysconf(_SC_PAGESIZE);
    uint32_t *code = mmap(NULL, pagesize,
                          PROT_READ | PROT_WRITE | PROT_EXEC,
                          MAP_ANONYMOUS | MAP_PRIVATE, -1, 0);
    if (code == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    // Inject your instruction (0x00dd31af)
    code[0] = 0x00dd31af;
    // Add ebreak after instruction to safely return
    code[1] = 0x00100073;

    if (sigsetjmp(jump_buffer, 1) == 0) {
        printf("Running instruction 0x00dd31af...\n");
        fflush(stdout);
        void (*func)() = (void(*)())code;
        func();  // execute instruction
        printf("Instruction executed without crashing\n");
    } else {
        printf("Instruction caused a fault, board did not crash\n");
    }

    munmap(code, pagesize);
    return 0;
}
