//! Per-account journal lifecycle, not machine coordination or mutation authority.
use crate::{
    recovery_context::{self, Context},
    recovery_reports as files, recovery_user,
};
use sde_coordination::{inspection::RestartMarker, observations::RestartEvidence};
use serde::{Deserialize, Serialize};
use std::{
    fs,
    path::{Path, PathBuf},
};
type Result<T> = std::result::Result<T, String>;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum GateActivity {
    Active,
    Inactive,
    Unknown,
}
/// Strictly read-only: an absent or unreadable gate is unknown, never created.
pub fn inspect_gate(directory: &Path) -> GateActivity {
    let parent = directory.join("recovery-state");
    if files::existing_private_directory(&parent).is_err() {
        return GateActivity::Unknown;
    }
    let mut options = fs::OpenOptions::new();
    options.read(true).write(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC | libc::O_NONBLOCK);
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        options.custom_flags(0x00200000).share_mode(0);
    }
    let file = match options.open(parent.join("user-operation.gate")) {
        Ok(file) => file,
        Err(error) => {
            #[cfg(windows)]
            if matches!(error.raw_os_error(), Some(32 | 33)) {
                return GateActivity::Active;
            }
            let _ = error;
            return GateActivity::Unknown;
        }
    };
    let Ok(metadata) = file.metadata() else {
        return GateActivity::Unknown;
    };
    if !metadata.is_file() {
        return GateActivity::Unknown;
    }
    #[cfg(unix)]
    {
        use std::os::{fd::AsRawFd, unix::fs::MetadataExt};
        if metadata.nlink() != 1
            || metadata.uid() != unsafe { libc::geteuid() }
            || metadata.mode() & 0o077 != 0
        {
            return GateActivity::Unknown;
        }
        if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
            return if matches!(
                std::io::Error::last_os_error().raw_os_error(),
                Some(libc::EWOULDBLOCK)
            ) {
                GateActivity::Active
            } else {
                GateActivity::Unknown
            };
        }
    }
    #[cfg(windows)]
    {
        use std::os::windows::io::AsRawHandle;
        use windows_sys::Win32::Storage::FileSystem::*;
        let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
        if unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) } == 0
            || info.nNumberOfLinks != 1
            || info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT != 0
        {
            return GateActivity::Unknown;
        }
    }
    GateActivity::Inactive
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct SessionRecord {
    schema: u8,
    incident_id: String,
    started_at: u64,
    marker: RestartMarker,
}
fn session_path(directory: &Path, incident: &crate::recovery_context::UserIncident) -> PathBuf {
    directory
        .join("recovery-state")
        .join("user-sessions")
        .join(format!("{}.json", incident.id))
}
/// Called only while the per-account lock is held. Captures legacy context
/// without acknowledging, clearing, or claiming the old process lifetime ended.
pub fn prepare_incident_session(
    directory: &Path,
    evidence: &crate::recovery_context::Evidence,
) -> Result<()> {
    let Context::User { incident } = &evidence.context else {
        return Err("User evidence is required.".into());
    };
    prepare_session(directory, incident)
}
fn prepare_session(
    directory: &Path,
    incident: &crate::recovery_context::UserIncident,
) -> Result<()> {
    let path = session_path(directory, incident);
    if fs::symlink_metadata(&path).is_ok() {
        let old: SessionRecord = serde_json::from_slice(&files::read(&path, 4096)?)
            .map_err(|_| "User session evidence is invalid; keep it and review Recovery.")?;
        if old.schema != 1
            || old.incident_id != incident.id
            || old.started_at != incident.started_at
        {
            return Err("User session evidence does not match this incident.".into());
        }
        if old.marker.missing() {
            let marker = RestartMarker::capture();
            if !marker.missing() {
                let updated = SessionRecord { marker, ..old };
                let temporary = path.with_extension(format!("pending-{}", uuid::Uuid::new_v4()));
                files::write(
                    &temporary,
                    &serde_json::to_vec(&updated)
                        .map_err(|_| "Session evidence encoding failed.")?,
                )?;
                replace(&temporary, &path)
                    .map_err(|_| "Newly available session evidence could not be saved.")?;
                files::sync(path.parent().ok_or("Session storage is unavailable.")?)?;
            }
        }
        return Ok(());
    }
    files::private_directory(path.parent().ok_or("Session storage is unavailable.")?)?;
    let record = SessionRecord {
        schema: 1,
        incident_id: incident.id.clone(),
        started_at: incident.started_at,
        marker: RestartMarker::capture(),
    };
    files::write(
        &path,
        &serde_json::to_vec(&record).map_err(|_| "Session evidence encoding failed.")?,
    )?;
    files::sync(path.parent().ok_or("Session storage is unavailable.")?)
}
fn require_restart(
    directory: &Path,
    incident: &crate::recovery_context::UserIncident,
) -> Result<()> {
    if inspect_restart(directory, incident) != RestartEvidence::Confirmed {
        return Err("The earlier user process lifetime is still unknown. Restart normally, then Check Again. Restart does not acknowledge or repair the incident.".into());
    }
    Ok(())
}
/// Inspect only existing provenance; never capture/refresh a baseline here.
pub fn inspect_restart(
    directory: &Path,
    incident: &crate::recovery_context::UserIncident,
) -> RestartEvidence {
    read_restart(directory, incident).unwrap_or(RestartEvidence::Unavailable)
}
fn read_restart(
    directory: &Path,
    incident: &crate::recovery_context::UserIncident,
) -> Result<RestartEvidence> {
    let path = session_path(directory, incident);
    files::existing_private_directory(
        path.parent()
            .ok_or("User restart evidence is unavailable.")?,
    )?;
    let record: SessionRecord = serde_json::from_slice(&files::read(&path, 4096)?)
        .map_err(|_| "User restart evidence is unreadable; keep the evidence and Check Again.")?;
    if record.schema != 1
        || record.incident_id != incident.id
        || record.started_at != incident.started_at
    {
        return Err("User restart evidence does not match this incident.".into());
    }
    Ok(record.marker.restarted())
}

