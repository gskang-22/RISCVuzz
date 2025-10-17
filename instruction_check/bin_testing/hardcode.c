// inject_exec.c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <string.h>
#include <unistd.h>

// helper to print bytes
static void hexdump(const uint8_t *p, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        printf("%02x ", p[i]);
    }
    printf("\n");
}

int main(void) {
    // Example: you can replace these bytes with any instruction bytes (LE order).
    // Example sequence: compressed c.nop (0x0001 -> bytes 0x01,0x00),
    // then 32-bit addi x0,x0,0 (0x00000013 -> bytes 0x13,0x00,0x00,0x00).
    // NOTE: replace/add bytes with your own machine-code bytes obtained from objdump.
    uint8_t code_bytes[] = {
    0x57, 0x70, 0x00, 0x00,   // 0x00007057
    0x57, 0x40, 0x05, 0x5e,   // 0x5e054057
    0xa7, 0x81, 0xb9, 0x02    // 0x02b981a7
    };
    size_t code_size = sizeof(code_bytes);

    // mmap a page-aligned RWX buffer
    size_t pagesz = sysconf(_SC_PAGESIZE);
    size_t alloc_size = ((code_size + pagesz - 1) / pagesz) * pagesz;

    void *buf = mmap(NULL, alloc_size,
                     PROT_READ | PROT_WRITE | PROT_EXEC,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (buf == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    // copy bytes
    memcpy(buf, code_bytes, code_size);

    // important: ensure icache sees the new code
    // GCC/Clang builtin to clear instruction cache
    __builtin___clear_cache((char*)buf, (char*)buf + code_size);

    printf("Injected %zu bytes at %p:\n", code_size, buf);
    hexdump((uint8_t*)buf, code_size);

    // Call the injected code. It must obey the ABI if it touches regs/stack.
    // Use a function pointer with no arguments and no return for simplicity.
    typedef void (*fn_t)(void);
    fn_t fn = (fn_t)buf;

    printf("About to call injected code — it may SIGILL if instruction unsupported.\n");
    fflush(stdout);

    // call it
    fn();

    printf("Returned from injected code (if it didn't SIGILL or crash)\n");

    // clean up
    munmap(buf, alloc_size);
    return 0;
}

