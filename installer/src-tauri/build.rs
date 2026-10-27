fn main() {
    // Give each Windows release a new Shell icon-cache key. The executable's
    // stable path can otherwise retain an earlier release's icon after upgrade.
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        let directory = std::path::Path::new("gen/app-icons");
        std::fs::create_dir_all(directory).expect("Create generated icon directory");
        let config: serde_json::Value = serde_json::from_slice(
            &std::fs::read("tauri.conf.json").expect("Read application configuration"),
        )
        .expect("Application configuration JSON");
        let overrides: serde_json::Value = std::env::var("TAURI_CONFIG")
            .map(|value| serde_json::from_str(&value).expect("Tauri override JSON"))
            .unwrap_or_default();
        // Native fixture builds can override the bundle version without changing
        // Cargo.toml. Match the installer version in that case as well.
        let version = overrides["version"]
            .as_str()
            .or_else(|| config["version"].as_str())
            .expect("Application version");
        let filename = format!("skyview-dev-setup-{version}.ico");
        for entry in std::fs::read_dir(directory).expect("Read generated icons") {
            let entry = entry.expect("Generated icon entry");
            let name = entry.file_name();
            let name = name.to_string_lossy();
            if name.starts_with("skyview-dev-setup-") && name.ends_with(".ico") && name != filename
            {
                std::fs::remove_file(entry.path()).expect("Remove previous generated icon");
            }
        }
        let bytes = std::fs::read("icons/icon.ico").expect("Read application icon");
        let output = directory.join(filename);
        if std::fs::read(&output).ok().as_deref() != Some(bytes.as_slice()) {
            std::fs::write(output, bytes).expect("Write versioned application icon");
        }
        println!("cargo:rerun-if-changed=icons/icon.ico");
    }
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "inspect_system",
            "inspect_schedule",
            "inspect_operation_incident",
            "acknowledge_operation_incident",
            "support_context",
            "save_support_report",
            "inspect_self_update",
            "set_self_update_paused",
            "run_operation",
            "open_destination",
            "check_application",
            "check_tools",
            "open_release",
            "check_operation_preflight",
        ]),
    ))
    .expect("Tauri build configuration must be valid");
}