pub struct Lock {
    _file: fs::File,
}
impl Lock {
    pub fn acquire(app_data: &Path) -> Result<Self> {
        let directory = app_data.join("recovery-state");
        files::private_directory(&directory)?;
        let path = directory.join("user-operation.gate");
        let mut options = fs::OpenOptions::new();
        options.read(true).write(true).create(true).truncate(false);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options
                .mode(0o600)
                .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC | libc::O_NONBLOCK);
        }
        #[cfg(windows)]
        {
            use std::os::windows::fs::OpenOptionsExt;
            options.custom_flags(0x00200000).share_mode(0);
        }
        let file = options
            .open(path)
            .map_err(|_| "User-operation coordination is unavailable or in use.")?;
        let metadata = file
            .metadata()
            .map_err(|_| "User-operation coordination is unavailable.")?;
        if !metadata.is_file() {
            return Err("Unsafe user-operation coordination file.".into());
        }
        #[cfg(unix)]
        {
            use std::os::{fd::AsRawFd, unix::fs::MetadataExt};
            if metadata.nlink() != 1
                || metadata.uid() != unsafe { libc::geteuid() }
                || metadata.mode() & 0o077 != 0
            {
                return Err("Unsafe user-operation coordination permissions or links.".into());
            }
            if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
                return Err("Another SDE user operation or acknowledgment is running.".into());
            }
        }
        #[cfg(windows)]
        {
            use std::os::windows::io::AsRawHandle;
            use windows_sys::Win32::Storage::FileSystem::*;
            let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
            if unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) } == 0
                || info.nNumberOfLinks != 1
                || info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT != 0
            {
                return Err("Unsafe user-operation coordination links.".into());
            }
        }
        Ok(Self { _file: file })
    }
}

