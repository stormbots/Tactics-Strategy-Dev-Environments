//! Read-only, handle-owned gates. A lease grants no elevation or command authority.
use serde::Serialize;
use std::{
    fs::File,
    path::{Path, PathBuf},
};
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

    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Option<Self> {
            #[cfg(unix)]
            if unsafe { libc::geteuid() } != 0 {
                assert!(
                    std::env::var_os("SDE_REQUIRE_COORDINATION").is_none(),
                    "Root-owned coordination tests must run as root"
                );
                return None;
            }
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
            Some(Self(path))
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            std::fs::remove_dir_all(&self.0).unwrap();
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
        let mut gui = child(&f.0, "session");
        let second_gui = acquire_at(&f.0, "sessions.gate", true).unwrap();
        assert_eq!(installation_at(&f.0).unwrap_err(), Error::Busy);
        // Failed second-gate acquisition must release the first gate.
        drop(acquire_at(&f.0, "operations.gate", false).unwrap());
        drop(second_gui);
        gui.kill().unwrap();
        gui.wait().unwrap();
        let installation = installation_at(&f.0).unwrap();
        assert_eq!(
            acquire_at(&f.0, "sessions.gate", true).unwrap_err(),
            Error::Busy
        );
        assert_eq!(
            acquire_at(&f.0, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        drop(installation);
        let mut backend = child(&f.0, "operation");
        assert_eq!(installation_at(&f.0).unwrap_err(), Error::Busy);
        assert_eq!(
            acquire_at(&f.0, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        backend.kill().unwrap();
        backend.wait().unwrap();
        drop(installation_at(&f.0).unwrap()); // OS releases handles after abrupt exit.
    }
    #[test]
    fn durable_installation_intent_and_bootstrap_preserve_live_gates() {
        let Some(f) = Fixture::new() else { return };
        let install = installation_at(&f.0).unwrap();
        initialize_at(&f.0).unwrap();
        assert_eq!(
            acquire_at(&f.0, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        let transaction = install.begin_transaction().unwrap();
        transaction.complete().unwrap();
        assert!(!f.0.join("transaction.json").exists());
        let transaction = install.begin_transaction().unwrap();
        drop(transaction);
        drop(install);
        assert_eq!(installation_at(&f.0).unwrap_err(), Error::Interrupted);
    }

    #[test]
    fn interrupted_record_blocks_even_with_free_kernel_gates() {
        let Some(f) = Fixture::new() else { return };
        std::fs::write(
            f.0.join("transaction.json"),
            b"not instructions; stale or malformed state",
        )
        .unwrap();
        assert_eq!(installation_at(&f.0).unwrap_err(), Error::Interrupted);
        drop(acquire_at(&f.0, "operations.gate", false).unwrap());
        // Initialization/reboot-style reopening must never delete a journal or
        // replace the lock inode to make an interrupted transaction look idle.
        initialize_at(&f.0).unwrap();
        assert_eq!(installation_at(&f.0).unwrap_err(), Error::Interrupted);
    }
    #[test]
    fn native_storage_rejects_links_writable_gates_and_untrusted_directories() {
        let Some(f) = Fixture::new() else { return };
        #[cfg(unix)]
        {
            use std::os::unix::fs::{symlink, PermissionsExt};
            let gate = f.0.join("operations.gate");
            std::fs::set_permissions(&gate, std::fs::Permissions::from_mode(0o644)).unwrap();
            assert_eq!(
                acquire_at(&f.0, "operations.gate", false).unwrap_err(),
                Error::Untrusted
            );
            std::fs::set_permissions(&gate, std::fs::Permissions::from_mode(0o444)).unwrap();
            std::fs::hard_link(&gate, f.0.join("alias")).unwrap();
            assert_eq!(
                acquire_at(&f.0, "operations.gate", false).unwrap_err(),
                Error::Untrusted
            );
            std::fs::remove_file(f.0.join("alias")).unwrap();
            std::fs::remove_file(&gate).unwrap();
            symlink("sessions.gate", &gate).unwrap();
            assert!(acquire_at(&f.0, "operations.gate", false).is_err());
            std::fs::set_permissions(&f.0, std::fs::Permissions::from_mode(0o777)).unwrap();
            assert_eq!(
                acquire_at(&f.0, "sessions.gate", true).unwrap_err(),
                Error::Untrusted
            );
        }
        #[cfg(windows)]
        {
            let path = f.0.to_string_lossy();
            let command = format!("icacls '{path}' /grant '*S-1-5-32-545:(OI)(CI)M'");
            assert!(
                Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
                    .args(["-NoProfile", "-NonInteractive", "-Command", &command])
                    .status()
                    .unwrap()
                    .success()
            );
            assert_eq!(
                acquire_at(&f.0, "sessions.gate", true).unwrap_err(),
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
}
