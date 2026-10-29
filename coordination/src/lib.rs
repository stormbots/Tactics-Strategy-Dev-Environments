//! Read-only, handle-owned gates. A lease grants no elevation or command authority.
use serde::Serialize;
use std::{
    fs::File,
    path::{Path, PathBuf},
};
pub mod recovery;
pub mod safety;
#[cfg(windows)]
mod windows;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Error {
    Busy,
    Interrupted,
    Unavailable,
    Untrusted,
    NeedsRepair,
}
impl std::fmt::Display for Error {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(match self {
            Self::Busy => "SDE is in use. Maintenance is deferred until a later invocation.",
            Self::Interrupted => {
                "An earlier system operation needs mentor review before another change."
            }
            Self::Unavailable => {
                "SDE coordination is unavailable. Install or repair the application first."
            }
            Self::Untrusted => "SDE coordination storage failed its security checks.",
            Self::NeedsRepair => {
                "Existing maintenance needs one mentor-approved Repair to enable safe coordination."
            }
        })
    }
}
impl std::error::Error for Error {}
pub type Result<T> = std::result::Result<T, Error>;

pub fn root() -> PathBuf {
    #[cfg(windows)]
    {
        PathBuf::from(r"C:\ProgramData\SkyviewRoboticsCoordination")
    }
    #[cfg(not(windows))]
    {
        PathBuf::from("/var/lib/skyview-robotics-coordination")
    }
}
/// Held for the complete GUI / supervised backend lifetime, never a PID sentinel.
#[derive(Debug)]
pub struct Lease {
    _file: File,
}
/// Retains both gates; dropping either after a failed acquisition leaves no lock.
#[derive(Debug)]
pub struct Installation {
    _operation: Lease,
    _sessions: Lease,
    directory: PathBuf,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Idle,
    Busy,
    Interrupted,
    Unavailable,
    Untrusted,
    NeedsRepair,
}

pub fn initialize() -> Result<()> {
    initialize_at(&root())
}
pub fn session() -> Result<Lease> {
    acquire_at(&root(), "sessions.gate", true)
}
pub fn operation() -> Result<Lease> {
    let dir = root();
    let lease = acquire_at(&dir, "operations.gate", false)?;
    no_interruption(&dir)?;
    Ok(lease)
}

/// Reports whether another process currently owns the privileged operation
/// gate. Unlike `status`, this intentionally ignores GUI session leases.
pub fn operation_active() -> Result<bool> {
    match acquire_at(&root(), "operations.gate", false) {
        Ok(_) => Ok(false),
        Err(Error::Busy) => Ok(true),
        Err(error) => Err(error),
    }
}
pub fn installation() -> Result<Installation> {
    let lease = installation_at(&root())?;
    compatible_maintenance()?;
    Ok(lease)
}
pub fn status() -> Status {
    let dir = root();
    match acquire_at(&dir, "operations.gate", false).and_then(|_lease| no_interruption(&dir)) {
        Ok(()) => match acquire_at(&dir, "sessions.gate", false) {
            Ok(_) => match compatible_maintenance() {
                Ok(()) => Status::Idle,
                Err(_) => Status::NeedsRepair,
            },
            Err(Error::Busy) => Status::Busy,
            Err(Error::Untrusted) => Status::Untrusted,
            Err(_) => Status::Unavailable,
        },
        Err(Error::Busy) => Status::Busy,
        Err(Error::Interrupted) => Status::Interrupted,
        Err(Error::Untrusted) => Status::Untrusted,
        Err(_) => Status::Unavailable,
    }
}

