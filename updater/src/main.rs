use sde_update_trust::{
    authenticate, create_manifest, read_bounded, sign_manifest, verify_installer, MAX_METADATA,
    PLATFORMS,
};
use std::path::Path;
fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    #[cfg(target_os = "linux")]
    if args.as_slice() == ["maintain-linux"] {
        std::process::exit(sde_update_trust::maintain_linux()?);
    }
    #[cfg(target_os = "linux")]
    if args.as_slice() == ["app-only-linux"] {
        return sde_update_trust::app_only_linux();
    }
    #[cfg(target_os = "linux")]
    if args.len() == 2 && args[0] == "app-only-progress" {
        println!("{}", sde_update_trust::app_only_progress(&args[1])?);
        return Ok(());
    }
    #[cfg(target_os = "linux")]
    if args.as_slice() == ["app-only-current-receipt"] {
        println!(
            "{}",
            serde_json::to_string(&sde_update_trust::app_only_current_receipt()?)
                .map_err(|_| "Receipt encoding failed")?
        );
        return Ok(());
    }
    #[cfg(windows)]
    if args.as_slice() == ["maintain-windows"] {
        std::process::exit(sde_update_trust::maintain_windows()?);
    }
    if args.len() == 1 && matches!(args[0].as_str(), "pause" | "resume") {
        #[cfg(target_os = "linux")]
        sde_update_trust::set_linux_pause(args[0] == "pause")?;
        #[cfg(windows)]
        sde_update_trust::set_windows_pause(args[0] == "pause")?;
        println!("SDE installation policy saved. Tool maintenance remains enabled. An installer already running is allowed to finish.");
        return Ok(());
    }
    if args.as_slice() == ["self-update-status"] {
        println!(
            "{}",
            serde_json::to_string(&sde_update_trust::observation::inspect())
                .map_err(|_| "Status encoding failed")?
        );
        return Ok(());
    }
    if args.as_slice() == ["verify-recovery"] {
        return sde_update_trust::observation::verify_recovery();
    }
    if args.as_slice() == ["coordination-status"] {
        println!(
            "{}",
            serde_json::to_string(&sde_coordination::status())
                .map_err(|_| "Report encoding failed")?
        );
        return Ok(());
    }
    if args.len() == 1 && matches!(args[0].as_str(), "check" | "stage") {
        let report = sde_update_trust::staging::run(args[0] == "stage");
        println!(
            "{}",
            serde_json::to_string(&report).map_err(|_| "Report encoding failed")?
        );
        if report.status == sde_update_trust::staging::Status::Unavailable {
            std::process::exit(2);
        }
        return Ok(());
    }
    if args.len() != 3 {
        return Err(
            "Usage: sde-update-trust <pause|resume|self-update-status|verify-recovery|coordination-status|check|stage> OR <create|sign|verify> <release-directory> <vMAJOR.MINOR.PATCH>"
                .into(),
        );
    }
    let dist = Path::new(&args[1]);
    let metadata = dist.join("sde-update.json");
    let signature = dist.join("sde-update.json.minisig");
    match args[0].as_str() {
        "create" => std::fs::write(metadata, create_manifest(dist, &args[2])?)
            .map_err(|_| "Metadata write failed")?,
        "sign" => {
            let bytes = read_bounded(&metadata, MAX_METADATA)?;
            let secret = std::env::var("SDE_UPDATE_SIGNING_KEY")
                .map_err(|_| "Signing secret not configured")?;
            let password = std::env::var("SDE_UPDATE_SIGNING_PASSWORD")
                .map_err(|_| "Signing password not configured")?;
            let signed = sign_manifest(&bytes, &args[2], &secret, password)?;
            std::fs::write(signature, signed).map_err(|_| "Signature write failed")?;
        }
        "verify" => {
            let bytes = read_bounded(&metadata, MAX_METADATA)?;
            let signed = String::from_utf8(read_bounded(&signature, 8192)?)
                .map_err(|_| "Invalid signature encoding")?;
            let manifest = authenticate(&bytes, &signed, &args[2])?;
            for (platform, name) in PLATFORMS {
                verify_installer(&manifest, platform, &dist.join(name))?;
            }
        }
        _ => return Err("Unknown release operation".into()),
    }
    Ok(())
}
fn main() {
    if let Err(error) = run() {
        eprintln!("SDE update trust: {error}");
        std::process::exit(1);
    }
}
