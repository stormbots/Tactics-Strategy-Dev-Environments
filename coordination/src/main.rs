fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.as_slice() {
        [mode] if mode == "init" => {
            if let Err(e) = sde_coordination::initialize() {
                eprintln!("{e}");
                std::process::exit(1);
            }
        }
        [mode] if mode == "status" => println!(
            "{}",
            serde_json::to_string(&sde_coordination::status()).unwrap()
        ),
        _ => {
            eprintln!("Usage: sde-coordination <init|status>");
            std::process::exit(1);
        }
    }
}
