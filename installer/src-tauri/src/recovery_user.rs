//! Per-account evidence and acknowledgment, separate from reports and machine
//! coordination. A record here is never authority to launch or retire anything.
use crate::{
    recovery_context::{self, Context, Evidence},
    recovery_reports as files,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs,
    path::{Path, PathBuf},
};

type Result<T> = std::result::Result<T, String>;

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Decision {
    pub incident_id: String,
    pub acknowledged_at: u64,
    pub report_id: Option<String>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Outcome {
    pub incident_id: String,
    pub report_id: Option<String>,
    pub report_warning: Option<String>,
    pub acknowledgment: Option<Decision>,
    pub acknowledgment_warning: Option<String>,
}
#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Receipt {
    schema: u8,
    generation: String,
    evidence_sha256: String,
    decision: Decision,
}

pub struct Store {
    app_data: PathBuf,
}
impl Store {
    pub fn new(app_data: PathBuf) -> Self {
        Self { app_data }
    }
    fn directory(&self, evidence: &Evidence) -> Result<PathBuf> {
        let Context::User { incident } = &evidence.context else {
            return Err("User acknowledgment requires user evidence.".into());
        };
        evidence.context.validate(&incident.id, u64::MAX)?;
        if evidence.generation.len() != 64
            || !evidence
                .generation
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err("Invalid user evidence generation.".into());
        }
        Ok(self
            .app_data
            .join("recovery-state")
            .join(&incident.id)
            .join(&evidence.generation))
    }
    fn id<'a>(&self, evidence: &'a Evidence) -> Result<&'a str> {
        match &evidence.context {
            Context::User { incident } => Ok(&incident.id),
            _ => Err("User acknowledgment requires user evidence.".into()),
        }
    }
    fn current(&self, evidence: &Evidence, now: u64) -> Result<()> {
        let current = recovery_context::read_evidence(&self.app_data, self.id(evidence)?, now)?;
        if current.generation != evidence.generation || current.bytes != evidence.bytes {
            return Err("User evidence changed; Check Again before acknowledging it.".into());
        }
        Ok(())
    }
    pub fn inspect(&self, evidence: &Evidence, now: u64) -> Result<Option<Decision>> {
        self.current(evidence, now)?;
        let directory = self.directory(evidence)?;
        // Normal absent-state inspection is read-only: do not create a tree.
        for path in [
            self.app_data.join("recovery-state"),
            directory.parent().unwrap().to_path_buf(),
            directory.clone(),
        ] {
            match fs::symlink_metadata(&path) {
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
                Err(_) => return Err("User acknowledgment history is unavailable.".into()),
                Ok(_) => files::private_directory(&path)?,
            }
        }
        self.inspect_in(&directory, evidence, now)
    }
    fn inspect_in(
        &self,
        directory: &Path,
        evidence: &Evidence,
        now: u64,
    ) -> Result<Option<Decision>> {
        let original = optional(&directory.join("evidence.json"), 16 * 1024)?;
        if original
            .as_ref()
            .is_some_and(|bytes| bytes != &evidence.bytes)
        {
            return Err("Preserved user evidence is changed or unreadable.".into());
        }
        let Some(bytes) = optional(&directory.join("acknowledged.json"), 4096)? else {
            return Ok(None);
        };
        if original.is_none() {
            return Err("Acknowledgment is missing its preserved evidence.".into());
        }
        let receipt: Receipt =
            serde_json::from_slice(&bytes).map_err(|_| "User acknowledgment record is invalid.")?;
        if receipt.schema != 1
            || receipt.generation != evidence.generation
            || receipt.evidence_sha256 != format!("{:x}", Sha256::digest(&evidence.bytes))
            || receipt.decision.incident_id != self.id(evidence)?
            || receipt.decision.acknowledged_at == 0
            || receipt.decision.acknowledged_at > now
            || receipt
                .decision
                .report_id
                .as_ref()
                .is_some_and(|id| !canonical(id))
        {
            return Err("User acknowledgment record is invalid or stale.".into());
        }
        Ok(Some(receipt.decision))
    }
    pub fn acknowledge(
        &self,
        evidence: &Evidence,
        report_id: Option<String>,
        now: u64,
    ) -> Result<Decision> {
        self.acknowledge_at(evidence, report_id, now, |_| Ok(()))
    }
    pub fn with_report(
        &self,
        evidence: &Evidence,
        now: u64,
        save: impl FnOnce() -> Result<String>,
    ) -> Result<Outcome> {
        self.current(evidence, now)?;
        let (report_id, report_warning) = match save() {
            Ok(id) => (Some(id), None),
            Err(_) => (None, Some("The summary could not be saved. Acknowledgment still requires preservation of the original user evidence.".into())),
        };
        let (acknowledgment, acknowledgment_warning) = match self.acknowledge(evidence, report_id.clone(), now) {
            Ok(decision) => (Some(decision), None),
            // Storage/source errors above are fixed messages, not raw paths,
            // journal text or OS debug output. Preserve the actionable reason.
            Err(message) => (None, Some(format!("User acknowledgment could not be confirmed: {message} Keep the evidence and Check Again; do not assume completion or permission to run changes."))),
        };
        Ok(Outcome {
            incident_id: self.id(evidence)?.into(),
            report_id,
            report_warning,
            acknowledgment,
            acknowledgment_warning,
        })
    }
    fn acknowledge_at(
        &self,
        evidence: &Evidence,
        report_id: Option<String>,
        now: u64,
        mut checkpoint: impl FnMut(u8) -> Result<()>,
    ) -> Result<Decision> {
        if now == 0 || report_id.as_ref().is_some_and(|id| !canonical(id)) {
            return Err("Invalid user acknowledgment request.".into());
        }
        self.current(evidence, now)?;
        if let Some(decision) = self.inspect(evidence, now)? {
            sync_chain(&self.directory(evidence)?)?;
            return Ok(decision);
        }
        let directory = self.directory(evidence)?;
        for path in [
            self.app_data.join("recovery-state"),
            directory.parent().unwrap().to_path_buf(),
            directory.clone(),
        ] {
            files::private_directory(&path)?;
        }
        publish(&directory, "evidence.json", &evidence.bytes)?;
        if files::read(&directory.join("evidence.json"), 16 * 1024)? != evidence.bytes {
            return Err("Original user evidence could not be preserved.".into());
        }
        checkpoint(1)?;
        self.current(evidence, now)?;
        let receipt = Receipt {
            schema: 1,
            generation: evidence.generation.clone(),
            evidence_sha256: format!("{:x}", Sha256::digest(&evidence.bytes)),
            decision: Decision {
                incident_id: self.id(evidence)?.into(),
                acknowledged_at: now,
                report_id,
            },
        };
        publish(
            &directory,
            "acknowledged.json",
            &serde_json::to_vec(&receipt).map_err(|_| "Acknowledgment encoding failed.")?,
        )?;
        checkpoint(2)?;
        self.current(evidence, now)?;
        self.inspect_in(&directory, evidence, now)?
            .ok_or_else(|| "Acknowledgment could not be confirmed; Check Again.".into())
    }
}

