//! Fixed Linux app-only worker. No caller-selected command, package or URL.
//! Activation/registration is deliberately separate from this implementation.
use crate::{
    discovery::{self, GitHub},
    host, linux_install as native, Result,
};
use serde::{Deserialize, Serialize};
use std::{
    cell::RefCell,
    fs::File,
    io::Write,
    path::{Path, PathBuf},
    time::Duration,
};
const RUNS: &str = "/var/lib/skyview-robotics/self-update/app-only/runs";
const OVERALL_MS: u64 = 900_000;
const READY_MS: u64 = 120_000;
const FILES: [&str; 6] = [
    "/usr/local/libexec/skyview-app-update-request",
    "/usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy",
    "/usr/bin/skyview-dev-setup",
    "/usr/lib/Skyview Dev Setup/backend/linux/self-update/bootstrap.py",
    "/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust",
    "/usr/lib/Skyview Dev Setup/backend/linux/lib/coordination.py",
];
#[derive(Deserialize, Serialize, Clone)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Request {
    schema_version: u32,
    request_id: String,
    uid: u32,
    boot_id: String,
    created_ms: u64,
    deadline_ms: u64,
}
fn uuid(value: &str) -> bool {
    uuid::Uuid::parse_str(value).is_ok_and(|id| id.to_string() == value)
}
fn now() -> Result<(String, u64)> {
    let boot = std::fs::read_to_string("/proc/sys/kernel/random/boot_id")
        .map_err(|_| "Boot identity unavailable")?;
    let boot = boot.trim().to_string();
    let mut time = libc::timespec {
        tv_sec: 0,
        tv_nsec: 0,
    };
    if !uuid(&boot)
        || unsafe { libc::clock_gettime(libc::CLOCK_BOOTTIME, &mut time) } != 0
        || time.tv_sec < 0
        || !(0..1_000_000_000).contains(&time.tv_nsec)
    {
        return Err("Suspend-aware clock unavailable".into());
    }
    let ms = (time.tv_sec as u64)
        .checked_mul(1000)
        .and_then(|s| s.checked_add(time.tv_nsec as u64 / 1_000_000))
        .ok_or("Clock overflow")?;
    Ok((boot, ms))
}
impl Request {
    fn check(&self, boot: &str, ms: u64, ready: Option<u64>) -> Result<()> {
        if self.schema_version != 1
            || !uuid(&self.request_id)
            || self.uid == 0
            || self.uid == u32::MAX
            || !uuid(&self.boot_id)
            || self.created_ms.checked_add(OVERALL_MS) != Some(self.deadline_ms)
            || boot != self.boot_id
            || ms < self.created_ms
            || ms >= self.deadline_ms
            || ready.is_some_and(|start| {
                start < self.created_ms || ms < start || ms - start >= READY_MS
            })
        {
            return Err("Authorized request expired or invalid; authorize a new attempt".into());
        }
        Ok(())
    }
    fn remaining(&self, ready: u64) -> Result<Duration> {
        let (boot, ms) = now()?;
        self.check(&boot, ms, Some(ready))?;
        Ok(Duration::from_millis(
            self.deadline_ms.min(ready + READY_MS) - ms,
        ))
    }
    fn live(&self, ready: Option<u64>) -> Result<()> {
        let (boot, ms) = now()?;
        self.check(&boot, ms, ready)
    }
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Capabilities {
    schema_version: u32,
    native_validation: String,
    files: std::collections::BTreeMap<String, String>,
    validated_candidate_sha256: Vec<String>,
}
fn read<T: serde::de::DeserializeOwned>(path: &Path) -> Result<T> {
    native::trusted_file(path)?;
    serde_json::from_slice(&crate::read_bounded(path, 16_384)?)
        .map_err(|_| "Invalid protected app-only record".into())
}
fn valid_digest(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v))
}
fn capabilities(candidate: Option<&str>) -> Result<()> {
    // No bootstrap or package hook creates this enablement receipt. Native proof
    // must bind exact deployed files AND exact candidate package bytes first.
    let c: Capabilities = read(&Path::new(native::ROOT).join("app-only-capabilities.json"))?;
    if c.schema_version != 1
        || c.native_validation != "linux-app-only-v1"
        || c.files.len() < FILES.len()
        || c.files.len() > FILES.len() + 2
        || c.validated_candidate_sha256.len() > 8
        || c.validated_candidate_sha256.is_empty()
        || c.validated_candidate_sha256
            .iter()
            .any(|v| !valid_digest(v))
    {
        return Err("App-only native compatibility validation is required".into());
    }
    for path in FILES {
        native::trusted_file(Path::new(path))?;
        if c.files.get(path) != Some(&crate::hash_file(Path::new(path))?.1) {
            return Err(
                "App-only deployed capability changed; mentor prerequisite upgrade required".into(),
            );
        }
    }
    let mut expected = FILES.len();
    for path in [
        "/usr/local/sbin/skyview-student-dev-update",
        "/usr/local/lib/skyview-student-dev/coordination.py",
    ] {
        match std::fs::symlink_metadata(path) {
            Ok(_) => {
                expected += 1;
                native::trusted_file(Path::new(path))?;
                if c.files.get(path) != Some(&crate::hash_file(Path::new(path))?.1) {
                    return Err("External maintenance capability changed".into());
                }
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
            Err(_) => return Err("External maintenance capability unavailable".into()),
        }
    }
    if c.files.len() != expected {
        return Err("Unexpected capability file set".into());
    }
    if candidate.is_some_and(|digest| !c.validated_candidate_sha256.iter().any(|v| v == digest)) {
        return Err("Candidate package hooks have not passed app-only native validation".into());
    }
    Ok(())
}
/// Named-user POSIX ACL: root writes, only the requesting uid reads. The root
/// parent path must separately permit traversal. No shared-primary-group grant.
fn reader_acl(file: &File, uid: u32) -> Result<()> {
    let bytes = acl(uid);
    let name = c"system.posix_acl_access";
    if unsafe {
        libc::fsetxattr(
            std::os::fd::AsRawFd::as_raw_fd(file),
            name.as_ptr(),
            bytes.as_ptr().cast(),
            bytes.len(),
            0,
        )
    } != 0
    {
        return Err("Protected progress ACL unavailable".into());
    }
    Ok(())
}
fn acl(uid: u32) -> Vec<u8> {
    let mut bytes = 2u32.to_le_bytes().to_vec();
    for (tag, permission, id) in [
        (1u16, 6u16, u32::MAX),
        (2, 4, uid),
        (4, 0, u32::MAX),
        (16, 4, u32::MAX),
        (32, 0, u32::MAX),
    ] {
        bytes.extend(tag.to_le_bytes());
        bytes.extend(permission.to_le_bytes());
        bytes.extend(id.to_le_bytes());
    }
    bytes
}
#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
enum State {
    Preparing,
    Downloading,
    Verifying,
    Ready,
    Committing,
    Installing,
    Postchecking,
    Current,
    Paused,
    Deferred,
    Updated,
    RecoveryRequired,
}
#[derive(Clone, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct CandidateProgress {
    version: String,
    sha256: String,
}
impl CandidateProgress {
    fn valid(&self) -> bool {
        crate::release_version(&format!("v{}", self.version)).is_ok() && valid_digest(&self.sha256)
    }
}
#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Progress {
    schema_version: u32,
    request_id: String,
    uid: u32,
    boot_id: String,
    sequence: u32,
    observed_ms: u64,
    deadline_ms: u64,
    ready_deadline_ms: Option<u64>,
    state: State,
    candidate: Option<CandidateProgress>,
    native_exit: Option<i32>,
    detail: Option<String>,
}
struct Publisher {
    request: Request,
    directory: PathBuf,
    sequence: u32,
    ready: Option<u64>,
    candidate: Option<CandidateProgress>,
    native_exit: Option<i32>,
    detail: Option<String>,
}
impl Publisher {
    fn publish(&mut self, state: State) -> Result<()> {
        let (_, observed_ms) = now()?;
        self.sequence = self
            .sequence
            .checked_add(1)
            .filter(|v| *v <= 32)
            .ok_or("Progress publication bound exceeded")?;
        let progress = Progress {
            schema_version: 1,
            request_id: self.request.request_id.clone(),
            uid: self.request.uid,
            boot_id: self.request.boot_id.clone(),
            sequence: self.sequence,
            observed_ms,
            deadline_ms: self.request.deadline_ms,
            ready_deadline_ms: self
                .ready
                .map(|v| (v + READY_MS).min(self.request.deadline_ms)),
            state,
            candidate: self.candidate.clone(),
            native_exit: self.native_exit,
            detail: self.detail.clone(),
        };
        let bytes = serde_json::to_vec(&progress).map_err(|_| "Progress encoding failed")?;
        if bytes.len() > 4096 {
            return Err("Progress bound exceeded".into());
        }
        let temp = self.directory.join(format!("{}.tmp", uuid::Uuid::new_v4()));
        let result = (|| {
            let mut file = host::exclusive(&temp).map_err(|_| "Progress creation failed")?;
            reader_acl(&file, self.request.uid)?;
            file.write_all(&bytes)
                .and_then(|_| file.sync_all())
                .map_err(|_| "Progress persistence failed")?;
            std::fs::rename(&temp, self.directory.join("progress.json"))
                .map_err(|_| "Progress activation failed")?;
            File::open(&self.directory)
                .and_then(|f| f.sync_all())
                .map_err(|_| "Progress directory flush failed")?;
            Ok(())
        })();
        if result.is_err() {
            let _ = std::fs::remove_file(&temp);
        }
        result
    }
}
/// Read-only fixed-location observation; freshness is observation, never authority.
pub fn app_only_progress(id: &str) -> Result<String> {
    if !uuid(id) {
        return Err("Invalid request correlation".into());
    }
    let path = Path::new(RUNS).join(id).join("progress.json");
    let p: Progress = read(&path)?;
    let (boot, ms) = now()?;
    if p.schema_version != 1
        || p.request_id != id
        || p.uid != unsafe { libc::getuid() }
        || p.boot_id != boot
        || p.sequence == 0
        || p.sequence > 32
        || p.detail.as_ref().is_some_and(|v| v.len() > 512)
        || p.candidate.as_ref().is_some_and(|c| !c.valid())
        || p.observed_ms > ms
        || p.ready_deadline_ms.is_some_and(|d| d > p.deadline_ms)
    {
        return Err("Progress identity or clock mismatch".into());
    }
    // Age and reboot are not interpreted as process completion or a close grant.
    serde_json::to_string(&p).map_err(|_| "Progress encoding failed".into())
}
fn worker_directory(exe: &Path) -> Result<PathBuf> {
    native::trusted_file(exe)?;
    let dir = exe.parent().ok_or("Missing worker snapshot")?;
    if exe.file_name().is_none_or(|v| v != "sde-update-trust")
        || dir.parent() != Some(Path::new(RUNS))
        || !dir.file_name().and_then(|v| v.to_str()).is_some_and(uuid)
    {
        return Err("App-only worker must run from a protected request snapshot".into());
    }
    Ok(dir.into())
}
fn interrupted() -> bool {
    ["transaction.json", "installation-scope.json"]
        .iter()
        .any(
            |name| match std::fs::symlink_metadata(sde_coordination::root().join(name)) {
                Ok(_) => true,
                Err(e) => e.kind() != std::io::ErrorKind::NotFound,
            },
        )
}
pub fn app_only_linux() -> Result<()> {
    if unsafe { libc::geteuid() } != 0 {
        return Err("Authorized root worker required".into());
    }
    let directory =
        worker_directory(&std::env::current_exe().map_err(|_| "Missing worker identity")?)?;
    let request: Request = read(&directory.join("request.json"))?;
    if directory.file_name().and_then(|s| s.to_str()) != Some(&request.request_id) {
        return Err("Request identity mismatch".into());
    }
    request.live(None)?;
    // Exclusive one-shot claim is deliberately never removed or replayed.
    let mut claim = host::exclusive(&directory.join("claimed"))
        .map_err(|_| "Request already claimed or unavailable")?;
    claim.write_all(&serde_json::to_vec(&serde_json::json!({"schemaVersion":1,"requestId":request.request_id,"workerPid":std::process::id(),"bootId":request.boot_id})).map_err(|_| "Claim encoding failed")?).map_err(|_| "Claim write failed")?;
    claim
        .sync_all()
        .and_then(|_| File::open(&directory)?.sync_all())
        .map_err(|_| "Request claim persistence failed")?;
    let publisher = RefCell::new(Publisher {
        request: request.clone(),
        directory: directory.clone(),
        sequence: 0,
        ready: None,
        candidate: None,
        native_exit: None,
        detail: None,
    });
    let mut committed = false;
    let mut installation_returned = false;
    let result = (|| {
        capabilities(None)?;
        // Snapshot must be the exact deployed trusted worker covered by capability.
        if crate::hash_file(&directory.join("sde-update-trust"))?
            != crate::hash_file(Path::new(FILES[4]))?
        {
            return Err("Worker snapshot capability mismatch".into());
        }
        let preparation = sde_coordination::prepare_app_only().map_err(|e| e.to_string())?;
        publisher.borrow_mut().publish(State::Preparing)?;
        if native::paused()? {
            publisher.borrow_mut().publish(State::Paused)?;
            return Ok(());
        }
        #[derive(Deserialize)]
        #[serde(rename_all = "camelCase", deny_unknown_fields)]
        struct Engine {
            schema_version: u32,
            version: String,
        }
        let engine: Engine = read(&directory.join("version.json"))?;
        if engine.schema_version != 1
            || crate::release_version(&format!("v{}", engine.version)).is_err()
        {
            return Err("Invalid worker engine receipt".into());
        }
        let installed = host::installed().map_err(|_| "Unsupported installed application")?;
        let mut github = GitHub::new().map_err(|_| "Release discovery unavailable")?;
        let root = host::store().map_err(|_| "Protected staging unavailable")?;
        // Recovery is a hard manual gate. Never install without authenticated recovery.
        if !native::recovery(&mut github, &root, &installed.version)? {
            return Err("Signed recovery unavailable; mentor prerequisite repair required".into());
        }
        request.live(None)?;
        let Some(candidate) =
            discovery::discover_with(&mut github, &installed.version, "linux-amd64")
                .map_err(|_| "Eligible release unavailable")?
        else {
            publisher.borrow_mut().publish(State::Current)?;
            return Ok(());
        };
        publisher.borrow_mut().publish(State::Downloading)?;
        let staged = root.join(native::stage(&mut github, &root, &candidate)?);
        request.live(None)?;
        publisher.borrow_mut().publish(State::Verifying)?;
        let digest = crate::hash_file(&staged.join(native::INSTALLER))?.1;
        publisher.borrow_mut().candidate = Some(CandidateProgress {
            version: candidate.version.clone(),
            sha256: digest.clone(),
        });
        capabilities(Some(&digest))?;
        let current = host::installed().map_err(|_| "Installed identity unavailable")?;
        if current.version != installed.version {
            return Err("Installed identity changed".into());
        }
        let eligible = discovery::discover_with(&mut github, &current.version, "linux-amd64")
            .map_err(|_| "Eligibility recheck unavailable")?;
        if eligible
            .as_ref()
            .map(|c| (&c.tag, &c.version, c.installer_size))
            != Some((&candidate.tag, &candidate.version, candidate.installer_size))
        {
            return Err("Release eligibility changed".into());
        }
        request.live(None)?;
        // Sample before the nonblocking closure so latency cannot extend consent.
        let ready = now()?.1;
        let mut admission = preparation.close_admission().map_err(|e| e.to_string())?;
        request.live(Some(ready))?;
        publisher.borrow_mut().ready = Some(ready);
        publisher.borrow_mut().publish(State::Ready)?;
        let lease = loop {
            request.live(Some(ready))?;
            match admission.try_installation() {
                Ok(lease) => break lease,
                Err((sde_coordination::Error::Busy, retained)) => {
                    admission = retained;
                    std::thread::sleep(Duration::from_millis(50));
                }
                Err((error, _retained)) => return Err(error.to_string()),
            }
        };
        let mut report = native::Report {
            schema_version: 1,
            phase: crate::observation::Phase::Verification,
            completed_at: None,
            checked_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map_err(|_| "Wall clock unavailable")?
                .as_secs(),
            application_version: current.version,
            maintenance_engine_version: engine.version,
            applied_baseline_version: None,
            tool_exit: None,
            outcome: "failed".into(),
            detail: String::new(),
            candidate_version: Some(candidate.version.clone()),
            native_exit: None,
            recovery_available: true,
            log_reference: None,
        };
        // This guard runs AFTER authentication/native preflight and final pause,
        // immediately before durable intent. No network or GUI operation follows it.
        capabilities(Some(&digest))?;
        publisher.borrow_mut().publish(State::Committing)?;
        let guard = || request.remaining(ready);
        let observe = |phase| {
            let state = match phase {
                crate::observation::Phase::Installer => Some(State::Installing),
                crate::observation::Phase::Postcheck => Some(State::Postchecking),
                _ => None,
            };
            // Once intent may exist, reporting never aborts native supervision.
            if let Some(state) = state {
                let _ = publisher.borrow_mut().publish(state);
            }
        };
        let installed =
            native::install_app_only(&lease, &staged, &candidate, &mut report, &guard, &observe);
        publisher.borrow_mut().native_exit = report.native_exit;
        committed = interrupted();
        installed?;
        installation_returned = true;
        publisher
            .borrow_mut()
            .publish(match report.outcome.as_str() {
                "updated" => State::Updated,
                "current" => State::Current,
                "paused" => State::Paused,
                _ => State::Deferred,
            })?;
        Ok(())
    })();
    if let Err(ref error) = result {
        publisher.borrow_mut().detail = Some(if error.len() <= 512 {
            error.clone()
        } else {
            "Update attempt failed; mentor review required".into()
        });
    }
    if result.is_err() && !installation_returned {
        // No recovery state is ever cleared here. Reporting failure cannot change
        // installation authority. Any uncertain intent remains a startup barrier.
        let _ = publisher
            .borrow_mut()
            .publish(if committed || interrupted() {
                State::RecoveryRequired
            } else {
                State::Deferred
            });
    }
    result
}
#[cfg(test)]
mod tests {
    use super::*;
    fn request() -> Request {
        Request {
            schema_version: 1,
            request_id: uuid::Uuid::new_v4().to_string(),
            uid: 1000,
            boot_id: uuid::Uuid::new_v4().to_string(),
            created_ms: 10_000,
            deadline_ms: 910_000,
        }
    }
    #[test]
    fn deadlines_are_exclusive_and_suspend_counts() {
        let r = request();
        assert!(r.check(&r.boot_id, 10_000, None).is_ok());
        assert!(r.check(&r.boot_id, 909_999, None).is_ok());
        assert!(r.check(&r.boot_id, 910_000, None).is_err());
        assert!(r.check(&r.boot_id, 129_999, Some(10_000)).is_ok());
        assert!(r.check(&r.boot_id, 130_000, Some(10_000)).is_err());
        assert!(r.check(&r.boot_id, 909_999, Some(900_000)).is_ok());
        assert!(r.check(&r.boot_id, 910_000, Some(900_000)).is_err());
        assert!(r.check("different-boot", 20_000, None).is_err());
        assert!(r.check(&r.boot_id, 9999, None).is_err());
        assert!(r.check(&r.boot_id, 20_000, Some(20_001)).is_err());
    }
    #[test]
    fn invalid_requests_cannot_extend_authorization() {
        for mutate in [
            |r: &mut Request| r.deadline_ms += 1,
            |r: &mut Request| r.uid = 0,
            |r: &mut Request| r.uid = u32::MAX,
            |r: &mut Request| r.schema_version = 2,
            |r: &mut Request| r.created_ms = u64::MAX,
        ] {
            let mut r = request();
            mutate(&mut r);
            assert!(r.check(&r.boot_id, 20_000, None).is_err());
        }
    }
    #[test]
    fn acl_is_bounded_named_user_read_only() {
        let a = acl(1001);
        assert_eq!(a.len(), 44);
        assert_eq!(&a[12..20], &[2, 0, 4, 0, 233, 3, 0, 0]);
        assert_eq!(&a[36..44], &[32, 0, 0, 0, 255, 255, 255, 255]);
    }
    #[test]
    #[ignore = "Requires POSIX ACL filesystem; separately selected native gate, no package operations"]
    fn named_reader_acl_roundtrips_on_an_unprivileged_owned_file() {
        use std::os::{fd::AsRawFd, unix::fs::OpenOptionsExt};
        let path = std::env::temp_dir().join(format!("sde-acl-local-{}", uuid::Uuid::new_v4()));
        let file = std::fs::OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .mode(0o600)
            .open(&path)
            .unwrap();
        let uid = unsafe { libc::getuid() };
        let result = reader_acl(&file, uid);
        let mut bytes = vec![0u8; 128];
        let length = unsafe {
            libc::fgetxattr(
                file.as_raw_fd(),
                c"system.posix_acl_access".as_ptr(),
                bytes.as_mut_ptr().cast(),
                bytes.len(),
            )
        };
        std::fs::remove_file(&path).unwrap();
        result.expect("local filesystem must support the proposed progress ACL");
        assert_eq!(length, 44);
        assert_eq!(&bytes[..44], &acl(uid));
        // Owned scratch-file syscall only; not root ownership or cross-user proof.
    }
    #[test]
    fn exhausted_progress_budget_stops_before_filesystem_mutation() {
        let mut p = Publisher {
            request: request(),
            directory: PathBuf::from("/nonexistent/sde-progress-test"),
            sequence: 32,
            ready: None,
            candidate: None,
            native_exit: None,
            detail: None,
        };
        assert_eq!(
            p.publish(State::Ready).unwrap_err(),
            "Progress publication bound exceeded"
        );
        assert_eq!(p.sequence, 32);
    }
    #[test]
    fn progress_rejects_unknown_fields_and_states() {
        assert!(serde_json::from_str::<Progress>(r#"{"state":"cancel"}"#).is_err());
        assert!(app_only_progress("../../policy.json").is_err());
    }
}
