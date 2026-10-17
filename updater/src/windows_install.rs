//! External SYSTEM worker. Production has no key, repository, installer-path or
//! OS-policy override. Test authentication is injected only by Rust unit tests.
use crate::{discovery::Candidate, AuthenticatedManifest};
use std::path::Path;

const INSTALLER: &str = "Skyview-Dev-Setup-Windows-x64.exe";
#[cfg(windows)]
const ROOT: &str = r"C:\ProgramData\SkyviewRobotics\SelfUpdate";

fn authenticate_staged(
    directory: &Path,
    candidate: &Candidate,
    authenticate: impl FnOnce(&[u8], &str, &str) -> crate::Result<AuthenticatedManifest>,
) -> crate::Result<AuthenticatedManifest> {
    if candidate.platform != "windows-x86_64" || candidate.installer != INSTALLER {
        return Err("Invalid Windows candidate".into());
    }
    crate::host::validate(directory).map_err(|_| "Untrusted staged directory")?;
    for name in [
        "sde-update.json",
        "sde-update.json.minisig",
        INSTALLER,
        "verified.json",
    ] {
        crate::host::validate(&directory.join(name)).map_err(|_| "Untrusted staged file")?;
    }
    let bytes = crate::read_bounded(&directory.join("sde-update.json"), crate::MAX_METADATA)?;
    let signature = String::from_utf8(crate::read_bounded(
        &directory.join("sde-update.json.minisig"),
        8192,
    )?)
    .map_err(|_| "Invalid signature encoding")?;
    // The marker is not an execution authorization. Repeat pinned-key and hash
    // verification under the installation gates, immediately before execution.
    let manifest = authenticate(&bytes, &signature, &candidate.tag)?;
    if manifest.metadata().version != candidate.version {
        return Err("Candidate identity changed".into());
    }
    crate::verify_installer(&manifest, "windows-x86_64", &directory.join(INSTALLER))?;
    Ok(manifest)
}

fn coordination_outcome(error: sde_coordination::Error) -> &'static str {
    match error {
        sde_coordination::Error::Busy => "deferred",
        sde_coordination::Error::Interrupted | sde_coordination::Error::NeedsRepair => "failed",
        _ => "unavailable",
    }
}
#[derive(Debug, PartialEq, Eq)]
enum NativeOutcome {
    Success,
    RebootRequired,
    Failed,
}
fn native_outcome(code: i32) -> NativeOutcome {
    // NSIS evidence establishes zero. MSI's 3010 is NOT assumed to mean NSIS
    // success: record it as reboot-required, retain intent, and require review.
    match code {
        0 => NativeOutcome::Success,
        3010 => NativeOutcome::RebootRequired,
        _ => NativeOutcome::Failed,
    }
}

