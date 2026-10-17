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
                "Installed components do not support safe coordination. Mentor review or a compatible update is required."
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
/// Retains installation ownership through postchecks and durable completion.
#[derive(Debug)]
pub struct Installation {
    _admission: Option<Lease>,
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
    session_at(&root())
}
/// Preparation owns O without blocking existing or new sessions.
#[derive(Debug)]
pub struct Preparation {
    operation: Lease,
    directory: PathBuf,
}
/// Admission is closed. Busy session acquisition retains O and A for the caller's
/// bounded wait; dropping this value safely releases both before commitment.
#[derive(Debug)]
pub struct Admission {
    preparation: Preparation,
    admission: Lease,
}
/// Coordination prerequisite only, not full Update Now feature enablement.
/// Platform bootstrap, request, deadline and package-hook validation remain gates.
pub fn prepare_app_only() -> Result<Preparation> {
    let dir = root();
    let preparation = prepare_at(&dir)?;
    compatible_maintenance_marker("# SDE_COORDINATION_ADMISSION_V2")?;
    // Missing admission support is not silently repaired or treated as legacy-safe.
    drop(acquire_at(&dir, "admission.gate", true)?);
    Ok(preparation)
}
fn prepare_at(dir: &Path) -> Result<Preparation> {
    let operation = acquire_at(dir, "operations.gate", false)?;
    no_interruption(dir)?;
    Ok(Preparation {
        operation,
        directory: dir.to_path_buf(),
    })
}
impl Preparation {
    pub fn close_admission(self) -> Result<Admission> {
        let admission = acquire_at(&self.directory, "admission.gate", false)?;
        no_interruption(&self.directory)?;
        Ok(Admission {
            preparation: self,
            admission,
        })
    }
}
impl Admission {
    /// Consuming transition returns ownership on failure, including Busy. No
    /// lease is reacquired and no caller may accidentally lose admission while
    /// polling existing sessions. The future worker must enforce its deadline.
    pub fn try_installation(self) -> std::result::Result<Installation, (Error, Self)> {
        let sessions = match no_interruption(&self.preparation.directory)
            .and_then(|()| acquire_at(&self.preparation.directory, "sessions.gate", false))
        {
            Ok(lease) => lease,
            Err(error) => return Err((error, self)),
        };
        Ok(Installation {
            _operation: self.preparation.operation,
            _admission: Some(self.admission),
            _sessions: sessions,
            directory: self.preparation.directory,
        })
    }
}
fn startup<L>(
    mut intent: impl FnMut() -> Result<()>,
    mut gate: impl FnMut(bool) -> Result<L>,
) -> Result<L> {
    intent()?;
    let admission = gate(true)?;
    intent()?;
    let session = gate(false)?;
    intent()?;
    drop(admission);
    Ok(session)
}
fn session_at(dir: &Path) -> Result<Lease> {
    startup(
        || no_interruption(dir),
        |admission| {
            acquire_at(
                dir,
                if admission {
                    "admission.gate"
                } else {
                    "sessions.gate"
                },
                true,
            )
        },
    )
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
    match idle_at(&root(), compatible_maintenance) {
        Ok(()) => Status::Idle,
        Err(Error::Busy) => Status::Busy,
        Err(Error::Interrupted) => Status::Interrupted,
        Err(Error::Untrusted) => Status::Untrusted,
        Err(Error::NeedsRepair) => Status::NeedsRepair,
        Err(_) => Status::Unavailable,
    }
}

fn idle_at(dir: &Path, compatible: impl FnOnce() -> Result<()>) -> Result<()> {
    let _installation = installation_at(dir)?;
    compatible()
}