/// An older deployed scheduler cannot participate in new locks. Never report
/// installation readiness until its existing entry point has been migrated by
/// an explicit mentor baseline Repair; app installation does not apply a baseline.
fn compatible_maintenance() -> Result<()> {
    #[cfg(unix)]
    let paths = [
        "/usr/local/sbin/skyview-student-dev-update",
        "/usr/local/lib/skyview-student-dev/coordination.py",
    ];
    #[cfg(windows)]
    let paths = [
        r"C:\ProgramData\SkyviewRobotics\Update-SkyviewTools.ps1",
        r"C:\ProgramData\SkyviewRobotics\Coordination.ps1",
    ];
    if !Path::new(paths[0])
        .try_exists()
        .map_err(|_| Error::NeedsRepair)?
    {
        return Ok(());
    }
    for name in paths {
        let path = Path::new(name);
        #[cfg(unix)]
        {
            use std::os::unix::fs::MetadataExt;
            validate_dir(path.parent().ok_or(Error::NeedsRepair)?)?;
            let m = std::fs::symlink_metadata(path).map_err(|_| Error::NeedsRepair)?;
            if !m.is_file() || m.uid() != 0 || m.mode() & 0o022 != 0 || m.nlink() != 1 {
                return Err(Error::NeedsRepair);
            }
        }
        #[cfg(windows)]
        {
            windows::validate(path.parent().ok_or(Error::NeedsRepair)?)?;
            windows::validate(path)?;
        }
        use std::io::Read;
        let mut bytes = Vec::new();
        File::open(path)
            .and_then(|file| file.take(65537).read_to_end(&mut bytes))
            .map_err(|_| Error::NeedsRepair)?;
        if bytes.len() > 65536 || !String::from_utf8_lossy(&bytes).contains("# SDE_COORDINATION_V1")
        {
            return Err(Error::NeedsRepair);
        }
    }
    Ok(())
}
fn no_interruption(dir: &Path) -> Result<()> {
    let entries = std::fs::read_dir(dir).map_err(|_| Error::Unavailable)?;
    for (count, entry) in entries.enumerate() {
        if count > 32 {
            return Err(Error::Untrusted);
        }
        if entry.map_err(|_| Error::Unavailable)?.file_name() == "transaction.json" {
            return Err(Error::Interrupted);
        }
    }
    Ok(())
}
fn installation_at(dir: &Path) -> Result<Installation> {
    let operation = acquire_at(dir, "operations.gate", false)?;
    no_interruption(dir)?;
    let sessions = acquire_at(dir, "sessions.gate", false)?;
    Ok(Installation {
        _operation: operation,
        _sessions: sessions,
        directory: dir.to_path_buf(),
    })
}

