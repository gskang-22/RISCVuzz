// run3_hardcoded.c
// Hardcoded 3 instructions to test on Beagle board

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <signal.h>
#include <sys/mman.h>
#include <unistd.h>

static void sig_handler(int sig, siginfo_t *si, void *unused) {
    const char *name = (sig == SIGILL) ? "SIGILL" :
                       (sig == SIGSEGV) ? "SIGSEGV" :
                       (sig == SIGFPE) ? "SIGFPE" : "SIGNAL";
    fprintf(stderr, "Caught %s (signo=%d). si_addr=%p si_code=%d\n",
            name, sig, si ? si->si_addr : NULL, si ? si->si_code : 0);
    _exit(128 + sig);
}

static int install_handlers(void) {
    struct sigaction sa;
    sa.sa_sigaction = sig_handler;
    sigemptyset(&sa.sa_mask);
    sa.sa_flags = SA_SIGINFO;
    if (sigaction(SIGILL, &sa, NULL) == -1) return -1;
    if (sigaction(SIGSEGV, &sa, NULL) == -1) return -1;
    if (sigaction(SIGFPE, &sa, NULL) == -1) return -1;
    return 0;
}

int main(void) {
    if (install_handlers() != 0) {
        perror("sigaction");
        return 1;
    }

    // ----- Hardcoded instruction words -----
    uint32_t instrs[4] = {
        0x00007057,
0x5e054057,
0x02b981a7,

	    
	    0x00008067, //ret    

};

    size_t n_words = sizeof(instrs)/sizeof(instrs[0]);
    size_t bufsize = n_words * 4;

    void *buf = mmap(NULL, bufsize,
                     PROT_READ | PROT_WRITE | PROT_EXEC,
                     MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (buf == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    // Copy instructions into mmap buffer (little-endian)
    uint8_t *p = (uint8_t *)buf;
    for (size_t i = 0; i < n_words; ++i) {
        uint32_t w = instrs[i];
        p[i*4 + 0] = w & 0xff;
        p[i*4 + 1] = (w >> 8) & 0xff;
        p[i*4 + 2] = (w >> 16) & 0xff;
        p[i*4 + 3] = (w >> 24) & 0xff;
    }

    // Ensure instruction cache sees the new code
    __builtin___clear_cache((char *)buf, (char *)buf + bufsize);

    printf("Executing 3 hardcoded instructions at %p\n", buf);

    typedef void (*fn_t)(void);
    fn_t fn = (fn_t)buf;

    fn(); // Execute instructions

    printf("Execution returned normally.\n");
    munmap(buf, bufsize);

    return 0;
}
