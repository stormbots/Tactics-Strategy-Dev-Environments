fn main() {
    tauri_build::try_build(tauri_build::Attributes::new().app_manifest(
        tauri_build::AppManifest::new().commands(&[
            "inspect_system",
            "inspect_schedule",
            "inspect_self_update",
            "inspect_app_update",
            "request_app_update",
            "discover_app_update",
            "inspect_app_update_progress",
            "inspect_app_update_receipt",
            "close_for_app_update",
            "run_operation",
            "open_destination",
        ]),
    ))
    .expect("Tauri build configuration must be valid");
}
