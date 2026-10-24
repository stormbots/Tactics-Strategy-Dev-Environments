//! Fixed, bounded, read-only receipts. Never return raw native output to students.
use crate::{host, read_bounded, release_version, Result};
use serde::{Deserialize, Serialize};
use std::path::Path;
#[cfg(windows)]
pub const ROOT: &str = r"C:\ProgramData\SkyviewRobotics\SelfUpdate";
#[cfg(not(windows))]
pub const ROOT: &str = "/var/lib/skyview-robotics/self-update";

pub(crate) fn trusted(path: &Path) -> Result<()> {
    for ancestor in path.ancestors() {
        #[cfg(windows)]
        host::windows::validate_acl(
            ancestor,
            ancestor == Path::new(r"C:\") || ancestor == Path::new(r"C:\ProgramData"),
        )
        .map_err(|_| "Untrusted maintenance receipt")?;
        #[cfg(not(windows))]
        host::validate(ancestor).map_err(|_| "Untrusted maintenance receipt")?;
    }
    let metadata = std::fs::symlink_metadata(path).map_err(|_| "Receipt unavailable")?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        if metadata.is_file() && metadata.nlink() != 1 {
            return Err("Linked receipt".into());
        }
    }
    if !metadata.is_file() && !metadata.is_dir() {
        return Err("Invalid receipt".into());
    }
    Ok(())
}
fn receipt<T: serde::de::DeserializeOwned>(name: &str) -> Result<T> {
    let path = Path::new(ROOT).join(name);
    trusted(&path)?;
    if !path.is_file() {
        return Err("Expected receipt file".into());
    }
    serde_json::from_slice(&read_bounded(&path, 16384)?).map_err(|_| "Invalid receipt".into())
}
#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub(crate) struct Policy {
    pub schema_version: u32,
    pub paused: bool,
}
#[derive(Debug, Deserialize, Serialize, PartialEq, Eq, Clone, Copy)]
#[serde(rename_all = "lowercase")]
pub enum Outcome {
    Current,
    Paused,
    Deferred,
    Unavailable,
    Failed,
    Updated,
}
#[derive(Debug, Deserialize, Serialize, PartialEq, Eq, Clone, Copy, Default)]
#[serde(rename_all = "lowercase")]
pub enum Phase {
    Tools,
    Identity,
    Policy,
    Discovery,
    Download,
    Verification,
    Packagehealth,
    Installer,
    Postcheck,
    #[default]
    Unknown,
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Record {
    schema_version: u32,
    checked_at: u64,
    #[serde(default)]
    completed_at: Option<u64>,
    application_version: String,
    maintenance_engine_version: String,
    #[serde(default)]
    applied_baseline: Option<String>,
    applied_baseline_version: Option<String>,
    tool_exit: Option<i32>,
    outcome: Outcome,
    detail: String,
    candidate_version: Option<String>,
    native_exit: Option<i32>,
    #[serde(default)]
    reboot_required: bool,
    recovery_available: bool,
    log_reference: Option<String>,
    #[serde(default)]
    phase: Phase,
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Status {
    pub paused: Option<bool>,
    pub policy_changed_at: Option<u64>,
    pub outcome: Outcome,
    pub phase: Phase,
    pub checked_at: Option<u64>,
    pub completed_at: Option<u64>,
    pub application_version: Option<String>,
    pub candidate_version: Option<String>,
    pub maintenance_engine_version: Option<String>,
    pub applied_baseline_version: Option<String>,
    pub tool_exit: Option<i32>,
    pub native_exit: Option<i32>,
    pub reboot_required: bool,
    pub recovery_available: bool,
    pub log_reference: Option<String>,
    pub log_folder: String,
    pub action: String,
    pub coordination: sde_coordination::Status,
}
fn version(value: &str) -> Result<String> {
    release_version(&format!("v{value}"))
}
fn valid(record: &Record) -> bool {
    record.schema_version == 1
        && record.checked_at > 0
        && record.checked_at <= 253402300799
        && record
            .completed_at
            .is_none_or(|end| end >= record.checked_at && end <= 253402300799)
        && (record.application_version.is_empty() || version(&record.application_version).is_ok())
        && version(&record.maintenance_engine_version).is_ok()
        && [&record.candidate_version, &record.applied_baseline_version]
            .into_iter()
            .all(|v| v.as_ref().is_none_or(|v| version(v).is_ok()))
        && record.detail.len() <= 4096
        && record
            .applied_baseline
            .as_ref()
            .is_none_or(|s| s.len() <= 256)
        && record.log_reference.as_ref().is_none_or(|s| {
            s.strip_prefix("logs/")
                .and_then(|s| s.strip_suffix(".log"))
                .is_some_and(|id| uuid::Uuid::parse_str(id).is_ok_and(|u| u.to_string() == id))
        })
}
fn action(outcome: Outcome, phase: Phase) -> &'static str {
    match outcome {
        Outcome::Current => "No newer eligible stable SDE release was found at this check.",
        Outcome::Paused => "SDE installation was paused. Tool maintenance has a separate result below.",
        Outcome::Updated => "SDE installation and native postchecks succeeded. Reopen SDE to use the installed version.",
        Outcome::Deferred => "Wait for active SDE, maintenance or package-manager work to finish; the next scheduled run can retry.",
        Outcome::Unavailable | Outcome::Failed => match phase {
            Phase::Download => "Download or staging did not complete. Check network and disk space; no installer was launched in this phase.",
            Phase::Discovery => "The release check was unavailable. Check the network and try the next scheduled run; this does not mean SDE is current.",
            Phase::Verification => "Release authentication or identity checks failed. Keep SDE paused and ask a mentor to inspect protected logs.",
            Phase::Packagehealth => "The package-manager health check failed. Ask a mentor to inspect DPKG state before retrying; do not delete package locks.",
            Phase::Installer | Phase::Postcheck => "Native installation or its postchecks did not complete reliably. Pause SDE updates and ask a mentor to inspect the transaction and native package state before retrying.",
            Phase::Tools => "Development-tool maintenance did not complete. Inspect its logs separately before retrying SDE installation.",
            _ => "Status is missing, unreadable or requires mentor review. Refresh and consult protected logs; do not infer a successful update.",
        }
    }
}
/// Does not launch a process, perform a release check, download, elevate or write.
pub fn inspect() -> Status {
    let policy = crate::policy::read().ok();
    let record = receipt::<Record>("status.json").ok().filter(valid);
    summarize(policy, record, sde_coordination::status())
}
fn summarize(
    policy: Option<Policy>,
    record: Option<Record>,
    coordination: sde_coordination::Status,
) -> Status {
    let mut result = Status {
        paused: policy.map(|p| p.paused),
        policy_changed_at: None,
        outcome: Outcome::Unavailable,
        phase: Phase::Unknown,
        checked_at: None,
        completed_at: None,
        application_version: None,
        candidate_version: None,
        maintenance_engine_version: None,
        applied_baseline_version: None,
        tool_exit: None,
        native_exit: None,
        reboot_required: false,
        recovery_available: false,
        log_reference: None,
        log_folder: Path::new(ROOT).join("logs").to_string_lossy().into(),
        action: action(Outcome::Unavailable, Phase::Unknown).into(),
        coordination,
    };
    if result.paused.is_some() {
        result.policy_changed_at = std::fs::metadata(Path::new(ROOT).join("policy.json"))
            .ok()
            .and_then(|m| m.modified().ok())
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|t| t.as_secs());
    }
    if let Some(r) = record {
        result.outcome = r.outcome;
        result.phase = r.phase;
        result.checked_at = Some(r.checked_at);
        result.completed_at = r.completed_at;
        result.application_version =
            (!r.application_version.is_empty()).then_some(r.application_version);
        result.candidate_version = r.candidate_version;
        result.maintenance_engine_version = Some(r.maintenance_engine_version);
        result.applied_baseline_version = r.applied_baseline_version;
        result.tool_exit = r.tool_exit;
        result.native_exit = r.native_exit;
        result.reboot_required = r.reboot_required;
        result.recovery_available = r.recovery_available;
        result.log_reference = r.log_reference;
        result.action = action(result.outcome, result.phase).into();
    }
    result
}
/// Manual mentor inspection only; never executes an installer or clears intent.
pub fn verify_recovery() -> Result<()> {
    let platform = if cfg!(windows) {
        "windows-x86_64"
    } else {
        "linux-amd64"
    };
    let filename = crate::PLATFORMS
        .iter()
        .find(|(p, _)| *p == platform)
        .ok_or("Unsupported platform")?
        .1;
    let mut found = false;
    for name in ["recovery.json", "previous-recovery.json"] {
        if !Path::new(ROOT)
            .join(name)
            .try_exists()
            .map_err(|_| "Recovery inspection unavailable")?
        {
            continue;
        }
        #[derive(Deserialize)]
        #[serde(rename_all = "camelCase", deny_unknown_fields)]
        struct Recovery {
            schema_version: u32,
            version: String,
            transaction: String,
        }
        let r: Recovery = receipt(name)?;
        if r.schema_version != 1
            || version(&r.version).is_err()
            || !uuid::Uuid::parse_str(&r.transaction)
                .is_ok_and(|id| id.to_string() == r.transaction)
        {
            return Err("Invalid recovery receipt".into());
        }
        let dir = Path::new(ROOT).join("staging").join(&r.transaction);
        for file in ["sde-update.json", "sde-update.json.minisig", filename] {
            trusted(&dir.join(file))?;
        }
        let metadata = read_bounded(&dir.join("sde-update.json"), crate::MAX_METADATA)?;
        let signature =
            String::from_utf8(read_bounded(&dir.join("sde-update.json.minisig"), 8192)?)
                .map_err(|_| "Invalid recovery signature")?;
        let manifest = crate::authenticate(&metadata, &signature, &format!("v{}", r.version))?;
        crate::verify_installer(&manifest, platform, &dir.join(filename))?;
        println!("{name}: authenticated version {} at {}. Manual recovery still requires mentor assessment.", r.version, dir.join(filename).display());
        found = true;
    }
    if !found {
        return Err("No retained signed recovery installer available".into());
    }
    Ok(())
}
#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> Record {
        serde_json::from_str(r#"{"schemaVersion":1,"checkedAt":100,"applicationVersion":"1.2.1","maintenanceEngineVersion":"1.2.1","appliedBaselineVersion":"1.1.5","toolExit":1,"outcome":"updated","detail":"secret credential must never reach UI","candidateVersion":"1.2.2","nativeExit":0,"recoveryAvailable":true,"logReference":null}"#).unwrap()
    }
    #[test]
    fn pause_is_current_and_results_are_independent() {
        let status = summarize(
            Some(Policy {
                schema_version: 1,
                paused: true,
            }),
            Some(fixture()),
            sde_coordination::Status::Interrupted,
        );
        assert_eq!(status.paused, Some(true));
        assert_eq!(status.outcome, Outcome::Updated);
        assert_eq!(status.tool_exit, Some(1));
        let json = serde_json::to_string(&status).unwrap();
        assert!(!json.contains("secret credential"));
        assert!(json.contains("interrupted"));
    }
    #[test]
    fn invalid_and_unknown_records_never_mean_current() {
        let mut r = fixture();
        assert!(valid(&r));
        r.candidate_version = Some("../../bad".into());
        assert!(!valid(&r));
        r = fixture();
        r.log_reference = Some("logs/../../credentials.log".into());
        assert!(!valid(&r));
        assert!(serde_json::from_str::<Outcome>("\"successful-ish\"").is_err());
        assert_eq!(
            summarize(None, None, sde_coordination::Status::Unavailable).outcome,
            Outcome::Unavailable
        );
    }
    #[test]
    fn actionable_failure_phases_are_distinct() {
        for phase in [Phase::Download, Phase::Packagehealth, Phase::Installer] {
            assert_ne!(
                action(Outcome::Failed, phase),
                action(Outcome::Failed, Phase::Unknown)
            );
        }
        assert_ne!(
            action(Outcome::Failed, Phase::Download),
            action(Outcome::Failed, Phase::Installer)
        );
    }
}