#[cfg(unix)]
fn validate_dir(dir: &Path) -> Result<()> {
    use std::os::unix::fs::MetadataExt;
    for ancestor in dir.ancestors() {
        let m = std::fs::symlink_metadata(ancestor).map_err(|_| Error::Unavailable)?;
        if !m.is_dir() || m.file_type().is_symlink() || m.uid() != 0 || m.mode() & 0o022 != 0 {
            return Err(Error::Untrusted);
        }
    }
    Ok(())
}
#[cfg(unix)]
fn initialize_at(dir: &Path) -> Result<()> {
    use std::os::unix::fs::{DirBuilderExt, OpenOptionsExt, PermissionsExt};
    if unsafe { libc::geteuid() } != 0 {
        return Err(Error::Untrusted);
    }
    validate_dir(dir.parent().ok_or(Error::Untrusted)?)?;
    match std::fs::DirBuilder::new().mode(0o755).create(dir) {
        Ok(()) => std::fs::set_permissions(dir, std::fs::Permissions::from_mode(0o755))
            .map_err(|_| Error::Unavailable)?,
        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => (),
        Err(_) => return Err(Error::Unavailable),
    }
    validate_dir(dir)?;
    for name in ["sessions.gate", "operations.gate"] {
        match std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o444)
            .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC)
            .open(dir.join(name))
        {
            Ok(file) => {
                use std::os::unix::fs::PermissionsExt;
                file.set_permissions(std::fs::Permissions::from_mode(0o444))
                    .map_err(|_| Error::Unavailable)?;
                file.sync_all().map_err(|_| Error::Unavailable)?;
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => (),
            Err(_) => return Err(Error::Unavailable),
        }
        drop(open_gate(dir, name)?);
    }
    File::open(dir)
        .and_then(|f| f.sync_all())
        .map_err(|_| Error::Unavailable)
}
#[cfg(unix)]
fn open_gate(dir: &Path, name: &str) -> Result<File> {
    use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
    validate_dir(dir)?;
    let file = std::fs::OpenOptions::new()
        .read(true)
        .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC)
        .open(dir.join(name))
        .map_err(|_| Error::Unavailable)?;
    let m = file.metadata().map_err(|_| Error::Unavailable)?;
    if !m.is_file() || m.uid() != 0 || m.mode() & 0o222 != 0 || m.nlink() != 1 || m.len() != 0 {
        return Err(Error::Untrusted);
    }
    Ok(file)
}
#[cfg(unix)]
fn acquire_at(dir: &Path, name: &str, shared: bool) -> Result<Lease> {
    use std::os::fd::AsRawFd;
    let file = open_gate(dir, name)?;
    if unsafe {
        libc::flock(
            file.as_raw_fd(),
            (if shared { libc::LOCK_SH } else { libc::LOCK_EX }) | libc::LOCK_NB,
        )
    } != 0
    {
        let error = std::io::Error::last_os_error();
        return Err(if error.raw_os_error() == Some(libc::EWOULDBLOCK) {
            Error::Busy
        } else {
            Error::Unavailable
        });
    }
    Ok(Lease { _file: file })
}
#[cfg(windows)]
fn initialize_at(dir: &Path) -> Result<()> {
    windows::initialize(dir)
}
#[cfg(windows)]
fn acquire_at(dir: &Path, name: &str, shared: bool) -> Result<Lease> {
    windows::acquire(dir, name, shared).map(|file| Lease { _file: file })
}

