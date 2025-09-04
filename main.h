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

void log_append(const char *fmt, ...);
int send_log(int sock);
