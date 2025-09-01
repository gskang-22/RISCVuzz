#[macro_use]
extern crate pest_derive;

use anyhow::{anyhow, Error};
use pest::Parser;
use rand::Rng;
use std::collections::HashMap;
use serde::Deserialize; 
use std::fs; 

#[allow(dead_code, clippy::type_complexity)]
mod opcodes;

mod asm_parser {
    #[derive(Parser)]
    #[grammar = "asm.pest"]
    pub(crate) struct AsmParser;
}
use asm_parser::{AsmParser, Rule};

// https://github.com/riscv/riscv-v-spec/blob/master/v-spec.adoc#101-vector-arithmetic-instruction-encoding
//
// NOTE: For ternary multiply-add operations, the assembler syntax always places the
// destination vector register first, followed by either rs1 or vs1, then vs2.
// This ordering provides a more natural reading of the assembler for these
// ternary operations, as the multiply operands are always next to each other.
const VV_TERNARY_INSTS: [&str; 19] = [
    "vmacc.vv",
    "vnmsac.vv",
    "vmadd.vv",
    "vnmsub.vv",
    "vwmaccu.vv",
    "vwmacc.vv",
    "vwmaccsu.vv",
    "vfmacc.vv",
    "vfnmacc.vv",
    "vfmsac.vv",
    "vfnmsac.vv",
    "vfmadd.vv",
    "vfnmadd.vv",
    "vfmsub.vv",
    "vfnmsub.vv",
    "vfwmacc.vv",
    "vfwnmacc.vv",
    "vfwmsac.vv",
    "vfwnmsac.vv",
];
const VX_VF_TERNARY_INSTS: [&str; 20] = [
    "vmacc.vx",
    "vnmsac.vx",
    "vmadd.vx",
    "vnmsub.vx",
    "vwmaccu.vx",
    "vwmacc.vx",
    "vwmaccsu.vx",
    "vwmaccus.vx",
    "vfmacc.vf",
    "vfnmacc.vf",
    "vfmsac.vf",
    "vfnmsac.vf",
    "vfmadd.vf",
    "vfnmadd.vf",
    "vfmsub.vf",
    "vfnmsub.vf",
    "vfwmacc.vf",
    "vfwnmacc.vf",
    "vfwmsac.vf",
    "vfwnmsac.vf",
];

#[derive(Deserialize, Debug)]
struct Config { 
    GPRs: Vec<u32>, 
    FREGs: Vec<u32>, 
    VREGs: Vec<u32>, 
    SPECIAL_GPRS: Vec<u32>, 
    SPECIAL_VREGS: Vec<u32>, 
    SPECIAL_SIMMS: Vec<i32>, 
    SPECIAL_UIMMS: Vec<u32>, 
    GPR_SPECIAL: f64, 
    VREG_SPECIAL: f64, 
    IMM_SPECIAL: f64, 
    ZIMM10_BIAS: f64,
    VLMUL_PROBABILITIES: HashMap<String, f64>,
}


fn load_config() -> Config {
    let data = fs::read_to_string("/home/szekang/Documents/RISCVuzz/config.json").expect("config.json not found");
    serde_json::from_str(&data).expect("Failed to parse config.json")
}

// / Convert one RISC-V Vector Extension(RVV) instruction into code.
// /
// / This function try to parse the instruction as normal asm instruction or
// / standalone label ("1:"/"label:"). If it's a valid RVV instruction, it will
// / try to encode it to target code. Otherwise, if it's a valid asm instruction
// / it will return `Ok(None)`. If parse or encode failed, it will return error.
// /
// / ## Example:
// / ```
// / assert_eq!(rvv_encode::encode("vle64.v v3, (a0), v0.t", false).unwrap(), Some(0b00000000000001010111000110000111));
// / ```
pub fn encode(inst: &str) -> Result<Option<u32>, Error> {
    // get config variables from python config file
    let config = load_config();

    let pairs = if let Ok(result) = AsmParser::parse(Rule::inst, inst.trim()) {
        result
    } else {
        let _ = AsmParser::parse(Rule::label, inst.trim())
            .map_err(|err| anyhow!("parse asm error: {}", err))?;
        return Ok(None);
    };
    let mut name = "unknown";
    let mut args = Vec::new();
    for pair in pairs.clone() {
        for inner1_pair in pair.into_inner() {
            match inner1_pair.as_rule() {
                Rule::inst_name => {
                    name = inner1_pair.as_str();
                }
                Rule::inst_arg => {
                    for inner2_pair in inner1_pair.into_inner() {
                        match inner2_pair.as_rule() {
                            Rule::inst_arg_mask | Rule::inst_arg_simple | Rule::integer => {
                                args.push(inner2_pair.as_str());
                            }
                            _ => {
                                return Ok(None);
                            }
                        }
                    }
                }
                _ => {
                    return Ok(None);
                }
            }
        }
    }


    opcodes::INSTRUCTIONS
        .iter()
        .find(|(inst_name, _, _)| *inst_name == name)
        .map(|(_, base, args_cfg)| gen_inst_code(&config, name, *base, args_cfg))
        .transpose()
    
// name = parsed instruction name (a &str, e.g. "vwmacc.vv")
// &args = parsed arguments from the asm string (e.g. ["v1", "v2", "v3"])
// *base = the MATCH_VWMACC_VV constant (the base encoding for vwmacc.vv)
// args_cfg = the ARGS_VWMACC_VV constant (how to slot "v1", "v2", "v3" into the instruction fields)
}

