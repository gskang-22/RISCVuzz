#include <stdint.h>
#include <stdio.h>

int main() {
    int compressed_supported = 0;

    // Attempt to execute a compressed instruction using inline assembly
    asm volatile (
        ".pushsection .text\n\t"
        ".hword 0x0001\n\t"     // c.nop (c.addi x0,0)
        ".popsection\n\t"
        "li %[out], 1\n\t"      // If we reach here, C extension worked
        : [out] "=r" (compressed_supported)
        :
        : 
    );

    if (compressed_supported) {
        printf("Compressed instructions supported!\n");
    } else {
        printf("Compressed instructions NOT supported!\n");
    }

    while (1); // Hang here for observation
}