/// An older deployed scheduler cannot participate in new locks. Never report
/// installation readiness until its existing entry point has been migrated by
/// an explicit mentor baseline Repair; app installation does not apply a baseline.
fn compatible_maintenance() -> Result<()> {
    compatible_maintenance_marker("# SDE_COORDINATION_V1")
}
fn compatible_maintenance_marker(marker: &str) -> Result<()> {
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
    compatible_maintenance_at(&paths.map(Path::new), marker)
}
fn compatible_maintenance_at(paths: &[&Path; 2], marker: &str) -> Result<()> {
    // lstat distinguishes true absence from a dangling link. A partial deployment
    // is not an application-only machine with no maintenance installation.
    let present = paths.map(|path| match std::fs::symlink_metadata(path) {
        Ok(_) => Ok(true),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(_) => Err(Error::NeedsRepair),
    });
    match (present[0], present[1]) {
        (Ok(false), Ok(false)) => return Ok(()),
        (Ok(true), Ok(true)) => (),
        _ => return Err(Error::NeedsRepair),
    }
    for name in paths {
        let path = *name;
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
        if bytes.len() > 65536 || !has_marker(&bytes, marker) {
            return Err(Error::NeedsRepair);
        }
    }
    Ok(())
}
fn has_marker(bytes: &[u8], marker: &str) -> bool {
    std::str::from_utf8(bytes).is_ok_and(|text| text.lines().any(|line| line == marker))
}

fn no_interruption(dir: &Path) -> Result<()> {
    let entries = std::fs::read_dir(dir).map_err(|_| Error::Unavailable)?;
    for (count, entry) in entries.enumerate() {
        if count > 32 {
            return Err(Error::Untrusted);
        }
        if matches!(
            entry.map_err(|_| Error::Unavailable)?.file_name().to_str(),
            Some("transaction.json" | "installation-scope.json")
        ) {
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
        _admission: None,
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
    for name in ["sessions.gate", "operations.gate", "admission.gate"] {
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
    scope_path: Option<PathBuf>,
}
fn create_intent(path: &Path) -> Result<File> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        if unsafe { libc::geteuid() } != 0 {
            return Err(Error::Untrusted);
        }
        std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .mode(0o600)
            .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC)
            .open(path)
            .map_err(|_| Error::Interrupted)
    }
    #[cfg(windows)]
    {
        windows::journal(path)
    }
}

