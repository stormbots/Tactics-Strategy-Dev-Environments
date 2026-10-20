//! Advisory discovery only. No staging, installer execution or privileged input.
use serde::{Deserialize, Serialize};
use std::{
    io::{Read, Write},
    process::{Command, Stdio},
    sync::{
        atomic::{AtomicBool, Ordering},
        Arc,
    },
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

#[derive(Default, Clone)]
pub struct Checks {
    pub app: Arc<AtomicBool>,
    pub tools: Arc<AtomicBool>,
    pub preflight: Arc<AtomicBool>,
}
pub(crate) struct Lease(Arc<AtomicBool>);
pub(crate) fn enter(flag: &Arc<AtomicBool>) -> Result<Lease, String> {
    flag.compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
        .map(|_| Lease(flag.clone()))
        .map_err(|_| "A check is already running. Please wait for its result.".into())
}
impl Drop for Lease {
    fn drop(&mut self) {
        self.0.store(false, Ordering::SeqCst);
    }
}
pub fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Application {
    version: String,
    checked_at: u64,
    candidate: Option<sde_update_trust::discovery::Candidate>,
    failure: Option<sde_update_trust::discovery::Failure>,
}
#[tauri::command]
pub async fn check_application(
    app: tauri::AppHandle,
    state: tauri::State<'_, Checks>,
) -> Result<Application, String> {
    let lease = enter(&state.app)?;
    let version = app.package_info().version.to_string();
    tauri::async_runtime::spawn_blocking(move || {
        let _lease = lease;
        let supported = crate::platform().supported;
        #[cfg(windows)]
        let platform = "windows-x86_64";
        #[cfg(not(windows))]
        let platform = "linux-amd64";
        let result = if supported {
            sde_update_trust::discovery::notify(&version, platform)
        } else {
            Err(sde_update_trust::discovery::Failure::Unsupported)
        };
        Application {
            version,
            checked_at: now(),
            candidate: result.as_ref().ok().cloned().flatten(),
            failure: result.err(),
        }
    })
    .await
    .map_err(|_| "SDE discovery could not finish. Please retry.".into())
}
#[derive(Deserialize, Serialize, Clone)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Snapshot {
    tool: String,
    installed_version: Option<String>,
}
const TOOLS: &[&str] = &[
    "Git",
    "GitHub CLI",
    "Node.js",
    "Python",
    "Python venv",
    "VSCodium",
    "DBeaver",
    "PyCharm",
    "Chrome",
    "Firefox",
    "PowerShell 7",
    "OpenSSH",
    "7-Zip",
    "npm",
];
fn valid_snapshot(rows: &[Snapshot]) -> bool {
    rows.len() <= TOOLS.len()
        && rows.iter().enumerate().all(|(i, r)| {
            TOOLS.contains(&r.tool.as_str())
                && !rows[..i].iter().any(|a| a.tool == r.tool)
                && r.installed_version.as_ref().is_none_or(|v| {
                    !v.is_empty()
                        && v.len() <= 120
                        && !v.chars().any(|c| c.is_control() || c == '|')
                })
        })
}
/// Only for fixed read-only metadata/preflight scripts. Never used for installers.
pub fn output(mut command: Command, input: &[u8], budget: Duration) -> Result<Vec<u8>, String> {
    let mut child = crate::process::hidden(&mut command)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| "Metadata source could not be started. Retry or ask a mentor.".to_string())?;
    if let Some(mut pipe) = child.stdin.take() {
        let _ = pipe.write_all(input);
    }
    let mut stdout = child.stdout.take().unwrap();
    let (send, recv) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let mut bytes = Vec::new();
        let result = stdout.by_ref().take(131073).read_to_end(&mut bytes);
        let _ = send.send((result, bytes));
    });
    let started = Instant::now();
    loop {
        if started.elapsed() >= budget {
            let _ = child.kill();
            let _ = child.wait();
            return Err("Update check timed out. Local validation is unchanged; retry when the source is available.".into());
        }
        if let Some(status) = child
            .try_wait()
            .map_err(|_| "Update check status unavailable.")?
        {
            let (result, bytes) = recv
                .recv_timeout(Duration::from_secs(1))
                .map_err(|_| "Incomplete update response. Retry.")?;
            if result.is_err() || bytes.len() > 131072 || !status.success() {
                return Err(
                    "Update source returned incomplete information. Retry or ask a mentor.".into(),
                );
            }
            return Ok(bytes);
        }
        std::thread::sleep(Duration::from_millis(25));
    }
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Preview {
    tools: serde_json::Value,
    checked_at: u64,
}
#[tauri::command]
pub async fn check_tools(
    app: tauri::AppHandle,
    state: tauri::State<'_, Checks>,
    snapshot: Vec<Snapshot>,
) -> Result<Preview, String> {
    if !valid_snapshot(&snapshot) {
        return Err("Invalid tool snapshot. Run validation again.".into());
    }
    // These scripts only read package records/cache and remote metadata. They do
    // not take the global operation gate or launch provisioning/package changes.
    let lease = enter(&state.tools)?;
    let root = crate::backend(&app)?;
    tauri::async_runtime::spawn_blocking(move || {
        let _lease = lease;
        #[cfg(windows)]
        let command =
            crate::process::script(&root, "chocolatey/tools/Inspect-SkyviewToolUpdates.ps1");
        #[cfg(not(windows))]
        let command = {
            let mut c = Command::new("/usr/bin/python3");
            c.arg(root.join("linux/lib/tool_records.py"))
                .arg("--preview");
            c
        };
        let bytes = output(
            command,
            &serde_json::to_vec(&snapshot).map_err(|_| "Invalid snapshot")?,
            Duration::from_secs(60),
        )?;
        let tools: serde_json::Value =
            serde_json::from_slice(&bytes).map_err(|_| "Tool metadata is incomplete. Retry.")?;
        if !tools.is_array() || tools.as_array().unwrap().len() > TOOLS.len() {
            return Err("Tool metadata is incomplete. Retry.".into());
        }
        Ok(Preview {
            tools,
            checked_at: now(),
        })
    })
    .await
    .map_err(|_| "Tool discovery stopped. Retry.".to_string())?
}
fn release_url(tag: &str, installer: bool) -> Result<String, String> {
    let version =
        sde_update_trust::release_version(tag).map_err(|_| "Invalid official release version.")?;
    if installer {
        #[cfg(windows)]
        let filename = "Skyview-Dev-Setup-Windows-x64.exe";
        #[cfg(not(windows))]
        let filename = "Skyview-Dev-Setup-LinuxMint-amd64.deb";
        Ok(format!("https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/download/v{version}/{filename}"))
    } else {
        Ok(format!("https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v{version}"))
    }
}
#[tauri::command]
pub fn open_release(tag: Option<String>, installer: bool) -> Result<(), String> {
    let url = match tag {
        Some(tag) => release_url(&tag, installer)?,
        None if !installer => {
            "https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/latest".into()
        }
        _ => return Err("Select a compatible release first.".into()),
    };
    #[cfg(windows)]
    let mut c = Command::new(r"C:\Windows\explorer.exe");
    #[cfg(not(windows))]
    let mut c = Command::new("/usr/bin/xdg-open");
    crate::process::hidden(c.arg(url))
        .spawn()
        .map_err(|_| "The browser could not be opened. Please retry.".to_string())?;
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(unix)]
    #[test]
    fn read_only_child_deadline_is_enforced() {
        let mut command = Command::new("/bin/sh");
        command.args(["-c", "while :; do :; done"]);
        let started = Instant::now();
        assert!(output(command, b"", Duration::from_millis(50))
            .unwrap_err()
            .contains("timed out"));
        assert!(started.elapsed() < Duration::from_secs(2));
    }
    #[test]
    fn destinations_are_fixed_and_canonical() {
        assert!(release_url("v1.2.13", true).unwrap().starts_with(
            "https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/download/"
        ));
        for tag in [
            "v1.2.13/../../evil",
            "v01.2.13",
            "v1.2.13-rc1",
            "https://evil",
        ] {
            assert!(release_url(tag, false).is_err());
        }
    }
    #[test]
    fn snapshot_is_bounded_and_advisory() {
        assert!(valid_snapshot(&[Snapshot {
            tool: "Git".into(),
            installed_version: Some("2.43.0".into())
        }]));
        assert!(!valid_snapshot(&[Snapshot {
            tool: "../script".into(),
            installed_version: None
        }]));
    }
    #[test]
    fn independent_requests_are_deduplicated_until_completion() {
        let checks = Checks::default();
        let a = enter(&checks.app).unwrap();
        assert!(enter(&checks.app).is_err());
        assert!(enter(&checks.tools).is_ok());
        drop(a);
        assert!(enter(&checks.app).is_ok());
    }
}