#[cfg(windows)]
mod native {
    use super::*;
    use crate::{
        discovery::{self, GitHub},
        host, staging,
    };
    use serde::{Deserialize, Serialize};
    use std::{
        io::Write,
        process::Command,
        time::{SystemTime, UNIX_EPOCH},
    };
    use windows_sys::Win32::{Foundation::*, Security::*, System::Threading::*};
    type Result<T> = crate::Result<T>;
    #[derive(Deserialize)]
    #[serde(rename_all = "camelCase", deny_unknown_fields)]
    struct Policy {
        schema_version: u32,
        paused: bool,
    }
    #[derive(Serialize)]
    #[serde(rename_all = "camelCase")]
    struct Report {
        phase: crate::observation::Phase,
        completed_at: Option<u64>,
        schema_version: u32,
        checked_at: u64,
        application_version: String,
        maintenance_engine_version: String,
        applied_baseline: &'static str,
        applied_baseline_version: Option<String>,
        tool_exit: Option<i32>,
        outcome: String,
        detail: String,
        candidate_version: Option<String>,
        native_exit: Option<i32>,
        reboot_required: bool,
        recovery_available: bool,
        log_reference: Option<String>,
    }
    fn trusted(path: &Path) -> Result<()> {
        for ancestor in path.ancestors() {
            host::windows::validate_acl(
                ancestor,
                ancestor == Path::new(r"C:\")
                    || ancestor == Path::new(r"C:\ProgramData")
                    || ancestor == Path::new(r"C:\Program Files"),
            )
            .map_err(|_| "Untrusted maintenance path")?;
        }
        Ok(())
    }
    pub(super) fn system() -> Result<()> {
        let mut token = std::ptr::null_mut();
        if unsafe { OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &mut token) } == 0 {
            return Err("SYSTEM maintenance identity is required".into());
        }
        let mut buffer = [0u64; 128];
        let mut length = 0;
        let ok = unsafe {
            GetTokenInformation(
                token,
                TokenUser,
                buffer.as_mut_ptr().cast(),
                std::mem::size_of_val(&buffer) as u32,
                &mut length,
            )
        };
        unsafe {
            CloseHandle(token);
        }
        if ok == 0 {
            return Err("Cannot validate maintenance identity".into());
        }
        let user = unsafe { &*buffer.as_ptr().cast::<TOKEN_USER>() };
        if unsafe { IsWellKnownSid(user.User.Sid, WinLocalSystemSid) } == 0 {
            return Err("SYSTEM maintenance identity is required".into());
        }
        Ok(())
    }
    pub(super) fn set_pause(paused: bool) -> Result<()> {
        host::windows::administrator()
            .map_err(|_| "Run pause/resume from an elevated administrator terminal")?;
        let _ = policy()?;
        let path = Path::new(ROOT).join("policy.json");
        atomic_json(
            &path,
            &crate::observation::Policy {
                schema_version: 1,
                paused,
            },
        )
    }
    fn policy() -> Result<bool> {
        let root = Path::new(ROOT);
        trusted(root)?;
        let path = root.join("policy.json");
        trusted(&path)?;
        let p: Policy = serde_json::from_slice(&crate::read_bounded(&path, 4096)?)
            .map_err(|_| "Invalid self-update policy; mentor review required")?;
        if p.schema_version != 1 {
            return Err("Unsupported self-update policy".into());
        }
        Ok(p.paused)
    }
    fn atomic_json(path: &Path, value: &impl Serialize) -> Result<()> {
        let parent = path.parent().ok_or("Invalid state path")?;
        trusted(parent)?;
        if path.exists() {
            trusted(path)?;
        }
        let temp = parent.join(format!("{}.tmp", uuid::Uuid::new_v4()));
        let mut file = host::exclusive(&temp).map_err(|_| "State creation failed")?;
        file.write_all(&serde_json::to_vec(value).map_err(|_| "State encoding failed")?)
            .map_err(|_| "State write failed")?;
        file.sync_all().map_err(|_| "State flush failed")?;
        drop(file);
        // Publish read access before the atomic policy switch. A failed ACL
        // change must not leave a resumed policy after a failed command.
        if path == Path::new(ROOT).join("policy.json") {
            host::windows::publish_readonly(&temp)
                .map_err(|_| "Policy permissions could not be published".to_string())?;
        }
        use std::os::windows::ffi::OsStrExt;
        let wide = |p: &Path| {
            p.as_os_str()
                .encode_wide()
                .chain(Some(0))
                .collect::<Vec<_>>()
        };
        if unsafe {
            windows_sys::Win32::Storage::FileSystem::MoveFileExW(
                wide(&temp).as_ptr(),
                wide(path).as_ptr(),
                windows_sys::Win32::Storage::FileSystem::MOVEFILE_REPLACE_EXISTING
                    | windows_sys::Win32::Storage::FileSystem::MOVEFILE_WRITE_THROUGH,
            )
        } == 0
        {
            return Err("State publication failed".into());
        }
        Ok(())
    }
    fn system_environment(command: &mut Command) {
        // Match the established Windows backend contract. SYSTEMDRIVE and
        // system profile folders are required by Windows known-folder APIs;
        // inherit no student profile, PATH, proxy or PowerShell module paths.
        command
            .env_clear()
            .env("SystemRoot", r"C:\Windows")
            .env("WINDIR", r"C:\Windows")
            .env("SYSTEMDRIVE", "C:")
            .env("ComSpec", r"C:\Windows\System32\cmd.exe")
            .env("ProgramData", r"C:\ProgramData")
            .env("ALLUSERSPROFILE", r"C:\ProgramData")
            .env("ProgramFiles", r"C:\Program Files")
            .env("ProgramFiles(x86)", r"C:\Program Files (x86)")
            .env("ProgramW6432", r"C:\Program Files")
            .env("ChocolateyInstall", r"C:\ProgramData\chocolatey")
            .env("USERPROFILE", r"C:\Windows\System32\config\systemprofile")
            .env("APPDATA", r"C:\Windows\System32\config\systemprofile\AppData\Roaming")
            .env("LOCALAPPDATA", r"C:\Windows\System32\config\systemprofile\AppData\Local")
            .env("PSModulePath", r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules;C:\Program Files\WindowsPowerShell\Modules")
            .env("PATHEXT", ".COM;.EXE;.BAT;.CMD")
            .env("PROCESSOR_ARCHITECTURE", "AMD64")
            .env("TEMP", r"C:\Windows\Temp")
            .env("TMP", r"C:\Windows\Temp")
            .env(
                "PATH",
                r"C:\Windows\System32;C:\Windows;C:\ProgramData\chocolatey\bin;C:\Program Files\Git\cmd",
            );
    }
    fn powershell() -> Command {
        let mut command =
            Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe");
        system_environment(&mut command);
        command.args([
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
        ]);
        command
    }
    fn baseline_version() -> Option<String> {
        // This package is installed only by explicit baseline actions. App/engine
        // versions never stand in for the currently applied Chocolatey baseline.
        let path = Path::new(
            r"C:\ProgramData\chocolatey\lib\skyview-student-dev\skyview-student-dev.nuspec",
        );
        trusted(path).ok()?;
        let bytes = crate::read_bounded(path, 65536).ok()?;
        let text = String::from_utf8(bytes).ok()?;
        let value = text.split_once("<version>")?.1.split_once("</version>")?.0;
        let version = semver::Version::parse(value).ok()?;
        if version.to_string() != value {
            return None;
        }
        Some(value.into())
    }
    fn tool_maintenance() -> Result<Option<i32>> {
        let path = Path::new(r"C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1");
        if !path.exists() {
            return Ok(None);
        }
        trusted(path)?;
        let run = std::env::current_exe()
            .map_err(|_| "Missing maintenance snapshot")?
            .parent()
            .ok_or("Missing maintenance directory")?
            .to_path_buf();
        trusted(&run)?;
        // Embedded supervisor acquires the operation gate before reading the
        // applied baseline. Never load a mutable deployed coordination module
        // before the lease, or mix scripts across a concurrent mentor Repair.
        for (name, bytes) in [
            (
                "MaintenanceCoordination.ps1",
                include_str!("../../windows/chocolatey/tools/Coordination.ps1"),
            ),
            (
                "Invoke-AppliedMaintenance.ps1",
                include_str!("../../windows/self-update/Invoke-AppliedMaintenance.ps1"),
            ),
        ] {
            let mut file = host::exclusive(&run.join(name))
                .map_err(|_| "Maintenance supervisor creation failed")?;
            file.write_all(bytes.as_bytes())
                .map_err(|_| "Maintenance supervisor write failed")?;
            file.sync_all()
                .map_err(|_| "Maintenance supervisor flush failed")?;
        }
        let code = powershell()
            .arg(run.join("Invoke-AppliedMaintenance.ps1"))
            .status()
            .map_err(|_| "Tool maintenance could not start")?
            .code();
        Ok(code)
    }
    fn resources(expected: &str) -> Result<()> {
        if host::windows::installed_identity()
            .map_err(|_| "Installed identity check failed")?
            .version
            != expected
        {
            return Err("Installed version does not match authenticated release".into());
        }
        let app =
            host::windows::install_location().map_err(|_| "Invalid machine installation path")?;
        for name in [
            "backend/windows/chocolatey/tools/Update-SkyviewTools.ps1",
            "backend/windows/chocolatey/tools/Coordination.ps1",
            "backend/windows/self-update/Bootstrap-SkyviewSelfUpdate.ps1",
            "backend/windows/self-update/sde-update-trust.exe",
        ] {
            let file = app.join(name);
            trusted(&file)?;
            if !file.is_file() {
                return Err("Installed maintenance resource missing".into());
            }
        }
        trusted(&Path::new(ROOT).join("active.json"))?;
        let receipt: serde_json::Value = serde_json::from_slice(&crate::read_bounded(
            &Path::new(ROOT).join("active.json"),
            4096,
        )?)
        .map_err(|_| "Invalid engine receipt")?;
        if receipt["schemaVersion"] != 1 || receipt["version"] != expected {
            return Err("Engine activation does not match installed application".into());
        }
        let generation = receipt["generation"]
            .as_str()
            .ok_or("Missing engine generation")?;
        if uuid::Uuid::parse_str(generation)
            .map(|id| id.to_string() != generation)
            .unwrap_or(true)
        {
            return Err("Invalid engine generation".into());
        }
        let engine = Path::new(ROOT).join("engines").join(generation);
        for name in ["sde-update-trust.exe", "version.json"] {
            trusted(&engine.join(name))?;
        }
        let generation_receipt: serde_json::Value =
            serde_json::from_slice(&crate::read_bounded(&engine.join("version.json"), 4096)?)
                .map_err(|_| "Invalid engine version receipt")?;
        if generation_receipt["schemaVersion"] != 1 || generation_receipt["version"] != expected {
            return Err("Engine snapshot version mismatch".into());
        }
        // Require the activated verifier to equal the newly installed bundle.
        if crate::hash_file(&engine.join("sde-update-trust.exe"))?
            != crate::hash_file(&app.join("backend/windows/self-update/sde-update-trust.exe"))?
        {
            return Err("Activated engine differs from authenticated application".into());
        }
        Ok(())
    }
    fn stage_candidate(github: &mut GitHub, root: &Path, candidate: &Candidate) -> Result<String> {
        staging::stage_with(github, root, candidate, |b, s, t| {
            crate::authenticate(b, s, t).map_err(|_| discovery::Failure::Untrusted)
        })
        .map(|s| s.id)
        .map_err(|e| format!("Authenticated staging failed: {e:?}"))
    }
    fn seed_recovery(github: &mut GitHub, root: &Path, installed: &str) -> Result<bool> {
        let receipt_path = Path::new(ROOT).join("recovery.json");
        if receipt_path.exists() {
            trusted(&receipt_path)?;
            let receipt: serde_json::Value =
                serde_json::from_slice(&crate::read_bounded(&receipt_path, 4096)?)
                    .map_err(|_| "Invalid recovery receipt")?;
            if receipt["schemaVersion"] != 1 {
                return Err("Unsupported recovery receipt".into());
            }
            if receipt["version"] == installed {
                let id = receipt["transaction"]
                    .as_str()
                    .ok_or("Invalid recovery transaction")?;
                if uuid::Uuid::parse_str(id)
                    .map(|u| u.to_string() != id)
                    .unwrap_or(true)
                {
                    return Err("Invalid recovery transaction".into());
                }
                let candidate = Candidate {
                    tag: format!("v{installed}"),
                    version: installed.into(),
                    platform: "windows-x86_64".into(),
                    installer: INSTALLER.into(),
                    installer_size: 0,
                };
                authenticate_staged(&root.join(id), &candidate, crate::authenticate)?;
                return Ok(true);
            }
        }
        // Exact installed release, never an unverified archived installer or an
        // installer for another baseline. Pre-updater releases may lack evidence.
        let releases = discovery::list_with(github).map_err(|_| "Recovery release unavailable")?;
        let matching: Vec<_> = releases
            .into_iter()
            .filter(|r| r.tag_name == format!("v{installed}") && !r.draft && !r.prerelease)
            .collect();
        if matching.len() != 1 {
            return Ok(false);
        }
        let candidate = discovery::select(&matching, "0.0.0", "windows-x86_64")
            .map_err(|_| "Installed release lacks signed recovery assets")?
            .ok_or("Recovery release missing")?;
        let id = stage_candidate(github, root, &candidate)?;
        atomic_json(
            &receipt_path,
            &serde_json::json!({"schemaVersion":1,"version":installed,"transaction":id}),
        )?;
        Ok(true)
    }
    fn install_selected(
        directory: &Path,
        candidate: &Candidate,
        report: &mut Report,
        authenticate: impl FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
        identity: impl Fn() -> Result<String>,
    ) -> Result<()> {
        report.phase = crate::observation::Phase::Verification;
        let lease = sde_coordination::installation().map_err(|e| {
            report.outcome = coordination_outcome(e).into();
            format!("Installation deferred or requires repair: {e}")
        })?;
        install_in_context(
            crate::install_core::Context::scheduled(&lease),
            directory,
            candidate,
            report,
            authenticate,
            identity,
        )
    }

    /// No bootstrap/CLI is exposed in Phase 1. Later admission and authorization
    /// supply the installation lease; this boundary never reacquires it.
    #[allow(dead_code)]
    fn install_app_only(
        lease: &sde_coordination::Installation,
        directory: &Path,
        candidate: &Candidate,
        report: &mut Report,
    ) -> Result<()> {
        system()?;
        report.tool_exit = crate::install_core::tools_for(
            crate::install_core::Scope::AppOnly,
            tool_maintenance,
        )?;
        install_in_context(crate::install_core::Context::app_only(lease), directory, candidate, report,
            crate::authenticate, || host::installed().map(|i| i.version).map_err(|_| "Installed identity unavailable".into()))
    }

    fn install_in_context(
        context: crate::install_core::Context<'_>,
        directory: &Path,
        candidate: &Candidate,
        report: &mut Report,
        authenticate: impl FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
        identity: impl Fn() -> Result<String>,
    ) -> Result<()> {
        crate::install_core::install(
            context,
            &mut WindowsBackend {
                directory,
                candidate,
                report,
                authenticate: Some(authenticate),
                identity,
            },
        )
    }

    struct WindowsBackend<'a, F, I> {
        directory: &'a Path,
        candidate: &'a Candidate,
        report: &'a mut Report,
        authenticate: Option<F>,
        identity: I,
    }
    impl<F, I> crate::install_core::Backend for WindowsBackend<'_, F, I>
    where
        F: FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
        I: Fn() -> Result<String>,
    {
        type Verified = AuthenticatedManifest;
        fn target_version(&self) -> &str {
            &self.candidate.version
        }
        fn phase(&mut self, phase: crate::observation::Phase) {
            self.report.phase = phase;
        }
        fn paused(&mut self) -> Result<bool> {
            policy()
        }
        fn installed_version(&mut self) -> Result<String> {
            (self.identity)()
        }
        fn mark_paused(&mut self) {
            self.report.outcome = "paused".into();
        }
        fn record_paused_intent(&mut self) -> Result<()> {
            atomic_json(&Path::new(ROOT).join("installation.json"),
                &serde_json::json!({"schemaVersion":1,"stage":"paused","candidateVersion":self.candidate.version}))
        }
        fn mark_current(&mut self) {
            self.report.outcome = "current".into();
        }
        fn mark_failed(&mut self) {
            self.report.outcome = "failed".into();
        }
        fn authenticate(&mut self) -> Result<AuthenticatedManifest> {
            authenticate_staged(self.directory, self.candidate, self.authenticate.take().ok_or("Authentication already consumed")?)
        }
        fn preflight(&mut self, _verified: &AuthenticatedManifest) -> Result<bool> {
            Ok(true)
        }
        fn record_intent(&mut self, before: &str, manifest: &AuthenticatedManifest) -> Result<()> {
            atomic_json(
                &Path::new(ROOT).join("installation.json"),
                &serde_json::json!({"schemaVersion":1,"stage":"installing","previousVersion":before,"candidateVersion":self.candidate.version,"sha256":manifest.metadata().platforms["windows-x86_64"].sha256,"transaction":self.directory.file_name().and_then(|s|s.to_str()),"startedAt":self.report.checked_at}),
            )
        }
        fn launch(&mut self) -> Result<i32> {
            // env is fixed; no relaunch, destination override, UI or reboot switches.
            let mut command = Command::new(self.directory.join(INSTALLER));
            system_environment(&mut command);
            command.current_dir(self.directory).args(["/S", "/UPDATE"]);
            // No timeout/kill: unknown child completion retains coordination intent.
            command.status().map_err(|_| "Native installer completion unknown; mentor review required")?
                .code().ok_or_else(|| "Native installer completion unknown".into())
        }
        fn native_finished(&mut self, before: &str, code: i32) -> Result<()> {
            self.report.native_exit = Some(code);
            self.report.reboot_required = code == 3010;
            atomic_json(
                &Path::new(ROOT).join("installation.json"),
                &serde_json::json!({"schemaVersion":1,"stage":"postcheck","previousVersion":before,"candidateVersion":self.candidate.version,"nativeExit":code,"transaction":self.directory.file_name().and_then(|s|s.to_str())}),
            )?;
            if native_outcome(code) != NativeOutcome::Success {
                return Err(format!("Native installer returned {code}; mentor review required"));
            }
            Ok(())
        }
        fn postcheck(&mut self) -> Result<()> {
            if (self.identity)()? != self.candidate.version {
                return Err("Post-install version mismatch; mentor review required".into());
            }
            resources(&self.candidate.version)
        }
        fn record_success(&mut self, before: &str, code: i32) -> Result<()> {
            let recovery = Path::new(ROOT).join("recovery.json");
            if recovery.exists() {
                let previous: serde_json::Value = serde_json::from_slice(&crate::read_bounded(&recovery, 4096)?)
                    .map_err(|_| "Recovery state invalid")?;
                atomic_json(&Path::new(ROOT).join("previous-recovery.json"), &previous)?;
            }
            atomic_json(&recovery,
                &serde_json::json!({"schemaVersion":1,"version":self.candidate.version,"transaction":self.directory.file_name().and_then(|s|s.to_str())}))?;
            atomic_json(&Path::new(ROOT).join("installation.json"),
                &serde_json::json!({"schemaVersion":1,"stage":"complete","previousVersion":before,"candidateVersion":self.candidate.version,"nativeExit":code}))
        }
        fn mark_updated(&mut self) {
            self.report.application_version = self.candidate.version.clone();
            self.report.outcome = "updated".into();
            if !self.report.recovery_available {
                self.report.detail = "Verified previous-version installer unavailable; reduced recovery capability".into();
            }
        }
    }
    fn prune_staging(root: &Path) -> Result<()> {
        let mut keep = Vec::new();
        for name in ["recovery.json", "previous-recovery.json"] {
            let receipt = Path::new(ROOT).join(name);
            if receipt.exists() {
                trusted(&receipt)?;
                let record: serde_json::Value =
                    serde_json::from_slice(&crate::read_bounded(&receipt, 4096)?)
                        .map_err(|_| "Invalid recovery receipt")?;
                if record["schemaVersion"] != 1 {
                    return Err("Unsupported recovery receipt".into());
                }
                let id = record["transaction"]
                    .as_str()
                    .ok_or("Invalid recovery transaction")?;
                if uuid::Uuid::parse_str(id)
                    .map(|u| u.to_string() != id)
                    .unwrap_or(true)
                {
                    return Err("Invalid recovery transaction".into());
                }
                keep.push(id.to_string());
            }
        }
        for entry in std::fs::read_dir(root).map_err(|_| "Staging enumeration failed")? {
            let entry = entry.map_err(|_| "Staging enumeration failed")?;
            let id = entry
                .file_name()
                .to_str()
                .ok_or("Invalid staging directory")?
                .to_string();
            if uuid::Uuid::parse_str(&id)
                .map(|u| u.to_string() != id)
                .unwrap_or(true)
            {
                return Err("Unknown staging state; mentor review required".into());
            }
            if keep.contains(&id) {
                continue;
            }
            let path = entry.path();
            trusted(&path)?;
            let files = std::fs::read_dir(&path).map_err(|_| "Staging cleanup failed")?;
            for file in files {
                let file = file.map_err(|_| "Staging cleanup failed")?;
                let name = file.file_name();
                if ![
                    "sde-update.json",
                    "sde-update.json.minisig",
                    INSTALLER,
                    "verified.json",
                ]
                .iter()
                .any(|n| name == *n)
                {
                    return Err("Unknown staging file; mentor review required".into());
                }
                trusted(&file.path())?;
                std::fs::remove_file(file.path()).map_err(|_| "Staging cleanup failed")?;
            }
            std::fs::remove_dir(path).map_err(|_| "Staging cleanup failed")?;
        }
        Ok(())
    }

