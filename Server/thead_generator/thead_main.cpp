#include "thead_main.h"

Config cfg;

void *match_opcode = nullptr;        // placeholder, not used in encoding
void *match_th_load_pair = nullptr;  // rd != rs1
void *match_th_load_inc = nullptr;   // rd1 != rd2 && rd1 != rs && rd2 != rs
void *match_vs1_eq_vs2 = nullptr;
void *match_vd_eq_vs1_eq_vs2 = nullptr;

std::vector<std::string> list2 = {"th.lbib"};
void init_rng() { std::srand(static_cast<unsigned int>(std::time(nullptr))); }

// Random number helpers
int rand_range(int min, int max) {
  if (min > max) {
    throw std::runtime_error("min is greater than max for rand_range()");
  }
  return min + std::rand() % (max - min + 1);
}

int64_t rand_range64(int64_t min, int64_t max) {
  if (min > max) {
    throw std::runtime_error("min is greater than max for rand_range64()");
  }
  return min +
         (std::rand() % (max - min + 1));  // only works if max-min < RAND_MAX
}
// Example: generate signed immediate of `width` bits
int64_t gen_signed_imm(int width) {
  if (width <= 0 || width > 64)
    throw std::runtime_error("Invalid immediate width");
  int64_t min = -(1LL << (width - 1));
  int64_t max = (1LL << (width - 1)) - 1;
  return rand_range64(min, max);
}

// -------------------- Helpers -------------------- //
inline void insert_field(uint32_t &insn, uint32_t value, uint32_t mask,
                         int pos) {
  if (pos >= 32) {
    throw std::runtime_error("pos is greater than 32 for insert_field");
  }
  insn &= ~(mask << pos);         // clear field
  insn |= (value & mask) << pos;  // insert masked value

  //   std::cout << "Inserted " << ": value=0x" << std::hex << value << "
  //   mask=0x"
  //             << mask << " pos=" << std::dec << pos << " result_field=0x"
  //             << ((value & mask) << pos) << std::endl;
}

inline void insert_reg(uint32_t &insn, uint32_t reg, uint32_t mask, int pos) {
  insert_field(insn, reg, mask, pos);
}

inline void insert_imm(uint32_t &insn, int64_t imm, uint32_t mask, int pos) {
  insert_field(insn, static_cast<uint32_t>(imm), mask, pos);
}