pub struct Active {
    directory: PathBuf,
    id: String,
    generation: String,
    bytes: Vec<u8>,
    _lock: Lock,
}
impl Active {
    pub fn begin(directory: PathBuf, id: &str, bytes: Vec<u8>, now: u64) -> Result<Self> {
        recovery_context::preserved_context(&bytes, id, now)?;
        let lock = Lock::acquire(&directory)?;
        if let Some(previous) = recovery_context::read_current_evidence(&directory, now)? {
            let Context::User { incident } = &previous.context else {
                unreachable!()
            };
            if incident.id == id {
                return Err("A new operation must have a fresh identifier.".into());
            }
            if recovery_user::Store::new(directory.clone())
                .inspect(&previous, now)?
                .is_none()
            {
                return Err("A previous user operation needs acknowledgment before another change. Open Recovery; its evidence has been retained.".into());
            }
            prepare_session(&directory, incident)?;
            require_restart(&directory, incident)?;
            // A matching separate decision implies verified preserved bytes.
            // No acknowledgment is minted merely to start a new journal.
        }
        let Context::User { incident } = recovery_context::preserved_context(&bytes, id, now)?
        else {
            unreachable!()
        };
        let marker = session_path(&directory, &incident);
        if fs::symlink_metadata(&marker).is_ok() {
            return Err("A new operation must not reuse existing session evidence.".into());
        }
        prepare_session(&directory, &incident)?;
        persist(&directory, &bytes)?;
        let evidence = recovery_context::read_evidence(&directory, id, now)?;
        if evidence.bytes != bytes {
            return Err("User journal publication could not be confirmed.".into());
        }
        let generation = evidence.generation.clone();
        drop(evidence);
        Ok(Self {
            directory,
            id: id.into(),
            generation,
            bytes,
            _lock: lock,
        })
    }
    fn current(&self, now: u64) -> Result<()> {
        let current = recovery_context::read_evidence(&self.directory, &self.id, now)?;
        if current.generation != self.generation || current.bytes != self.bytes {
            return Err("The user journal changed. Keep the evidence and review Recovery.".into());
        }
        Ok(())
    }
    pub fn stage(&mut self, bytes: Vec<u8>, now: u64) -> Result<()> {
        recovery_context::preserved_context(&bytes, &self.id, now)?;
        self.current(now)?;
        persist(&self.directory, &bytes)?;
        let evidence = recovery_context::read_evidence(&self.directory, &self.id, now)?;
        if evidence.bytes != bytes {
            return Err("User journal update could not be confirmed.".into());
        }
        self.generation = evidence.generation.clone();
        self.bytes = bytes;
        Ok(())
    }
    /// Only the caller's known-success branch may finish its own matching run.
    /// Failure, cancellation and Drop leave its current journal intact.
    pub fn finish_known(self, now: u64) -> Result<()> {
        self.current(now)?;
        fs::remove_file(self.directory.join("operation-journal.json"))
            .map_err(|_| "The completed user journal could not be retired.".to_string())?;
        files::sync(&self.directory)
    }
    /// Only the live caller's typed native no-start branch may use this. It
    /// cannot clear a retained prior incident or protected machine transaction.
    pub fn finish_not_started(self, now: u64) -> Result<()> {
        self.finish_known(now)
    }
}

