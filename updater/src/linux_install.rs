//! Fixed root maintenance path. Test authentication is compiled only into unit tests.
use crate::{
    discovery::{self, Candidate, GitHub},
    host, staging, AuthenticatedManifest, Result,
};
use serde::{Deserialize, Serialize};
use std::{
    fs::File,
    io::Write,
    os::{
        fd::AsRawFd,
        unix::fs::{MetadataExt, OpenOptionsExt, PermissionsExt},
    },
    path::Path,
    process::Command,
    time::Duration,
};
pub(super) const ROOT: &str = "/var/lib/skyview-robotics/self-update";
pub(super) const INSTALLER: &str = "Skyview-Dev-Setup-LinuxMint-amd64.deb";
const BUNDLE: &str = "/usr/lib/Skyview Dev Setup/backend/linux";

pub(super) fn trusted(path: &Path) -> Result<()> {
    for ancestor in path.ancestors() {
        host::validate(ancestor).map_err(|_| "Untrusted maintenance path")?;
    }
    let m = std::fs::symlink_metadata(path).map_err(|_| "Missing maintenance path")?;
    if m.is_file() && m.nlink() != 1 {
        return Err("Linked maintenance file".into());
    }
    Ok(())
}
pub(super) fn trusted_file(path: &Path) -> Result<()> {
    trusted(path)?;
    if !std::fs::symlink_metadata(path)
        .map_err(|_| "Missing maintenance file")?
        .is_file()
    {
        return Err("Expected regular maintenance file".into());
    }
    Ok(())
}
fn command(program: &str) -> Command {
    let mut command = Command::new(program);
    command
        .env_clear()
        .env("PATH", "/usr/sbin:/usr/bin:/sbin:/bin")
        .env("HOME", "/root")
        .env("LC_ALL", "C")
        .env("DEBIAN_FRONTEND", "noninteractive");
    command
}
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Policy {
    schema_version: u32,
    paused: bool,
}
pub(super) fn paused() -> Result<bool> {
    let path = Path::new(ROOT).join("policy.json");
    trusted(&path)?;
    let p: Policy = serde_json::from_slice(&crate::read_bounded(&path, 4096)?)
        .map_err(|_| "Invalid pause policy")?;
    if p.schema_version != 1 {
        return Err("Unsupported pause policy".into());
    }
    Ok(p.paused)
}
pub(super) fn atomic(path: &Path, value: &impl Serialize, readable: bool) -> Result<()> {
    let parent = path.parent().ok_or("Invalid receipt path")?;
    trusted(parent)?;
    if path.exists() {
        trusted(path)?;
    }
    let temporary = parent.join(format!("{}.tmp", uuid::Uuid::new_v4()));
    let mut file = host::exclusive(&temporary).map_err(|_| "Receipt creation failed")?;
    file.write_all(&serde_json::to_vec(value).map_err(|_| "Receipt encoding failed")?)
        .map_err(|_| "Receipt write failed")?;
    if readable {
        file.set_permissions(std::fs::Permissions::from_mode(0o644))
            .map_err(|_| "Status permissions failed")?;
    }
    file.sync_all().map_err(|_| "Receipt flush failed")?;
    std::fs::rename(temporary, path).map_err(|_| "Receipt activation failed")?;
    File::open(parent)
        .and_then(|f| f.sync_all())
        .map_err(|_| "Receipt directory flush failed".into())
}
fn authenticate_staged(
    directory: &Path,
    candidate: &Candidate,
    authenticate: impl FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
) -> Result<AuthenticatedManifest> {
    if candidate.platform != "linux-amd64" || candidate.installer != INSTALLER {
        return Err("Invalid Linux candidate".into());
    }
    trusted(directory)?;
    for name in [
        "sde-update.json",
        "sde-update.json.minisig",
        INSTALLER,
        "verified.json",
    ] {
        trusted_file(&directory.join(name))?;
    }
    let bytes = crate::read_bounded(&directory.join("sde-update.json"), crate::MAX_METADATA)?;
    let signature = String::from_utf8(crate::read_bounded(
        &directory.join("sde-update.json.minisig"),
        8192,
    )?)
    .map_err(|_| "Invalid signature encoding")?;
    let manifest = authenticate(&bytes, &signature, &candidate.tag)?;
    if manifest.metadata().version != candidate.version {
        return Err("Candidate identity changed".into());
    }
    crate::verify_installer(&manifest, "linux-amd64", &directory.join(INSTALLER))?;
    Ok(manifest)
}
// Only read-only pre-install probes may be timed out. APT/DPKG installation
// itself is NEVER wrapped, killed or cancelled when an authorization expires.
fn inspection(program: &str, guard: Option<&dyn Fn() -> Result<Duration>>) -> Result<Command> {
    if !matches!(program, "/usr/bin/dpkg-deb" | "/usr/bin/dpkg") {
        return Err("Not a read-only package probe".into());
    }
    let Some(guard) = guard else {
        return Ok(command(program));
    };
    trusted_file(Path::new("/usr/bin/timeout"))?;
    let budget = probe_timeout(guard()?)?;
    let mut c = command("/usr/bin/timeout");
    c.args(["--signal=KILL", &budget, program]);
    Ok(c)
}
fn probe_timeout(remaining: Duration) -> Result<String> {
    let ms = remaining.as_millis().min(10_000);
    if ms == 0 {
        return Err("Pre-install request expired".into());
    }
    Ok(format!("{}.{:03}s", ms / 1000, ms % 1000))
}
fn deb_identity(
    directory: &Path,
    version: &str,
    guard: Option<&dyn Fn() -> Result<Duration>>,
) -> Result<()> {
    let output = inspection("/usr/bin/dpkg-deb", guard)?
        .args(["-f"])
        .arg(directory.join(INSTALLER))
        .args(["Package", "Version", "Architecture"])
        .output()
        .map_err(|_| "DEB identity unavailable")?;
    let expected = format!("Package: skyview-dev-setup\nVersion: {version}\nArchitecture: amd64\n");
    if !output.status.success() || output.stdout != expected.as_bytes() {
        return Err("Authenticated DEB has unexpected native identity".into());
    }
    Ok(())
}
// POSIX record locks match APT/DPKG. flock would test a different lock namespace.
// This is a preflight only: APT remains the authority for atomic lock acquisition.
fn package_busy() -> Result<bool> {
    for path in [
        "/var/lib/dpkg/lock-frontend",
        "/var/lib/dpkg/lock",
        "/var/lib/apt/lists/lock",
        "/var/cache/apt/archives/lock",
    ] {
        if !Path::new(path).exists() {
            continue;
        }
        trusted(Path::new(path))?;
        let file = std::fs::OpenOptions::new()
            .read(true)
            .write(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC)
            .open(path)
            .map_err(|_| "Package lock inspection failed")?;
        let mut lock: libc::flock = unsafe { std::mem::zeroed() };
        lock.l_type = libc::F_WRLCK as _;
        lock.l_whence = libc::SEEK_SET as _;
        if unsafe { libc::fcntl(file.as_raw_fd(), libc::F_GETLK, &mut lock) } == -1 {
            return Err("Package lock inspection failed".into());
        }
        if lock.l_type != libc::F_UNLCK as libc::c_short {
            return Ok(true);
        }
    }
    Ok(false)
}
fn apt_command(directory: &Path) -> Command {
    let mut c = command("/usr/bin/apt-get");
    c.args([
        "-y",
        "--no-remove",
        "--no-install-recommends",
        "-o",
        "DPkg::Lock::Timeout=30",
        "-o",
        "Dpkg::Options::=--force-confdef",
        "-o",
        "Dpkg::Options::=--force-confold",
        "install",
    ])
    .arg(directory.join(INSTALLER));
    c
}
fn resources(version: &str) -> Result<()> {
    if host::installed_linux_identity()
        .map_err(|_| "Installed package identity unavailable")?
        .version
        != version
    {
        return Err("Installed package version mismatch".into());
    }
    for path in [
        "/usr/bin/skyview-dev-setup",
        "/usr/local/libexec/skyview-self-update.py",
    ] {
        trusted_file(Path::new(path))?;
    }
    for name in [
        "Update-SkyviewStudentDev.sh",
        "lib/coordination.py",
        "self-update/bootstrap.py",
        "self-update/sde-update-trust",
    ] {
        trusted_file(&Path::new(BUNDLE).join(name))?;
    }
    let active = read_receipt("active.json")?;
    if active["schemaVersion"] != 1 || active["version"] != version {
        return Err("Engine activation version mismatch".into());
    }
    let id = receipt_id(&active, "generation")?;
    let engine = Path::new(ROOT).join("engines").join(id);
    trusted(&engine.join("version.json"))?;
    trusted(&engine.join("sde-update-trust"))?;
    let receipt: serde_json::Value =
        serde_json::from_slice(&crate::read_bounded(&engine.join("version.json"), 4096)?)
            .map_err(|_| "Invalid engine receipt")?;
    if receipt != serde_json::json!({"schemaVersion":1,"version":version})
        || crate::hash_file(&engine.join("sde-update-trust"))?
            != crate::hash_file(&Path::new(BUNDLE).join("self-update/sde-update-trust"))?
    {
        return Err("Activated engine differs from installed bundle".into());
    }
    Ok(())
}
fn read_receipt(name: &str) -> Result<serde_json::Value> {
    let path = Path::new(ROOT).join(name);
    trusted(&path)?;
    serde_json::from_slice(&crate::read_bounded(&path, 4096)?)
        .map_err(|_| "Invalid protected receipt".into())
}
fn receipt_id<'a>(value: &'a serde_json::Value, field: &str) -> Result<&'a str> {
    let id = value[field].as_str().ok_or("Missing receipt identity")?;
    if uuid::Uuid::parse_str(id)
        .map(|v| v.to_string() != id)
        .unwrap_or(true)
    {
        return Err("Invalid receipt identity".into());
    }
    Ok(id)
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub(super) struct Report {
    pub(super) phase: crate::observation::Phase,
    pub(super) completed_at: Option<u64>,
    pub(super) schema_version: u32,
    pub(super) checked_at: u64,
    pub(super) application_version: String,
    pub(super) maintenance_engine_version: String,
    pub(super) applied_baseline_version: Option<String>,
    pub(super) tool_exit: Option<i32>,
    pub(super) outcome: String,
    pub(super) detail: String,
    pub(super) candidate_version: Option<String>,
    pub(super) native_exit: Option<i32>,
    pub(super) recovery_available: bool,
    pub(super) log_reference: Option<String>,
}
fn coordination_error(report: &mut Report, error: sde_coordination::Error) -> String {
    report.outcome = match error {
        sde_coordination::Error::Busy => "deferred",
        sde_coordination::Error::Interrupted | sde_coordination::Error::NeedsRepair => "failed",
        _ => "unavailable",
    }
    .into();
    error.to_string()
}
fn install_selected(
    directory: &Path,
    candidate: &Candidate,
    report: &mut Report,
    authenticate: impl FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
) -> Result<()> {
    report.phase = crate::observation::Phase::Verification;
    let lease = sde_coordination::installation().map_err(|e| coordination_error(report, e))?;
    install_in_context(
        crate::install_core::Context::scheduled(&lease),
        directory,
        candidate,
        report,
        authenticate,
        None,
        None,
    )
}