// Encode instruction given operands and instruction entry
// handles d, s, t, r, D, S, T, U, XtsN@S, XtuN@S, V(d/s/t/m/i)
uint32_t encode(const THOpcode &entry) {
  srand(time(NULL) ^ getpid());  // mix in PID for uniqueness
  load_config("/home/szekang/Documents/RISCVuzz/Server/config.cfg");

  bool implicit_zero_offset = false;
  uint32_t insn = 0;
  int reg_idx = 0, vreg_idx = 0, xtu_idx = 0;

  const std::string &fmt = entry.format;
  size_t i = 0;

  while (i < fmt.size()) {
    char c = fmt[i];
    // std::cout << "c == " << c << std::endl;
    switch (c) {
      case '0':
        // the displacement must be zero for the next mem/imm field
        implicit_zero_offset = true;
        i++;
        break;

      // ------------------ General-purpose registers ------------------ //
      case 'd': {  // destination GPR (rd)
        insert_reg(insn, pick_gpr(), OP_MASK_RD, OP_SH_RD);
        ++i;
        break;
      }
      case 's': {  // source GPR (rs1)
        insert_reg(insn, pick_gpr(), OP_MASK_RS1, OP_SH_RS1);
        ++i;
        break;
      }
      case 't': {  // source GPR (rs2)
        insert_reg(insn, pick_gpr(), OP_MASK_RS2, OP_SH_RS2);
        ++i;
        break;
      }
      case 'r': {  // third GPR (rs3)
        insert_reg(insn, pick_gpr(), OP_MASK_RS3, OP_SH_RS3);
        ++i;
        break;
      }

        // ------------------ Floating-point registers ------------------ //
      case 'D': {  // FP dest (frd)
        insert_reg(insn, pick_fpr(), OP_MASK_RD, OP_SH_RD);
        ++i;
        break;
      }
      case 'S': {  // FP source 1 (frs1)
        insert_reg(insn, pick_fpr(), OP_MASK_RS1, OP_SH_RS1);
        ++i;
        break;
      }
      case 'T': {  // FP source 2 (frs2)
        insert_reg(insn, pick_fpr(), OP_MASK_RS2, OP_SH_RS2);
        ++i;
        break;
      }
      case 'U': {  // FP source 3 (frs3)
        insert_reg(insn, pick_fpr(), OP_MASK_RS3, OP_SH_RS3);
        ++i;
        break;
      }

      // ------------------ Vendor-specific Xt operands ------------------ //
      case 'X': {            // Vendor-specific operands
        switch (fmt[++i]) {  // advance past 'X' to look at next char
          case 't':          // T-head specific
          {
            bool is_signed;
            switch (fmt[++i]) {  // next char determines type
              case 'V': {
                ++i;  // move past 'V'
                if (i >= fmt.size() || fmt[i] != 'c')
                  throw std::runtime_error(
                      "Expected 'c' after XtV in instruction '" + entry.name +
                      "'");
                int imm = implicit_zero_offset
                              ? 0
                              : pick_uimm(11);  // Insert into instruction
                insert_imm(insn, imm, 11,
                           20);  // 11 bits wide VC field
                i++;             // move past 'c'
                implicit_zero_offset = false;
                continue;
              }

              case 'l': {  // literal token -- consume until next comma or end
                // In binutils this is matched to an assembler string (asarg)
                size_t lit_start = i + 1;
                size_t lit_end = lit_start;
                while (lit_end < fmt.size() && fmt[lit_end] != ',') {
                  ++lit_end;
                }
                i = lit_end;
                continue;
              }
              case 's':  // signed immediate
                is_signed = true;
                goto parse_ximm;
              case 'u':  // unsigned immediate
                is_signed = false;
                goto parse_ximm;
              default:
                throw std::runtime_error("Unknown Xt type in instruction '" +
                                         entry.name + "'");
            }

          parse_ximm: {
            // assumed: fmt[i] == 'X' and variable `is_signed` already set
            // find '@' separating width and position
            size_t at = fmt.find('@', i);
            if (at == std::string::npos)
              throw std::runtime_error("Malformed Xtu/s in instruction '" +
                                       entry.name + "'");

            // find the first digit after the 'X' piece (skip any letters
            // like 't','s','u')
            size_t digit_start = i + 1;
            while (digit_start < fmt.size() &&
                   !isdigit((unsigned char)fmt[digit_start]))
              ++digit_start;

            if (digit_start >= at)
              throw std::runtime_error(
                  "Malformed Xtu/s width in instruction '" + entry.name + "'");

            // Parse width (N)
            std::string width_str = fmt.substr(digit_start, at - digit_start);
            int width = 0;
            try {
              width = std::stoi(width_str);
            } catch (...) {
              throw std::runtime_error(
                  "Failed to parse immediate width in instruction '" +
                  entry.name + "'");
            }
            if (width <= 0 || width > 64)
              throw std::runtime_error(
                  "Immediate width out of range (1..64) in instruction '" +
                  entry.name + "'");

            // Parse position (S)
            size_t pos_start = at + 1;
            size_t pos_end = pos_start;
            while (pos_end < fmt.size() && isdigit((unsigned char)fmt[pos_end]))
              ++pos_end;
            if (pos_start == pos_end)
              throw std::runtime_error(
                  "Malformed Xtu/s position in instruction '" + entry.name +
                  "'");

            int pos = std::stoi(fmt.substr(pos_start, pos_end - pos_start));

            // Generate immediate
            int64_t imm = 0;
            if (!implicit_zero_offset) {
              if (is_signed) {
                imm = pick_simm(width);  // signed
              } else {
                imm = pick_uimm(width);  // unsigned
              }
            }

            // insert into instruction
            // std::cout << "imm == " << imm << std::endl;
            insert_imm(insn, imm, width, pos);
            i = pos_end;
            implicit_zero_offset = false;
            break;
          }
          } break;
        }
        break;
      }  // end case 'X'

      // RVV operands (multi-character like VtVm)
      case 'V': {
        if (i + 1 >= fmt.size())
          throw std::runtime_error("Malformed V operand in '" + entry.name +
                                   "'");
        char rvv = fmt[++i];  // look at the letter after 'V'

        // single declarations for reuse across cases (avoid shadowing)
        int regno;
        int imm_val;

        switch (rvv) {
          case 'd':  // VD
            insert_reg(insn, pick_vreg(), OP_MASK_VD, OP_SH_VD);
            break;
          case 's':  // VS1
            insert_reg(insn, pick_vreg(), OP_MASK_VS1, OP_SH_VS1);
            break;
          case 't':  // VS2
            insert_reg(insn, pick_vreg(), OP_MASK_VS2, OP_SH_VS2);
            break;
          case 'u': {  // VS1 == VS2
            regno = pick_vreg();
            insert_reg(insn, regno, OP_MASK_VS1, OP_SH_VS1);
            insert_reg(insn, regno, OP_MASK_VS2, OP_SH_VS2);
            break;
          }
          case 'v': {  // VD == VS1 == VS2
            regno = pick_vreg();
            insert_reg(insn, regno, OP_MASK_VD, OP_SH_VD);
            insert_reg(insn, regno, OP_MASK_VS1, OP_SH_VS1);
            insert_reg(insn, regno, OP_MASK_VS2, OP_SH_VS2);
            break;
          }
          case 'm': {                  // optional vector mask (VM)
            uint32_t vm = rand() & 1;  // 0 = masked, 1 = unmasked
            insert_reg(insn, vm, OP_MASK_VMASK, OP_SH_VMASK);
          } break;
          case 'i': {  // signed imm (-16..15), 5 bits
            int imm_val =
                implicit_zero_offset
                    ? 0
                    : pick_simm(5);  // signed 5-bit immediate -> width 5
            insert_imm(insn, imm_val, OP_MASK_VIMM, OP_SH_VIMM);
            implicit_zero_offset = false;
          } break;
          case 'j': {  // unsigned imm (0..31), 5 bits
            int imm_val = implicit_zero_offset ? 0 : pick_uimm(5);
            insert_imm(insn, imm_val, OP_MASK_VIMM, OP_SH_VIMM);
            implicit_zero_offset = false;
            break;
          }
          case 'k': {  // signed imm (-15..16), encoded as imm-1
            int imm_val = implicit_zero_offset ? 0 : pick_simm(5);
            insert_imm(insn, imm_val - 1, OP_MASK_VIMM, OP_SH_VIMM);
            implicit_zero_offset = false;
            break;
          }
          case 'e': {  // AMO VD (Ve)
            // In assembler, "Ve" can be x0 (GPR zero) or a vector register.
            // In fuzzer: choose randomly.
            bool use_zero = rand() & 1;
            if (use_zero) {
              // Encodes as VWD=0 (means x0 case, no destination vector)
              insert_reg(insn, 0, OP_MASK_VWD, OP_SH_VWD);  // VWD=0
            } else {
              // Pick a random vector register (0..31)
              insert_reg(insn, 1, OP_MASK_VWD, OP_SH_VWD);  // VWD=1
              insert_reg(insn, pick_vreg(), OP_MASK_VD, OP_SH_VD);
            }
            break;
          }
          case 'f': {  // AMO VS3 (f)
            // Decide randomly whether VWD=0 (no VD) or VWD=1
            bool use_vd = rand() & 1;

            if (!use_vd) {
              insert_reg(insn, 0, OP_MASK_VWD,
                         OP_SH_VWD);  // VWD = 0, skip VD
            } else {
              insert_reg(insn, 1, OP_MASK_VWD, OP_SH_VWD);  // VWD = 1
              insert_reg(insn, pick_vreg(), OP_MASK_VD,
                         OP_SH_VD);  // VD = random vector reg
            }

            break;
          }
          case '0': {  // carry-in / V0
            // Randomly choose 0 or 1 for the V0 field
            uint32_t v0 = rand() & 1;
            insert_reg(insn, v0, OP_MASK_VMASK,
                       OP_SH_VMASK);  // same encoding as VM
            break;
          }
          default:
            throw std::runtime_error(std::string("Unknown RVV operand: V") +
                                     rvv + " in instruction '" + entry.name +
                                     "'");
        }
        i++;
        break;
      }  // end case 'V'

      // Skip delimiters
      case ',':  // in bin-utils: compares actual assembly input (like "x1,
                 // x2") to format string (like "d,s")
      case ')':
      case '(':
        ++i;
        break;

      default:
        throw std::runtime_error("Unknown operand in instruction '" +
                                 entry.name + "' at format string index " +
                                 std::to_string(i) + ": '" + c + "'");
    }
  }

  insn |= entry.match;  // Apply fixed opcode bits
  return insn;
}