    pub(super) fn maintain() -> Result<i32> {
        system()?;
        trusted(Path::new(ROOT))?;
        let engine: serde_json::Value = serde_json::from_slice(&crate::read_bounded(
            &std::env::current_exe()
                .map_err(|_| "Worker path missing")?
                .with_file_name("version.json"),
            4096,
        )?)
        .map_err(|_| "Worker receipt invalid")?;
        let mut report = Report {
            schema_version: 1,
            phase: crate::observation::Phase::Tools,
            completed_at: None,
            checked_at: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map_err(|_| "Clock unavailable")?
                .as_secs(),
            application_version: host::windows::installed_identity()
                .map(|i| i.version)
                .unwrap_or_default(),
            maintenance_engine_version: engine["version"]
                .as_str()
                .ok_or("Worker version missing")?
                .into(),
            applied_baseline: "preserved deployed tool-maintenance generation",
            applied_baseline_version: baseline_version(),
            tool_exit: None,
            outcome: "unavailable".into(),
            detail: String::new(),
            candidate_version: None,
            native_exit: None,
            reboot_required: false,
            recovery_available: false,
            log_reference: std::env::current_exe().ok().and_then(|p| {
                p.parent()
                    .and_then(|d| d.file_name())
                    .and_then(|n| n.to_str())
                    .and_then(|n| uuid::Uuid::parse_str(n).ok())
                    .map(|id| format!("logs/{id}.log"))
            }),
        };
        let result = (|| {
            report.tool_exit = crate::install_core::tools_for(
                crate::install_core::Scope::ScheduledMaintenance,
                tool_maintenance,
            )?;
            report.phase = crate::observation::Phase::Identity;
            let installed =
                host::installed().map_err(|e| format!("Installed identity unavailable: {e:?}"))?;
            report.application_version = installed.version.clone();
            report.phase = crate::observation::Phase::Policy;
            if policy()? {
                report.outcome = "paused".into();
                return Ok(());
            }
            let mut github = GitHub::new().map_err(|_| "GitHub unavailable")?;
            let staging_root = host::store().map_err(|_| "Protected staging unavailable")?;
            let operation = sde_coordination::operation().map_err(|e| {
                report.outcome = coordination_outcome(e).into();
                e.to_string()
            })?;
            prune_staging(&staging_root)?;
            report.recovery_available =
                seed_recovery(&mut github, &staging_root, &installed.version).unwrap_or(false);
            report.phase = crate::observation::Phase::Discovery;
            let candidate =
                discovery::discover_with(&mut github, &installed.version, "windows-x86_64")
                    .map_err(|e| format!("Release check unavailable: {e:?}"))?;
            let Some(candidate) = candidate else {
                report.outcome = "current".into();
                return Ok(());
            };
            report.candidate_version = Some(candidate.version.clone());
            report.phase = crate::observation::Phase::Download;
            let id = stage_candidate(&mut github, &staging_root, &candidate)?;
            drop(operation);
            // Recheck official draft/prerelease status after downloading. A stable-
            // intent signature alone cannot authorize a candidate's promotion.
            let eligible = discovery::discover_with(
                &mut github,
                &host::installed()
                    .map_err(|_| "Installed identity changed")?
                    .version,
                "windows-x86_64",
            )
            .map_err(|_| "Release eligibility recheck unavailable")?;
            if eligible.as_ref().map(|c| (&c.tag, &c.version))
                != Some((&candidate.tag, &candidate.version))
            {
                return Err("Release eligibility changed; installation deferred".into());
            }
            install_selected(
                &staging_root.join(id),
                &candidate,
                &mut report,
                crate::authenticate,
                || {
                    host::installed()
                        .map(|i| i.version)
                        .map_err(|_| "Installed identity unavailable".into())
                },
            )
        })();
        if let Err(ref e) = result {
            report.detail = e.clone();
        }
        report.completed_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .ok()
            .map(|t| t.as_secs());
        atomic_json(&Path::new(ROOT).join("status.json"), &report)?;
        // Set only the sanitized status readable by students, never private state.
        let acl_script = Path::new(ROOT).join("Publish-SkyviewStatus.ps1");
        trusted(&acl_script)?;
        if !powershell()
            .arg(acl_script)
            .status()
            .map_err(|_| "Status publication failed")?
            .success()
        {
            return Err("Status permissions failed".into());
        }
        println!(
            "{}",
            serde_json::to_string(&report).map_err(|_| "Status encoding failed")?
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
    #[cfg(test)]
    mod tests {
        use super::*;
        use minisign::KeyPair;
        #[test]
        fn signed_upgrade_under_system() {
            let Some(fixture) = std::env::var_os("SDE_NATIVE_UPGRADE_FIXTURE") else {
                return;
            };
            system().unwrap();
            let fixture = Path::new(&fixture);
            let installed = host::windows::installed_identity().unwrap();
            assert_eq!(installed.version, "1.2.1");
            let baseline =
                std::fs::read(r"C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1").unwrap();
            let policy_before = std::fs::read(Path::new(ROOT).join("policy.json")).unwrap();
            set_pause(false).unwrap();
            assert_eq!(crate::observation::inspect().paused, Some(false));
            set_pause(true).unwrap();
            assert_eq!(crate::observation::inspect().paused, Some(true));
            assert_eq!(
                std::fs::read(r"C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1").unwrap(),
                baseline
            );

            atomic_json(
                &Path::new(ROOT).join("policy.json"),
                &serde_json::json!({"schemaVersion":1,"paused":false}),
            )
            .unwrap();
            let marker = Path::new(r"C:\Development\sde-self-update-preservation.txt");
            std::fs::write(marker, b"student project sentinel").unwrap();
            let settings = Path::new(r"C:\Development\.vscode\settings.json");
            std::fs::create_dir_all(settings.parent().unwrap()).unwrap();
            std::fs::write(
                settings,
                br#"{"editor.fontSize":17,"files.autoSave":"afterDelay"}"#,
            )
            .unwrap();
            let settings_before = std::fs::read(settings).unwrap();
            let source = fixture.join("Skyview-Dev-Setup-Windows-x64.exe");
            assert!(source.is_file());
            std::fs::write(
                fixture.join("Skyview-Dev-Setup-LinuxMint-amd64.deb"),
                b"test-only Linux placeholder",
            )
            .unwrap();
            let keys = KeyPair::generate_unencrypted_keypair().unwrap();
            let staging = host::store().unwrap();
            let partial = staging.join(uuid::Uuid::new_v4().to_string());
            host::create_private(&partial).unwrap();
            std::fs::write(partial.join("sde-update.json"), b"partial").unwrap();
            let operation = sde_coordination::operation().unwrap();
            prune_staging(&staging).unwrap();
            assert!(!partial.exists());
            let mut release = crate::e2e::Fixture::new(fixture, "1.2.2", &keys);
            let metadata = release.assets["sde-update.json"].clone();
            let candidate = release
                .discover(&installed.version, "windows-x86_64")
                .unwrap()
                .unwrap();
            let staged = release.stage(&staging, &candidate).unwrap();
            drop(operation);
            assert_eq!(
                release
                    .discover(&installed.version, "windows-x86_64")
                    .unwrap()
                    .unwrap()
                    .version,
                candidate.version
            );
            let directory = staging.join(staged.id);
            // Marker forgery is insufficient; production's pinned key rejects
            // this test key. Then verify tampered metadata and payload rejection.
            assert!(authenticate_staged(&directory, &candidate, crate::authenticate).is_err());
            std::fs::write(directory.join("sde-update.json"), b"tampered").unwrap();
            assert!(authenticate_staged(&directory, &candidate, |b, s, t| {
                crate::authenticate_with_key(b, s, t, &keys.pk)
            })
            .is_err());
            std::fs::write(directory.join("sde-update.json"), &metadata).unwrap();
            let original_payload = std::fs::read(directory.join(INSTALLER)).unwrap();
            std::fs::write(directory.join(INSTALLER), b"modified executable").unwrap();
            assert!(authenticate_staged(&directory, &candidate, |b, s, t| {
                crate::authenticate_with_key(b, s, t, &keys.pk)
            })
            .is_err());
            std::fs::write(directory.join(INSTALLER), original_payload).unwrap();
            let mut report = Report {
                schema_version: 1,
                phase: crate::observation::Phase::Tools,
                completed_at: None,
                checked_at: 100,
                application_version: installed.version,
                maintenance_engine_version: "1.2.1".into(),
                applied_baseline: "preserved",
                applied_baseline_version: Some("1.2.1".into()),
                tool_exit: Some(0),
                outcome: "unavailable".into(),
                detail: String::new(),
                candidate_version: Some(candidate.version.clone()),
                native_exit: None,
                reboot_required: false,
                recovery_available: false,
                log_reference: None,
            };
            atomic_json(
                &Path::new(ROOT).join("policy.json"),
                &serde_json::json!({"schemaVersion":1,"paused":true}),
            )
            .unwrap();
            install_selected(
                &directory,
                &candidate,
                &mut report,
                |b, s, t| crate::authenticate_with_key(b, s, t, &keys.pk),
                || {
                    host::windows::installed_identity()
                        .map(|i| i.version)
                        .map_err(|_| "Invalid installation".into())
                },
            )
            .unwrap();
            assert_eq!(report.outcome, "paused");
            assert_eq!(report.native_exit, None);
            assert_eq!(
                host::windows::installed_identity().unwrap().version,
                "1.2.1"
            );
            assert!(!sde_coordination::root().join("transaction.json").exists());
            atomic_json(
                &Path::new(ROOT).join("policy.json"),
                &serde_json::json!({"schemaVersion":1,"paused":false}),
            )
            .unwrap();
            // A real independent GUI-style session must defer replacement and
            // failed acquisition must release the operation gate.
            let session = sde_coordination::session().unwrap();
            assert!(install_selected(
                &directory,
                &candidate,
                &mut report,
                |b, s, t| crate::authenticate_with_key(b, s, t, &keys.pk),
                || host::windows::installed_identity()
                    .map(|i| i.version)
                    .map_err(|_| "Invalid installation".into())
            )
            .is_err());
            assert_eq!(report.outcome, "deferred");
            drop(session);
            let maintenance = sde_coordination::operation().unwrap();
            assert!(install_selected(
                &directory,
                &candidate,
                &mut report,
                |b, s, t| crate::authenticate_with_key(b, s, t, &keys.pk),
                || host::windows::installed_identity()
                    .map(|i| i.version)
                    .map_err(|_| "Invalid installation".into())
            )
            .is_err());
            assert_eq!(report.outcome, "deferred");
            assert_eq!(report.native_exit, None);
            drop(maintenance);
            install_selected(
                &directory,
                &candidate,
                &mut report,
                |b, s, t| crate::authenticate_with_key(b, s, t, &keys.pk),
                || {
                    host::windows::installed_identity()
                        .map(|i| i.version)
                        .map_err(|_| "Invalid installation".into())
                },
            )
            .unwrap();
            assert_eq!(report.outcome, "updated");
            assert_eq!(report.native_exit, Some(0));
            assert_eq!(std::fs::read(marker).unwrap(), b"student project sentinel");
            assert_eq!(std::fs::read(settings).unwrap(), settings_before);
            assert_eq!(
                std::fs::read(r"C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1").unwrap(),
                baseline
            );
            report.completed_at = Some(101);
            atomic_json(&Path::new(ROOT).join("status.json"), &report).unwrap();
            host::windows::publish_readonly(&Path::new(ROOT).join("status.json")).unwrap();
            let visible = crate::observation::inspect();
            assert_eq!(visible.outcome, crate::observation::Outcome::Updated);
            assert_eq!(visible.application_version.as_deref(), Some("1.2.2"));
            assert_eq!(visible.candidate_version.as_deref(), Some("1.2.2"));
            assert_eq!(visible.applied_baseline_version.as_deref(), Some("1.2.1"));
            report.native_exit = None;
            install_selected(
                &directory,
                &candidate,
                &mut report,
                crate::authenticate,
                || {
                    host::windows::installed_identity()
                        .map(|i| i.version)
                        .map_err(|_| "Invalid installation".into())
                },
            )
            .unwrap();
            assert_eq!(report.outcome, "current");
            assert_eq!(report.native_exit, None);
            resources("1.2.2").unwrap();
            assert!(!sde_coordination::root().join("transaction.json").exists());
            let process=Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe").args(["-NoProfile","-NonInteractive","-Command","if (Get-Process skyview-dev-setup -ErrorAction SilentlyContinue) { exit 1 }; exit 0"]).output().unwrap();
            assert!(
                process.status.success(),
                "Installer launched GUI under SYSTEM"
            );
            assert!(
                process.stdout.is_empty(),
                "Installer launched SDE under SYSTEM"
            );
            set_pause(
                serde_json::from_slice::<Policy>(&policy_before)
                    .unwrap()
                    .paused,
            )
            .unwrap();
            // Test receipts must never survive as production pinned-key evidence.
            std::fs::remove_file(Path::new(ROOT).join("recovery.json")).unwrap();
            // A signed synthetic executable that exits unsuccessfully must
            // leave durable intent and block a second attempt. Never kill a
            // package process: this isolated fixture always exits with code 23.
            let failure_build = fixture.join("failure");
            host::create_private(&failure_build).unwrap();
            std::fs::copy(
                fixture.join("sde-synthetic-failure.exe"),
                failure_build.join(INSTALLER),
            )
            .unwrap();
            std::fs::write(
                failure_build.join("Skyview-Dev-Setup-LinuxMint-amd64.deb"),
                b"fixture",
            )
            .unwrap();
            let mut failure_release = crate::e2e::Fixture::new(&failure_build, "1.2.3", &keys);
            let failing_candidate = failure_release
                .discover("1.2.2", "windows-x86_64")
                .unwrap()
                .unwrap();
            let operation = sde_coordination::operation().unwrap();
            let failed = staging.join(
                failure_release
                    .stage(&staging, &failing_candidate)
                    .unwrap()
                    .id,
            );
            drop(operation);
            atomic_json(
                &Path::new(ROOT).join("policy.json"),
                &serde_json::json!({"schemaVersion":1,"paused":false}),
            )
            .unwrap();
            assert!(install_selected(
                &failed,
                &failing_candidate,
                &mut report,
                |b, s, t| crate::authenticate_with_key(b, s, t, &keys.pk),
                || host::windows::installed_identity()
                    .map(|i| i.version)
                    .map_err(|_| "Invalid installation".into())
            )
            .is_err());
            assert_eq!(report.native_exit, Some(23));
            assert_eq!(report.outcome, "failed");
            assert!(matches!(
                sde_coordination::status(),
                sde_coordination::Status::Interrupted
            ));
            assert!(sde_coordination::installation().is_err());
            report.candidate_version = Some(failing_candidate.version.clone());
            report.completed_at = Some(102);
            atomic_json(&Path::new(ROOT).join("status.json"), &report).unwrap();
            host::windows::publish_readonly(&Path::new(ROOT).join("status.json")).unwrap();
            let failed_status = crate::observation::inspect();
            assert_eq!(failed_status.outcome, crate::observation::Outcome::Failed);
            assert!(matches!(
                failed_status.coordination,
                sde_coordination::Status::Interrupted
            ));
            println!("SDE_E2E_NATIVE_WINDOWS_OK");
            // Explicit cleanup of a completed synthetic fixture, under its
            // operation gate. No native package state or package lock is changed.
            use std::os::windows::fs::OpenOptionsExt;
            let guard = std::fs::OpenOptions::new()
                .read(true)
                .share_mode(0)
                .open(sde_coordination::root().join("operations.gate"))
                .unwrap();
            std::fs::remove_file(sde_coordination::root().join("transaction.json")).unwrap();
            drop(guard);
            set_pause(
                serde_json::from_slice::<Policy>(&policy_before)
                    .unwrap()
                    .paused,
            )
            .unwrap();
            println!("SDE_SIGNED_SYSTEM_UPGRADE_OK: identity, trust rejection, session deferral, native upgrade, engine activation, baseline/student preservation, no GUI/reboot");
        }
    }
}
#[cfg(windows)]
pub fn maintain_windows() -> crate::Result<i32> {
    native::maintain()
}

#[cfg(windows)]
pub fn set_windows_pause(paused: bool) -> crate::Result<()> {
    native::set_pause(paused)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn nsis_exit_contract_never_assumes_msi_success() {
        assert_eq!(native_outcome(0), NativeOutcome::Success);
        assert_eq!(native_outcome(3010), NativeOutcome::RebootRequired);
        for code in [1, 2, 75, 1603, 1641, -1] {
            assert_eq!(native_outcome(code), NativeOutcome::Failed);
        }
    }
}