/// Authorized worker retains O/A/S and supplies a mandatory late commit check.
pub(super) fn install_app_only(
    lease: &sde_coordination::Installation,
    directory: &Path,
    candidate: &Candidate,
    report: &mut Report,
    guard: &dyn Fn() -> Result<Duration>,
    observe: &dyn Fn(crate::observation::Phase),
) -> Result<()> {
    if unsafe { libc::geteuid() } != 0 {
        return Err("Root maintenance required".into());
    }
    report.tool_exit =
        crate::install_core::tools_for(crate::install_core::Scope::AppOnly, tool_maintenance)?;
    install_in_context(
        crate::install_core::Context::app_only(lease),
        directory,
        candidate,
        report,
        crate::authenticate,
        Some(guard),
        Some(observe),
    )
}

fn install_in_context(
    context: crate::install_core::Context<'_>,
    directory: &Path,
    candidate: &Candidate,
    report: &mut Report,
    authenticate: impl FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
    guard: Option<&dyn Fn() -> Result<Duration>>,
    observe: Option<&dyn Fn(crate::observation::Phase)>,
) -> Result<()> {
    let scope = context.scope();
    crate::install_core::install(
        context,
        &mut LinuxBackend {
            directory,
            candidate,
            report,
            authenticate: Some(authenticate),
            scope,
            guard,
            observe,
        },
    )
}

