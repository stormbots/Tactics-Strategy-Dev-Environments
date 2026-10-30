#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
#[cfg(windows)]
mod desktop_icon;
mod journal;
mod preflight;
mod process;
mod protocol;
mod recovery_acknowledgment;
mod recovery_reports;
mod recovery_summary;
mod schedule;
mod support;
mod updates;
use serde::{Deserialize, Serialize};
use std::{
    io::Write,
    path::PathBuf,
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
};
use tauri::{Emitter, Manager};

#[derive(Clone, Default)]
struct Busy(Arc<AtomicBool>);
struct Guard(Busy);
impl Busy {
    fn enter(&self) -> Result<Guard, String> {
        if self.0.swap(true, Ordering::SeqCst) {
            Err("Another operation is already running.".into())
        } else {
            Ok(Guard(self.clone()))
        }
    }
}
impl Drop for Guard {
    fn drop(&mut self) {
        self.0 .0.store(false, Ordering::SeqCst);
    }
}
#[derive(Clone, Copy, Deserialize, Serialize, Debug)]
#[serde(rename_all = "lowercase")]
pub(crate) enum Operation {
    Install,
    Repair,
    Validate,
    Update,
}
impl Operation {
    pub(crate) fn name(self) -> &'static str {
        match self {
            Self::Install => "install",
            Self::Repair => "repair",
            Self::Validate => "validate",
            Self::Update => "update",
        }
    }
}
#[derive(Serialize)]
struct Platform {
    label: String,
    supported: bool,
}
#[derive(Serialize)]
struct Report {
    code: i32,
    success: bool,
    lines: Vec<String>,
    log_path: String,
    platform: Platform,
}
#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct Line {
    run_id: String,
    line: String,
}