fn gen_inst_code(
    config: &Config,
    name: &str,
    mut base: u32,
    arg_cfg: &[(&str, usize)],
) -> Result<u32, Error> {

    // The order of `simm5`/`vs1` and `vs2` in opcodes-rvv is not the same with v-spec.adoc
    // fixes listing in opcodes-rvv to be in accordance with v-spec.adoc
    let simm5_idx = arg_cfg.iter().position(|(name, _)| *name == "simm5");
    let vs1_idx = arg_cfg.iter().position(|(name, _)| *name == "vs1");
    let rs1_idx = arg_cfg.iter().position(|(name, _)| *name == "rs1");
    let vs2_idx = arg_cfg.iter().position(|(name, _)| *name == "vs2");
    let last_7bits = base & 0b1111111; 

    let mut arg_cfg_vec = arg_cfg.iter().collect::<Vec<_>>();
    if let (Some(simm5_idx), Some(vs2_idx), 0x57) = (simm5_idx, vs2_idx, last_7bits) {
        arg_cfg_vec.swap(simm5_idx, vs2_idx);
    }
    if let (Some(vs1_idx), Some(vs2_idx), 0x57) = (vs1_idx, vs2_idx, last_7bits) {
        if !VV_TERNARY_INSTS.contains(&name) {
            arg_cfg_vec.swap(vs1_idx, vs2_idx);
        }
    }
    if let (Some(rs1_idx), Some(vs2_idx), 0x57) = (rs1_idx, vs2_idx, last_7bits) {
        if !VX_VF_TERNARY_INSTS.contains(&name) {
            arg_cfg_vec.swap(rs1_idx, vs2_idx);
        }
    }

    // loop through each individual argument
    for (_, (arg_name, arg_pos)) in arg_cfg_vec.iter().rev().enumerate() {
        let value = match *arg_name {
            "rs1" | "rs2" | "rd" => map_x_reg(&config)?,
            "vs1" | "vs2" | "vs3" | "vd" => map_v_reg(&config)?,
            "simm5" => {
                let value = rand_simm(5, &config);
                (value & 0b00011111) as u32
            }
            "zimm" => {
                let value = rand_uimm(5, &config);
                (value as u8 & 0b00011111) as u32
            }
            // NOTE: special case
            "zimm10" | "zimm11" => {
                // bits:   [vill mu tu ma ta vlmul vsew]
                // value:   0    1  1  0  0   000   010

                // vsew random generation with bias towards higher extreme numbers 
                    // 8 => 0,
                    // 16 => 1,
                    // 32 => 2,
                    // 64 => 3,
                    // 128 => 4,
                    // 256 => 5,
                    // 512 => 6,
                    // 1024 => 7,
                let mut rng = rand::thread_rng();
                let r: f64 = rng.gen(); // random number between 0.0 and 1.0
                let skewed = r.powf(config.ZIMM10_BIAS); // <1 favors higher numbers, >1 favors lower numbers
                let temp = (skewed * 8.0).floor() as u8; // scale to 0..7
                let vsew = temp.min(7); // ensure it never exceeds 7

                // lmul random generation with bias towards extreme values (MF8, M8)
                let lmul = random_vlmul(&config);

                let mut value = lmul as u8;
                value |= vsew << 3;

                // randomly set ta and ma about half the time
                let mut rng = rand::thread_rng();
                if rng.gen_bool(0.5) { // 50% chance
                    value |= 1 << 6; // ta
                }
                if rng.gen_bool(0.5) { // 50% chance
                    value |= 1 << 7; // ma
                }

                value as u32
            }
            "vm" => {
                // decides if vector masking is enabled
                let mut rng = rand::thread_rng();
                if rng.gen_bool(0.5) {
                    0
                } else {
                    1
                }
            }
            "nf" => {
            // for vector segment load/store instructions
            // nf: number of fields per segment to be moved
                // nf[2:0] 	NFIELDS
                //  000   ->   1
                //  001   ->   2
                //  010   ->   3
                //  011   ->   4   
                //  100   ->   5
                //  101   ->   6
                //  110   ->   7
                //  111   ->   8
                let mut rng = rand::thread_rng();
                let fields = rng.gen_range(1..=8); // pick between 1 and 8
                let value = fields - 1;            // encoding is fields - 1
                (value as u8 & 0b00000111) as u32
            }
            // // FIXME: support `Zvamo`
            // "wd" => return Err(anyhow!("Zvamo instructions are not supported.")),
            _ => unreachable!(),
        };
        base |= value << arg_pos;
    }
    Ok(base)
}

