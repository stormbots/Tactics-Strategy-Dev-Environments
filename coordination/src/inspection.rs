//! Read-only native facts. An unavailable/partial diagnostic is not inactivity.
//! No package manager mutation, lock removal, registry edit, or reboot occurs.
use crate::safety::{Activity, PackageHealth};
use serde::{Deserialize, Serialize};
use std::{
    io::Read,
    process::{Command, Stdio},
    time::{Duration, Instant},
};

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Reason {
    NoPackageActivity,
    PackageActive,
    PackageIncomplete,
    PackageHealthy,
    Unavailable,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum FailureSource {
    BootEvent,
    SessionIdentity,
    PackageActivity,
    PackageHealth,
    Diagnostic,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Failure {
    pub source: FailureSource,
    pub code: Option<i64>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct NativeFacts {
    schema: u8,
    pub activity: Activity,
    pub health: PackageHealth,
    pub activity_reason: Reason,
    pub health_reason: Reason,
    #[serde(default)]
    pub diagnostics: Vec<Failure>,
    // Local restart provenance, not report content or execution authority.
    #[serde(skip_serializing)]
    pub(crate) boot_key: Option<String>,
}

impl NativeFacts {
    pub(crate) fn unavailable() -> Self {
        Self {
            schema: 1,
            activity: Activity::Unknown,
            health: PackageHealth::Unknown,
            activity_reason: Reason::Unavailable,
            health_reason: Reason::Unavailable,
            boot_key: None,
            diagnostics: vec![Failure {
                source: FailureSource::Diagnostic,
                code: None,
            }],
        }
    }
}

/// Fresh OS observations only, not the complete SDE operation/incident decision.
/// Callers must also own/probe the SDE gate and account for an earlier unknown
/// process lifetime. Boot provenance never substitutes for current package checks.
pub fn collect() -> NativeFacts {
    let facts = collect_native();
    let activity_ok = matches!(
        (facts.activity, facts.activity_reason),
        (Activity::Active, Reason::PackageActive)
            | (Activity::Inactive, Reason::NoPackageActivity)
            | (Activity::Unknown, Reason::Unavailable)
    );
    let health_ok = matches!(
        (facts.health, facts.health_reason),
        (PackageHealth::Healthy, Reason::PackageHealthy)
            | (PackageHealth::Incomplete, Reason::PackageIncomplete)
            | (PackageHealth::Unknown, Reason::Unavailable)
    );
    if facts.schema != 1 || !activity_ok || !health_ok {
        NativeFacts::unavailable()
    } else {
        facts
    }
}

#[cfg(test)]
pub(crate) fn test_facts(
    activity: Activity,
    health: PackageHealth,
    boot_key: Option<String>,
) -> NativeFacts {
    NativeFacts {
        schema: 1,
        activity,
        health,
        boot_key,
        diagnostics: Vec::new(),
        activity_reason: match activity {
            Activity::Active => Reason::PackageActive,
            Activity::Inactive => Reason::NoPackageActivity,
            Activity::Unknown => Reason::Unavailable,
        },
        health_reason: match health {
            PackageHealth::Healthy => Reason::PackageHealthy,
            PackageHealth::Incomplete => Reason::PackageIncomplete,
            PackageHealth::Unknown => Reason::Unavailable,
        },
    }
}

pub(crate) fn boot_key() -> Option<String> {
    #[cfg(target_os = "linux")]
    {
        linux_boot_key()
    }
    #[cfg(windows)]
    {
        windows_facts("boot").boot_key
    }
    #[cfg(all(unix, not(target_os = "linux")))]
    {
        None
    }
}

pub(crate) fn valid_boot_key(value: &str) -> bool {
    if value.len() > 128 {
        return false;
    }
    if let Some(id) = value.strip_prefix("linux:") {
        return uuid::Uuid::parse_str(id)
            .is_ok_and(|id_value| !id_value.is_nil() && id_value.to_string() == id);
    }
    let Some(rest) = value.strip_prefix("windows-session-start:") else {
        return false;
    };
    let parts: Vec<_> = rest.split(':').collect();
    parts.len() == 4
        && parts.iter().all(|p| {
            !p.is_empty()
                && p.bytes().all(|b| b.is_ascii_digit())
                && p.parse::<u64>().is_ok_and(|n| n > 0 && n.to_string() == *p)
        })
}

struct DiagnosticResult {
    code: Option<i32>,
    stdout: Vec<u8>,
    stderr: Vec<u8>,
}

/// Only the fixed read-only diagnostic commands below use this timeout. Never
/// use it for an installer, package mutation, or arbitrary caller-provided job.
fn diagnostic(mut command: Command, budget: Duration) -> Option<DiagnosticResult> {
    let mut child = command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .ok()?;
    let (send, recv) = std::sync::mpsc::channel();
    let stdout = child.stdout.take()?;
    let stderr = child.stderr.take()?;
    for (is_error, mut pipe) in [
        (false, Box::new(stdout) as Box<dyn Read + Send>),
        (true, Box::new(stderr) as Box<dyn Read + Send>),
    ] {
        let send = send.clone();
        std::thread::spawn(move || {
            let mut bytes = Vec::new();
            let ok = pipe.by_ref().take(65537).read_to_end(&mut bytes).is_ok();
            let _ = send.send((is_error, ok, bytes));
        });
    }
    drop(send);
    let start = Instant::now();
    let status = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status,
            Ok(None) if start.elapsed() < budget => std::thread::sleep(Duration::from_millis(10)),
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                return None;
            }
        }
    };
    let mut result = DiagnosticResult {
        code: status.code(),
        stdout: Vec::new(),
        stderr: Vec::new(),
    };
    for _ in 0..2 {
        let (is_error, ok, bytes) = recv.recv_timeout(Duration::from_secs(1)).ok()?;
        if !ok || bytes.len() > 65536 {
            return None;
        }
        if is_error {
            result.stderr = bytes;
        } else {
            result.stdout = bytes;
        }
    }
    Some(result)
}