fn linux_platform(release: &str, arch: &str) -> Platform {
    let value = |key: &str| {
        release
            .lines()
            .find_map(|s| {
                s.strip_prefix(&format!("{key}="))
                    .map(|v| v.trim_matches('"'))
            })
            .unwrap_or("")
    };
    Platform {
        label: format!("{} · {}", value("PRETTY_NAME"), arch),
        supported: value("ID") == "linuxmint"
            && value("VERSION_ID").starts_with("22")
            && value("UBUNTU_CODENAME") == "noble"
            && arch == "x86_64",
    }
}
fn platform() -> Platform {
    #[cfg(windows)]
    {
        let mut cmd = std::process::Command::new(
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        );
        cmd.args(["-NoProfile","-NonInteractive","-Command","(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion').CurrentBuildNumber"]);
        let build = process::hidden(&mut cmd)
            .output()
            .ok()
            .and_then(|o| String::from_utf8(o.stdout).ok())
            .and_then(|s| s.trim().parse::<u32>().ok())
            .unwrap_or(0);
        Platform {
            label: format!(
                "Windows {} · x64 (build {build})",
                if build >= 22000 { "11" } else { "10" }
            ),
            supported: build >= 22000 && std::env::consts::ARCH == "x86_64",
        }
    }
    #[cfg(not(windows))]
    {
        linux_platform(
            &std::fs::read_to_string("/etc/os-release").unwrap_or_default(),
            std::env::consts::ARCH,
        )
    }
}
fn backend(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    if cfg!(debug_assertions) {
        return Ok(PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."));
    }
    app.path()
        .resource_dir()
        .map(|p| p.join("backend"))
        .map_err(|e| e.to_string())
}
fn validation(root: &std::path::Path, check_updates: bool) -> std::process::Command {
    #[cfg(windows)]
    let mut c = process::script(root, "chocolatey/tools/Test-SkyviewStudentDev.ps1");
    #[cfg(not(windows))]
    let mut c = process::script(root, "Validate-SkyviewStudentDev.sh");
    if check_updates {
        #[cfg(windows)]
        c.arg("-CheckUpdates");
        #[cfg(not(windows))]
        c.arg("--check-updates");
    }
    c
}
fn run(
    app: tauri::AppHandle,
    op: Operation,
    run_id: String,
    check_updates: bool,
    acknowledged_uncertainty: bool,
) -> Result<Report, String> {
    if uuid::Uuid::parse_str(&run_id).is_err() {
        return Err("Invalid operation identifier.".into());
    }
    let root = backend(&app)?;
    let platform = platform();
    if !matches!(op, Operation::Validate) && !platform.supported {
        return Err("Provisioning supports Windows 11 x64 and Linux Mint Cinnamon 22.x amd64. Validation is still available.".into());
    }
    let logs = app.path().app_log_dir().map_err(|e| e.to_string())?;
    std::fs::create_dir_all(&logs).map_err(|e| e.to_string())?;
    let log = logs.join(format!("{}-{run_id}.log", op.name()));
    let mut file = std::fs::OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&log)
        .map_err(|e| e.to_string())?;
    let mut journal = if matches!(op, Operation::Validate) {
        None
    } else {
        Some(journal::Active::begin(&app, &run_id, op, &log)?)
    };
    let mut lines: Vec<String> = Vec::new();
    let mut emit = |line: String| {
        let line = protocol::redact(&line);
        let _ = writeln!(file, "{line}");
        let _ = file.flush();
        let _ = app.emit(
            "skyview-line",
            Line {
                run_id: run_id.clone(),
                line: line.clone(),
            },
        );
        // Validation and structured diagnostics are retained; ordinary output has
        // a bounded in-memory tail while the complete sanitized log stays on disk.
        if lines.len() >= 4000 {
            if let Some(n) = lines.iter().position(|s| protocol::parse(s).is_none()) {
                lines.remove(n);
            }
        }
        lines.push(line);
    };
    let result = (|| -> Result<i32, String> {
        if matches!(op, Operation::Install | Operation::Update)
            && !preflight::before_operation(
                &root,
                op,
                acknowledged_uncertainty,
                &mut emit,
            )
        {
            return Ok(75);
        }
        if !matches!(op, Operation::Validate) {
            if let Some(record) = journal.as_mut() {
                record.stage(journal::Stage::System)?;
            }
            emit("SKYVIEW_EVENT|progress|2|Approve administrator privileges to continue".into());
            let code = process::elevated(
                op.name(),
                &run_id,
                acknowledged_uncertainty,
                &mut emit,
            )?;
            if code != 0 {
                if code == 75 {
                    emit("SKYVIEW_EVENT|warning|deferred|Another SDE operation is running. Please retry when it finishes.".into());
                } else if matches!(
                    sde_coordination::status(),
                    sde_coordination::Status::Interrupted
                ) {
                    emit("SKYVIEW_EVENT|error|system|System setup stopped. An interrupted operation needs mentor review before another change.".into());
                } else {
                    emit(format!("SKYVIEW_EVENT|error|system|System setup stopped (exit {code}). Review the last package error in Show details, then retry."));
                }
                return Ok(code);
            }
            #[cfg(windows)]
            let user = process::script(&root, "chocolatey/tools/Configure-SkyviewUser.ps1");
            #[cfg(not(windows))]
            let user = process::script(&root, "Configure-SkyviewUser.sh");
            if let Some(record) = journal.as_mut() {
                record.stage(journal::Stage::Profile)?;
            }
            let code = process::stream(user, &mut emit)?;
            if code != 0 {
                emit(format!("SKYVIEW_EVENT|error|profile|Your editor or workspace could not be configured (exit {code}). Review details and retry."));
                return Ok(code);
            }
        }
        if let Some(record) = journal.as_mut() {
            record.stage(journal::Stage::Validation)?;
        }
        emit("SKYVIEW_EVENT|progress|95|Validating your development environment".into());
        process::stream(validation(&root, check_updates), &mut emit)
    })();
    let code = match result {
        Ok(code) => code,
        Err(message) => {
            emit(format!("SKYVIEW_EVENT|error|operation|{message}"));
            1
        }
    };
    drop(emit);
    let success = protocol::validated_success(code, &lines);
    if success {
        let line = "SKYVIEW_EVENT|progress|100|Development environment ready".to_string();
        let _ = writeln!(file, "{line}");
        let _ = app.emit(
            "skyview-line",
            Line {
                run_id,
                line: line.clone(),
            },
        );
        lines.push(line);
    }
    if let Some(record) = journal {
        if !matches!(
            sde_coordination::status(),
            sde_coordination::Status::Interrupted
        ) {
            record.complete()?;
        }
    }
    Ok(Report {
        code,
        success,
        lines,
        log_path: log.display().to_string(),
        platform,
    })
}
#[tauri::command]
fn inspect_operation_incident(app: tauri::AppHandle) -> Result<journal::Observation, String> {
    journal::inspect(&app)
}

