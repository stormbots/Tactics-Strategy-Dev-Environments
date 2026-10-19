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
const READY_REPORT_MS: u64 = 5_000;
fn ready_report_due(last: u64, ms: u64) -> bool {
    ms.checked_sub(last)
        .is_some_and(|elapsed| elapsed >= READY_REPORT_MS)
}
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
pub(crate) fn now() -> Result<(String, u64)> {
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
fn validate_capability_record(
    c: &Capabilities,
    candidate: Option<&str>,
    external: &[&str],
    mut hash: impl FnMut(&str) -> Result<String>,
) -> Result<()> {
    if c.schema_version != 1
        || c.native_validation != "linux-app-only-v1"
        || c.files.len() != FILES.len() + external.len()
        || c.validated_candidate_sha256.len() > 8
        || c.validated_candidate_sha256.is_empty()
        || c.validated_candidate_sha256
            .iter()
            .any(|v| !valid_digest(v))
    {
        return Err("App-only native compatibility validation is required".into());
    }
    // Compare the complete deployed set; a matching count cannot hide substitutions.
    for path in FILES.into_iter().chain(external.iter().copied()) {
        if c.files.get(path) != Some(&hash(path)?) {
            return Err(
                "App-only deployed capability changed; mentor prerequisite upgrade required".into(),
            );
        }
    }
    if candidate.is_some_and(|digest| !c.validated_candidate_sha256.iter().any(|v| v == digest)) {
        return Err("Candidate package hooks have not passed app-only native validation".into());
    }
    Ok(())
}
fn capabilities(candidate: Option<&str>) -> Result<()> {
    // No bootstrap or package hook creates this enablement receipt. Native proof
    // must bind exact deployed files AND exact candidate package bytes first.
    let c: Capabilities = read(&Path::new(native::ROOT).join("app-only-capabilities.json"))?;
    let mut external = Vec::new();
    for path in [
        "/usr/local/sbin/skyview-student-dev-update",
        "/usr/local/lib/skyview-student-dev/coordination.py",
    ] {
        match std::fs::symlink_metadata(path) {
            Ok(_) => external.push(path),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
            Err(_) => return Err("External maintenance capability unavailable".into()),
        }
    }
    validate_capability_record(&c, candidate, &external, |path| {
        native::trusted_file(Path::new(path))?;
        Ok(crate::hash_file(Path::new(path))?.1)
    })
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
    validate_progress(&p, id, unsafe { libc::getuid() }, &boot, ms)?;
    // Age and reboot are not interpreted as process completion or a close grant.
    serde_json::to_string(&p).map_err(|_| "Progress encoding failed".into())
}
fn validate_progress(p: &Progress, id: &str, uid: u32, boot: &str, ms: u64) -> Result<()> {
    if p.schema_version != 1
        || p.request_id != id
        || p.uid != uid
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
    Ok(())
}
/// Bounded presentation projection. This is observation, never worker liveness,
/// an installation grant, a recovery clearance or permission to close the GUI.
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ProgressObservation {
    request_id: String,
    boot_id: String,
    sequence: u32,
    state: State,
    observed_ms: u64,
    age_ms: u64,
    remaining_ms: u64,
    fresh: bool,
    candidate_version: Option<String>,
    candidate_sha256: Option<String>,
    close_allowed: bool,
}
fn project_progress(
    p: Progress,
    id: &str,
    uid: u32,
    boot: &str,
    ms: u64,
) -> Result<ProgressObservation> {
    validate_progress(&p, id, uid, boot, ms)?;
    if p.state == State::Ready && (p.candidate.is_none() || p.ready_deadline_ms.is_none()) {
        return Err("Incomplete readiness observation".into());
    }
    let precommit = matches!(
        p.state,
        State::Preparing | State::Downloading | State::Verifying | State::Ready
    );
    let age_ms = ms - p.observed_ms;
    let remaining_ms = p
        .ready_deadline_ms
        .unwrap_or(p.deadline_ms)
        .min(p.deadline_ms)
        .saturating_sub(ms);
    if remaining_ms > OVERALL_MS
        || p.observed_ms > 9_007_199_254_740_991
        || age_ms > 9_007_199_254_740_991
    {
        return Err("Progress presentation bounds exceeded".into());
    }
    Ok(ProgressObservation {
        request_id: p.request_id,
        boot_id: p.boot_id,
        sequence: p.sequence,
        state: p.state,
        observed_ms: p.observed_ms,
        age_ms,
        remaining_ms,
        fresh: age_ms <= 10_000 && (!precommit || remaining_ms > 0),
        candidate_version: p.candidate.as_ref().map(|c| c.version.clone()),
        candidate_sha256: p.candidate.map(|c| c.sha256),
        close_allowed: false,
    })
}
pub fn app_only_observation(id: &str) -> Result<ProgressObservation> {
    if !uuid(id) {
        return Err("Invalid request correlation".into());
    }
    let p: Progress = read(&Path::new(RUNS).join(id).join("progress.json"))?;
    let (boot, ms) = now()?;
    project_progress(p, id, unsafe { libc::getuid() }, &boot, ms)
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct ReceiptIndex {
    schema_version: u32,
    request_id: String,
    uid: u32,
    boot_id: String,
}
#[derive(Debug, Clone, Copy, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
enum ReceiptStatus {
    Pending,
    Accepted,
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct StoredReceipt {
    schema_version: u32,
    request_id: String,
    uid: u32,
    boot_id: String,
    created_ms: u64,
    deadline_ms: u64,
    status: ReceiptStatus,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ReceiptObservation {
    schema_version: u32,
    request_id: String,
    boot_id: String,
    created_ms: u64,
    deadline_ms: u64,
    status: ReceiptStatus,
    expired: bool,
}
fn receipt_view(
    p: StoredReceipt,
    id: &str,
    uid: u32,
    boot: &str,
    ms: u64,
) -> Result<ReceiptObservation> {
    if p.schema_version != 1
        || !uuid(id)
        || p.request_id != id
        || p.uid != uid
        || uid == 0
        || uid == u32::MAX
        || !uuid(boot)
        || p.boot_id != boot
        || p.created_ms > ms
        || p.created_ms.checked_add(OVERALL_MS) != Some(p.deadline_ms)
        || p.deadline_ms > 9_007_199_254_740_991
    {
        return Err("Protected request receipt identity or clock mismatch".into());
    }
    Ok(ReceiptObservation {
        schema_version: 1,
        request_id: p.request_id,
        boot_id: p.boot_id,
        created_ms: p.created_ms,
        deadline_ms: p.deadline_ms,
        status: p.status,
        expired: ms >= p.deadline_ms,
    })
}
/// Fixed real-UID lookup, never a URL/local-storage supplied receipt. Missing
/// namespaces are distinct from untrusted/inaccessible ones. No intent is cleared.
pub fn app_only_current_receipt() -> Result<Option<ReceiptObservation>> {
    let uid = unsafe { libc::getuid() };
    let index_path = Path::new(RUNS)
        .parent()
        .ok_or("Missing app-only namespace")?
        .join(format!("current-{uid}.json"));
    for path in index_path.ancestors() {
        match std::fs::symlink_metadata(path) {
            Ok(_) => native::trusted(path)?,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
            Err(_) => return Err("Protected request lookup unavailable".into()),
        }
    }
    match std::fs::symlink_metadata(&index_path) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err("Protected request lookup unavailable".into()),
        Ok(_) => (),
    }
    let index: ReceiptIndex = read(&index_path)?;
    let (boot, ms) = now()?;
    if index.schema_version != 1
        || index.uid != uid
        || index.boot_id != boot
        || !uuid(&index.request_id)
    {
        return Err("Protected request index identity mismatch".into());
    }
    let receipt: StoredReceipt =
        read(&Path::new(RUNS).join(&index.request_id).join("receipt.json"))?;
    receipt_view(receipt, &index.request_id, uid, &boot, ms).map(Some)
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct BrokerReply {
    schema_version: u32,
    request_id: String,
}
fn confirm_reply(
    bytes: &[u8],
    lookup: impl FnOnce() -> Result<Option<ReceiptObservation>>,
) -> Result<ReceiptObservation> {
    if bytes.len() > 1024 {
        return Err("Broker reply bound exceeded".into());
    }
    let reply: BrokerReply =
        serde_json::from_slice(bytes).map_err(|_| "Unconfirmed broker reply")?;
    if reply.schema_version != 1 || !uuid(&reply.request_id) {
        return Err("Unconfirmed broker correlation".into());
    }
    let receipt = lookup()?.ok_or("Protected request receipt missing")?;
    if receipt.request_id != reply.request_id || receipt.status != ReceiptStatus::Accepted {
        return Err("Broker reply has no matching accepted protected receipt".into());
    }
    Ok(receipt)
}
pub fn app_only_confirm_request(bytes: &[u8]) -> Result<ReceiptObservation> {
    confirm_reply(bytes, app_only_current_receipt)
}
/// Read-only compatibility guard, not enablement or installation authority.
pub fn app_only_prerequisites() -> Result<()> {
    capabilities(None)?;
    if interrupted() {
        return Err("Recovery review required before a new request".into());
    }
    Ok(())
}
fn validate_close(
    receipt: &ReceiptObservation,
    p: &Progress,
    id: &str,
    uid: u32,
    boot: &str,
    ms: u64,
) -> Result<()> {
    validate_progress(p, id, uid, boot, ms)?;
    if receipt.request_id != id
        || receipt.boot_id != boot
        || receipt.status != ReceiptStatus::Accepted
        || receipt.expired
        || ms < receipt.created_ms
        || ms >= receipt.deadline_ms
        || p.deadline_ms != receipt.deadline_ms
        || p.observed_ms < receipt.created_ms
        || p.state != State::Ready
        || ms - p.observed_ms > 10_000
        || p.candidate.is_none()
        || p.native_exit.is_some()
        || p.ready_deadline_ms
            .is_none_or(|d| d <= ms || d > p.observed_ms.saturating_add(READY_MS))
    {
        return Err("Protected readiness changed; keep SDE open and inspect status".into());
    }
    Ok(())
}
/// A fresh independent read before voluntarily closing this GUI. This is not a
/// close grant, worker liveness proof or permission for a package operation.
/// The root worker still owns and rechecks every lock/policy/intent boundary.
pub fn app_only_check_close(id: &str) -> Result<()> {
    if !uuid(id) {
        return Err("Invalid request correlation".into());
    }
    let receipt = app_only_current_receipt()?.ok_or("Protected request receipt missing")?;
    let p: Progress = read(&Path::new(RUNS).join(id).join("progress.json"))?;
    let (boot, ms) = now()?;
    validate_close(&receipt, &p, id, unsafe { libc::getuid() }, &boot, ms)?;
    if interrupted() {
        return Err("Recovery review required before closing".into());
    }
    capabilities(p.candidate.as_ref().map(|c| c.sha256.as_str()))?;
    // Hashing deployment files can take time. Re-read at the last boundary;
    // still not atomic with the worker, which alone decides whether to install.
    let current = app_only_current_receipt()?.ok_or("Protected request receipt missing")?;
    let latest: Progress = read(&Path::new(RUNS).join(id).join("progress.json"))?;
    if latest.candidate.as_ref().map(|c| (&c.version, &c.sha256))
        != p.candidate.as_ref().map(|c| (&c.version, &c.sha256))
    {
        return Err("Protected candidate changed before close".into());
    }
    let (boot, ms) = now()?;
    validate_close(&current, &latest, id, unsafe { libc::getuid() }, &boot, ms)?;
    if interrupted() {
        return Err("Recovery review required before closing".into());
    }
    Ok(())
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
        let mut last_ready_report = ready;
        let lease = loop {
            request.live(Some(ready))?;
            let ms = now()?.1;
            if ready_report_due(last_ready_report, ms) {
                publisher.borrow_mut().publish(State::Ready)?;
                last_ready_report = ms;
            }
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
    fn stored_receipt() -> StoredReceipt {
        let r = request();
        StoredReceipt {
            schema_version: 1,
            request_id: r.request_id,
            uid: r.uid,
            boot_id: r.boot_id,
            created_ms: r.created_ms,
            deadline_ms: r.deadline_ms,
            status: ReceiptStatus::Accepted,
        }
    }
    #[test]
    fn receipt_is_observation_not_liveness_and_expiry_does_not_clear_it() {
        let r = stored_receipt();
        let id = r.request_id.clone();
        let boot = r.boot_id.clone();
        assert!(receipt_view(r, &id, 1000, &boot, 910_000).unwrap().expired);
        for case in 0..5 {
            let mut r = stored_receipt();
            let id = r.request_id.clone();
            let boot = r.boot_id.clone();
            match case {
                0 => r.uid = 1001,
                1 => r.boot_id = uuid::Uuid::new_v4().to_string(),
                2 => r.deadline_ms += 1,
                3 => r.created_ms = 30_000,
                _ => r.schema_version = 2,
            }
            assert!(receipt_view(r, &id, 1000, &boot, 20_000).is_err());
        }
    }
    #[test]
    fn stdout_is_never_sufficient_without_matching_protected_accepted_receipt() {
        let r = stored_receipt();
        let id = r.request_id.clone();
        let boot = r.boot_id.clone();
        let reply =
            serde_json::to_vec(&serde_json::json!({"schemaVersion":1,"requestId":id})).unwrap();
        let view = receipt_view(r, &id, 1000, &boot, 20_000).unwrap();
        assert!(confirm_reply(&reply, || Ok(Some(view))).is_ok());
        assert!(confirm_reply(&reply, || Ok(None)).is_err());
        let r = stored_receipt();
        let id2 = r.request_id.clone();
        let boot2 = r.boot_id.clone();
        assert!(
            confirm_reply(&reply, || receipt_view(r, &id2, 1000, &boot2, 20_000)
                .map(Some))
            .is_err()
        );
        for bytes in [b"{}".as_slice(), b"{\"schemaVersion\":true}", b"not json"] {
            assert!(confirm_reply(bytes, || panic!(
                "malformed reply must not query protected namespace"
            ))
            .is_err());
        }
    }
    fn observation_fixture() -> Progress {
        let r = request();
        Progress {
            schema_version: 1,
            request_id: r.request_id,
            uid: r.uid,
            boot_id: r.boot_id,
            sequence: 4,
            observed_ms: 20_000,
            deadline_ms: r.deadline_ms,
            ready_deadline_ms: Some(140_000),
            state: State::Ready,
            candidate: Some(CandidateProgress {
                version: "1.2.2".into(),
                sha256: "a".repeat(64),
            }),
            native_exit: None,
            detail: Some("not exported".into()),
        }
    }
    #[test]
    fn compatibility_requires_exact_deployment_and_candidate_without_creating_markers() {
        fn fixture() -> Capabilities {
            Capabilities {
                schema_version: 1,
                native_validation: "linux-app-only-v1".into(),
                files: FILES
                    .iter()
                    .map(|p| (p.to_string(), "a".repeat(64)))
                    .collect(),
                validated_candidate_sha256: vec!["b".repeat(64)],
            }
        }
        let good = fixture();
        assert!(
            validate_capability_record(&good, Some(&"b".repeat(64)), &[], |_| Ok("a".repeat(64)))
                .is_ok()
        );
        assert!(
            validate_capability_record(&good, Some(&"c".repeat(64)), &[], |_| Ok("a".repeat(64)))
                .is_err()
        );
        for case in 0..7 {
            let mut c = fixture();
            match case {
                0 => c.schema_version = 2,
                1 => c.native_validation = "pending".into(),
                2 => c.validated_candidate_sha256.clear(),
                3 => c.validated_candidate_sha256 = vec!["bad".into()],
                4 => {
                    c.files.remove(FILES[0]);
                    c.files.insert("/tmp/substitution".into(), "a".repeat(64));
                }
                5 => {
                    c.files.insert(FILES[1].into(), "c".repeat(64));
                }
                _ => c.validated_candidate_sha256 = vec!["b".repeat(64); 9],
            }
            assert!(
                validate_capability_record(&c, None, &[], |_| Ok("a".repeat(64))).is_err(),
                "case {case}"
            );
        }
        let external = "/usr/local/sbin/skyview-student-dev-update";
        assert!(
            validate_capability_record(&good, None, &[external], |_| Ok("a".repeat(64))).is_err()
        );
        let mut c = fixture();
        c.files.insert(external.into(), "a".repeat(64));
        assert!(validate_capability_record(&c, None, &[external], |_| Ok("a".repeat(64))).is_ok());
        assert!(validate_capability_record(&c, None, &[], |_| Ok("a".repeat(64))).is_err());
        assert!(
            validate_capability_record(&good, None, &[], |_| Err("untrusted file".into())).is_err()
        );
    }
    #[test]
    fn ready_reports_fit_existing_budget_without_extending_deadlines() {
        let mut last = 0;
        let mut reports = 0;
        for ms in (0..READY_MS).step_by(50) {
            if ready_report_due(last, ms) {
                reports += 1;
                last = ms;
            }
        }
        assert_eq!(reports, 23);
        // Preparing/downloading/verifying/initial Ready, commit/install/postcheck,
        // terminal and one uncertainty report still fit the unchanged bound.
        assert!(reports + 9 <= 32);
        assert!(!ready_report_due(5000, 4999));
        assert!(!ready_report_due(5000, 9999));
        assert!(ready_report_due(5000, 10000));
    }
    #[test]
    fn protected_close_rechecks_receipt_ready_identity_deadlines_and_candidate() {
        let mut r = stored_receipt();
        let p = observation_fixture();
        // Fixtures normally use independent UUIDs: bind only this healthy case.
        r.request_id = p.request_id.clone();
        r.boot_id = p.boot_id.clone();
        let receipt = receipt_view(r, &p.request_id, 1000, &p.boot_id, 20_000).unwrap();
        assert!(validate_close(&receipt, &p, &p.request_id, 1000, &p.boot_id, 20_000).is_ok());
        for case in 0..11 {
            let mut p = observation_fixture();
            p.request_id = receipt.request_id.clone();
            p.boot_id = receipt.boot_id.clone();
            match case {
                0 => p.uid = 1001,
                1 => p.state = State::Installing,
                2 => p.state = State::RecoveryRequired,
                3 => p.candidate = None,
                4 => p.deadline_ms += 1,
                5 => p.observed_ms = 1,
                6 => p.ready_deadline_ms = Some(20_000),
                7 => p.ready_deadline_ms = None,
                8 => p.native_exit = Some(0),
                9 => p.boot_id = uuid::Uuid::new_v4().to_string(),
                _ => p.candidate.as_mut().unwrap().sha256 = "invalid".into(),
            }
            assert!(
                validate_close(
                    &receipt,
                    &p,
                    &receipt.request_id,
                    1000,
                    &receipt.boot_id,
                    20_000
                )
                .is_err(),
                "case {case}"
            );
        }
        let mut pending = receipt;
        pending.status = ReceiptStatus::Pending;
        assert!(validate_close(&pending, &p, &p.request_id, 1000, &p.boot_id, 20_000).is_err());
    }
    #[test]
    fn observations_never_authorize_close_even_when_ready_and_fresh() {
        let p = observation_fixture();
        let id = p.request_id.clone();
        let boot = p.boot_id.clone();
        let view = project_progress(p, &id, 1000, &boot, 20_001).unwrap();
        assert!(view.fresh);
        assert!(!view.close_allowed);
        assert!(!serde_json::to_string(&view)
            .unwrap()
            .contains("not exported"));
    }
    #[test]
    fn stale_and_expired_ready_are_not_liveness_or_authority() {
        for ms in [30_001, 140_000] {
            let p = observation_fixture();
            let id = p.request_id.clone();
            let boot = p.boot_id.clone();
            let view = project_progress(p, &id, 1000, &boot, ms).unwrap();
            assert!(!view.fresh);
            assert!(!view.close_allowed);
        }
    }
    #[test]
    fn mismatched_identity_future_clock_and_incomplete_ready_reject() {
        for case in 0..8 {
            let mut p = observation_fixture();
            let id = p.request_id.clone();
            let boot = p.boot_id.clone();
            match case {
                0 => p.uid = 1001,
                1 => p.request_id = uuid::Uuid::new_v4().to_string(),
                2 => p.boot_id = uuid::Uuid::new_v4().to_string(),
                3 => p.observed_ms = 20_001,
                4 => p.sequence = 33,
                5 => p.candidate = None,
                6 => p.ready_deadline_ms = None,
                _ => p.candidate.as_mut().unwrap().sha256 = "invalid".into(),
            }
            assert!(project_progress(p, &id, 1000, &boot, 20_000).is_err());
        }
        assert!(app_only_observation("../../policy.json").is_err());
    }
    #[test]
    fn progress_rejects_unknown_fields_and_states() {
        assert!(serde_json::from_str::<Progress>(r#"{"state":"cancel"}"#).is_err());
        assert!(app_only_progress("../../policy.json").is_err());
    }
}