impl Installation {
    pub fn begin_transaction(&self) -> Result<Transaction<'_>> {
        self.begin_transaction_with_scope(false)
    }
    /// App-only package hooks must preserve maintenance configuration. Only an
    /// admission-owning Installation can publish this scoped transaction.
    pub fn begin_app_only_transaction(&self) -> Result<Transaction<'_>> {
        if self._admission.is_none() {
            return Err(Error::NeedsRepair);
        }
        self.begin_transaction_with_scope(true)
    }
    fn begin_transaction_with_scope(&self, app_only: bool) -> Result<Transaction<'_>> {
        use std::io::Write;
        let path = self.directory.join("transaction.json");
        let mut file = create_intent(&path)?;
        let mut record =
            serde_json::json!({"schema": 1, "pid": std::process::id(), "kind": "installation"});
        if app_only {
            record["scope"] = serde_json::json!("app_only");
        }
        file.write_all(record.to_string().as_bytes())
            .and_then(|_| file.sync_all())
            .map_err(|_| Error::Unavailable)?;
        sync_directory(&self.directory)?;
        #[cfg(windows)]
        let file = windows::seal_journal(file, &path)?;
        // A separate closed hint is readable by packaging even when an older
        // updater retains its legacy exclusive journal handle. No legacy worker
        // publishes this hint. Native launch occurs only after both are durable.
        let scope_path = if app_only {
            let path = self.directory.join("installation-scope.json");
            let mut hint = create_intent(&path)?;
            hint.write_all(br#"{"schema":1,"kind":"installation","scope":"app_only"}"#)
                .and_then(|_| hint.sync_all())
                .map_err(|_| Error::Unavailable)?;
            drop(hint);
            sync_directory(&self.directory)?;
            Some(path)
        } else {
            None
        };
        Ok(Transaction {
            _installation: self,
            file: Some(file),
            path,
            scope_path,
        })
    }
}
impl Transaction<'_> {
    /// Call only after the native installer and all package children end with a
    /// known outcome. Unknown completion must retain the record.
    pub fn complete(mut self) -> Result<()> {
        // Remove the hint first, while the journal still blocks legacy/new
        // workers. A failure must never remove the recovery barrier first.
        if let Some(path) = &self.scope_path {
            std::fs::remove_file(path).map_err(|_| Error::Unavailable)?;
            sync_directory(path.parent().ok_or(Error::Unavailable)?)?;
        }
        let file = self.file.take().ok_or(Error::Unavailable)?;
        // Windows retains a read-only handle after the creation writer is
        // durably flushed. FlushFileBuffers requires write access; there are no
        // subsequent journal writes to flush. Close before terminal deletion.
        #[cfg(not(windows))]
        file.sync_all().map_err(|_| Error::Unavailable)?;
        drop(file);
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
            let guard = FIXTURE_LOCK.lock().unwrap();
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
    fn startup_checks_each_boundary_and_releases_every_temporary_lease() {
        use std::cell::{Cell, RefCell};
        use std::rc::Rc;
        struct Token(Rc<Cell<usize>>);
        impl Drop for Token {
            fn drop(&mut self) {
                self.0.set(self.0.get() - 1);
            }
        }
        for blocked_check in 0..=3 {
            let checks = Cell::new(0);
            let live = Rc::new(Cell::new(0));
            let order = RefCell::new(Vec::new());
            let result = startup(
                || {
                    checks.set(checks.get() + 1);
                    order.borrow_mut().push("I");
                    if checks.get() == blocked_check {
                        Err(Error::Interrupted)
                    } else {
                        Ok(())
                    }
                },
                |admission| {
                    order.borrow_mut().push(if admission { "A" } else { "S" });
                    live.set(live.get() + 1);
                    Ok(Token(live.clone()))
                },
            );
            if blocked_check == 0 {
                assert!(result.is_ok());
                assert_eq!(*order.borrow(), ["I", "A", "I", "S", "I"]);
                assert_eq!(live.get(), 1);
            } else {
                assert!(matches!(result, Err(Error::Interrupted)));
                assert_eq!(checks.get(), blocked_check);
                assert_eq!(live.get(), 0);
            }
            drop(result);
            assert_eq!(live.get(), 0);
        }
    }
    #[test]
    fn startup_propagates_gate_failures_without_admitting_session() {
        for failed_gate in [true, false] {
            let result = startup(
                || Ok(()),
                |admission| {
                    if admission == failed_gate {
                        Err(Error::Busy)
                    } else {
                        Ok(())
                    }
                },
            );
            assert_eq!(result.unwrap_err(), Error::Busy);
        }
    }
    #[test]
    fn admission_retains_ownership_and_intent_blocks_reopen() {
        let Some(f) = Fixture::new() else { return };
        let gui = session_at(&f.path).unwrap();
        let preparation = prepare_at(&f.path).unwrap();
        drop(session_at(&f.path).unwrap()); // preparation permits startup
        let admission = preparation.close_admission().unwrap();
        assert_eq!(session_at(&f.path).unwrap_err(), Error::Busy);
        let (error, admission) = admission.try_installation().unwrap_err();
        assert_eq!(error, Error::Busy);
        assert_eq!(
            acquire_at(&f.path, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        assert_eq!(session_at(&f.path).unwrap_err(), Error::Busy);
        drop(gui);
        let installation = admission.try_installation().unwrap();
        // Package initialization must preserve the live identities/locks.
        initialize_at(&f.path).unwrap();
        assert_eq!(session_at(&f.path).unwrap_err(), Error::Busy);
        drop(installation.begin_transaction().unwrap());
        drop(installation);
        assert_eq!(session_at(&f.path).unwrap_err(), Error::Interrupted);
        assert_eq!(prepare_at(&f.path).unwrap_err(), Error::Interrupted);
    }
    #[test]
    fn admission_deferral_reopens_without_replacing_gates() {
        let Some(f) = Fixture::new() else { return };
        let admission = prepare_at(&f.path).unwrap().close_admission().unwrap();
        drop(admission);
        drop(session_at(&f.path).unwrap());
        drop(prepare_at(&f.path).unwrap());
        std::fs::remove_file(f.path.join("admission.gate")).unwrap();
        assert_eq!(session_at(&f.path).unwrap_err(), Error::Unavailable);
    }
    #[test]
    fn idle_query_retains_both_leases_during_compatibility_check() {
        let Some(f) = Fixture::new() else { return };
        idle_at(&f.path, || {
            assert_eq!(
                acquire_at(&f.path, "operations.gate", false).unwrap_err(),
                Error::Busy
            );
            assert_eq!(
                acquire_at(&f.path, "sessions.gate", true).unwrap_err(),
                Error::Busy
            );
            Ok(())
        })
        .unwrap();
        drop(installation_at(&f.path).unwrap());
    }
    #[test]
    fn maintenance_markers_require_complete_utf8_lines() {
        assert!(has_marker(
            b"#!/bin/sh\n# SDE_COORDINATION_V1\r\n",
            "# SDE_COORDINATION_V1"
        ));
        for bytes in [
            b"echo '# SDE_COORDINATION_V1'".as_slice(),
            b"# SDE_COORDINATION_V10",
            b"# SDE_COORDINATION_V1\xff",
        ] {
            assert!(!has_marker(bytes, "# SDE_COORDINATION_V1"));
        }
    }
    #[test]
    fn partial_or_legacy_maintenance_never_enables_manual_preparation() {
        let Some(f) = Fixture::new() else { return };
        let entry = f.path.join("maintenance");
        let helper = f.path.join("helper");
        let paths = [entry.as_path(), helper.as_path()];
        let v1 = "# SDE_COORDINATION_V1";
        let v2 = "# SDE_COORDINATION_ADMISSION_V2";
        assert!(compatible_maintenance_at(&paths, v2).is_ok());
        // Ordinary Windows file creation assigns the runner's personal SID,
        // which is intentionally not a trusted installed-component owner.
        #[cfg(windows)]
        drop(windows::journal(&helper).unwrap());
        std::fs::write(&helper, v1).unwrap();
        assert_eq!(
            compatible_maintenance_at(&paths, v2),
            Err(Error::NeedsRepair)
        );
        #[cfg(windows)]
        drop(windows::journal(&entry).unwrap());
        std::fs::write(&entry, v1).unwrap();
        assert!(compatible_maintenance_at(&paths, v1).is_ok());
        assert_eq!(
            compatible_maintenance_at(&paths, v2),
            Err(Error::NeedsRepair)
        );
        std::fs::write(&entry, format!("{v1}\n{v2}\n")).unwrap();
        std::fs::write(&helper, format!("{v1}\n{v2}\n")).unwrap();
        assert!(compatible_maintenance_at(&paths, v2).is_ok());
        #[cfg(unix)]
        {
            std::fs::remove_file(&entry).unwrap();
            std::os::unix::fs::symlink("missing", &entry).unwrap();
            assert_eq!(
                compatible_maintenance_at(&paths, v2),
                Err(Error::NeedsRepair)
            );
        }
    }
    #[test]
    fn app_only_intent_requires_admission_and_survives_package_initialization() {
        let Some(f) = Fixture::new() else { return };
        let scheduled = installation_at(&f.path).unwrap();
        assert!(matches!(
            scheduled.begin_app_only_transaction(),
            Err(Error::NeedsRepair)
        ));
        assert!(!f.path.join("transaction.json").exists());
        drop(scheduled);
        let install = prepare_at(&f.path)
            .unwrap()
            .close_admission()
            .unwrap()
            .try_installation()
            .unwrap();
        let transaction = install.begin_app_only_transaction().unwrap();
        let path = f.path.join("transaction.json");
        let before = std::fs::read(&path).unwrap();
        let record: serde_json::Value = serde_json::from_slice(&before).unwrap();
        assert_eq!(record["scope"], "app_only");
        // A separate packaging child initializes while its parent retains O/A/S/I.
        let hook = Command::new(std::env::current_exe().unwrap())
            .args(["--exact", "tests::process_probe", "--nocapture"])
            .env("SDE_TEST_COORDINATION_DIR", &f.path)
            .env("SDE_TEST_COORDINATION_MODE", "initialize")
            .stdin(Stdio::null())
            .output()
            .unwrap();
        assert!(
            hook.status.success(),
            "{}",
            String::from_utf8_lossy(&hook.stderr)
        );
        assert_eq!(std::fs::read(&path).unwrap(), before);
        assert_eq!(
            acquire_at(&f.path, "admission.gate", false).unwrap_err(),
            Error::Busy
        );
        assert_eq!(
            acquire_at(&f.path, "sessions.gate", true).unwrap_err(),
            Error::Busy
        );
        assert_eq!(
            acquire_at(&f.path, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        transaction.complete().unwrap();
        drop(install);
        drop(session_at(&f.path).unwrap());
    }
    #[cfg(windows)]
    #[test]
    fn published_intent_allows_hook_readers_but_rejects_writers_and_deletion() {
        let Some(f) = Fixture::new() else { return };
        let install = installation_at(&f.path).unwrap();
        let transaction = install.begin_transaction().unwrap();
        let path = f.path.join("transaction.json");
        assert!(!std::fs::read(&path).unwrap().is_empty());
        assert!(std::fs::OpenOptions::new()
            .append(true)
            .open(&path)
            .is_err());
        assert!(std::fs::remove_file(&path).is_err());
        transaction.complete().unwrap();
        assert!(!path.exists());
    }
    #[test]
    fn scoped_hint_is_durable_and_clears_before_journal() {
        let Some(f) = Fixture::new() else { return };
        let install = prepare_at(&f.path)
            .unwrap()
            .close_admission()
            .unwrap()
            .try_installation()
            .unwrap();
        let transaction = install.begin_app_only_transaction().unwrap();
        let hint = f.path.join("installation-scope.json");
        let content: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&hint).unwrap()).unwrap();
        assert_eq!(content["scope"], "app_only");
        transaction.complete().unwrap();
        assert!(!hint.exists());
        assert!(!f.path.join("transaction.json").exists());
        let transaction = install.begin_app_only_transaction().unwrap();
        drop(transaction);
        drop(install);
        assert!(hint.exists());
        assert_eq!(session_at(&f.path).unwrap_err(), Error::Interrupted);
        // A retained/orphan hint is itself a startup barrier.
        std::fs::remove_file(f.path.join("transaction.json")).unwrap();
        assert_eq!(session_at(&f.path).unwrap_err(), Error::Interrupted);
    }
    #[test]
    fn failed_scoped_hint_cleanup_retains_journal() {
        let Some(f) = Fixture::new() else { return };
        let install = prepare_at(&f.path)
            .unwrap()
            .close_admission()
            .unwrap()
            .try_installation()
            .unwrap();
        let transaction = install.begin_app_only_transaction().unwrap();
        let hint = f.path.join("installation-scope.json");
        std::fs::remove_file(&hint).unwrap();
        std::fs::create_dir(&hint).unwrap();
        assert!(transaction.complete().is_err());
        assert!(f.path.join("transaction.json").exists());
    }
    #[test]
    fn process_probe() {
        let Some(dir) = std::env::var_os("SDE_TEST_COORDINATION_DIR") else {
            return;
        };
        let dir = PathBuf::from(dir);
        let mode = std::env::var("SDE_TEST_COORDINATION_MODE").unwrap();
        let _lease = if mode == "initialize" {
            initialize_at(&dir).unwrap();
            None
        } else if mode == "session" {
            Some(acquire_at(&dir, "sessions.gate", true).unwrap())
        } else {
            Some(acquire_at(&dir, "operations.gate", false).unwrap())
        };
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
}