fn persist(directory: &Path, bytes: &[u8]) -> Result<()> {
    let temporary = directory.join(format!("operation-pending-{}", uuid::Uuid::new_v4()));
    files::write(&temporary, bytes)?;
    replace(&temporary, &directory.join("operation-journal.json")).map_err(|_| {
        "User journal publication failed; existing evidence was retained.".to_string()
    })?;
    files::sync(directory)
}
#[cfg(unix)]
fn replace(source: &Path, destination: &Path) -> std::io::Result<()> {
    fs::rename(source, destination)
}
#[cfg(windows)]
fn replace(source: &Path, destination: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::{
        MoveFileExW, MOVEFILE_REPLACE_EXISTING, MOVEFILE_WRITE_THROUGH,
    };
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
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH,
        )
    } != 0
    {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Fixture {
        directory: PathBuf,
    }
    impl Fixture {
        fn new() -> Self {
            let directory =
                std::env::temp_dir().join(format!("sde-user-journal-ci-{}", uuid::Uuid::new_v4()));
            fs::create_dir(&directory).unwrap();
            Self { directory }
        }
        fn path(&self) -> PathBuf {
            self.directory.join("operation-journal.json")
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.directory).unwrap();
        }
    }
    fn record(id: &str, stage: &str) -> Vec<u8> {
        serde_json::to_vec(&serde_json::json!({"schema":1,"id":id,"operation":"update",
            "stage":stage,"startedAt":10,"observedAt":20,"logPath":null,"acknowledged":false}))
        .unwrap()
    }
    #[test]
    fn user_journal_drop_retains_source_and_unacknowledged_begin_never_overwrites_it() {
        let f = Fixture::new();
        let id = uuid::Uuid::new_v4().to_string();
        let bytes = record(&id, "starting");
        let active = Active::begin(f.directory.clone(), &id, bytes.clone(), 100).unwrap();
        assert!(Lock::acquire(&f.directory).is_err());
        drop(active);
        assert_eq!(fs::read(f.path()).unwrap(), bytes);
        let next = uuid::Uuid::new_v4().to_string();
        assert!(Active::begin(f.directory.clone(), &next, record(&next, "starting"), 100).is_err());
        assert_eq!(fs::read(f.path()).unwrap(), bytes);
        assert!(!f.directory.join("recovery-state").join(id).exists());
    }
    #[test]
    fn user_journal_acknowledged_transition_preserves_old_evidence_and_finishes_only_new_run() {
        let f = Fixture::new();
        let old = uuid::Uuid::new_v4().to_string();
        let original = record(&old, "profile");
        fs::write(f.path(), &original).unwrap();
        {
            let evidence = recovery_context::read_evidence(&f.directory, &old, 100).unwrap();
            recovery_user::Store::new(f.directory.clone())
                .acknowledge(&evidence, None, 100)
                .unwrap();
        }
        let before: Vec<_> = fs::read_dir(f.directory.join("recovery-state").join(&old))
            .unwrap()
            .map(|entry| entry.unwrap().path())
            .collect();
        let saved = before[0].join("evidence.json");
        let next = uuid::Uuid::new_v4().to_string();
        assert!(Active::begin(f.directory.clone(), &next, record(&next, "starting"), 101).is_err());
        // Simulated independent prior session, not an actual reboot test. Both
        // Windows components differ; no production bypass flag exists.
        let marker_path = f
            .directory
            .join("recovery-state/user-sessions")
            .join(format!("{old}.json"));
        let mut marker: serde_json::Value =
            serde_json::from_slice(&fs::read(&marker_path).unwrap()).unwrap();
        marker["marker"]["bootKey"] = if cfg!(windows) {
            serde_json::json!("windows-session-start:1:1:1:1")
        } else {
            serde_json::json!(format!("linux:{}", uuid::Uuid::new_v4()))
        };
        fs::write(marker_path, serde_json::to_vec(&marker).unwrap()).unwrap();
        let mut active =
            Active::begin(f.directory.clone(), &next, record(&next, "starting"), 101).unwrap();
        active.stage(record(&next, "validation"), 102).unwrap();
        active.finish_known(103).unwrap();
        assert!(!f.path().exists());
        assert_eq!(fs::read(saved).unwrap(), original);
        assert!(Lock::acquire(&f.directory).is_ok());
    }
    #[test]
    fn user_journal_changed_or_foreign_generation_cannot_be_updated_or_finished() {
        for finish in [false, true] {
            let f = Fixture::new();
            let id = uuid::Uuid::new_v4().to_string();
            let mut active =
                Active::begin(f.directory.clone(), &id, record(&id, "starting"), 100).unwrap();
            let replacement = record(&uuid::Uuid::new_v4().to_string(), "system");
            fs::write(f.path(), &replacement).unwrap();
            if finish {
                assert!(active.finish_known(101).is_err());
            } else {
                assert!(active.stage(record(&id, "profile"), 101).is_err());
                drop(active);
            }
            assert_eq!(fs::read(f.path()).unwrap(), replacement);
        }
    }
    #[test]
    fn user_journal_invalid_or_missing_preservation_blocks_transition_without_repair() {
        let f = Fixture::new();
        let id = uuid::Uuid::new_v4().to_string();
        fs::write(f.path(), b"malformed legacy evidence").unwrap();
        assert!(Active::begin(f.directory.clone(), &id, record(&id, "starting"), 100).is_err());
        assert_eq!(fs::read(f.path()).unwrap(), b"malformed legacy evidence");
        fs::write(f.path(), record(&id, "profile")).unwrap();
        let evidence = recovery_context::read_evidence(&f.directory, &id, 100).unwrap();
        recovery_user::Store::new(f.directory.clone())
            .acknowledge(&evidence, None, 100)
            .unwrap();
        drop(evidence);
        let state = f.directory.join("recovery-state").join(&id);
        let generation = fs::read_dir(state).unwrap().next().unwrap().unwrap().path();
        fs::write(generation.join("evidence.json"), b"damaged copy").unwrap();
        let next = uuid::Uuid::new_v4().to_string();
        assert!(Active::begin(f.directory.clone(), &next, record(&next, "starting"), 101).is_err());
        assert_eq!(fs::read(f.path()).unwrap(), record(&id, "profile"));
    }
    #[test]
    fn user_journal_missing_session_baseline_never_proves_restart_or_drops_acknowledgment() {
        let f = Fixture::new();
        let id = uuid::Uuid::new_v4().to_string();
        let active = Active::begin(f.directory.clone(), &id, record(&id, "starting"), 100).unwrap();
        drop(active);
        let evidence = recovery_context::read_evidence(&f.directory, &id, 100).unwrap();
        let Context::User { incident } = &evidence.context else {
            unreachable!()
        };
        recovery_user::Store::new(f.directory.clone())
            .acknowledge(&evidence, None, 100)
            .unwrap();
        let path = session_path(&f.directory, incident);
        let mut marker: serde_json::Value =
            serde_json::from_slice(&fs::read(&path).unwrap()).unwrap();
        marker["marker"]["bootKey"] = serde_json::Value::Null;
        fs::write(&path, serde_json::to_vec(&marker).unwrap()).unwrap();
        prepare_incident_session(&f.directory, &evidence).unwrap();
        assert!(require_restart(&f.directory, incident).is_err());
        assert!(recovery_user::Store::new(f.directory.clone())
            .inspect(&evidence, 100)
            .unwrap()
            .is_some());
        assert_eq!(fs::read(f.path()).unwrap(), evidence.bytes);
        let invalid: RestartMarker =
            serde_json::from_value(serde_json::json!({"schema":2,"bootKey":null})).unwrap();
        assert_eq!(invalid.restarted(), RestartEvidence::Unavailable);
    }
    #[test]
    fn user_journal_gate_rejects_hardlinks_without_modifying_the_target() {
        let f = Fixture::new();
        drop(Lock::acquire(&f.directory).unwrap());
        let gate = f.directory.join("recovery-state/user-operation.gate");
        let original = f.directory.join("recovery-state/original-gate");
        fs::rename(&gate, &original).unwrap();
        fs::hard_link(&original, &gate).unwrap();
        let before = fs::read(&original).unwrap();
        assert!(Lock::acquire(&f.directory).is_err());
        assert_eq!(fs::read(original).unwrap(), before);
    }
    #[test]
    fn user_journal_proven_non_start_retires_only_this_attempt_and_allows_explicit_retry() {
        let f = Fixture::new();
        let id = uuid::Uuid::new_v4().to_string();
        let protected_standin = f.directory.join("synthetic-prior-protected-evidence");
        fs::write(&protected_standin, b"not an actual machine root").unwrap();
        let active = Active::begin(f.directory.clone(), &id, record(&id, "starting"), 100).unwrap();
        active.finish_not_started(101).unwrap();
        assert!(!f.path().exists());
        assert_eq!(
            fs::read(&protected_standin).unwrap(),
            b"not an actual machine root"
        );
        let next = uuid::Uuid::new_v4().to_string();
        let active =
            Active::begin(f.directory.clone(), &next, record(&next, "starting"), 101).unwrap();
        fs::write(
            f.path(),
            record(&uuid::Uuid::new_v4().to_string(), "system"),
        )
        .unwrap();
        let replacement = fs::read(f.path()).unwrap();
        assert!(active.finish_not_started(102).is_err());
        assert_eq!(fs::read(f.path()).unwrap(), replacement);
    }
    #[test]
    fn recovery_account_observation_never_creates_absent_state_and_reports_held_gate() {
        let f = Fixture::new();
        assert_eq!(inspect_gate(&f.directory), GateActivity::Unknown);
        assert!(!f.directory.join("recovery-state").exists());
        let id = uuid::Uuid::new_v4().to_string();
        fs::write(f.path(), record(&id, "profile")).unwrap();
        let evidence = recovery_context::read_evidence(&f.directory, &id, 100).unwrap();
        let Context::User { incident } = &evidence.context else {
            unreachable!()
        };
        assert_eq!(
            inspect_restart(&f.directory, incident),
            RestartEvidence::Unavailable
        );
        assert!(!f.directory.join("recovery-state").exists());
        let held = Lock::acquire(&f.directory).unwrap();
        assert_eq!(inspect_gate(&f.directory), GateActivity::Active);
        drop(held);
        assert_eq!(inspect_gate(&f.directory), GateActivity::Inactive);
    }
    #[test]
    fn recovery_view_rejects_recreated_identical_user_evidence_before_any_acknowledgment() {
        let f = Fixture::new();
        let id = uuid::Uuid::new_v4().to_string();
        let bytes = record(&id, "profile");
        fs::write(f.path(), &bytes).unwrap();
        let views = crate::recovery_state::Views::default();
        let evidence = recovery_context::read_evidence(&f.directory, &id, 100).unwrap();
        let token = views.bind(&id, &evidence.generation).unwrap();
        drop(evidence);
        fs::rename(f.path(), f.directory.join("earlier-journal.json")).unwrap();
        fs::write(f.path(), &bytes).unwrap();
        let current = recovery_context::read_evidence(&f.directory, &id, 100).unwrap();
        assert!(views.verify(&token, &id, &current.generation).is_err());
        assert!(!f.directory.join("recovery-state").exists());
        assert_eq!(fs::read(f.path()).unwrap(), bytes);
    }
    #[test]
    fn user_journal_gate_probe() {
        let Some(directory) = std::env::var_os("SDE_TEST_USER_JOURNAL_DIR") else {
            return;
        };
        let result = Lock::acquire(Path::new(&directory));
        assert_eq!(
            result.is_ok(),
            std::env::var("SDE_TEST_USER_JOURNAL_AVAILABLE").as_deref() == Ok("1")
        );
    }
    #[test]
    fn user_journal_gate_excludes_an_independent_process_and_releases_after_close() {
        let f = Fixture::new();
        let held = Lock::acquire(&f.directory).unwrap();
        let output = std::process::Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "user_journal_store::tests::user_journal_gate_probe",
                "--nocapture",
            ])
            .env("SDE_TEST_USER_JOURNAL_DIR", &f.directory)
            .env("SDE_TEST_USER_JOURNAL_AVAILABLE", "0")
            .output()
            .unwrap();
        assert!(
            output.status.success() && String::from_utf8_lossy(&output.stdout).contains("1 passed"),
            "independent exclusion probe failed: {} {}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        drop(held);
        let output = std::process::Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "user_journal_store::tests::user_journal_gate_probe",
                "--nocapture",
            ])
            .env("SDE_TEST_USER_JOURNAL_DIR", &f.directory)
            .env("SDE_TEST_USER_JOURNAL_AVAILABLE", "1")
            .output()
            .unwrap();
        assert!(
            output.status.success() && String::from_utf8_lossy(&output.stdout).contains("1 passed"),
            "independent acquisition probe failed: {} {}",
            String::from_utf8_lossy(&output.stdout),
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(Lock::acquire(&f.directory).is_ok());
    }
}