struct LinuxBackend<'a, F> {
    directory: &'a Path,
    candidate: &'a Candidate,
    report: &'a mut Report,
    authenticate: Option<F>,
    scope: crate::install_core::Scope,
    guard: Option<&'a dyn Fn() -> Result<Duration>>,
    observe: Option<&'a dyn Fn(crate::observation::Phase)>,
}

impl<F> crate::install_core::Backend for LinuxBackend<'_, F>
where
    F: FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
{
    type Verified = AuthenticatedManifest;
    fn target_version(&self) -> &str {
        &self.candidate.version
    }
    fn phase(&mut self, phase: crate::observation::Phase) {
        self.report.phase = phase;
        if let Some(observe) = self.observe {
            observe(phase);
        }
    }
    fn paused(&mut self) -> Result<bool> {
        paused()
    }
    fn installed_version(&mut self) -> Result<String> {
        Ok(host::installed_linux_identity()
            .map_err(|_| "Installed identity unavailable")?
            .version)
    }
    fn mark_paused(&mut self) {
        self.report.outcome = "paused".into();
    }
    fn record_paused_intent(&mut self) -> Result<()> {
        Ok(())
    }
    fn mark_current(&mut self) {
        self.report.outcome = "current".into();
    }
    fn mark_failed(&mut self) {
        self.report.outcome = "failed".into();
    }
    fn authenticate(&mut self) -> Result<AuthenticatedManifest> {
        authenticate_staged(
            self.directory,
            self.candidate,
            self.authenticate
                .take()
                .ok_or("Authentication already consumed")?,
        )
    }
    fn preflight(&mut self, _verified: &AuthenticatedManifest) -> Result<bool> {
        deb_identity(self.directory, &self.candidate.version, self.guard)?;
        if package_busy()? {
            self.report.outcome = "deferred".into();
            self.report.detail = match self.scope {
                crate::install_core::Scope::ScheduledMaintenance => {
                    "Package manager is busy; retry on the next scheduled run"
                }
                crate::install_core::Scope::AppOnly => {
                    "Package manager is busy; start a new authorized update attempt later"
                }
            }
            .into();
            return Ok(false);
        }
        self.report.phase = crate::observation::Phase::Packagehealth;
        let audit = inspection("/usr/bin/dpkg", self.guard)?
            .arg("--audit")
            .output()
            .map_err(|_| "Package health check unavailable")?;
        if !audit.status.success() || !audit.stdout.is_empty() || !audit.stderr.is_empty() {
            return Err(
                "Existing package state needs mentor repair before self-installation".into(),
            );
        }
        Ok(true)
    }
    fn validate_commit(&mut self) -> Result<()> {
        self.guard.ok_or("Missing app-only authorization guard")?().map(|_| ())
    }
    fn record_intent(&mut self, before: &str, manifest: &AuthenticatedManifest) -> Result<()> {
        atomic(
            &Path::new(ROOT).join("installation.json"),
            &serde_json::json!({"schemaVersion":1,"stage":"installing","previousVersion":before,"candidateVersion":self.candidate.version,"sha256":manifest.metadata().platforms["linux-amd64"].sha256,"transaction":self.directory.file_name().and_then(|s|s.to_str()),"startedAt":self.report.checked_at}),
            false,
        )
    }
    fn launch(&mut self) -> Result<i32> {
        self.report.outcome = "failed".into();
        // Wait for actual completion; never kill APT/DPKG, remove locks or force reboot.
        apt_command(self.directory)
            .status()
            .map_err(|_| "Native completion unknown; mentor review required")?
            .code()
            .ok_or_else(|| "Native completion unknown; mentor review required".into())
    }
    fn native_finished(&mut self, before: &str, code: i32) -> Result<()> {
        self.report.native_exit = Some(code);
        atomic(
            &Path::new(ROOT).join("installation.json"),
            &serde_json::json!({"schemaVersion":1,"stage":"postcheck","previousVersion":before,"candidateVersion":self.candidate.version,"nativeExit":code}),
            false,
        )?;
        if code != 0 {
            return Err(format!(
                "APT returned {code}; mentor review required before retry"
            ));
        }
        Ok(())
    }
    fn postcheck(&mut self) -> Result<()> {
        resources(&self.candidate.version)
    }
    fn record_success(&mut self, before: &str, code: i32) -> Result<()> {
        if Path::new(ROOT).join("recovery.json").exists() {
            atomic(
                &Path::new(ROOT).join("previous-recovery.json"),
                &read_receipt("recovery.json")?,
                false,
            )?;
        }
        atomic(
            &Path::new(ROOT).join("recovery.json"),
            &serde_json::json!({"schemaVersion":1,"version":self.candidate.version,"transaction":self.directory.file_name().and_then(|s|s.to_str())}),
            false,
        )?;
        atomic(
            &Path::new(ROOT).join("installation.json"),
            &serde_json::json!({"schemaVersion":1,"stage":"complete","previousVersion":before,"candidateVersion":self.candidate.version,"nativeExit":code}),
            false,
        )
    }
    fn mark_updated(&mut self) {
        self.report.application_version = self.candidate.version.clone();
        self.report.outcome = "updated".into();
        if !self.report.recovery_available {
            self.report.detail =
                "Previous signed installer unavailable; reduced recovery capability".into();
        }
    }
}

