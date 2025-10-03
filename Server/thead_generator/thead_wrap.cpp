#include <cstdint>

#include "thead_main.h"  // your find_opcode(), encode(), etc.

extern "C" {
uint32_t encode_thead(const char* mnemonic) {
  const THOpcode* op = find_opcode(mnemonic);
  if (!op) return 0xffffffff;  // invalid marker
  return encode(*op);
}
}