#[cfg(target_os = "linux")]
fn linux_boot_key() -> Option<String> {
    let bytes = read_bounded(std::path::Path::new("/proc/sys/kernel/random/boot_id"), 128).ok()?;
    let value = format!("linux:{}", std::str::from_utf8(&bytes).ok()?.trim());
    valid_boot_key(&value).then_some(value)
}

#[cfg(target_os = "linux")]
fn read_bounded(path: &std::path::Path, limit: u64) -> std::io::Result<Vec<u8>> {
    let mut bytes = Vec::new();
    std::fs::File::open(path)?
        .take(limit + 1)
        .read_to_end(&mut bytes)?;
    if bytes.len() as u64 > limit {
        return Err(std::io::Error::other("Diagnostic exceeded its budget"));
    }
    Ok(bytes)
}

#[cfg(target_os = "linux")]
fn linux_locks(text: &str, keys: &[(u64, u64, u64)]) -> Activity {
    for line in text.lines() {
        let mut identity = None;
        for field in line.split_whitespace() {
            let parts: Vec<_> = field.split(':').collect();
            if parts.len() == 3 {
                match (
                    u64::from_str_radix(parts[0], 16),
                    u64::from_str_radix(parts[1], 16),
                    parts[2].parse::<u64>(),
                ) {
                    (Ok(major), Ok(minor), Ok(inode)) => identity = Some((major, minor, inode)),
                    _ => return Activity::Unknown,
                }
            }
        }
        let Some(identity) = identity else {
            return Activity::Unknown;
        };
        if keys.contains(&identity) {
            return Activity::Active;
        }
    }
    Activity::Inactive
}

