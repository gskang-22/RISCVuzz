.section .trampoline, "ax"
.global signal_trampoline
.global _trampoline_start
.global _trampoline_end

_trampoline_start:
signal_trampoline:
    # Restore gp/tp
    la      t6, temp_storage
    ld      gp, 16(t6)
    ld      tp, 24(t6)

    # Call C signal handler
    la      t0, signal_handler
    jr      t0
_trampoline_end:

