use clap::{AppSettings, Parser};

#[derive(Parser)]
#[clap(author, version, about)]
#[clap(global_setting(AppSettings::PropagateVersion))]
#[clap(global_setting(AppSettings::UseLongFormatForHelpSubcommand))]

struct Cli {
    /// Instruction string directly from CLI
    asm: String,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    let line = cli.asm;
    if let Ok(Some(code)) = rvv_encode::encode(line.as_str()) {
        let indent = line.chars().take_while(|c| *c == ' ').collect::<String>();
        // let [b0, b1, b2, b3] = code.to_le_bytes();
        // println!(
        //     "{}.byte {:#04x}, {:#04x}, {:#04x}, {:#04x}",
        //     indent, b0, b1, b2, b3
        // );
        // println!(
        //     "{}{}{:032b}",
        //     indent,
        //     ".inst ",
        //     code
        // );
        // println!("Input: {}", line.trim());
        print!("0x{:08x}", code); // 32-bit instruction in hex
    } else {
        println!("{}", line);
    }

    Ok(())
}
//     let origin_asm_file = File::open(cli.asm_file)?;
//     for result_line in BufReader::new(origin_asm_file).lines() {
//         let line = result_line?;
//         if let Ok(Some(code)) = rvv_encode::encode(line.as_str()) {
//             let indent = line.chars().take_while(|c| *c == ' ').collect::<String>();
//             let [b0, b1, b2, b3] = code.to_le_bytes();
//             let comment = if cli.comment_origin {
//                 format!(" {} {:032b} - {}", cli.comment_prefix, code, line.trim())
//             } else {
//                 Default::default()
//             };
//             println!(
//                 "{}.byte {:#04x}, {:#04x}, {:#04x}, {:#04x}{}",
//                 indent, b0, b1, b2, b3, comment
//             );
//             println!(
//                 "{}{}{:032b}{}",
//                 indent,
//                 ".inst ",       // optional prefix like .inst
//                 code,           // the 32-bit instruction
//                 comment
//             );
//         } else {
//             println!("{}", line);
//         }
//     }
//     Ok(())
// }
