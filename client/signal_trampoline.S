    .section .text
    .globl signal_trampoline
    .extern temp_storage

signal_trampoline:
    # a0 = signo
    # a1 = siginfo*
    # a2 = ucontext*

    # Restore gp and tp first so libc can work
    la      t6, temp_storage
    ld      gp, 16(t6)       # saved_gp
    ld      tp, 24(t6)       # saved_tp

    # Now call the C handler: void signal_handler(int, siginfo*, void*)
    la      t0, signal_handler
    jr      t0