#[cfg(target_os = "linux")]
fn linux_package_activity() -> Activity {
    use std::os::unix::fs::MetadataExt;
    let mut keys = Vec::new();
    for path in [
        "/var/lib/dpkg/lock",
        "/var/lib/dpkg/lock-frontend",
        "/var/lib/apt/lists/lock",
        "/var/cache/apt/archives/lock",
    ] {
        match std::fs::symlink_metadata(path) {
            Ok(m) if m.is_file() && m.uid() == 0 && m.mode() & 0o022 == 0 && m.nlink() == 1 => {
                keys.push((
                    libc::major(m.dev()) as u64,
                    libc::minor(m.dev()) as u64,
                    m.ino(),
                ));
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => (),
            _ => return Activity::Unknown,
        }
    }
    let Ok(bytes) = read_bounded(std::path::Path::new("/proc/locks"), 2 * 1024 * 1024) else {
        return Activity::Unknown;
    };
    let Ok(text) = std::str::from_utf8(&bytes) else {
        return Activity::Unknown;
    };
    linux_locks(text, &keys)
}

#[cfg(target_os = "linux")]
fn audit_health(result: Option<DiagnosticResult>) -> PackageHealth {
    match result {
        Some(result) if result.code == Some(0) && result.stderr.is_empty() => {
            if result.stdout.iter().all(u8::is_ascii_whitespace) {
                PackageHealth::Healthy
            } else {
                PackageHealth::Incomplete
            }
        }
        _ => PackageHealth::Unknown,
    }
}

#[cfg(target_os = "linux")]
fn collect_native() -> NativeFacts {
    let activity = linux_package_activity();
    let mut command = Command::new("/usr/bin/dpkg");
    command
        .args(["--admindir=/var/lib/dpkg", "--audit"])
        .env("LC_ALL", "C")
        .env_remove("DPKG_ADMINDIR")
        .env_remove("DPKG_ROOT")
        .current_dir("/");
    let health = audit_health(diagnostic(command, Duration::from_secs(5)));
    NativeFacts {
        schema: 1,
        activity,
        health,
        activity_reason: match activity {
            Activity::Active => Reason::PackageActive,
            Activity::Inactive => Reason::NoPackageActivity,
            Activity::Unknown => Reason::Unavailable,
        },
        health_reason: match health {
            PackageHealth::Healthy => Reason::PackageHealthy,
            PackageHealth::Incomplete => Reason::PackageIncomplete,
            PackageHealth::Unknown => Reason::Unavailable,
        },
        boot_key: linux_boot_key(),
        diagnostics: if activity == Activity::Unknown || health == PackageHealth::Unknown {
            vec![Failure {
                source: FailureSource::Diagnostic,
                code: None,
            }]
        } else {
            Vec::new()
        },
    }
}

#[cfg(windows)]
fn windows_facts(mode: &str) -> NativeFacts {
    use std::os::windows::process::CommandExt;
    let mut command = Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe");
    // Mode comes only from the two fixed callers below, never from IPC/input.
    let code = format!("& {{ {} }} {mode}", include_str!("inspection/windows.ps1"));
    command
        .args(["-NoProfile", "-NonInteractive", "-Command", &code])
        .env(
            "PSModulePath",
            r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules",
        )
        .current_dir(r"C:\Windows\System32")
        .creation_flags(0x08000000);
    let Some(result) = diagnostic(command, Duration::from_secs(10)) else {
        return NativeFacts::unavailable();
    };
    if result.code != Some(0) || !result.stderr.is_empty() {
        return NativeFacts::unavailable();
    }
    let Ok(mut facts) = serde_json::from_slice::<NativeFacts>(&result.stdout) else {
        return NativeFacts::unavailable();
    };
    if facts.schema != 1 {
        return NativeFacts::unavailable();
    }
    if facts
        .boot_key
        .as_ref()
        .is_some_and(|key| !valid_boot_key(key))
    {
        facts.boot_key = None;
    }
    facts
}

#[cfg(windows)]
fn collect_native() -> NativeFacts {
    windows_facts("all")
}

#[cfg(all(unix, not(target_os = "linux")))]
fn collect_native() -> NativeFacts {
    NativeFacts::unavailable()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn boot_provenance_is_bounded_canonical_not_a_wall_clock_or_bcd_identifier() {
        assert!(valid_boot_key("linux:9fe3858b-58da-4b96-b47d-ec2f1b867353"));
        assert!(valid_boot_key(
            "windows-session-start:12:123456789:45:123456790"
        ));
        for value in [
            "",
            "linux:00000000-0000-0000-0000-000000000000",
            "windows-session-start:0:123:4:5",
            "windows-session-start:12:001:4:5",
            "windows-session-start:12:-123:4:5",
            "boot-time:123",
            "bcd:{guid}",
        ] {
            assert!(!valid_boot_key(value));
        }
    }

    #[test]
    fn native_restart_provenance_and_package_activity_are_available_on_required_runners() {
        if std::env::var("SDE_REQUIRE_COORDINATION").as_deref() != Ok("1") {
            return;
        }
        let facts = collect();
        assert_ne!(
            facts.activity,
            Activity::Unknown,
            "Native package activity inspection must be supported on the required runner: {:?}",
            facts.diagnostics
        );
        let first = facts.boot_key.unwrap_or_else(|| {
            panic!(
                "Required native restart provenance must be readable: {:?}",
                facts.diagnostics
            )
        });
        assert!(valid_boot_key(&first));
        assert!(
            boot_key().as_deref() == Some(first.as_str()),
            "Restart provenance must be stable across independent read-only probes"
        );
    }

    #[cfg(unix)]
    #[test]
    fn read_only_timeout_never_becomes_a_successful_probe() {
        let mut command = Command::new("/bin/sh");
        command.args(["-c", "exec /bin/sleep 1"]);
        assert!(diagnostic(command, Duration::from_millis(20)).is_none());
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn audit_errors_are_unknown_not_positive_evidence_of_package_damage() {
        let result = |code, stdout: &[u8], stderr: &[u8]| {
            Some(DiagnosticResult {
                code: Some(code),
                stdout: stdout.to_vec(),
                stderr: stderr.to_vec(),
            })
        };
        assert_eq!(audit_health(result(0, b"", b"")), PackageHealth::Healthy);
        assert_eq!(
            audit_health(result(0, b"unconfigured package", b"")),
            PackageHealth::Incomplete
        );
        assert_eq!(
            audit_health(result(2, b"", b"cannot read package database")),
            PackageHealth::Unknown
        );
        assert_eq!(audit_health(None), PackageHealth::Unknown);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn native_lock_parse_handles_active_absent_and_incomplete_evidence() {
        let key = (8, 1, 12345);
        assert_eq!(
            linux_locks("1: POSIX ADVISORY WRITE 999 08:01:12345 0 EOF", &[key]),
            Activity::Active
        );
        assert_eq!(
            linux_locks("1: -> POSIX ADVISORY WRITE 999 08:01:12345 0 EOF", &[key]),
            Activity::Active
        );
        assert_eq!(linux_locks("", &[key]), Activity::Inactive);
        assert_eq!(
            linux_locks("unrecognized lock record", &[key]),
            Activity::Unknown
        );
    }
}
