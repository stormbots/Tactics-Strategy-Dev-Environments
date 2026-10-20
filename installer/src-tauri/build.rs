fn main() {
    // Give each Windows release a new Shell icon-cache key. The executable's
    // stable path can otherwise retain an earlier release's icon after upgrade.
    if std::env::var("CARGO_CFG_TARGET_OS").as_deref() == Ok("windows") {
        let directory = std::path::Path::new("gen/app-icons");
        std::fs::create_dir_all(directory).expect("Create generated icon directory");
        let filename = format!(
            "skyview-dev-setup-{}.ico",
            std::env::var("CARGO_PKG_VERSION").expect("Application version")
        );
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
            "inspect_self_update",
            "run_operation",
            "open_destination",
        ]),
    ))
    .expect("Tauri build configuration must be valid");
}