#[tauri::command]
fn acknowledge_operation_incident(app: tauri::AppHandle, id: String) -> Result<(), String> {
    if uuid::Uuid::parse_str(&id).is_err() {
        return Err("Invalid operation identifier.".into());
    }
    journal::acknowledge(&app, &id)
}

#[tauri::command]
fn support_context(app: tauri::AppHandle, include_logs: bool) -> Result<support::Context, String> {
    support::context(&app, include_logs)
}

#[tauri::command]
fn save_support_report(app: tauri::AppHandle, html: String) -> Result<Option<String>, String> {
    support::save(&app, &html)
}
#[tauri::command]
async fn inspect_system(
    app: tauri::AppHandle,
    state: tauri::State<'_, Busy>,
) -> Result<Report, String> {
    let guard = state.enter()?;
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = guard;
        run(
            app,
            Operation::Validate,
            uuid::Uuid::new_v4().to_string(),
            false,
            false,
        )
    })
    .await
    .map_err(|e| e.to_string())?
}
#[tauri::command]
async fn run_operation(
    app: tauri::AppHandle,
    state: tauri::State<'_, Busy>,
    operation: Operation,
    run_id: String,
    check_updates: bool,
    acknowledged_uncertainty: bool,
) -> Result<Report, String> {
    let guard = state.enter()?;
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = guard;
        run(
            app,
            operation,
            run_id,
            check_updates,
            acknowledged_uncertainty,
        )
    })
    .await
    .map_err(|e| e.to_string())?
}
#[derive(Deserialize)]
#[serde(rename_all = "lowercase")]
enum Destination {
    Editor,
    Workspace,
    Logs,
    Maintenance,
    Repository,
    Skyview,
}
#[tauri::command]
async fn inspect_self_update() -> Result<sde_update_trust::observation::Status, String> {
    tauri::async_runtime::spawn_blocking(sde_update_trust::observation::inspect)
        .await
        .map_err(|_| "SDE update status could not be read. Please refresh.".to_string())
}
#[tauri::command]
async fn set_self_update_paused(
    paused: bool,
) -> Result<sde_update_trust::observation::Status, String> {
    tauri::async_runtime::spawn_blocking(move || {
        sde_update_trust::policy::set_paused(paused)?;
        Ok(sde_update_trust::observation::inspect())
    })
    .await
    .map_err(|_| "Could not save the SDE update setting. Refresh and try again.".to_string())?
}
#[tauri::command]
async fn inspect_schedule(app: tauri::AppHandle) -> Result<schedule::Schedule, String> {
    let root = backend(&app)?;
    tauri::async_runtime::spawn_blocking(move || schedule::inspect(&root))
        .await
        .map_err(|e| e.to_string())?
}
#[tauri::command]
fn open_destination(app: tauri::AppHandle, destination: Destination) -> Result<(), String> {
    let url = match destination {
        Destination::Repository => {
            Some("https://github.com/stormbots/Tactics-Strategy-Dev-Environments")
        }
        Destination::Skyview => Some("https://skyviewrobotics.com"),
        _ => None,
    };
    if let Some(url) = url {
        #[cfg(windows)]
        let mut command = std::process::Command::new(r"C:\Windows\explorer.exe");
        #[cfg(not(windows))]
        let mut command = std::process::Command::new("/usr/bin/xdg-open");
        crate::process::hidden(command.arg(url))
            .spawn()
            .map_err(|e| e.to_string())?;
        return Ok(());
    }
    let path = match destination {
        #[cfg(windows)]
        Destination::Editor => PathBuf::from(r"C:\Program Files\VSCodium\VSCodium.exe"),
        #[cfg(not(windows))]
        Destination::Editor => PathBuf::from("/usr/bin/codium"),
        #[cfg(windows)]
        Destination::Workspace => PathBuf::from(r"C:\Development"),
        #[cfg(not(windows))]
        Destination::Workspace => app
            .path()
            .home_dir()
            .map_err(|e| e.to_string())?
            .join("Development"),
        Destination::Logs => app.path().app_log_dir().map_err(|e| e.to_string())?,
        #[cfg(windows)]
        Destination::Maintenance => PathBuf::from(r"C:\ProgramData\SkyviewRobotics\Logs"),
        #[cfg(not(windows))]
        Destination::Maintenance => PathBuf::from("/var/log/skyview-robotics/student-dev"),
        Destination::Repository | Destination::Skyview => unreachable!(),
    };
    if !path.exists() {
        return Err(
            "This destination is not available yet. Install or repair the environment first."
                .into(),
        );
    }
    let mut cmd = if matches!(destination, Destination::Editor) {
        std::process::Command::new(path)
    } else {
        #[cfg(windows)]
        let mut c = std::process::Command::new(r"C:\Windows\explorer.exe");
        #[cfg(not(windows))]
        let mut c = std::process::Command::new("/usr/bin/xdg-open");
        c.arg(path);
        c
    };
    process::hidden(&mut cmd)
        .spawn()
        .map_err(|e| e.to_string())?;
    Ok(())
}
fn main() {
    let args: Vec<String> = std::env::args().collect();
    #[cfg(windows)]
    if args.get(1).map(String::as_str) == Some("--supervise-windows-maintenance") {
        let native_args: Vec<std::ffi::OsString> = std::env::args_os().skip(2).collect();
        let result = native_args
            .first()
            .ok_or(sde_coordination::manual::Failure::InvalidInvocation)
            .and_then(|script| {
                sde_update_trust::manual_windows::run(std::path::Path::new(script), &native_args[1..])
            });
        let code = match result {
            Ok(code) => code,
            Err(error) => {
                eprintln!(
                    "SKYVIEW_EVENT|error|coordination|{}",
                    serde_json::to_string(&error).unwrap()
                );
                error.exit_code()
            }
        };
        std::process::exit(code);
    }
    #[cfg(target_os = "linux")]
    if args.get(1).map(String::as_str) == Some("--supervise-linux-system") {
        let native_args: Vec<std::ffi::OsString> = std::env::args_os().skip(2).collect();
        let result = native_args
            .first()
            .ok_or(sde_coordination::manual::Failure::InvalidInvocation)
            .and_then(|script| {
                sde_coordination::manual::run(std::path::Path::new(script), &native_args[1..])
            });
        let code = match result {
            Ok(code) => code,
            Err(error) => {
                eprintln!(
                    "SKYVIEW_EVENT|error|coordination|{}",
                    serde_json::to_string(&error).unwrap()
                );
                error.exit_code()
            }
        };
        std::process::exit(code);
    }
    if args.get(1).map(String::as_str) == Some("--privileged") {
        let acknowledgement = args.get(4).map(String::as_str);
        let code = if args.len() == 5
            && matches!(acknowledgement, Some("clean" | "acknowledged"))
        {
            process::helper(
                &args[2],
                &args[3],
                acknowledgement == Some("acknowledged"),
            )
            .unwrap_or_else(|e| {
                eprintln!("{e}");
                1
            })
        } else {
            1
        };
        std::process::exit(code);
    }
    if args.get(1).map(String::as_str) == Some("--coordination-init") && args.len() == 2 {
        match sde_coordination::initialize() {
            Ok(()) => {
                // Existing safe non-GUI mode lets old/new shell wrappers
                // negotiate support without sending an unknown flag to an old
                // app (which would otherwise open a GUI). Not an execution permit.
                #[cfg(target_os = "linux")]
                println!("SDE_LINUX_SYSTEM_SUPERVISOR_V1");
                #[cfg(windows)]
                let _ = writeln!(std::io::stdout(), "SDE_WINDOWS_MAINTENANCE_SUPERVISOR_V1");
                return;
            }
            Err(e) => {
                eprintln!("{e}");
                std::process::exit(1);
            }
        }
    }
    let session = match sde_coordination::session() {
        Ok(lease) => lease,
        Err(e) => {
            let message = if e == sde_coordination::Error::Busy {
                "SDE is being updated. Please reopen it shortly.".to_string()
            } else {
                e.to_string()
            };
            process::coordination_message(&message);
            return;
        }
    };
    let builder = tauri::Builder::default();
    #[cfg(windows)]
    let builder = builder.setup(|app| {
        if let Some(window) = app.get_webview_window("main") {
            desktop_icon::set_taskbar_icon(&window);
        }
        Ok(())
    });
    builder
        .manage(Busy::default())
        .manage(updates::Checks::default())
        .manage(session)
        .invoke_handler(tauri::generate_handler![
            inspect_system,
            inspect_schedule,
            inspect_operation_incident,
            acknowledge_operation_incident,
            support_context,
            save_support_report,
            recovery_summary::save_recovery_summary,
            recovery_summary::acknowledge_recovery_incident,
            recovery_summary::list_recovery_reports,
            recovery_summary::read_recovery_report,
            recovery_summary::delete_recovery_report,
            inspect_self_update,
            set_self_update_paused,
            run_operation,
            open_destination,
            updates::check_application,
            updates::check_tools,
            updates::open_release,
            preflight::check_operation_preflight
        ])
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.state::<Busy>().0.load(Ordering::SeqCst) {
                    api.prevent_close();
                    let _ = window.emit("skyview-close-blocked", ());
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("Could not launch Skyview Dev Setup");
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn pause_toggle_ipc_is_granted_only_to_the_main_window() {
        // Exercise Tauri's actual generated permissions and production handler.
        // Missing/invalid boolean arguments stop before the fixed policy writer;
        // this test never reads or changes the workstation's pause preference.
        let app = tauri::test::mock_builder()
            .invoke_handler(tauri::generate_handler![set_self_update_paused])
            .build(tauri::generate_context!())
            .expect("Build the application with its real capability context");
        for label in ["main", "untrusted-test-window"] {
            let webview = tauri::WebviewWindowBuilder::new(&app, label, Default::default())
                .build()
                .unwrap();
            for body in [serde_json::json!({}), serde_json::json!({"paused": "true"})] {
                let response = tauri::test::get_ipc_response(
                    &webview,
                    tauri::webview::InvokeRequest {
                        cmd: "set_self_update_paused".into(),
                        callback: tauri::ipc::CallbackFn(0),
                        error: tauri::ipc::CallbackFn(1),
                        url: if cfg!(windows) {
                            "http://tauri.localhost"
                        } else {
                            "tauri://localhost"
                        }
                        .parse()
                        .unwrap(),
                        body: tauri::ipc::InvokeBody::Json(body),
                        headers: Default::default(),
                        invoke_key: tauri::test::INVOKE_KEY.into(),
                    },
                )
                .expect_err("Invalid arguments or an untrusted window must be rejected");
                let message = response.to_string();
                if label == "main" {
                    assert!(message.contains("paused"), "{message}");
                    assert!(!message.contains("not allowed"), "{message}");
                    assert!(message.contains("invalid args"), "{message}");
                } else {
                    assert!(message.contains("not allowed"), "{message}");
                }
            }
        }
        println!("SDE_PAUSE_TOGGLE_IPC_PERMISSIONS_OK: main reaches strict argument decoding; other window denied; no policy writes");
    }
    #[test]
    fn platform_detection() {
        let mint="ID=linuxmint\nVERSION_ID=\"22.2\"\nPRETTY_NAME=\"Linux Mint 22.2\"\nUBUNTU_CODENAME=noble\n";
        assert!(linux_platform(mint, "x86_64").supported);
        assert!(!linux_platform(mint, "aarch64").supported);
        assert!(!linux_platform("ID=ubuntu\nVERSION_ID=22.04", "x86_64").supported);
    }
    #[test]
    fn rejects_unapproved_operations() {
        assert!(serde_json::from_str::<Operation>("\"shell\"").is_err());
        assert!(process::helper("bash", "invalid", false).is_err());
        assert!(serde_json::from_str::<Destination>("\"https://example.com\"").is_err());
        assert!(serde_json::from_str::<Destination>("\"C:\\\\Windows\"").is_err());
    }
    #[test]
    fn operation_lock_recovers() {
        let busy = Busy::default();
        let guard = busy.enter().unwrap();
        assert!(busy.enter().is_err());
        drop(guard);
        assert!(busy.enter().is_ok());
    }
    #[test]
    fn all_modes_deserialize() {
        for op in ["install", "repair", "validate", "update"] {
            assert_eq!(
                serde_json::from_str::<Operation>(&format!("\"{op}\""))
                    .unwrap()
                    .name(),
                op
            );
        }
    }
}