/// Durable intent deliberately survives Drop/crash. Borrowing the installation
/// lease prevents releasing either gate before the transaction ends.
pub struct Transaction<'a> {
    _installation: &'a Installation,
    file: Option<File>,
    path: PathBuf,
}
impl Installation {
    pub fn begin_transaction(&self) -> Result<Transaction<'_>> {
        use std::io::Write;
        let path = self.directory.join("transaction.json");
        #[cfg(unix)]
        let mut file = {
            use std::os::unix::fs::OpenOptionsExt;
            if unsafe { libc::geteuid() } != 0 {
                return Err(Error::Untrusted);
            }
            std::fs::OpenOptions::new()
                .write(true)
                .create_new(true)
                .mode(0o600)
                .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC)
                .open(&path)
                .map_err(|_| Error::Interrupted)?
        };
        #[cfg(windows)]
        let mut file = windows::journal(&path)?;
        let record =
            serde_json::json!({"schema": 1, "pid": std::process::id(), "kind": "installation"});
        file.write_all(record.to_string().as_bytes())
            .and_then(|_| file.sync_all())
            .map_err(|_| Error::Unavailable)?;
        sync_directory(&self.directory)?;
        Ok(Transaction {
            _installation: self,
            file: Some(file),
            path,
        })
    }
}
impl Transaction<'_> {
    /// Call only after the native installer and all package children end with a
    /// known outcome. Unknown completion must retain the record.
    pub fn complete(mut self) -> Result<()> {
        self.file
            .take()
            .ok_or(Error::Unavailable)?
            .sync_all()
            .map_err(|_| Error::Unavailable)?;
        std::fs::remove_file(&self.path).map_err(|_| Error::Unavailable)?;
        sync_directory(self.path.parent().ok_or(Error::Unavailable)?)
    }
}
fn sync_directory(dir: &Path) -> Result<()> {
    #[cfg(unix)]
    {
        File::open(dir)
            .and_then(|file| file.sync_all())
            .map_err(|_| Error::Unavailable)
    }
    #[cfg(windows)]
    {
        let _ = dir;
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use std::{
        io::{BufRead, BufReader, Read, Write},
        process::{Command, Stdio},
    };

    // A concurrent fork briefly inherits other threads' descriptors until exec,
    // even with CLOEXEC. Isolate fixtures so such an unrelated fork cannot retain
    // a lease just released by another test. Each contention test still runs
    // several real processes against its own gates.
    static FIXTURE_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());
    fn lock_fixtures(lock: &std::sync::Mutex<()>) -> std::sync::MutexGuard<'_, ()> {
        // This mutex serializes independent fixture directories; it protects no
        // shared transaction state. Preserve the original failing test, but do
        // not turn its panic into unrelated PoisonError failures in later tests.
        lock.lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }

    fn storage_fixture_powershell() -> Command {
        let mut command =
            Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe");
        // Actions starts Rust under pwsh. Unlike a direct pwsh -> powershell
        // invocation, Rust does not strip PowerShell 7's incompatible module
        // paths. Let the fixed Windows PowerShell 5.1 executable build its own
        // defaults. Preserve every other inherited CI/runtime variable.
        command.env_remove("PSModulePath").args([
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
        ]);
        command
    }

    #[test]
    fn storage_fixture_does_not_inherit_powershell_seven_module_paths() {
        let command = storage_fixture_powershell();
        assert_eq!(
            command.get_program(),
            std::ffi::OsStr::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
        );
        let overrides: Vec<_> = command.get_envs().collect();
        assert_eq!(overrides.len(), 1);
        assert!(overrides[0]
            .0
            .to_string_lossy()
            .eq_ignore_ascii_case("PSModulePath"));
        assert!(overrides[0].1.is_none());
        assert!(command.get_args().any(|arg| arg == "-NoProfile"));
        assert_eq!(
            command.get_args().last(),
            Some(std::ffi::OsStr::new("-File"))
        );
    }

    #[test]
    fn a_failed_fixture_does_not_poison_independent_fixture_execution() {
        let lock = std::sync::Arc::new(std::sync::Mutex::new(()));
        let child = lock.clone();
        let failure = std::thread::spawn(move || {
            let _guard = child.lock().unwrap();
            panic!("Synthetic fixture failure; the original test must still fail");
        })
        .join();
        assert!(failure.is_err());
        assert!(lock.is_poisoned());
        drop(lock_fixtures(&lock));
        drop(lock_fixtures(&lock));
    }
    struct Fixture {
        path: PathBuf,
        _guard: std::sync::MutexGuard<'static, ()>,
    }
    impl Fixture {
        fn new() -> Option<Self> {
            #[cfg(unix)]
            if unsafe { libc::geteuid() } != 0 {
                assert!(
                    std::env::var("SDE_REQUIRE_COORDINATION").as_deref() != Ok("1"),
                    "Root-owned coordination tests must run as root"
                );
                return None;
            }
            let guard = lock_fixtures(&FIXTURE_LOCK);
            let name = format!(
                "coordination-test-{}-{}",
                std::process::id(),
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_nanos()
            );
            #[cfg(windows)]
            let path = PathBuf::from(r"C:\ProgramData").join(name);
            #[cfg(unix)]
            let path = PathBuf::from("/var/lib").join(name);
            initialize_at(&path).unwrap();
            Some(Self {
                path,
                _guard: guard,
            })
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.path).unwrap();
        }
    }
    #[test]
    fn process_probe() {
        let Some(dir) = std::env::var_os("SDE_TEST_COORDINATION_DIR") else {
            return;
        };
        let dir = PathBuf::from(dir);
        let mode = std::env::var("SDE_TEST_COORDINATION_MODE").unwrap();
        let _lease = if mode == "session" {
            acquire_at(&dir, "sessions.gate", true)
        } else {
            acquire_at(&dir, "operations.gate", false)
        }
        .unwrap();
        println!("SDE_LEASE_READY");
        std::io::stdout().flush().unwrap();
        let mut b = [0u8];
        let _ = std::io::stdin().read(&mut b);
    }
    fn child(dir: &Path, mode: &str) -> std::process::Child {
        let mut child = Command::new(std::env::current_exe().unwrap())
            .args(["--exact", "tests::process_probe", "--nocapture"])
            .env("SDE_TEST_COORDINATION_DIR", dir)
            .env("SDE_TEST_COORDINATION_MODE", mode)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();
        let mut reader = BufReader::new(child.stdout.take().unwrap());
        let mut line = String::new();
        loop {
            line.clear();
            assert_ne!(
                reader.read_line(&mut line).unwrap(),
                0,
                "Child failed to acquire its lease"
            );
            if line.trim() == "SDE_LEASE_READY" {
                break;
            }
        }
        child
    }
    #[test]
    fn cross_process_sessions_operations_crash_and_installation_race() {
        let Some(f) = Fixture::new() else { return };
        let mut gui = child(&f.path, "session");
        let second_gui = acquire_at(&f.path, "sessions.gate", true).unwrap();
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Busy);
        // Failed second-gate acquisition must release the first gate.
        drop(acquire_at(&f.path, "operations.gate", false).unwrap());
        drop(second_gui);
        gui.kill().unwrap();
        gui.wait().unwrap();
        let installation = installation_at(&f.path).unwrap();
        assert_eq!(
            acquire_at(&f.path, "sessions.gate", true).unwrap_err(),
            Error::Busy
        );
        assert_eq!(
            acquire_at(&f.path, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        drop(installation);
        let mut backend = child(&f.path, "operation");
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Busy);
        assert_eq!(
            acquire_at(&f.path, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        backend.kill().unwrap();
        backend.wait().unwrap();
        drop(installation_at(&f.path).unwrap()); // OS releases handles after abrupt exit.
    }
    #[test]
    fn durable_installation_intent_and_bootstrap_preserve_live_gates() {
        let Some(f) = Fixture::new() else { return };
        let install = installation_at(&f.path).unwrap();
        initialize_at(&f.path).unwrap();
        assert_eq!(
            acquire_at(&f.path, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        let transaction = install.begin_transaction().unwrap();
        transaction.complete().unwrap();
        assert!(!f.path.join("transaction.json").exists());
        let transaction = install.begin_transaction().unwrap();
        drop(transaction);
        drop(install);
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
    }

    #[test]
    fn interrupted_record_blocks_even_with_free_kernel_gates() {
        let Some(f) = Fixture::new() else { return };
        std::fs::write(
            f.path.join("transaction.json"),
            b"not instructions; stale or malformed state",
        )
        .unwrap();
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
        drop(acquire_at(&f.path, "operations.gate", false).unwrap());
        // Initialization/reboot-style reopening must never delete a journal or
        // replace the lock inode to make an interrupted transaction look idle.
        initialize_at(&f.path).unwrap();
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
    }
    #[test]
    fn native_storage_rejects_links_writable_gates_and_untrusted_directories() {
        let Some(f) = Fixture::new() else { return };
        #[cfg(unix)]
        {
            use std::os::unix::fs::{symlink, PermissionsExt};
            let gate = f.path.join("operations.gate");
            std::fs::set_permissions(&gate, std::fs::Permissions::from_mode(0o644)).unwrap();
            assert_eq!(
                acquire_at(&f.path, "operations.gate", false).unwrap_err(),
                Error::Untrusted
            );
            std::fs::set_permissions(&gate, std::fs::Permissions::from_mode(0o444)).unwrap();
            std::fs::hard_link(&gate, f.path.join("alias")).unwrap();
            assert_eq!(
                acquire_at(&f.path, "operations.gate", false).unwrap_err(),
                Error::Untrusted
            );
            std::fs::remove_file(f.path.join("alias")).unwrap();
            std::fs::remove_file(&gate).unwrap();
            symlink("sessions.gate", &gate).unwrap();
            assert!(acquire_at(&f.path, "operations.gate", false).is_err());
            std::fs::set_permissions(&f.path, std::fs::Permissions::from_mode(0o777)).unwrap();
            assert_eq!(
                acquire_at(&f.path, "sessions.gate", true).unwrap_err(),
                Error::Untrusted
            );
        }
        #[cfg(windows)]
        {
            let path = f.path.to_string_lossy();
            let command = format!("icacls '{path}' /grant '*S-1-5-32-545:(OI)(CI)M'");
            assert!(
                Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
                    .args(["-NoProfile", "-NonInteractive", "-Command", &command])
                    .status()
                    .unwrap()
                    .success()
            );
            assert_eq!(
                acquire_at(&f.path, "sessions.gate", true).unwrap_err(),
                Error::Untrusted
            );
        }
    }
    #[test]
    fn status_has_explicit_safe_failure_outcomes() {
        for error in [
            Error::Busy,
            Error::Interrupted,
            Error::Unavailable,
            Error::Untrusted,
            Error::NeedsRepair,
        ] {
            assert!(!error.to_string().is_empty());
            assert!(serde_json::to_string(&error).is_ok());
        }
    }

    fn interrupted_fixture(f: &Fixture) -> Vec<u8> {
        let install = installation_at(&f.path).unwrap();
        // Synthetic installation record without a public incident ID, matching
        // the legacy shape. No installer/package child is ever started.
        drop(install.begin_transaction().unwrap());
        drop(install);
        std::fs::read(f.path.join("transaction.json")).unwrap()
    }

    #[test]
    fn recovery_legacy_binding_survives_restart_without_clearing_or_authorizing() {
        let Some(f) = Fixture::new() else { return };
        let original = interrupted_fixture(&f);
        let first = recovery::prepare_at(&f.path).unwrap().unwrap();
        assert_eq!(recovery::inspect_at(&f.path).unwrap(), Some(first.clone()));
        recovery::submit_at(&f.path, &first.incident_id).unwrap();
        {
            let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
            assert!(recovery::pending_at(&f.path).unwrap());
        }
        initialize_at(&f.path).unwrap();
        assert_eq!(recovery::prepare_at(&f.path).unwrap(), Some(first));
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        // An intent is not a disposition or a permission to execute. Until the
        // lifecycle/safety consumers are integrated, both old guards still hold.
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
        assert_eq!(no_interruption(&f.path).unwrap_err(), Error::Interrupted);
    }

    #[test]
    fn recovery_changed_evidence_rotates_identity_and_rejects_stale_intent() {
        let Some(f) = Fixture::new() else { return };
        interrupted_fixture(&f);
        let first = recovery::prepare_at(&f.path).unwrap().unwrap();
        recovery::submit_at(&f.path, &first.incident_id).unwrap();
        std::fs::write(
            f.path.join("transaction.json"),
            b"different synthetic journal",
        )
        .unwrap();
        {
            let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
            assert!(!recovery::pending_at(&f.path).unwrap());
        }
        let second = recovery::prepare_at(&f.path).unwrap().unwrap();
        assert_ne!(first.incident_id, second.incident_id);
        assert_eq!(
            recovery::submit_at(&f.path, &first.incident_id).unwrap_err(),
            Error::Interrupted
        );
        let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
        assert!(!recovery::pending_at(&f.path).unwrap());
    }

    #[test]
    fn recovery_no_record_and_busy_gate_never_provision_a_fake_incident() {
        let Some(f) = Fixture::new() else { return };
        assert_eq!(recovery::prepare_at(&f.path).unwrap(), None);
        assert!(!f.path.join("recovery-incident.json").exists());
        interrupted_fixture(&f);
        let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
        assert_eq!(recovery::prepare_at(&f.path).unwrap_err(), Error::Busy);
        assert_eq!(recovery::inspect_at(&f.path).unwrap_err(), Error::Busy);
        assert!(recovery::submit_at(&f.path, "not-an-id").is_err());
        assert!(!f.path.join("recovery-incident.json").exists());
    }

    #[test]
    fn recovery_partial_intent_is_not_approval_and_public_marker_has_no_private_data() {
        let Some(f) = Fixture::new() else { return };
        interrupted_fixture(&f);
        recovery::prepare_at(&f.path).unwrap();
        let public: serde_json::Value =
            serde_json::from_slice(&std::fs::read(f.path.join("recovery-incident.json")).unwrap())
                .unwrap();
        assert_eq!(public.as_object().unwrap().len(), 2);
        assert!(public.get("schema").is_some());
        assert!(public.get("incidentId").is_some());
        for data in [b"{".as_slice(), b"{}".as_slice(), b"\xff".as_slice()] {
            std::fs::write(f.path.join("recovery-acknowledgment.json"), data).unwrap();
            let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
            assert!(!recovery::pending_at(&f.path).unwrap());
        }
    }

    #[test]
    fn recovery_student_probe() {
        let Some(dir) = std::env::var_os("SDE_TEST_RECOVERY_DIR") else {
            return;
        };
        let dir = PathBuf::from(dir);
        #[cfg(unix)]
        assert_eq!(unsafe { libc::geteuid() }, 65534);
        let incident = recovery::inspect_at(&dir).unwrap().unwrap();
        assert!(std::fs::read(dir.join("transaction.json")).is_err());
        assert!(std::fs::read(dir.join("recovery-binding.json")).is_err());
        assert!(std::fs::OpenOptions::new()
            .write(true)
            .open(dir.join("transaction.json"))
            .is_err());
        assert!(std::fs::OpenOptions::new()
            .write(true)
            .open(dir.join("recovery-incident.json"))
            .is_err());
        recovery::submit_at(&dir, &incident.incident_id).unwrap();
        println!("SDE_RECOVERY_PRODUCTION_STUDENT_SUBMISSION_OK");
    }

    #[test]
    fn recovery_real_standard_user_can_submit_through_production_storage() {
        #[cfg(windows)]
        if std::env::var("GITHUB_ACTIONS").as_deref() != Ok("true") {
            assert!(
                std::env::var("SDE_REQUIRE_COORDINATION").as_deref() != Ok("1"),
                "Required Windows account probe needs a disposable CI runner"
            );
            return;
        }
        let Some(f) = Fixture::new() else { return };
        let original = interrupted_fixture(&f);
        recovery::prepare_at(&f.path).unwrap();
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            use std::os::unix::process::CommandExt;
            // The runner checkout's ancestors may be private. Test storage
            // permissions, not incidental access to /home/runner or its cache.
            let binary = f.path.join("student-probe");
            std::fs::copy(std::env::current_exe().unwrap(), &binary).unwrap();
            std::fs::set_permissions(&binary, std::fs::Permissions::from_mode(0o755)).unwrap();
            let mut command = Command::new(binary);
            command
                .args(["--exact", "tests::recovery_student_probe", "--nocapture"])
                .env("SDE_TEST_RECOVERY_DIR", &f.path);
            // Only async-signal-safe syscalls in the forked child. No global
            // process privilege change, account change, or package invocation.
            unsafe {
                command.pre_exec(|| {
                    if libc::setgroups(0, std::ptr::null()) != 0
                        || libc::setgid(65534) != 0
                        || libc::setuid(65534) != 0
                    {
                        return Err(std::io::Error::last_os_error());
                    }
                    Ok(())
                });
            }
            let result = command.output().unwrap();
            assert!(
                result.status.success(),
                "Student storage probe failed: {}",
                String::from_utf8_lossy(&result.stderr)
            );
            assert!(String::from_utf8_lossy(&result.stdout)
                .contains("SDE_RECOVERY_PRODUCTION_STUDENT_SUBMISSION_OK"));
        }
        #[cfg(windows)]
        {
            let script = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
                .join("../tests/Invoke-RecoveryStorageStudentCI.ps1");
            let result = storage_fixture_powershell()
                .arg(script)
                .arg("-FixtureRoot")
                .arg(&f.path)
                .arg("-TestBinary")
                .arg(std::env::current_exe().unwrap())
                .output()
                .unwrap();
            assert!(
                result.status.success(),
                "Windows student storage fixture failed: {}",
                String::from_utf8_lossy(&result.stderr)
            );
            assert!(String::from_utf8_lossy(&result.stdout)
                .contains("SDE_RECOVERY_PRODUCTION_STUDENT_SUBMISSION_OK"));
        }
        let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
        assert!(recovery::pending_at(&f.path).unwrap());
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
    }

    #[test]
    fn recovery_recreated_identical_legacy_bytes_are_a_new_generation() {
        let Some(f) = Fixture::new() else { return };
        let original = interrupted_fixture(&f);
        let first = recovery::prepare_at(&f.path).unwrap().unwrap();
        recovery::submit_at(&f.path, &first.incident_id).unwrap();
        // Fixture-only replacement: model a new old-format record whose PID and
        // bytes are identical. Retain the old object to prevent inode reuse.
        std::fs::rename(
            f.path.join("transaction.json"),
            f.path.join("old-fixture.json"),
        )
        .unwrap();
        assert_eq!(interrupted_fixture(&f), original);
        let second = recovery::prepare_at(&f.path).unwrap().unwrap();
        assert_ne!(first.incident_id, second.incident_id);
        let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
        assert!(!recovery::pending_at(&f.path).unwrap());
    }

    #[cfg(unix)]
    #[test]
    fn recovery_native_storage_rejects_link_and_permission_changes() {
        use std::os::unix::ffi::OsStrExt;
        use std::os::unix::fs::{symlink, PermissionsExt};
        let Some(f) = Fixture::new() else { return };
        let original = interrupted_fixture(&f);
        let incident = recovery::prepare_at(&f.path).unwrap().unwrap();
        let slot = f.path.join("recovery-acknowledgment.json");
        std::fs::set_permissions(&slot, std::fs::Permissions::from_mode(0o644)).unwrap();
        assert_eq!(
            recovery::submit_at(&f.path, &incident.incident_id).unwrap_err(),
            Error::Untrusted
        );
        std::fs::remove_file(&slot).unwrap();
        symlink("transaction.json", &slot).unwrap();
        assert!(recovery::submit_at(&f.path, &incident.incident_id).is_err());
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        std::fs::remove_file(&slot).unwrap();
        let fifo = std::ffi::CString::new(slot.as_os_str().as_bytes()).unwrap();
        assert_eq!(unsafe { libc::mkfifo(fifo.as_ptr(), 0o666) }, 0);
        assert_eq!(
            recovery::submit_at(&f.path, &incident.incident_id).unwrap_err(),
            Error::Untrusted
        );
    }

    #[cfg(windows)]
    #[test]
    fn recovery_rejects_overbroad_intent_rights_and_exposed_private_binding() {
        let Some(f) = Fixture::new() else { return };
        interrupted_fixture(&f);
        let incident = recovery::prepare_at(&f.path).unwrap().unwrap();
        let slot = f.path.join("recovery-acknowledgment.json");
        assert!(Command::new("icacls.exe")
            .arg(&slot)
            .args(["/grant", "*S-1-5-32-545:M"])
            .output()
            .unwrap()
            .status
            .success());
        assert_eq!(
            recovery::submit_at(&f.path, &incident.incident_id).unwrap_err(),
            Error::Untrusted
        );
        let binding = f.path.join("recovery-binding.json");
        assert!(Command::new("icacls.exe")
            .arg(binding)
            .args(["/grant", "*S-1-5-32-545:R"])
            .output()
            .unwrap()
            .status
            .success());
        assert_eq!(recovery::prepare_at(&f.path).unwrap_err(), Error::Untrusted);
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
    }
}