pub(super) fn stage(github: &mut GitHub, root: &Path, candidate: &Candidate) -> Result<String> {
    staging::stage_with(github, root, candidate, |b, s, t| {
        crate::authenticate(b, s, t).map_err(|_| discovery::Failure::Untrusted)
    })
    .map(|s| s.id)
    .map_err(|e| format!("Authenticated staging failed: {e:?}"))
}
pub(super) fn recovery(github: &mut GitHub, root: &Path, installed: &str) -> Result<bool> {
    if Path::new(ROOT).join("recovery.json").exists() {
        let r = read_receipt("recovery.json")?;
        if r["schemaVersion"] != 1 {
            return Err("Invalid recovery schema".into());
        }
        if r["version"] == installed {
            let id = receipt_id(&r, "transaction")?;
            let c = Candidate {
                tag: format!("v{installed}"),
                version: installed.into(),
                platform: "linux-amd64".into(),
                installer: INSTALLER.into(),
                installer_size: 0,
            };
            authenticate_staged(&root.join(id), &c, crate::authenticate)?;
            return Ok(true);
        }
    }
    let releases: Vec<_> = discovery::list_with(github)
        .map_err(|_| "Recovery release unavailable")?
        .into_iter()
        .filter(|r| r.tag_name == format!("v{installed}") && !r.draft && !r.prerelease)
        .collect();
    if releases.len() != 1 {
        return Ok(false);
    }
    let c = discovery::select(&releases, "0.0.0", "linux-amd64")
        .map_err(|_| "Unsigned recovery release")?
        .ok_or("Recovery candidate missing")?;
    let id = stage(github, root, &c)?;
    atomic(
        &Path::new(ROOT).join("recovery.json"),
        &serde_json::json!({"schemaVersion":1,"version":installed,"transaction":id}),
        false,
    )?;
    Ok(true)
}
fn prune(root: &Path) -> Result<()> {
    let mut keep = Vec::new();
    for name in ["recovery.json", "previous-recovery.json"] {
        if Path::new(ROOT).join(name).exists() {
            let r = read_receipt(name)?;
            if r["schemaVersion"] != 1 {
                return Err("Invalid recovery schema".into());
            }
            keep.push(receipt_id(&r, "transaction")?.to_string());
        }
    }
    for entry in std::fs::read_dir(root).map_err(|_| "Staging enumeration failed")? {
        let entry = entry.map_err(|_| "Staging enumeration failed")?;
        let id = entry
            .file_name()
            .to_str()
            .ok_or("Invalid staging name")?
            .to_owned();
        if uuid::Uuid::parse_str(&id)
            .map(|v| v.to_string() != id)
            .unwrap_or(true)
        {
            return Err("Unknown staging state".into());
        }
        if keep.contains(&id) {
            continue;
        }
        trusted(&entry.path())?;
        for file in std::fs::read_dir(entry.path()).map_err(|_| "Staging cleanup failed")? {
            let file = file.map_err(|_| "Staging cleanup failed")?;
            if ![
                "sde-update.json",
                "sde-update.json.minisig",
                INSTALLER,
                "verified.json",
            ]
            .iter()
            .any(|n| file.file_name() == *n)
            {
                return Err("Unknown staging file".into());
            }
            trusted(&file.path())?;
            std::fs::remove_file(file.path()).map_err(|_| "Staging cleanup failed")?;
        }
        std::fs::remove_dir(entry.path()).map_err(|_| "Staging cleanup failed")?;
    }
    Ok(())
}
fn tool_maintenance() -> Result<Option<i32>> {
    if !Path::new("/usr/local/sbin/skyview-student-dev-update").exists() {
        return Ok(None);
    }
    let run = std::env::current_exe()
        .map_err(|_| "Missing worker path")?
        .parent()
        .ok_or("Missing worker directory")?
        .to_path_buf();
    trusted(&run)?;
    for (name, bytes) in [
        (
            "coordination.py",
            include_str!("../../linux/lib/coordination.py"),
        ),
        (
            "applied.py",
            include_str!("../../linux/self-update/applied.py"),
        ),
    ] {
        let mut file =
            host::exclusive(&run.join(name)).map_err(|_| "Supervisor creation failed")?;
        file.write_all(bytes.as_bytes())
            .and_then(|_| file.sync_all())
            .map_err(|_| "Supervisor write failed")?;
    }
    command("/usr/bin/python3")
        .arg("-I")
        .arg("-B")
        .arg(run.join("applied.py"))
        .status()
        .map(|s| Some(s.code().unwrap_or(1)))
        .map_err(|_| "Tool maintenance could not start".into())
}
pub fn maintain_linux() -> Result<i32> {
    if unsafe { libc::geteuid() } != 0 {
        return Err("Root maintenance required".into());
    }
    trusted(Path::new(ROOT))?;
    let exe = std::env::current_exe().map_err(|_| "Missing worker identity")?;
    trusted(&exe)?;
    trusted(&exe.with_file_name("version.json"))?;
    let engine: serde_json::Value = serde_json::from_slice(&crate::read_bounded(
        &exe.with_file_name("version.json"),
        4096,
    )?)
    .map_err(|_| "Invalid worker receipt")?;
    if engine["schemaVersion"] != 1
        || engine["version"]
            .as_str()
            .is_none_or(|v| crate::release_version(&format!("v{v}")).is_err())
    {
        return Err("Invalid engine identity receipt".into());
    }
    let baseline = Path::new("/var/lib/skyview-robotics/student-dev/version");
    let baseline_version = trusted(baseline)
        .ok()
        .and_then(|_| crate::read_bounded(baseline, 128).ok())
        .and_then(|b| String::from_utf8(b).ok())
        .map(|s| s.trim().to_string())
        .filter(|s| crate::release_version(&format!("v{s}")).is_ok());
    let mut report = Report {
        schema_version: 1,
        phase: crate::observation::Phase::Tools,
        completed_at: None,
        checked_at: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| "Clock unavailable")?
            .as_secs(),
        application_version: host::installed_linux_identity()
            .map(|i| i.version)
            .unwrap_or_default(),
        maintenance_engine_version: engine["version"]
            .as_str()
            .ok_or("Missing engine version")?
            .into(),
        applied_baseline_version: baseline_version,
        tool_exit: None,
        outcome: "unavailable".into(),
        detail: String::new(),
        candidate_version: None,
        native_exit: None,
        recovery_available: false,
        log_reference: exe
            .parent()
            .and_then(|p| p.file_name())
            .and_then(|s| s.to_str())
            .and_then(|s| uuid::Uuid::parse_str(s).ok())
            .map(|id| format!("logs/{id}.log")),
    };
    let result = (|| {
        report.tool_exit = crate::install_core::tools_for(
            crate::install_core::Scope::ScheduledMaintenance,
            tool_maintenance,
        )?;
        if report.tool_exit.is_some_and(|c| c != 0) {
            report.outcome = if report.tool_exit == Some(75) {
                "deferred"
            } else {
                "failed"
            }
            .into();
            return Err(
                "Tool maintenance did not complete successfully; application installation deferred"
                    .into(),
            );
        }
        report.phase = crate::observation::Phase::Identity;
        let installed =
            host::installed().map_err(|e| format!("Installed identity unavailable: {e:?}"))?;
        report.application_version = installed.version.clone();
        report.phase = crate::observation::Phase::Policy;
        if paused()? {
            report.outcome = "paused".into();
            return Ok(());
        }
        let mut github = GitHub::new().map_err(|_| "GitHub unavailable")?;
        let root = host::store().map_err(|_| "Protected staging unavailable")?;
        let operation =
            sde_coordination::operation().map_err(|e| coordination_error(&mut report, e))?;
        prune(&root)?;
        report.recovery_available =
            recovery(&mut github, &root, &installed.version).unwrap_or(false);
        report.phase = crate::observation::Phase::Discovery;
        let candidate = discovery::discover_with(&mut github, &installed.version, "linux-amd64")
            .map_err(|e| format!("Release check unavailable: {e:?}"))?;
        let Some(candidate) = candidate else {
            report.outcome = "current".into();
            return Ok(());
        };
        report.candidate_version = Some(candidate.version.clone());
        report.phase = crate::observation::Phase::Download;
        let id = stage(&mut github, &root, &candidate)?;
        drop(operation);
        let current = host::installed().map_err(|_| "Installed identity changed")?;
        let eligible = discovery::discover_with(&mut github, &current.version, "linux-amd64")
            .map_err(|_| "Release eligibility recheck unavailable")?;
        if eligible.as_ref().map(|c| (&c.tag, &c.version))
            != Some((&candidate.tag, &candidate.version))
        {
            return Err("Release eligibility changed".into());
        }
        install_selected(&root.join(id), &candidate, &mut report, crate::authenticate)
    })();
    if let Err(ref e) = result {
        report.detail = e.clone();
    }
    report.completed_at = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .ok()
        .map(|t| t.as_secs());
    atomic(&Path::new(ROOT).join("status.json"), &report, true)?;
    println!(
        "{}",
        serde_json::to_string(&report).map_err(|_| "Report encoding failed")?
    );
    Ok(
        if report.outcome == "deferred" || report.tool_exit == Some(75) {
            75
        } else if result.is_err() || report.tool_exit.is_some_and(|c| c != 0) {
            1
        } else {
            0
        },
    )
}