fn canonical(id: &str) -> bool {
    uuid::Uuid::parse_str(id).is_ok_and(|value| value.to_string() == id)
}
fn optional(path: &Path, max: u64) -> Result<Option<Vec<u8>>> {
    match fs::symlink_metadata(path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(_) => Err("User acknowledgment evidence is unavailable.".into()),
        Ok(_) => files::read(path, max).map(Some),
    }
}
// Flush a new private staging file, then publish atomically without replacing
// an existing record. Partial staging remains private; retries verify fixed
// committed filenames, never interpret staging files as consent or purge them.
fn publish(directory: &Path, name: &str, bytes: &[u8]) -> Result<()> {
    let destination = directory.join(name);
    if fs::symlink_metadata(&destination).is_ok() {
        return Ok(());
    }
    let temporary = directory.join(format!("pending-{}", uuid::Uuid::new_v4()));
    files::write(&temporary, bytes)?;
    if rename_new(&temporary, &destination).is_err() && fs::symlink_metadata(&destination).is_err()
    {
        return Err("User acknowledgment publication failed; evidence was retained.".into());
    }
    sync_chain(directory)
}
fn sync_chain(directory: &Path) -> Result<()> {
    for path in directory.ancestors().take(4) {
        files::sync(path)?;
    }
    Ok(())
}
#[cfg(target_os = "linux")]
fn rename_new(source: &Path, destination: &Path) -> std::io::Result<()> {
    use std::os::unix::ffi::OsStrExt;
    let source = std::ffi::CString::new(source.as_os_str().as_bytes())?;
    let destination = std::ffi::CString::new(destination.as_os_str().as_bytes())?;
    if unsafe {
        libc::renameat2(
            libc::AT_FDCWD,
            source.as_ptr(),
            libc::AT_FDCWD,
            destination.as_ptr(),
            libc::RENAME_NOREPLACE,
        )
    } == 0
    {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error())
    }
}
#[cfg(windows)]
fn rename_new(source: &Path, destination: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::{MoveFileExW, MOVEFILE_WRITE_THROUGH};
    let source: Vec<u16> = source.as_os_str().encode_wide().chain(Some(0)).collect();
    let destination: Vec<u16> = destination
        .as_os_str()
        .encode_wide()
        .chain(Some(0))
        .collect();
    if unsafe {
        MoveFileExW(
            source.as_ptr(),
            destination.as_ptr(),
            MOVEFILE_WRITE_THROUGH,
        )
    } != 0
    {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error())
    }
}
#[cfg(not(any(target_os = "linux", windows)))]
fn rename_new(_: &Path, _: &Path) -> std::io::Result<()> {
    Err(std::io::Error::new(
        std::io::ErrorKind::Unsupported,
        "Unsupported platform",
    ))
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Fixture {
        app: PathBuf,
        id: String,
    }
    impl Fixture {
        fn new() -> Self {
            let app =
                std::env::temp_dir().join(format!("sde-user-ack-ci-{}", uuid::Uuid::new_v4()));
            fs::create_dir(&app).unwrap();
            let f = Self {
                app,
                id: uuid::Uuid::new_v4().to_string(),
            };
            fs::write(f.path(), serde_json::to_vec(&serde_json::json!({
                "schema":1,"id":f.id,"operation":"update","stage":"profile",
                "startedAt":10,"observedAt":20,"logPath":"/private/student/log.txt","acknowledged":false
            })).unwrap()).unwrap();
            f
        }
        fn path(&self) -> PathBuf {
            self.app.join("operation-journal.json")
        }
        fn store(&self) -> Store {
            Store::new(self.app.clone())
        }
        fn evidence(&self) -> Evidence {
            recovery_context::read_evidence(&self.app, &self.id, 100).unwrap()
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.app).unwrap();
        }
    }

    #[test]
    fn user_acknowledgment_preserves_source_and_commits_separate_generation_bound_decision() {
        let f = Fixture::new();
        let evidence = f.evidence();
        let store = f.store();
        let bytes = fs::read(f.path()).unwrap();
        let metadata = fs::metadata(f.path()).unwrap();
        assert_eq!(store.inspect(&evidence, 100).unwrap(), None);
        assert!(!f.app.join("recovery-state").exists());
        let report_id = uuid::Uuid::new_v4().to_string();
        let decision = store
            .acknowledge(&evidence, Some(report_id.clone()), 100)
            .unwrap();
        assert_eq!(decision.incident_id, f.id);
        assert_eq!(decision.report_id, Some(report_id));
        assert_eq!(
            store.inspect(&evidence, 100).unwrap(),
            Some(decision.clone())
        );
        assert_eq!(
            Store::new(f.app.clone())
                .acknowledge(&evidence, None, 101)
                .unwrap(),
            decision
        );
        assert_eq!(fs::read(f.path()).unwrap(), bytes);
        assert_eq!(
            fs::metadata(f.path()).unwrap().modified().unwrap(),
            metadata.modified().unwrap()
        );
        assert_eq!(
            files::read(
                &store.directory(&evidence).unwrap().join("evidence.json"),
                16384
            )
            .unwrap(),
            bytes
        );
        let public = serde_json::to_string(&decision).unwrap();
        assert!(!public.contains("generation"));
        assert!(!public.contains("private"));
    }

    #[test]
    fn user_acknowledgment_replays_each_publication_boundary_without_replacing_originals() {
        for phase in [1, 2] {
            let f = Fixture::new();
            let evidence = f.evidence();
            let store = f.store();
            assert!(store
                .acknowledge_at(&evidence, None, 100, |current| if phase == current {
                    Err("injected termination checkpoint".into())
                } else {
                    Ok(())
                })
                .is_err());
            let directory = store.directory(&evidence).unwrap();
            let original = files::read(&directory.join("evidence.json"), 16384).unwrap();
            let partial = directory.join("pending-injected-partial");
            files::write(&partial, b"{incomplete staging").unwrap();
            assert_eq!(store.inspect(&evidence, 100).unwrap().is_some(), phase == 2);
            let result = store.acknowledge(&evidence, None, 101).unwrap();
            assert_eq!(result.acknowledged_at, if phase == 2 { 100 } else { 101 });
            assert_eq!(
                files::read(&directory.join("evidence.json"), 16384).unwrap(),
                original
            );
            assert_eq!(fs::read(f.path()).unwrap(), original);
            assert_eq!(fs::read(partial).unwrap(), b"{incomplete staging");
        }
    }

    #[test]
    fn user_acknowledgment_report_failure_is_nonblocking_but_preservation_failure_blocks() {
        let f = Fixture::new();
        let evidence = f.evidence();
        let store = f.store();
        let result = store
            .with_report(&evidence, 100, || Err("disk full".into()))
            .unwrap();
        assert!(result.report_id.is_none());
        assert!(result.report_warning.is_some());
        assert!(result.acknowledgment.is_some());
        let second = Fixture::new();
        let evidence = second.evidence();
        let store = second.store();
        let directory = store.directory(&evidence).unwrap();
        for path in directory
            .ancestors()
            .take(3)
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
        {
            files::private_directory(path).unwrap();
        }
        // Invalid evidence destination must never be overwritten or waived.
        fs::create_dir(directory.join("evidence.json")).unwrap();
        let report = uuid::Uuid::new_v4().to_string();
        let result = store
            .with_report(&evidence, 100, || Ok(report.clone()))
            .unwrap();
        assert_eq!(result.report_id, Some(report));
        assert!(result.acknowledgment.is_none());
        assert!(result.acknowledgment_warning.is_some());
        assert!(!directory.join("acknowledged.json").exists());
        assert_eq!(fs::read(second.path()).unwrap(), evidence.bytes);
    }

    #[test]
    fn user_acknowledgment_new_identical_record_is_not_the_old_generation() {
        let f = Fixture::new();
        let evidence = f.evidence();
        let store = f.store();
        let bytes = evidence.bytes.clone();
        let old = store.directory(&evidence).unwrap();
        store.acknowledge(&evidence, None, 100).unwrap();
        drop(evidence); // Windows deliberately denies replacement while held.
        fs::rename(f.path(), f.app.join("original-evidence.json")).unwrap();
        fs::write(f.path(), &bytes).unwrap();
        let new = f.evidence();
        assert_ne!(store.directory(&new).unwrap(), old);
        assert!(store.inspect(&new, 100).unwrap().is_none());
        assert_eq!(
            files::read(&old.join("evidence.json"), 16384).unwrap(),
            bytes
        );
    }

    #[test]
    fn user_acknowledgment_corruption_missing_evidence_and_hardlinks_fail_closed() {
        for mode in [0, 1, 2, 3] {
            let f = Fixture::new();
            let evidence = f.evidence();
            let store = f.store();
            store.acknowledge(&evidence, None, 100).unwrap();
            let directory = store.directory(&evidence).unwrap();
            match mode {
                0 => fs::write(directory.join("acknowledged.json"), b"{broken").unwrap(),
                1 => fs::remove_file(directory.join("evidence.json")).unwrap(),
                2 => fs::hard_link(
                    directory.join("evidence.json"),
                    directory.join("untrusted-link"),
                )
                .unwrap(),
                _ => {
                    let path = directory.join("acknowledged.json");
                    let mut value: serde_json::Value =
                        serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
                    value["decision"]["acknowledgedAt"] = serde_json::json!(1000);
                    fs::write(path, serde_json::to_vec(&value).unwrap()).unwrap();
                }
            }
            assert!(store.inspect(&evidence, 100).is_err());
            assert!(store.acknowledge(&evidence, None, 101).is_err());
            assert_eq!(fs::read(f.path()).unwrap(), evidence.bytes);
        }
    }

    #[test]
    fn user_acknowledgment_report_deletion_leaves_minimum_state_and_original_evidence() {
        use crate::recovery_reports::{Safety, Summary};
        let f = Fixture::new();
        let evidence = f.evidence();
        let store = f.store();
        let reports = crate::recovery_reports::Store::new(f.app.join("recovery-reports")).unwrap();
        let report = Summary {
            schema: 1,
            report_id: uuid::Uuid::new_v4().to_string(),
            incident_id: f.id.clone(),
            captured_at: 100,
            application_version: "CI".into(),
            device_name: "CI".into(),
            platform: "CI".into(),
            context: Some(evidence.context.clone()),
            validation: None,
            safety: Safety {
                observed_at: 99,
                trust: "unknown".into(),
                activity: "unknown".into(),
                package_health: "unknown".into(),
                activity_reason: "native_inspection_unavailable".into(),
                decision: "block_trust_unknown".into(),
            },
        };
        let outcome = store
            .with_report(&evidence, 100, || reports.save(&report))
            .unwrap();
        let decision = outcome.acknowledgment.unwrap();
        reports.delete(&outcome.report_id.unwrap()).unwrap();
        assert_eq!(store.inspect(&evidence, 100).unwrap(), Some(decision));
        assert_eq!(fs::read(f.path()).unwrap(), evidence.bytes);
    }

    #[test]
    fn user_acknowledgment_atomic_publication_never_overwrites_existing_record() {
        let f = Fixture::new();
        let evidence = f.evidence();
        let store = f.store();
        store.acknowledge(&evidence, None, 100).unwrap();
        let directory = store.directory(&evidence).unwrap();
        let destination = directory.join("acknowledged.json");
        let original = fs::read(&destination).unwrap();
        let temporary = directory.join("pending-test");
        files::write(&temporary, b"replacement").unwrap();
        assert!(rename_new(&temporary, &destination).is_err());
        assert_eq!(fs::read(&destination).unwrap(), original);
        assert_eq!(fs::read(&temporary).unwrap(), b"replacement");
    }

    #[cfg(unix)]
    #[test]
    fn user_acknowledgment_changed_during_report_capture_never_commits_a_decision() {
        let f = Fixture::new();
        let evidence = f.evidence();
        let store = f.store();
        let report = uuid::Uuid::new_v4().to_string();
        let outcome = store
            .with_report(&evidence, 100, || {
                let mut value: serde_json::Value = serde_json::from_slice(&evidence.bytes).unwrap();
                value["stage"] = serde_json::json!("system");
                fs::write(f.path(), serde_json::to_vec(&value).unwrap()).unwrap();
                Ok(report.clone())
            })
            .unwrap();
        assert_eq!(outcome.report_id, Some(report));
        assert!(outcome.acknowledgment.is_none());
        assert!(!f.app.join("recovery-state").exists());
    }

    #[cfg(windows)]
    #[test]
    fn user_acknowledgment_live_writer_prevents_source_capture() {
        use std::os::windows::fs::OpenOptionsExt;
        let f = Fixture::new();
        let _writer = fs::OpenOptions::new()
            .write(true)
            .share_mode(1)
            .open(f.path())
            .unwrap();
        assert!(recovery_context::read_evidence(&f.app, &f.id, 100).is_err());
        assert!(!f.app.join("recovery-state").exists());
    }
}
