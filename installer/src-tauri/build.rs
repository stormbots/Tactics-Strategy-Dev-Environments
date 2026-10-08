fn main() {
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "inspect_system",
            "inspect_schedule",
            "run_operation",
            "open_destination",
        ]),
    ))
    .expect("Tauri build configuration must be valid");
}
