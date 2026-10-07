#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod process;
mod protocol;
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
#[derive(Clone, Copy, Deserialize, Debug)]
#[serde(rename_all = "lowercase")]
enum Operation {
    Install,
    Repair,
    Validate,
    Update,
}
impl Operation {
    fn name(self) -> &'static str {
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
        if !matches!(op, Operation::Validate) {
            emit("SKYVIEW_EVENT|progress|2|Approve administrator privileges to continue".into());
            let code = process::elevated(op.name(), &run_id, &mut emit)?;
            if code != 0 {
                emit(format!("SKYVIEW_EVENT|error|system|System setup stopped (exit {code}). Review the last package error in Show details, then retry."));
                return Ok(code);
            }
            #[cfg(windows)]
            let user = process::script(&root, "chocolatey/tools/Configure-SkyviewUser.ps1");
            #[cfg(not(windows))]
            let user = process::script(&root, "Configure-SkyviewUser.sh");
            let code = process::stream(user, &mut emit)?;
            if code != 0 {
                emit(format!("SKYVIEW_EVENT|error|profile|Your editor or workspace could not be configured (exit {code}). Review details and retry."));
                return Ok(code);
            }
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
    Ok(Report {
        code,
        success,
        lines,
        log_path: log.display().to_string(),
        platform,
    })
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
            true,
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
) -> Result<Report, String> {
    let guard = state.enter()?;
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = guard;
        run(app, operation, run_id, check_updates)
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
}
#[tauri::command]
fn open_destination(app: tauri::AppHandle, destination: Destination) -> Result<(), String> {
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
    if args.get(1).map(String::as_str) == Some("--privileged") {
        let code = if args.len() == 4 {
            process::helper(&args[2], &args[3]).unwrap_or_else(|e| {
                eprintln!("{e}");
                1
            })
        } else {
            1
        };
        std::process::exit(code);
    }
    tauri::Builder::default()
        .manage(Busy::default())
        .invoke_handler(tauri::generate_handler![
            inspect_system,
            run_operation,
            open_destination
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
    fn platform_detection() {
        let mint="ID=linuxmint\nVERSION_ID=\"22.2\"\nPRETTY_NAME=\"Linux Mint 22.2\"\nUBUNTU_CODENAME=noble\n";
        assert!(linux_platform(mint, "x86_64").supported);
        assert!(!linux_platform(mint, "aarch64").supported);
        assert!(!linux_platform("ID=ubuntu\nVERSION_ID=22.04", "x86_64").supported);
    }
    #[test]
    fn rejects_unapproved_operations() {
        assert!(serde_json::from_str::<Operation>("\"shell\"").is_err());
        assert!(process::helper("bash", "invalid").is_err());
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