/// Fixed administrator policy command; no scheduler, tools or journal mutation.
pub fn set_linux_pause(paused: bool) -> Result<()> {
    if unsafe { libc::geteuid() } != 0 {
        return Err("Run pause/resume as an administrator using sudo".into());
    }
    // Require an installed, trusted policy rather than initialize arbitrary state.
    let _ = self::paused()?;
    atomic(
        &Path::new(ROOT).join("policy.json"),
        &crate::observation::Policy {
            schema_version: 1,
            paused,
        },
        true,
    )
}

#[cfg(test)]
mod tests {
    #[test]
    fn read_only_probe_budgets_never_disable_timeout_or_wrap_installer() {
        use super::*;
        assert_eq!(probe_timeout(Duration::from_millis(1)).unwrap(), "0.001s");
        assert_eq!(probe_timeout(Duration::from_secs(100)).unwrap(), "10.000s");
        assert!(probe_timeout(Duration::ZERO).is_err());
        assert!(inspection("/usr/bin/apt-get", None).is_err());
        assert_eq!(
            inspection("/usr/bin/dpkg", None).unwrap().get_program(),
            "/usr/bin/dpkg"
        );
    }

    use super::*;
    use minisign::KeyPair;
    use std::{
        io::{BufRead, BufReader},
        process::Stdio,
    };
    fn fixture(source: &Path, version: &str, keys: &KeyPair) -> (std::path::PathBuf, Candidate) {
        let staging = host::store().unwrap();
        let mut release = crate::e2e::Fixture::new(source.parent().unwrap(), version, keys);
        let installed = host::installed().unwrap().version;
        let candidate = release
            .discover(&installed, "linux-amd64")
            .unwrap()
            .unwrap();
        let operation = sde_coordination::operation().unwrap();
        let staged = release.stage(&staging, &candidate).unwrap();
        drop(operation);
        assert_eq!(
            release
                .discover(&installed, "linux-amd64")
                .unwrap()
                .unwrap()
                .version,
            candidate.version
        );
        (staging.join(staged.id), candidate)
    }
    #[test]
    fn apt_contract_is_narrow_noninteractive_and_bounded() {
        let c = apt_command(Path::new(
            "/var/lib/skyview-robotics/self-update/staging/fixture",
        ));
        let args: Vec<_> = c.get_args().map(|s| s.to_str().unwrap()).collect();
        assert!(args.contains(&"--no-remove"));
        assert!(args.contains(&"DPkg::Lock::Timeout=30"));
        assert!(!args.iter().any(|v| [
            "upgrade",
            "dist-upgrade",
            "autoremove",
            "--allow-downgrades",
            "--allow-unauthenticated"
        ]
        .contains(v)));
        assert_eq!(c.get_program(), "/usr/bin/apt-get");
        assert!(c
            .get_envs()
            .any(|(k, v)| k == "DEBIAN_FRONTEND" && v.is_some_and(|v| v == "noninteractive")));
    }
    #[test]
    fn signed_upgrade_on_native_mint() {
        let Some(source) = std::env::var_os("SDE_MINT_NATIVE_FIXTURE") else {
            return;
        };
        assert_eq!(unsafe { libc::geteuid() }, 0);
        let source = Path::new(&source);
        assert_eq!(
            host::installed().unwrap().version,
            "1.2.1",
            "Required proof must run on actual supported Mint"
        );
        let baseline_path = Path::new("/usr/local/sbin/skyview-student-dev-update");
        let baseline = std::fs::read(baseline_path).unwrap();
        let student = Path::new("/home/sde-student/project.txt");
        let student_before = std::fs::read(student).unwrap();
        let settings = Path::new("/home/sde-student/.config/Code/User/settings.json");
        std::fs::create_dir_all(settings.parent().unwrap()).unwrap();
        std::fs::write(
            settings,
            br#"{"editor.fontSize":17,"files.autoSave":"afterDelay"}"#,
        )
        .unwrap();
        let settings_before = std::fs::read(settings).unwrap();
        let timer = std::fs::read("/etc/systemd/system/skyview-student-dev-update.timer").unwrap();
        let policy_before = std::fs::read(Path::new(ROOT).join("policy.json")).unwrap();
        set_linux_pause(false).unwrap();
        assert_eq!(crate::observation::inspect().paused, Some(false));
        set_linux_pause(true).unwrap();
        assert_eq!(crate::observation::inspect().paused, Some(true));
        assert_eq!(std::fs::read(baseline_path).unwrap(), baseline);
        assert_eq!(
            std::fs::read("/etc/systemd/system/skyview-student-dev-update.timer").unwrap(),
            timer
        );

        // Model a killed downloader's private partial transaction. Only known
        // unretained files may be pruned under the operation gate.
        let staging = host::store().unwrap();
        let partial = staging.join(uuid::Uuid::new_v4().to_string());
        host::create_private(&partial).unwrap();
        std::fs::write(partial.join("sde-update.json"), b"partial").unwrap();
        let operation = sde_coordination::operation().unwrap();
        prune(&staging).unwrap();
        drop(operation);
        assert!(!partial.exists());
        let keys = KeyPair::generate_unencrypted_keypair().unwrap();
        let (directory, candidate) = fixture(source, "1.2.2", &keys);
        assert!(authenticate_staged(&directory, &candidate, crate::authenticate).is_err());
        let metadata = std::fs::read(directory.join("sde-update.json")).unwrap();
        std::fs::write(directory.join("sde-update.json"), b"tampered").unwrap();
        assert!(authenticate_staged(&directory, &candidate, |b, s, t| {
            crate::authenticate_with_key(b, s, t, &keys.pk)
        })
        .is_err());
        std::fs::write(directory.join("sde-update.json"), metadata).unwrap();
        let payload = std::fs::read(directory.join(INSTALLER)).unwrap();
        std::fs::write(directory.join(INSTALLER), b"tampered payload").unwrap();
        assert!(authenticate_staged(&directory, &candidate, |b, s, t| {
            crate::authenticate_with_key(b, s, t, &keys.pk)
        })
        .is_err());
        std::fs::write(directory.join(INSTALLER), payload).unwrap();
        let mut report = Report {
            schema_version: 1,
            phase: crate::observation::Phase::Tools,
            completed_at: None,
            checked_at: 100,
            application_version: "1.2.1".into(),
            maintenance_engine_version: "1.2.1".into(),
            applied_baseline_version: Some("1.2.1".into()),
            tool_exit: Some(0),
            outcome: "unavailable".into(),
            detail: String::new(),
            candidate_version: Some("1.2.2".into()),
            native_exit: None,
            recovery_available: false,
            log_reference: None,
        };
        install_selected(&directory, &candidate, &mut report, |b, s, t| {
            crate::authenticate_with_key(b, s, t, &keys.pk)
        })
        .unwrap();
        assert_eq!(report.outcome, "paused");
        assert_eq!(report.native_exit, None);
        atomic(
            &Path::new(ROOT).join("policy.json"),
            &serde_json::json!({"schemaVersion":1,"paused":false}),
            false,
        )
        .unwrap();
        let session = sde_coordination::session().unwrap();
        assert!(
            install_selected(&directory, &candidate, &mut report, |b, s, t| {
                crate::authenticate_with_key(b, s, t, &keys.pk)
            })
            .is_err()
        );
        assert_eq!(report.outcome, "deferred");
        drop(session);
        let maintenance = sde_coordination::operation().unwrap();
        assert!(
            install_selected(&directory, &candidate, &mut report, |b, s, t| {
                crate::authenticate_with_key(b, s, t, &keys.pk)
            })
            .is_err()
        );
        assert_eq!(report.outcome, "deferred");
        assert_eq!(report.native_exit, None);
        drop(maintenance);
        // A real other process owns a POSIX DPKG frontend lock. No package kill.
        let mut blocker=command("/usr/bin/python3").args(["-I","-c","import fcntl,sys; f=open('/var/lib/dpkg/lock-frontend','r+'); fcntl.lockf(f,fcntl.LOCK_EX); print('LOCKED',flush=True); sys.stdin.read()"] ).stdin(Stdio::piped()).stdout(Stdio::piped()).spawn().unwrap();
        let mut line = String::new();
        BufReader::new(blocker.stdout.take().unwrap())
            .read_line(&mut line)
            .unwrap();
        assert_eq!(line.trim(), "LOCKED");
        install_selected(&directory, &candidate, &mut report, |b, s, t| {
            crate::authenticate_with_key(b, s, t, &keys.pk)
        })
        .unwrap();
        assert_eq!(report.outcome, "deferred");
        assert_eq!(report.native_exit, None);
        assert!(!sde_coordination::root().join("transaction.json").exists());
        drop(blocker.stdin.take());
        assert!(blocker.wait().unwrap().success());
        install_selected(&directory, &candidate, &mut report, |b, s, t| {
            crate::authenticate_with_key(b, s, t, &keys.pk)
        })
        .unwrap();
        assert_eq!(report.outcome, "updated");
        assert_eq!(report.native_exit, Some(0));
        report.completed_at = Some(101);
        atomic(&Path::new(ROOT).join("status.json"), &report, true).unwrap();
        let visible = crate::observation::inspect();
        assert_eq!(visible.outcome, crate::observation::Outcome::Updated);
        assert_eq!(visible.application_version.as_deref(), Some("1.2.2"));
        assert_eq!(visible.candidate_version.as_deref(), Some("1.2.2"));
        assert_eq!(visible.applied_baseline_version.as_deref(), Some("1.2.1"));
        // Re-presenting the same/older candidate cannot start another installer.
        report.native_exit = None;
        install_selected(&directory, &candidate, &mut report, crate::authenticate).unwrap();
        assert_eq!(report.outcome, "current");
        assert_eq!(report.native_exit, None);
        resources("1.2.2").unwrap();
        assert_eq!(std::fs::read(baseline_path).unwrap(), baseline);
        assert_eq!(std::fs::read(student).unwrap(), student_before);
        assert_eq!(std::fs::read(settings).unwrap(), settings_before);
        assert_eq!(
            std::fs::read("/etc/systemd/system/skyview-student-dev-update.timer").unwrap(),
            timer
        );
        assert!(!sde_coordination::root().join("transaction.json").exists());
        assert!(!command("/usr/bin/pgrep")
            .args(["-f", "^/usr/bin/skyview-dev-setup( |$)"])
            .status()
            .unwrap()
            .success());
        let old_engine = read_receipt("previous-engine.json").unwrap();
        assert_eq!(old_engine["version"], "1.2.1");
        set_linux_pause(true).unwrap();
        let next = command("/usr/bin/python3")
            .args(["-I", "/usr/local/libexec/skyview-self-update.py"])
            .status()
            .unwrap();
        assert!(next.success());
        let status = read_receipt("status.json").unwrap();
        assert_eq!(status["maintenanceEngineVersion"], "1.2.2");
        assert_eq!(status["toolExit"], 0);
        assert_eq!(status["outcome"], "paused");
        assert_eq!(status["appliedBaselineVersion"], "1.2.1");
        let visible = crate::observation::inspect();
        assert_eq!(visible.paused, Some(true));
        assert_eq!(visible.outcome, crate::observation::Outcome::Paused);
        assert_eq!(visible.tool_exit, Some(0));
        assert!(visible.completed_at.unwrap() >= visible.checked_at.unwrap());
        // Real standard user can read public status/policy but cannot alter policy.
        let worker = "/usr/lib/Skyview Dev Setup/backend/linux/self-update/sde-update-trust";
        let read = command("/usr/sbin/runuser")
            .args(["-u", "nobody", "--", worker, "self-update-status"])
            .output()
            .unwrap();
        assert!(read.status.success());
        let public: serde_json::Value = serde_json::from_slice(&read.stdout).unwrap();
        assert_eq!(public["paused"], true);
        assert_eq!(public["outcome"], "paused");
        assert_eq!(public["toolExit"], 0);
        let denied = command("/usr/sbin/runuser")
            .args(["-u", "nobody", "--", worker, "resume"])
            .status()
            .unwrap();
        assert!(!denied.success());
        assert!(paused().unwrap());
        assert!(
            crate::observation::verify_recovery().is_err(),
            "Production must reject test-key recovery assets"
        );

        assert!(std::fs::read_to_string(
            "/etc/systemd/system/skyview-student-dev-update.service.d/sde-self-update.conf"
        )
        .unwrap()
        .contains("/usr/local/libexec/skyview-self-update.py"));
        atomic(
            &Path::new(ROOT).join("policy.json"),
            &serde_json::json!({"schemaVersion":1,"paused":false}),
            false,
        )
        .unwrap();
        // Test-key recovery evidence is never passed to production pinned verification.
        std::fs::remove_file(Path::new(ROOT).join("recovery.json")).unwrap();
        // A real DEB whose postinst returns 23 leaves a partially configured package.
        // APT returns failure and durable intent must prevent all automatic retry.
        let failed_source = source.parent().unwrap().join("failure").join(INSTALLER);
        let (failed, c) = fixture(&failed_source, "1.2.3", &keys);
        assert!(install_selected(&failed, &c, &mut report, |b, s, t| {
            crate::authenticate_with_key(b, s, t, &keys.pk)
        })
        .is_err());
        assert_ne!(report.native_exit, Some(0));
        assert_eq!(report.outcome, "failed");
        assert!(matches!(
            sde_coordination::status(),
            sde_coordination::Status::Interrupted
        ));
        assert!(sde_coordination::installation().is_err());
        report.candidate_version = Some(c.version.clone());
        report.completed_at = Some(102);
        atomic(&Path::new(ROOT).join("status.json"), &report, true).unwrap();
        let failed_status = crate::observation::inspect();
        assert_eq!(failed_status.outcome, crate::observation::Outcome::Failed);
        assert!(matches!(
            failed_status.coordination,
            sde_coordination::Status::Interrupted
        ));
        println!("SDE_E2E_NATIVE_MINT_OK");
        // No cleanup of a real partial DPKG transaction. Disposable container exits.
        std::fs::write(Path::new(ROOT).join("policy.json"), policy_before).unwrap();
        println!("SDE_NATIVE_MINT_UPGRADE_OK: pinned-key rejection, metadata/payload tamper, pause, GUI/package deferral, real APT upgrade, next engine, home/baseline/timer preservation, failed postinst blocks retry");
    }
}