const THOpcode *find_opcode(const std::string &name) {
  for (auto &op : th_opcodes) {
    if (op.name == name) return &op;
  }
  return nullptr;
}

// Example usage
// int main() {
//   srand(time(NULL) ^ getpid());  // mix in PID for uniqueness
//   load_config("/home/szekang/Documents/RISCVuzz/Server/config.cfg");
//   for (const auto &item : list2) {
//     const THOpcode *op = find_opcode(item.c_str());
//     if (!op) {
//       std::cerr << "Opcode not found: " << item << "\n";
//       continue;
//     }
//     uint32_t encoded = encode(*op);
//     // std::cout << item << " --> Encoded: 0x" << std::hex << std::setw(8)
//     //           << std::setfill('0') << encoded << "\n";
//   }
//   return 0;
// }

std::vector<uint32_t> parse_uint_list(const std::string &line) {
  std::vector<uint32_t> result;
  std::stringstream ss(line);
  std::string item;
  while (std::getline(ss, item, ',')) {
    if (!item.empty()) result.push_back(std::stoul(item));
  }
  return result;
}

std::vector<int32_t> parse_int_list(const std::string &line) {
  std::vector<int32_t> result;
  std::stringstream ss(line);
  std::string item;
  while (std::getline(ss, item, ',')) {
    if (!item.empty()) result.push_back(std::stoi(item));
  }
  return result;
}

