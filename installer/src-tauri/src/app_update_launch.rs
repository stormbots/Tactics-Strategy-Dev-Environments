//! Fixed Linux launch transport. Only reachable after the independent source gate.
//! No caller arguments, shell, installer bytes or authority in stdout.
use std::process::{Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
static BUSY: AtomicBool = AtomicBool::new(false);
// Ambiguous attempts are not automatically retried within this GUI process.
static UNCERTAIN: AtomicBool = AtomicBool::new(false);
fn command() -> Command {
    let mut c = Command::new("/usr/bin/pkexec");
    c.args([
        "--disable-internal-agent",
        "/usr/local/libexec/skyview-app-update-request",
    ])
    .env_clear()
    .env("PATH", "/usr/sbin:/usr/bin:/sbin:/bin")
    .env("LC_ALL", "C")
    .stdin(Stdio::null())
    .stdout(Stdio::piped())
    .stderr(Stdio::null());
    c
}
pub fn request() -> Result<serde_json::Value, &'static str> {
    if UNCERTAIN.load(Ordering::SeqCst)
        || BUSY
            .compare_exchange(false, true, Ordering::SeqCst, Ordering::SeqCst)
            .is_err()
    {
        return Err("Request outcome requires protected status review");
    }
    // The worker thread owns the child through completion, including after a UI
    // deadline. Never kill a broker/worker or equate closing stdout with cancellation.
    let (tx, rx) = std::sync::mpsc::sync_channel(1);
    let spawn = std::thread::Builder::new()
        .name("app-update-request".into())
        .spawn(move || {
            let result = (|| {
                use std::io::Read;
                use std::os::unix::fs::MetadataExt;
                for path in [
                    "/usr/bin/pkexec",
                    "/usr/local/libexec/skyview-app-update-request",
                ] {
                    for ancestor in std::path::Path::new(path).ancestors() {
                        let m = std::fs::symlink_metadata(ancestor)
                            .map_err(|_| "Untrusted request deployment")?;
                        if m.uid() != 0
                            || m.mode() & 0o022 != 0
                            || m.file_type().is_symlink()
                            || !(m.is_file() || m.is_dir())
                            || (m.is_file() && m.nlink() != 1)
                        {
                            return Err("Untrusted request deployment");
                        }
                    }
                }
                let mut child = command()
                    .spawn()
                    .map_err(|_| "OS authorization unavailable")?;
                let mut bytes = Vec::new();
                let read = child
                    .stdout
                    .take()
                    .ok_or("Missing authorization response")?
                    .take(1025)
                    .read_to_end(&mut bytes);
                let status = child
                    .wait()
                    .map_err(|_| "Authorization outcome uncertain")?;
                if read.is_err() || bytes.len() > 1024 || !status.success() {
                    return Err("No protected request acceptance confirmed");
                }
                serde_json::to_value(
                    sde_update_trust::app_only_confirm_request(&bytes)
                        .map_err(|_| "No protected request acceptance confirmed")?,
                )
                .map_err(|_| "Receipt encoding unavailable")
            })();
            if result.is_err() {
                UNCERTAIN.store(true, Ordering::SeqCst);
            }
            BUSY.store(false, Ordering::SeqCst);
            let _ = tx.send(result);
        });
    if spawn.is_err() {
        BUSY.store(false, Ordering::SeqCst);
        return Err("Authorization transport unavailable");
    }
    match rx.recv_timeout(std::time::Duration::from_secs(120)) {
        Ok(value) => value,
        Err(_) => {
            UNCERTAIN.store(true, Ordering::SeqCst);
            Err("Authorization outcome uncertain; no automatic retry")
        }
    }
}
#[cfg(test)]
mod tests {
    #[test]
    fn fixed_command_never_accepts_caller_parameters() {
        let c = super::command();
        assert_eq!(c.get_program(), "/usr/bin/pkexec");
        assert_eq!(
            c.get_args().collect::<Vec<_>>(),
            [
                "--disable-internal-agent",
                "/usr/local/libexec/skyview-app-update-request"
            ]
        );
        assert!(c.get_envs().all(|(k, _)| k == "PATH" || k == "LC_ALL"));
    }
}
