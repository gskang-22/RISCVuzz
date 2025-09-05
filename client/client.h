#include <stdint.h>
#include <unistd.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <time.h>
#include <stdbool.h>

#define MAX_MAPPED_PAGES 4
int run_client(uint32_t *instructions, size_t n_instructions);