void load_config(const std::string &filename) {
  std::ifstream file(filename);
  std::string line;

  while (std::getline(file, line)) {
    // Skip empty lines or comments
    if (line.empty() || line[0] == '#') continue;

    // Split key = value
    auto eq_pos = line.find('=');
    if (eq_pos == std::string::npos) continue;

    std::string key = line.substr(0, eq_pos);
    std::string value = line.substr(eq_pos + 1);

    // Remove spaces
    key.erase(remove_if(key.begin(), key.end(), ::isspace), key.end());
    value.erase(remove_if(value.begin(), value.end(), ::isspace), value.end());

    // Assign to cfg
    if (key == "GPRs")
      cfg.GPRs = parse_uint_list(value);
    else if (key == "SPECIAL_GPRS")
      cfg.SPECIAL_GPRS = parse_uint_list(value);
    else if (key == "GPR_SPECIAL")
      cfg.GPR_SPECIAL = std::stod(value);

    else if (key == "FREGs")
      cfg.FREGs = parse_uint_list(value);
    else if (key == "SPECIAL_FPRS")
      cfg.SPECIAL_FPRS = parse_uint_list(value);
    else if (key == "FPR_SPECIAL")
      cfg.FPR_SPECIAL = std::stod(value);

    else if (key == "VREGs")
      cfg.VREGs = parse_uint_list(value);
    else if (key == "SPECIAL_VREGS")
      cfg.SPECIAL_VREGS = parse_uint_list(value);
    else if (key == "VREG_SPECIAL")
      cfg.VREG_SPECIAL = std::stod(value);

    else if (key == "SPECIAL_SIMMS")
      cfg.SPECIAL_SIMMS = parse_int_list(value);
    else if (key == "SPECIAL_UIMMS")
      cfg.SPECIAL_UIMMS = parse_uint_list(value);
    else if (key == "IMM_SPECIAL")
      cfg.IMM_SPECIAL = std::stod(value);

    else if (key == "ENDIAN_PROBABILITY")
      cfg.ENDIAN_PROBABILITY = std::stod(value);
    else if (key == "FLIP_PROBABILITY")
      cfg.FLIP_PROBABILITY = std::stod(value);
    else if (key == "MAX_FLIPS")
      cfg.MAX_FLIPS = std::stoi(value);

    // VLMUL probabilities (flattened)
    else if (key.find("VLMUL_PROBABILITIES.") == 0) {
      std::string name = key.substr(20);  // remove prefix
      cfg.VLMUL_PROBABILITIES.emplace_back(name, std::stod(value));
    }
  }
}

