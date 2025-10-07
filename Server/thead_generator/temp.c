static struct riscv_ip_error riscv_ip(char *str, struct riscv_cl_insn *ip,
                                      expressionS *imm_expr,
                                      bfd_reloc_code_real_type *imm_reloc,
                                      htab_t hash) {
  /* The operand string defined in the riscv_opcodes.  */
  const char *oparg, *opargStart;
  /* The parsed operands from assembly.  */
  char *asarg, *asargStart;
  char save_c = 0;
  struct riscv_opcode *insn;
  unsigned int regno;
  const struct percent_op_match *p;
  struct riscv_ip_error error;
  error.msg = "unrecognized opcode";
  error.statement = str;
  error.missing_ext = NULL;
  /* Indicate we are assembling instruction with CSR.  */
  bool insn_with_csr = false;
  bool force_reloc = false;

  /* Parse the name of the instruction.  Terminate the string if whitespace
     is found so that str_hash_find only sees the name part of the string.  */
  for (asarg = str; *asarg != '\0'; ++asarg)
    if (is_whitespace(*asarg)) {
      save_c = *asarg;
      *asarg++ = '\0';
      break;
    }

  insn = str_hash_find(hash, str);

  probing_insn_operands = true;

  asargStart = asarg;
  for (; insn && insn->name && strcmp(insn->name, str) == 0; insn++) {
    if ((insn->xlen_requirement != 0) && (xlen != insn->xlen_requirement))
      continue;

    if (!riscv_multi_subset_supports(&riscv_rps_as, insn->insn_class)) {
      error.missing_ext =
          riscv_multi_subset_supports_ext(&riscv_rps_as, insn->insn_class);
      continue;
    }

    /* Reset error message of the previous round.  */
    error.msg = _("illegal operands");
    error.missing_ext = NULL;

    /* Purge deferred symbols from the previous round, if any.  */
    while (deferred_sym_rootP) {
      symbolS *sym = deferred_sym_rootP;

      symbol_remove(sym, &deferred_sym_rootP, &deferred_sym_lastP);
      symbol_append(sym, orphan_sym_lastP, &orphan_sym_rootP,
                    &orphan_sym_lastP);
    }

    create_insn(ip, insn);

    imm_expr->X_op = O_absent;
    *imm_reloc = BFD_RELOC_UNUSED;
    p = percent_op_null;

    for (oparg = insn->args;; ++oparg) {
      opargStart = oparg;
      while (is_whitespace(*asarg)) ++asarg;
      switch (*oparg) {
        case '\0': /* End of args.  */
          if (insn->match_func && !insn->match_func(insn, ip->insn_opcode))
            break;

          if (insn->pinfo != INSN_MACRO) {
            /* For .insn, insn->match and insn->mask are 0.  */
            if (riscv_insn_length((insn->match == 0 && insn->mask == 0)
                                      ? ip->insn_opcode
                                      : insn->match) == 2 &&
                !riscv_opts.rvc)
              break;

            if (riscv_is_priv_insn(ip->insn_opcode)) explicit_priv_attr = true;

            /* Check if we write a read-only CSR by the CSR
               instruction.  */
            if (insn_with_csr && riscv_opts.csr_check &&
                !riscv_csr_read_only_check(ip->insn_opcode)) {
              /* Restore the character in advance, since we want to
                 report the detailed warning message here.  */
              if (save_c) *(asargStart - 1) = save_c;
              as_warn(_("read-only CSR is written `%s'"), str);
              insn_with_csr = false;
            }

            /* The (segmant) load and store with EEW 64 cannot be used
               when zve32x is enabled.  */
            if (ip->insn_mo->pinfo & INSN_V_EEW64 &&
                riscv_subset_supports(&riscv_rps_as, "zve32x") &&
                !riscv_subset_supports(&riscv_rps_as, "zve64x")) {
              error.msg = _("illegal opcode for zve32x");
              break;
            }
          }
          if (*asarg != '\0') break;

          /* Successful assembly.  */
          error.msg = NULL;
          insn_with_csr = false;

          /* Commit deferred symbols, if any.  */
          while (deferred_sym_rootP) {
            symbolS *sym = deferred_sym_rootP;

            symbol_remove(sym, &deferred_sym_rootP, &deferred_sym_lastP);
            symbol_append(sym, symbol_lastP, &symbol_rootP, &symbol_lastP);
            symbol_table_insert(sym);
          }
          goto out;

        case 'V': /* RVV */
          switch (*++oparg) {
            case 'd': /* VD */
              if (!reg_lookup(&asarg, RCLASS_VECR, &regno)) break;
              INSERT_OPERAND(VD, *ip, regno);
              continue;

            case 'e': /* AMO VD */
              if (reg_lookup(&asarg, RCLASS_GPR, &regno) && regno == 0)
                INSERT_OPERAND(VWD, *ip, 0);
              else if (reg_lookup(&asarg, RCLASS_VECR, &regno)) {
                INSERT_OPERAND(VWD, *ip, 1);
                INSERT_OPERAND(VD, *ip, regno);
              } else
                break;
              continue;

            case 'f': /* AMO VS3 */
              if (!reg_lookup(&asarg, RCLASS_VECR, &regno)) break;
              if (!EXTRACT_OPERAND(VWD, ip->insn_opcode))
                INSERT_OPERAND(VD, *ip, regno);
              else {
                /* VS3 must match VD.  */
                if (EXTRACT_OPERAND(VD, ip->insn_opcode) != regno) break;
              }
              continue;

            case 's': /* VS1 */
              if (!reg_lookup(&asarg, RCLASS_VECR, &regno)) break;
              INSERT_OPERAND(VS1, *ip, regno);
              continue;

            case 't': /* VS2 */
              if (!reg_lookup(&asarg, RCLASS_VECR, &regno)) break;
              INSERT_OPERAND(VS2, *ip, regno);
              continue;

            case 'u': /* VS1 == VS2 */
              if (!reg_lookup(&asarg, RCLASS_VECR, &regno)) break;
              INSERT_OPERAND(VS1, *ip, regno);
              INSERT_OPERAND(VS2, *ip, regno);
              continue;

            case 'v': /* VD == VS1 == VS2 */
              if (!reg_lookup(&asarg, RCLASS_VECR, &regno)) break;
              INSERT_OPERAND(VD, *ip, regno);
              INSERT_OPERAND(VS1, *ip, regno);
              INSERT_OPERAND(VS2, *ip, regno);
              continue;

            /* The `V0` is carry-in register for v[m]adc and v[m]sbc,
               and is used to choose vs1/rs1/frs1/imm or vs2 for
               v[f]merge.  It use the same encoding as the vector mask
               register.  */
            case '0':
              if (reg_lookup(&asarg, RCLASS_VECR, &regno) && regno == 0)
                continue;
              break;

            case 'b': /* vtypei for vsetivli */
              my_getVsetvliExpression(imm_expr, asarg);
              check_absolute_expr(ip, imm_expr, FALSE);
              if (!VALID_RVV_VB_IMM(imm_expr->X_add_number))
                as_bad(
                    _("bad value for vsetivli immediate field, "
                      "value must be 0..1023"));
              ip->insn_opcode |= ENCODE_RVV_VB_IMM(imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case 'c': /* vtypei for vsetvli */
              my_getVsetvliExpression(imm_expr, asarg);
              check_absolute_expr(ip, imm_expr, FALSE);
              if (!VALID_RVV_VC_IMM(imm_expr->X_add_number))
                as_bad(
                    _("bad value for vsetvli immediate field, "
                      "value must be 0..2047"));
              ip->insn_opcode |= ENCODE_RVV_VC_IMM(imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case 'i': /* vector arith signed immediate */
              my_getExpression(imm_expr, asarg, force_reloc);
              check_absolute_expr(ip, imm_expr, FALSE);
              if (imm_expr->X_add_number > 15 || imm_expr->X_add_number < -16)
                as_bad(
                    _("bad value for vector immediate field, "
                      "value must be -16...15"));
              INSERT_OPERAND(VIMM, *ip, imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case 'j': /* vector arith unsigned immediate */
              my_getExpression(imm_expr, asarg, force_reloc);
              check_absolute_expr(ip, imm_expr, FALSE);
              if (imm_expr->X_add_number < 0 || imm_expr->X_add_number >= 32)
                as_bad(
                    _("bad value for vector immediate field, "
                      "value must be 0...31"));
              INSERT_OPERAND(VIMM, *ip, imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case 'k': /* vector arith signed immediate, minus 1 */
              my_getExpression(imm_expr, asarg, force_reloc);
              check_absolute_expr(ip, imm_expr, FALSE);
              if (imm_expr->X_add_number > 16 || imm_expr->X_add_number < -15)
                as_bad(
                    _("bad value for vector immediate field, "
                      "value must be -15...16"));
              INSERT_OPERAND(VIMM, *ip, imm_expr->X_add_number - 1);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case 'l': /* 6-bit vector arith unsigned immediate */
              my_getExpression(imm_expr, asarg, force_reloc);
              check_absolute_expr(ip, imm_expr, FALSE);
              if (imm_expr->X_add_number < 0 || imm_expr->X_add_number >= 64)
                as_bad(
                    _("bad value for vector immediate field, "
                      "value must be 0...63"));
              ip->insn_opcode |= ENCODE_RVV_VI_UIMM6(imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case 'm': /* optional vector mask */
              if (*asarg == '\0') {
                INSERT_OPERAND(VMASK, *ip, 1);
                continue;
              } else if (*asarg == ',' && asarg++ &&
                         reg_lookup(&asarg, RCLASS_VECM, &regno) &&
                         regno == 0) {
                INSERT_OPERAND(VMASK, *ip, 0);
                continue;
              }
              break;

            case 'M': /* required vector mask */
              if (reg_lookup(&asarg, RCLASS_VECM, &regno) && regno == 0) {
                INSERT_OPERAND(VMASK, *ip, 0);
                continue;
              }
              break;

            case 'T': /* vector macro temporary register */
              if (!reg_lookup(&asarg, RCLASS_VECR, &regno) || regno == 0) break;
              /* Store it in the FUNCT6 field as we don't have anyplace
                 else to store it.  */
              INSERT_OPERAND(VFUNCT6, *ip, regno);
              continue;

            default:
              goto unknown_riscv_ip_operand;
          }
          break; /* end RVV */

        case ',':
          if (*asarg++ == *oparg) continue;
          asarg--;
          break;

        case '(':
        case ')':
        case '[':
        case ']':
        case '{':
        case '}':
          if (*asarg++ == *oparg) continue;
          break;

        case '<': /* Shift amount, 0 - 31.  */
          my_getExpression(imm_expr, asarg, force_reloc);
          check_absolute_expr(ip, imm_expr, false);
          if ((unsigned long)imm_expr->X_add_number > 31)
            as_bad(_("improper shift amount (%" PRIu64 ")"),
                   imm_expr->X_add_number);
          INSERT_OPERAND(SHAMTW, *ip, imm_expr->X_add_number);
          imm_expr->X_op = O_absent;
          asarg = expr_parse_end;
          continue;

        case '>': /* Shift amount, 0 - (XLEN-1).  */
          my_getExpression(imm_expr, asarg, force_reloc);
          check_absolute_expr(ip, imm_expr, false);
          if ((unsigned long)imm_expr->X_add_number >= xlen)
            as_bad(_("improper shift amount (%" PRIu64 ")"),
                   imm_expr->X_add_number);
          INSERT_OPERAND(SHAMT, *ip, imm_expr->X_add_number);
          imm_expr->X_op = O_absent;
          asarg = expr_parse_end;
          continue;

        case 'Z': /* CSRRxI immediate.  */
          my_getExpression(imm_expr, asarg, force_reloc);
          check_absolute_expr(ip, imm_expr, false);
          if ((unsigned long)imm_expr->X_add_number > 31)
            as_bad(_("improper CSRxI immediate (%" PRIu64 ")"),
                   imm_expr->X_add_number);
          INSERT_OPERAND(RS1, *ip, imm_expr->X_add_number);
          imm_expr->X_op = O_absent;
          asarg = expr_parse_end;
          continue;

        case 'E': /* Control register.  */
          insn_with_csr = true;
          explicit_priv_attr = true;
          if (reg_lookup(&asarg, RCLASS_CSR, &regno))
            INSERT_OPERAND(CSR, *ip, regno);
          else {
            my_getExpression(imm_expr, asarg, force_reloc);
            check_absolute_expr(ip, imm_expr, true);
            if ((unsigned long)imm_expr->X_add_number > 0xfff)
              as_bad(_("improper CSR address (%" PRIu64 ")"),
                     imm_expr->X_add_number);
            INSERT_OPERAND(CSR, *ip, imm_expr->X_add_number);
            imm_expr->X_op = O_absent;
            asarg = expr_parse_end;
          }
          continue;

        case 'm': /* Rounding mode.  */
          if (arg_lookup(&asarg, riscv_rm, ARRAY_SIZE(riscv_rm), &regno)) {
            INSERT_OPERAND(RM, *ip, regno);
            continue;
          }
          break;

        case 'P':
        case 'Q': /* Fence predecessor/successor.  */
          if (arg_lookup(&asarg, riscv_pred_succ, ARRAY_SIZE(riscv_pred_succ),
                         &regno)) {
            if (*oparg == 'P')
              INSERT_OPERAND(PRED, *ip, regno);
            else
              INSERT_OPERAND(SUCC, *ip, regno);
            continue;
          }
          break;

        case 'I':
          my_getExpression(imm_expr, asarg, force_reloc);
          if (imm_expr->X_op != O_big && imm_expr->X_op != O_constant) break;
          normalize_constant_expr(imm_expr);
          asarg = expr_parse_end;
          continue;

        case 'A':
          my_getExpression(imm_expr, asarg, force_reloc);
          normalize_constant_expr(imm_expr);
          /* The 'A' format specifier must be a symbol.  */
          if (imm_expr->X_op != O_symbol) break;
          *imm_reloc = BFD_RELOC_32;
          asarg = expr_parse_end;
          continue;

        case 'B':
          if (ip->insn_mo->mask == M_LGA ||
              (riscv_opts.pic && ip->insn_mo->mask == M_LA))
            force_reloc = true;
          my_getExpression(imm_expr, asarg, force_reloc);
          normalize_constant_expr(imm_expr);
          /* The 'B' format specifier must be a symbol or a constant.  */
          if (imm_expr->X_op != O_symbol && imm_expr->X_op != O_constant) break;
          if (imm_expr->X_op == O_symbol) *imm_reloc = BFD_RELOC_32;
          asarg = expr_parse_end;
          continue;

        case 'j': /* Sign-extended immediate.  */
          p = percent_op_itype;
          *imm_reloc = BFD_RELOC_RISCV_LO12_I;
          goto alu_op;
        case 'q': /* Store displacement.  */
          p = percent_op_stype;
          *imm_reloc = BFD_RELOC_RISCV_LO12_S;
          goto load_store;
        case 'o': /* Load displacement.  */
          p = percent_op_itype;
          *imm_reloc = BFD_RELOC_RISCV_LO12_I;
          goto load_store;
        case '1':
          /* This is used for TLS relocations that acts as relaxation
             markers and do not change the instruction encoding,
             i.e. %tprel_add and %tlsdesc_call.  */
          p = percent_op_relax_only;
          goto alu_op;
        case '0': /* AMO displacement, which must be zero.  */
        load_store:
          if (riscv_handle_implicit_zero_offset(imm_expr, asarg)) continue;
        alu_op:
          /* If this value won't fit into a 16 bit offset, then go
             find a macro that will generate the 32 bit offset
             code pattern.  */
          if (!my_getSmallExpression(imm_expr, imm_reloc, asarg, p)) {
            normalize_constant_expr(imm_expr);
            if (imm_expr->X_op != O_constant ||
                (*oparg == '0' && imm_expr->X_add_number != 0) ||
                (*oparg == '1') ||
                imm_expr->X_add_number >= (signed)RISCV_IMM_REACH / 2 ||
                imm_expr->X_add_number < -(signed)RISCV_IMM_REACH / 2)
              break;
          }
          asarg = expr_parse_end;
          continue;

        case 'p': /* PC-relative offset.  */
        branch:
          *imm_reloc = BFD_RELOC_12_PCREL;
          my_getExpression(imm_expr, asarg, force_reloc);
          asarg = expr_parse_end;
          continue;

        case 'u': /* Upper 20 bits.  */
          p = percent_op_utype;
          if (!my_getSmallExpression(imm_expr, imm_reloc, asarg, p)) {
            if (imm_expr->X_op != O_constant) break;

            if (imm_expr->X_add_number < 0 ||
                imm_expr->X_add_number >= (signed)RISCV_BIGIMM_REACH)
              as_bad(_("lui expression not in range 0..1048575"));

            *imm_reloc = BFD_RELOC_RISCV_HI20;
            imm_expr->X_add_number <<= RISCV_IMM_BITS;
          }
          asarg = expr_parse_end;
          continue;

        case 'a': /* 20-bit PC-relative offset.  */
        jump:
          my_getExpression(imm_expr, asarg, force_reloc);
          asarg = expr_parse_end;
          *imm_reloc = BFD_RELOC_RISCV_JMP;
          continue;

        case 'c':
          my_getExpression(imm_expr, asarg, force_reloc);
          asarg = expr_parse_end;
          if (strcmp(asarg, "@plt") == 0) asarg += 4;
          *imm_reloc = BFD_RELOC_RISCV_CALL_PLT;
          continue;

        case 'O':
          switch (*++oparg) {
            case '4':
              if (my_getOpcodeExpression(imm_expr, imm_reloc, asarg) ||
                  imm_expr->X_op != O_constant || imm_expr->X_add_number < 0 ||
                  imm_expr->X_add_number >= 128 ||
                  (imm_expr->X_add_number & 0x3) != 3) {
                as_bad(
                    _("bad value for opcode field, "
                      "value must be 0...127 and "
                      "lower 2 bits must be 0x3"));
                break;
              }
              INSERT_OPERAND(OP, *ip, imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case '2':
              if (my_getOpcodeExpression(imm_expr, imm_reloc, asarg) ||
                  imm_expr->X_op != O_constant || imm_expr->X_add_number < 0 ||
                  imm_expr->X_add_number >= 3) {
                as_bad(
                    _("bad value for opcode field, "
                      "value must be 0...2"));
                break;
              }
              INSERT_OPERAND(OP2, *ip, imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            default:
              goto unknown_riscv_ip_operand;
          }
          break;

        case 'F':
          switch (*++oparg) {
            case '7':
              if (my_getSmallExpression(imm_expr, imm_reloc, asarg, p) ||
                  imm_expr->X_op != O_constant || imm_expr->X_add_number < 0 ||
                  imm_expr->X_add_number >= 128) {
                as_bad(
                    _("bad value for funct7 field, "
                      "value must be 0...127"));
                break;
              }
              INSERT_OPERAND(FUNCT7, *ip, imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case '3':
              if (my_getSmallExpression(imm_expr, imm_reloc, asarg, p) ||
                  imm_expr->X_op != O_constant || imm_expr->X_add_number < 0 ||
                  imm_expr->X_add_number >= 8) {
                as_bad(
                    _("bad value for funct3 field, "
                      "value must be 0...7"));
                break;
              }
              INSERT_OPERAND(FUNCT3, *ip, imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            case '2':
              if (my_getSmallExpression(imm_expr, imm_reloc, asarg, p) ||
                  imm_expr->X_op != O_constant || imm_expr->X_add_number < 0 ||
                  imm_expr->X_add_number >= 4) {
                as_bad(
                    _("bad value for funct2 field, "
                      "value must be 0...3"));
                break;
              }
              INSERT_OPERAND(FUNCT2, *ip, imm_expr->X_add_number);
              imm_expr->X_op = O_absent;
              asarg = expr_parse_end;
              continue;

            default:
              goto unknown_riscv_ip_operand;
          }
          break;

        case 'y': /* bs immediate */
          my_getExpression(imm_expr, asarg, force_reloc);
          check_absolute_expr(ip, imm_expr, FALSE);
          if ((unsigned long)imm_expr->X_add_number > 3)
            as_bad(_("Improper bs immediate (%lu)"),
                   (unsigned long)imm_expr->X_add_number);
          INSERT_OPERAND(BS, *ip, imm_expr->X_add_number);
          imm_expr->X_op = O_absent;
          asarg = expr_parse_end;
          continue;

        case 'Y': /* rnum immediate */
          my_getExpression(imm_expr, asarg, force_reloc);
          check_absolute_expr(ip, imm_expr, FALSE);
          if ((unsigned long)imm_expr->X_add_number > 10)
            as_bad(_("Improper rnum immediate (%lu)"),
                   (unsigned long)imm_expr->X_add_number);
          INSERT_OPERAND(RNUM, *ip, imm_expr->X_add_number);
          imm_expr->X_op = O_absent;
          asarg = expr_parse_end;
          continue;

        case 'z':
          if (my_getSmallExpression(imm_expr, imm_reloc, asarg, p) ||
              imm_expr->X_op != O_constant || imm_expr->X_add_number != 0)
            break;
          asarg = expr_parse_end;
          imm_expr->X_op = O_absent;
          continue;

        case 'W': /* Various operands for standard z extensions.  */
          switch (*++oparg) {
            case 'i':
              switch (*++oparg) {
                case 'f':
                  /* Prefetch offset for 'Zicbop' extension.
                     pseudo S-type but lower 5-bits zero.  */
                  if (riscv_handle_implicit_zero_offset(imm_expr, asarg))
                    continue;
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, false);
                  if (((unsigned)(imm_expr->X_add_number) & 0x1fU) ||
                      imm_expr->X_add_number >= RISCV_IMM_REACH / 2 ||
                      imm_expr->X_add_number < -RISCV_IMM_REACH / 2)
                    as_bad(_("improper prefetch offset (%ld)"),
                           (long)imm_expr->X_add_number);
                  ip->insn_opcode |= ENCODE_STYPE_IMM(
                      (unsigned)(imm_expr->X_add_number) & ~0x1fU);
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;
                default:
                  goto unknown_riscv_ip_operand;
              }
              break;

            case 'f':
              switch (*++oparg) {
                case 'v':
                  /* FLI.[HSDQ] value field for 'Zfa' extension.  */
                  if (!arg_lookup(&asarg, riscv_fli_symval,
                                  ARRAY_SIZE(riscv_fli_symval), &regno)) {
                    /* 0.0 is not a valid entry in riscv_fli_numval.  */
                    errno = 0;
                    float f = strtof(asarg, &asarg);
                    if (errno != 0 || f == 0.0 ||
                        !flt_lookup(f, riscv_fli_numval,
                                    ARRAY_SIZE(riscv_fli_numval), &regno)) {
                      as_bad(
                          _("bad fli constant operand, "
                            "supported constants must be in "
                            "decimal or hexadecimal floating-point "
                            "literal form"));
                      break;
                    }
                  }
                  INSERT_OPERAND(RS1, *ip, regno);
                  continue;
                default:
                  goto unknown_riscv_ip_operand;
              }
              break;

            case 'c':
              switch (*++oparg) {
                case 'h': /* Immediate field for c.lh/c.lhu/c.sh.  */
                  /* Handle cases, such as c.sh rs2', (rs1').  */
                  if (riscv_handle_implicit_zero_offset(imm_expr, asarg))
                    continue;
                  if (my_getSmallExpression(imm_expr, imm_reloc, asarg, p) ||
                      imm_expr->X_op != O_constant ||
                      !VALID_ZCB_HALFWORD_UIMM((valueT)imm_expr->X_add_number))
                    break;
                  ip->insn_opcode |=
                      ENCODE_ZCB_HALFWORD_UIMM(imm_expr->X_add_number);
                  goto rvc_imm_done;
                case 'b': /* Immediate field for c.lbu/c.sb.  */
                  /* Handle cases, such as c.lbu rd', (rs1').  */
                  if (riscv_handle_implicit_zero_offset(imm_expr, asarg))
                    continue;
                  if (my_getSmallExpression(imm_expr, imm_reloc, asarg, p) ||
                      imm_expr->X_op != O_constant ||
                      !VALID_ZCB_BYTE_UIMM((valueT)imm_expr->X_add_number))
                    break;
                  ip->insn_opcode |=
                      ENCODE_ZCB_BYTE_UIMM(imm_expr->X_add_number);
                  goto rvc_imm_done;
                case 'r':
                  if (!reglist_lookup(&asarg, &regno)) break;
                  INSERT_OPERAND(REG_LIST, *ip, regno);
                  continue;
                case 'p':
                  if (my_getSmallExpression(imm_expr, imm_reloc, asarg, p) ||
                      imm_expr->X_op != O_constant)
                    break;
                  /* Convert stack adjustment of cm.push to a positive
                     offset.  */
                  if (ip->insn_mo->match == MATCH_CM_PUSH)
                    imm_expr->X_add_number *= -1;
                  /* Subtract base stack adjustment and get spimm.  */
                  imm_expr->X_add_number -=
                      riscv_get_sp_base(ip->insn_opcode, *riscv_rps_as.xlen);
                  if (!VALID_ZCMP_SPIMM(imm_expr->X_add_number)) break;
                  ip->insn_opcode |= ENCODE_ZCMP_SPIMM(imm_expr->X_add_number);
                  goto rvc_imm_done;
                case 'f': /* Operand for matching immediate 255.  */
                  if (my_getSmallExpression(imm_expr, imm_reloc, asarg, p) ||
                      imm_expr->X_op != O_constant ||
                      imm_expr->X_add_number != 255)
                    break;
                  /* This operand is used for matching immediate 255, and
                     we do not write anything to encoding by this operand.  */
                  asarg = expr_parse_end;
                  imm_expr->X_op = O_absent;
                  continue;
                case '1':
                  if (!reg_lookup(&asarg, RCLASS_GPR, &regno) ||
                      !RISCV_SREG_0_7(regno))
                    break;
                  INSERT_OPERAND(SREG1, *ip, regno % 8);
                  continue;
                case '2':
                  if (!reg_lookup(&asarg, RCLASS_GPR, &regno) ||
                      !RISCV_SREG_0_7(regno))
                    break;
                  INSERT_OPERAND(SREG2, *ip, regno % 8);
                  continue;
                case 'I': /* index operand of cm.jt. The range is from 0 to 31.
                           */
                  my_getSmallExpression(imm_expr, imm_reloc, asarg, p);
                  if (imm_expr->X_op != O_constant ||
                      imm_expr->X_add_number < 0 ||
                      imm_expr->X_add_number > 31) {
                    as_bad("bad index value for cm.jt, range: [0, 31]");
                    break;
                  }
                  ip->insn_opcode |= ENCODE_ZCMT_INDEX(imm_expr->X_add_number);
                  goto rvc_imm_done;
                case 'i': /* index operand of cm.jalt. The range is from 32 to
                             255.  */
                  my_getSmallExpression(imm_expr, imm_reloc, asarg, p);
                  if (imm_expr->X_op != O_constant ||
                      imm_expr->X_add_number < 32 ||
                      imm_expr->X_add_number > 255) {
                    as_bad("bad index value for cm.jalt, range: [32, 255]");
                    break;
                  }
                  ip->insn_opcode |= ENCODE_ZCMT_INDEX(imm_expr->X_add_number);
                  goto rvc_imm_done;
                default:
                  goto unknown_riscv_ip_operand;
              }
              break;

            default:
              goto unknown_riscv_ip_operand;
          }
          break;

        case 'X': /* Vendor-specific operands.  */
          switch (*++oparg) {
            case 't': /* Vendor-specific (T-head) operands.  */
            {
              size_t n;
              size_t s;
              bool sign;
              switch (*++oparg) {
                case 'V':
                  /* Vtypei for th.vsetvli.  */
                  ++oparg;
                  if (*oparg != 'c') goto unknown_riscv_ip_operand;

                  my_getThVsetvliExpression(imm_expr, asarg);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  if (!VALID_RVV_VC_IMM(imm_expr->X_add_number))
                    as_bad(
                        _("bad value for th.vsetvli immediate field, "
                          "value must be 0..2047"));
                  ip->insn_opcode |= ENCODE_RVV_VC_IMM(imm_expr->X_add_number);
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;

                case 'l': /* Integer immediate, literal.  */
                  n = strcspn(++oparg, ",");
                  if (strncmp(oparg, asarg, n))
                    as_bad(_("unexpected literal (%s)"), asarg);
                  oparg += n - 1;
                  asarg += n;
                  continue;
                case 's': /* Integer immediate, 'XsN@S' ... N-bit signed
                             immediate at bit S.  */
                  sign = true;
                  goto parse_imm;
                case 'u': /* Integer immediate, 'XuN@S' ... N-bit unsigned
                             immediate at bit S.  */
                  sign = false;
                  goto parse_imm;
                parse_imm:
                  n = strtol(oparg + 1, (char **)&oparg, 10);
                  if (*oparg != '@') goto unknown_riscv_ip_operand;
                  s = strtol(oparg + 1, (char **)&oparg, 10);
                  oparg--;

                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, false);
                  if (!sign) {
                    if (!VALIDATE_U_IMM(imm_expr->X_add_number, n))
                      as_bad(_("improper immediate value (%" PRIu64 ")"),
                             imm_expr->X_add_number);
                  } else {
                    if (!VALIDATE_S_IMM(imm_expr->X_add_number, n))
                      as_bad(_("improper immediate value (%" PRIi64 ")"),
                             imm_expr->X_add_number);
                  }
                  INSERT_IMM(n, s, *ip, imm_expr->X_add_number);
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;
                default:
                  goto unknown_riscv_ip_operand;
              }
            } break;

            case 'c': /* Vendor-specific (CORE-V) operands.  */
              switch (*++oparg) {
                case '2':
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  asarg = expr_parse_end;
                  if (imm_expr->X_add_number < 0 || imm_expr->X_add_number > 31)
                    break;
                  ip->insn_opcode |=
                      ENCODE_CV_IS2_UIMM5(imm_expr->X_add_number);
                  continue;
                case '3':
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  asarg = expr_parse_end;
                  if (imm_expr->X_add_number < 0 || imm_expr->X_add_number > 31)
                    break;
                  ip->insn_opcode |=
                      ENCODE_CV_IS3_UIMM5(imm_expr->X_add_number);
                  continue;
                case '4':
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  asarg = expr_parse_end;
                  if (imm_expr->X_add_number < -16 ||
                      imm_expr->X_add_number > 15)
                    break;
                  ip->insn_opcode |=
                      ENCODE_CV_IS2_UIMM5(imm_expr->X_add_number);
                  continue;
                case '5':
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  asarg = expr_parse_end;
                  if (imm_expr->X_add_number < -32 ||
                      imm_expr->X_add_number > 31)
                    break;
                  ip->insn_opcode |=
                      ENCODE_CV_SIMD_IMM6(imm_expr->X_add_number);
                  continue;
                case '6':
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  asarg = expr_parse_end;
                  if (imm_expr->X_add_number < 0 || imm_expr->X_add_number > 31)
                    break;
                  ip->insn_opcode |=
                      ENCODE_CV_BITMANIP_UIMM5(imm_expr->X_add_number);
                  continue;
                case '7':
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  asarg = expr_parse_end;
                  if (imm_expr->X_add_number < 0 || imm_expr->X_add_number > 3)
                    break;
                  ip->insn_opcode |=
                      ENCODE_CV_BITMANIP_UIMM2(imm_expr->X_add_number);
                  continue;
                case '8':
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  asarg = expr_parse_end;
                  ++oparg;
                  if (imm_expr->X_add_number < 0 || imm_expr->X_add_number > 63)
                    break;
                  else if (*oparg == '1' && imm_expr->X_add_number > 1)
                    break;
                  else if (*oparg == '2' && imm_expr->X_add_number > 3)
                    break;
                  else if (*oparg == '3' && imm_expr->X_add_number > 7)
                    break;
                  else if (*oparg == '4' && imm_expr->X_add_number > 15)
                    break;
                  ip->insn_opcode |=
                      ENCODE_CV_SIMD_UIMM6(imm_expr->X_add_number);
                  continue;
                default:
                  goto unknown_riscv_ip_operand;
              }
              break;

            case 's': /* Vendor-specific (SiFive) operands.  */
#define UIMM_BITFIELD_VAL(S, E) (1 << ((E) - (S) + 1))
#define ENCODE_UIMM_BIT_FIELD(NAME, IP, EXPR, RELOC, ASARG, START, END) \
  do {                                                                  \
    if (my_getOpcodeExpression(EXPR, RELOC, ASARG) ||                   \
        EXPR->X_op != O_constant || EXPR->X_add_number < 0 ||           \
        EXPR->X_add_number >= UIMM_BITFIELD_VAL(START, END)) {          \
      as_bad(_("bad value for <bit-%s-%s> "                             \
               "field, value must be 0...%d"),                          \
             #START, #END, UIMM_BITFIELD_VAL(START, END));              \
      break;                                                            \
    }                                                                   \
    INSERT_OPERAND(NAME, *IP, EXPR->X_add_number);                      \
    EXPR->X_op = O_absent;                                              \
    ASARG = expr_parse_end;                                             \
  } while (0);
              switch (*++oparg) {
                case 'd': /* Xsd */
                  ENCODE_UIMM_BIT_FIELD(RD, ip, imm_expr, imm_reloc, asarg, 7,
                                        11);
                  continue;
                case 't': /* Xst */
                  ENCODE_UIMM_BIT_FIELD(RS2, ip, imm_expr, imm_reloc, asarg, 20,
                                        24)
                  continue;
                case 'O':
                  switch (*++oparg) {
                    case '2': /* XsO2 */
                      ENCODE_UIMM_BIT_FIELD(XSO2, ip, imm_expr, imm_reloc,
                                            asarg, 26, 27);
                      continue;
                    case '1': /* XsO1 */
                      ENCODE_UIMM_BIT_FIELD(XSO1, ip, imm_expr, imm_reloc,
                                            asarg, 26, 26);
                      continue;
                  }
                default:
                  goto unknown_riscv_ip_operand;
              }
#undef UIMM_BITFIELD_VAL
#undef ENCODE_UIMM_BIT_FIELD
              break;

            case 'm': /* Vendor-specific (MIPS) operands.  */
              switch (*++oparg) {
                case '@': /* hint 0 - 31.  */
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  if ((unsigned long)imm_expr->X_add_number > 31)
                    as_bad(_("Improper hint amount (%lu)"),
                           (unsigned long)imm_expr->X_add_number);
                  INSERT_OPERAND(MIPS_HINT, *ip, imm_expr->X_add_number);
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;

                case '#': /* immediate 0 - 511.  */
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  if ((unsigned long)imm_expr->X_add_number > 511)
                    as_bad(_("Improper immediate amount (%lu)"),
                           (unsigned long)imm_expr->X_add_number);
                  INSERT_OPERAND(MIPS_IMM9, *ip, imm_expr->X_add_number);
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;

                case '$': /* LDP offset 0 to (1<<7)-8.  */
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  if ((unsigned long)imm_expr->X_add_number >= (1 << 7) ||
                      ((unsigned long)imm_expr->X_add_number & 0x7) != 0)
                    as_bad(_("Improper LDP offset amount (%lu)"),
                           (unsigned long)imm_expr->X_add_number);
                  INSERT_OPERAND(MIPS_LDP_OFFSET, *ip,
                                 (imm_expr->X_add_number >> 3));
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;

                case '%': /* LWP offset 0 to (1<<7)-4.  */
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  if ((unsigned long)imm_expr->X_add_number >= (1 << 7) ||
                      ((unsigned long)imm_expr->X_add_number & 0x3) != 0)
                    as_bad(_("Improper LWP offset amount (%lu)"),
                           (unsigned long)imm_expr->X_add_number);
                  INSERT_OPERAND(MIPS_LWP_OFFSET, *ip,
                                 (imm_expr->X_add_number >> 2));
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;

                case '^': /* SDP offset 0 to (1<<7)-8.  */
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  if ((unsigned long)imm_expr->X_add_number >= (1 << 7) ||
                      ((unsigned long)imm_expr->X_add_number & 0x7) != 0)
                    as_bad(_("Improper SDP offset amount (%lu)"),
                           (unsigned long)imm_expr->X_add_number);
                  INSERT_OPERAND(MIPS_SDP_OFFSET10, *ip,
                                 (imm_expr->X_add_number >> 3));
                  INSERT_OPERAND(MIPS_SDP_OFFSET25, *ip,
                                 (imm_expr->X_add_number >> 5));
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;

                case '&': /* SWP offset 0 to (1<<7)-4.  */
                  my_getExpression(imm_expr, asarg, force_reloc);
                  check_absolute_expr(ip, imm_expr, FALSE);
                  if ((unsigned long)imm_expr->X_add_number >= (1 << 7) ||
                      ((unsigned long)imm_expr->X_add_number & 0x3) != 0)
                    as_bad(_("Improper SWP offset amount (%lu)"),
                           (unsigned long)imm_expr->X_add_number);
                  INSERT_OPERAND(MIPS_SWP_OFFSET9, *ip,
                                 (imm_expr->X_add_number >> 2));
                  INSERT_OPERAND(MIPS_SWP_OFFSET25, *ip,
                                 (imm_expr->X_add_number >> 5));
                  imm_expr->X_op = O_absent;
                  asarg = expr_parse_end;
                  continue;

                default:
                  goto unknown_riscv_ip_operand;
              }
              break;

            default:
              goto unknown_riscv_ip_operand;
          }
          break;

        default:
        unknown_riscv_ip_operand:
          as_fatal(_("internal: unknown argument type `%s'"), opargStart);
      }
      break;
    }
    asarg = asargStart;
    insn_with_csr = false;
  }

out:
  /* Restore the character we might have clobbered above.  */
  if (save_c) *(asargStart - 1) = save_c;

  probing_insn_operands = false;

  return error;
}

/* Similar to riscv_ip, but assembles an instruction according to the
   hardcode values of .insn directive.  */

static const char *riscv_ip_hardcode(char *str, struct riscv_cl_insn *ip,
                                     expressionS *imm_expr, const char *error) {
  struct riscv_opcode *insn;
  insn_t values[2] = {0, 0};
  unsigned int num = 0;

  input_line_pointer = str;
  do {
    expression(imm_expr);
    switch (imm_expr->X_op) {
      case O_constant:
        values[num++] = imm_expr->X_add_number;
        break;
      case O_big:
        /* Extract lower 32-bits of a big number.
           Assume that generic_bignum_to_int32 work on such number.  */
        values[num++] = generic_bignum_to_int32();
        break;
      default:
        /* The first value isn't constant, so it should be
           .insn <type> <operands>.  We have been parsed it
           in the riscv_ip.  */
        if (num == 0) return error;
        return _("values must be constant");
    }
  } while (*input_line_pointer++ == ',' && num < 2 && imm_expr->X_op != O_big);

  input_line_pointer--;
  if (*input_line_pointer != '\0') return _("unrecognized values");

  insn = XCNEW(struct riscv_opcode);
  insn->match = values[num - 1];
  create_insn(ip, insn);
  unsigned int bytes = riscv_insn_length(insn->match);

  if (num == 2 && values[0] != bytes)
    return _("value conflicts with instruction length");

  if (imm_expr->X_op == O_big) {
    unsigned int llen = 0;
    for (LITTLENUM_TYPE lval = generic_bignum[imm_expr->X_add_number - 1];
         lval != 0; llen++)
      lval >>= BITS_PER_CHAR;
    unsigned int repr_bytes =
        (imm_expr->X_add_number - 1) * CHARS_PER_LITTLENUM + llen;
    if (bytes < repr_bytes) return _("value conflicts with instruction length");
    for (num = 0; num < imm_expr->X_add_number - 1; ++num)
      number_to_chars_littleendian(
          ip->insn_long_opcode + num * CHARS_PER_LITTLENUM, generic_bignum[num],
          CHARS_PER_LITTLENUM);
    if (llen != 0)
      number_to_chars_littleendian(
          ip->insn_long_opcode + num * CHARS_PER_LITTLENUM, generic_bignum[num],
          llen);
    memset(ip->insn_long_opcode + repr_bytes, 0, bytes - repr_bytes);
  } else if (bytes < sizeof(values[0]) && values[num - 1] >> (8 * bytes) != 0)
    return _("value conflicts with instruction length");

  if (!riscv_opts.rvc && (bytes & 2))
    seg_info(now_seg)->tc_segment_info_data.last_insn16 = true;

  return NULL;
}

void md_assemble(char *str) {
  struct riscv_cl_insn insn;
  expressionS imm_expr;
  bfd_reloc_code_real_type imm_reloc = BFD_RELOC_UNUSED;

  /* The architecture and privileged elf attributes should be set
     before assembling.  */
  if (!start_assemble) {
    start_assemble = true;

    riscv_set_abi_by_arch();
    if (!riscv_set_default_priv_spec(NULL)) return;
  }

  riscv_mapping_state(MAP_INSN, 0, false /* fr_align_code */);

  const struct riscv_ip_error error =
      riscv_ip(str, &insn, &imm_expr, &imm_reloc, op_hash);

  if (error.msg) {
    if (error.missing_ext)
      as_bad("%s `%s', extension `%s' required", error.msg, error.statement,
             error.missing_ext);
    else
      as_bad("%s `%s'", error.msg, error.statement);
    return;
  }

  if (insn.insn_mo->pinfo == INSN_MACRO)
    macro(&insn, &imm_expr, &imm_reloc);
  else
    append_insn(&insn, &imm_expr, imm_reloc);
}