#[repr(u8)]
enum Vlmul {
    // LMUL=1/8
    Mf8 = 0b101,
    // LMUL=1/4
    Mf4 = 0b110,
    // LMUL=1/2
    Mf2 = 0b111,
    // LMUL=1
    M1 = 0b000,
    // LMUL=2
    M2 = 0b001,
    // LMUL=4
    M4 = 0b010,
    // LMUL=8
    M8 = 0b011,
}

fn random_vlmul(cfg: &Config) -> Vlmul {
    let mut rng = rand::thread_rng();
    let roll: f64 = rng.gen(); // generates a float between 0.0..1.0
    let mut cumulative = 0.0;

    for (key, &prob) in &cfg.VLMUL_PROBABILITIES {
        cumulative += prob;
        if roll < cumulative {
            return match key.as_str() {
                "Mf8" => Vlmul::Mf8,
                "Mf4" => Vlmul::Mf4,
                "M8"  => Vlmul::M8,
                "Mf2" => Vlmul::Mf2,
                "M2"  => Vlmul::M2,
                "M4"  => Vlmul::M4,
                "M1"  => Vlmul::M1,
                _     => Vlmul::M1, // fallback
            };
        }
    }
    Vlmul::M1 // fallback if rounding errors
}

fn map_v_reg(config: &Config) -> Result<u32, Error> {    
    let mut rng = rand::thread_rng();

    if rng.gen::<f64>() < config.VREG_SPECIAL {
        // Pick a special vector register
        let idx = rng.gen_range(0..config.SPECIAL_VREGS.len());
        Ok(config.SPECIAL_VREGS[idx])
    } else {
        // Pick a random register between 0 and 31
        let idx = rng.gen_range(0..config.VREGs.len());
        Ok(config.VREGs[idx])
    }
}

fn map_x_reg(config: &Config) -> Result<u32, Error> {
    let mut rng = rand::thread_rng();

    if rng.gen::<f64>() < config.GPR_SPECIAL {
        // Pick a special GPR
        let idx = rng.gen_range(0..config.SPECIAL_GPRS.len());
        Ok(config.SPECIAL_GPRS[idx])
    } else {
        let idx = rng.gen_range(0..config.GPRs.len());
        Ok(config.GPRs[idx])
    }
}

// Random signed immediate generator
fn rand_simm(bits: u32, config: &Config) -> i32 {
    let mut rng = rand::thread_rng();
    let val = if rng.gen::<f64>() < config.IMM_SPECIAL {
        // Pick from special values
        let idx = rng.gen_range(0..config.SPECIAL_SIMMS.len());
        config.SPECIAL_SIMMS[idx]
    } else {
        // Pick random signed value in range [-2^(bits-1), 2^(bits-1)-1]
        let lo = -(1 << (bits - 1));
        let hi = (1 << (bits - 1)) - 1;
        rng.gen_range(lo..=hi)
    };
    // to_bin(val, bits)
    val
}

// Random unsigned immediate generator
fn rand_uimm(bits: u32, config: &Config) -> u32 {
    let mut rng = rand::thread_rng();
    let val: u32 = if rng.gen::<f64>() < config.IMM_SPECIAL {
        let idx = rng.gen_range(0..config.SPECIAL_UIMMS.len());
        config.SPECIAL_UIMMS[idx]
    } else {
        rng.gen_range(0..(1 << bits))
    };
    // to_bin(val as i32, bits)
    val
}