uint32_t pick_gpr(bool avoidZero, const std::vector<uint32_t> &exclude) {
  const std::vector<uint32_t> *pool = &cfg.GPRs;
  if (((double)rand() / RAND_MAX) < cfg.GPR_SPECIAL) {
    pool = &cfg.SPECIAL_GPRS;
  }

  uint32_t val;
  do {
    val = (*pool)[rand() % pool->size()];
  } while ((avoidZero && val == 0) ||
           (std::find(exclude.begin(), exclude.end(), val) != exclude.end()));
  return val;
}

uint32_t pick_fpr(bool avoidZero, const std::vector<uint32_t> &exclude) {
  const std::vector<uint32_t> *pool = &cfg.FREGs;
  if (((double)rand() / RAND_MAX) < cfg.FPR_SPECIAL) {
    pool = &cfg.SPECIAL_FPRS;
  }

  uint32_t val;
  do {
    val = (*pool)[rand() % pool->size()];
  } while ((avoidZero && val == 0) ||
           (std::find(exclude.begin(), exclude.end(), val) != exclude.end()));
  return val;
}

uint32_t pick_vreg(bool avoidZero, const std::vector<uint32_t> &exclude) {
  const std::vector<uint32_t> *pool = &cfg.VREGs;
  if (((double)rand() / RAND_MAX) < cfg.VREG_SPECIAL) {
    pool = &cfg.SPECIAL_VREGS;
  }

  uint32_t val;
  do {
    val = (*pool)[rand() % pool->size()];
  } while ((avoidZero && val == 0) ||
           (std::find(exclude.begin(), exclude.end(), val) != exclude.end()));
  return val;
}

int32_t pick_simm(int width) {
  if (width <= 0 || width > 32)
    throw std::runtime_error("Invalid signed immediate width");

  int32_t min = -(1 << (width - 1));
  int32_t max = (1 << (width - 1)) - 1;
  int32_t mask = (1 << width) - 1;

  if (((double)rand() / RAND_MAX) < cfg.IMM_SPECIAL &&
      !cfg.SPECIAL_SIMMS.empty()) {
    int32_t val = cfg.SPECIAL_SIMMS[rand() % cfg.SPECIAL_SIMMS.size()];
    val &= mask;  // mask to width bits
    // sign-extend if the top bit is 1
    if (val & (1 << (width - 1))) val |= ~mask;
    return val;
  }

  return rand_range(min, max);
}

uint32_t pick_uimm(int width) {
  if (width <= 0 || width > 32)
    throw std::runtime_error("Invalid unsigned immediate width");

  uint32_t max_mask = (1U << width) - 1;

  if (((double)rand() / RAND_MAX) < cfg.IMM_SPECIAL &&
      !cfg.SPECIAL_UIMMS.empty()) {
    uint32_t val = cfg.SPECIAL_UIMMS[rand() % cfg.SPECIAL_UIMMS.size()];
    return val & max_mask;  // keep only 'width' bits
  }

  return rand_range(0, max_mask);
}
