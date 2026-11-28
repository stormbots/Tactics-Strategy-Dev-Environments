//! Read-only observations of an existing per-account location record.
//! No directory creation, repair, defaults, Save or operation authority.
use super::{decode, Platform, References, MAX_BYTES};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, Metadata, OpenOptions},
    io::Read,
    path::Path,
};

pub const FILE_NAME: &str = "references.json";

#[derive(Debug, PartialEq, Eq)]
pub enum Unavailable {
    NormalUserRequired,
    UnsupportedPath,
    Storage,
    InvalidRecord,
    Changed,
}

#[derive(Debug)]
pub struct Snapshot {
    references: References,
    fingerprint: String,
}

impl Snapshot {
    pub fn references(&self) -> &References {
        &self.references
    }

    /// Local comparison evidence only, never a native execution or Save permit.
    /// Callers must read again and inspect the selected folders before use.
    pub fn fingerprint(&self) -> &str {
        &self.fingerprint
    }
}

#[derive(Debug)]
pub enum Observation {
    /// Only the fixed file was absent inside a verified existing directory.
    Absent,
    Saved(Snapshot),
    Unavailable(Unavailable),
}

/// The caller supplies a fixed application-owned per-user directory, never an
/// arbitrary path from IPC or a saved preference. The directory must already
/// exist. A missing directory is unavailable, not proof of an absent record.
/// This API never provisions storage, opens project folders or runs a command.
pub fn observe(directory: &Path) -> Observation {
    if !platform::ordinary_user() {
        return Observation::Unavailable(Unavailable::NormalUserRequired);
    }
    match read_existing(directory) {
        Ok(value) => value,
        Err(reason) => Observation::Unavailable(reason),
    }
}

fn current_platform() -> Platform {
    #[cfg(windows)]
    return Platform::Windows;
    #[cfg(target_os = "linux")]
    Platform::Linux
}

fn ancestors(directory: &Path) -> Result<(), Unavailable> {
    let value = directory.to_str().ok_or(Unavailable::UnsupportedPath)?;
    if !super::path(value, current_platform()) {
        return Err(Unavailable::UnsupportedPath);
    }
    for part in directory.ancestors() {
        let metadata = fs::symlink_metadata(part).map_err(|_| Unavailable::Storage)?;
        if !metadata.is_dir() || metadata.file_type().is_symlink() || platform::linked(&metadata) {
            return Err(Unavailable::Storage);
        }
        platform::parent(part, &metadata)?;
    }
    Ok(())
}

fn directory_identity(directory: &Path) -> Result<String, Unavailable> {
    ancestors(directory)?;
    let file = platform::open(directory, true).map_err(|_| Unavailable::Storage)?;
    platform::private(&file)?;
    platform::identity(&file)
}

fn read_existing(directory: &Path) -> Result<Observation, Unavailable> {
    let before_directory = directory_identity(directory)?;
    // Retain the directory handle throughout the read. On Windows it denies
    // deletion/rename; on Linux the explicit identity comparison detects change.
    let directory_handle = platform::open(directory, true).map_err(|_| Unavailable::Storage)?;
    platform::private(&directory_handle)?;
    if platform::identity(&directory_handle)? != before_directory {
        return Err(Unavailable::Changed);
    }
    let path = directory.join(FILE_NAME);
    let file = match platform::open(&path, false) {
        Ok(file) => file,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            if !matches!(fs::symlink_metadata(&path), Err(error) if error.kind() == std::io::ErrorKind::NotFound)
            {
                return Err(Unavailable::Changed);
            }
            if directory_identity(directory)? != before_directory {
                return Err(Unavailable::Changed);
            }
            return Ok(Observation::Absent);
        }
        Err(_) => return Err(Unavailable::Storage),
    };
    platform::private(&file)?;
    let before_file = platform::identity(&file)?;
    let mut bytes = Vec::new();
    (&file)
        .take(MAX_BYTES as u64 + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| Unavailable::Storage)?;
    let references = decode(&bytes, current_platform()).map_err(|_| Unavailable::InvalidRecord)?;
    platform::private(&file)?;
    // Re-open the fixed name to catch atomic replacement, including replacement
    // with identical bytes/revision. Neither content nor revision alone suffices.
    let current = platform::open(&path, false).map_err(|_| Unavailable::Changed)?;
    platform::private(&current)?;
    if before_file != platform::identity(&file)?
        || before_file != platform::identity(&current)?
        || before_directory != directory_identity(directory)?
    {
        return Err(Unavailable::Changed);
    }
    let mut hash = Sha256::new();
    hash.update(b"sde-project-reference-observation-v1\0");
    hash.update(before_directory.as_bytes());
    hash.update(b"\0");
    hash.update(before_file.as_bytes());
    hash.update(b"\0");
    hash.update(&bytes);
    Ok(Observation::Saved(Snapshot {
        references,
        fingerprint: format!("{:x}", hash.finalize()),
    }))
}

#[cfg(target_os = "linux")]
mod platform {
    use super::*;
    use std::os::unix::fs::{MetadataExt, OpenOptionsExt};

    pub(super) fn ordinary_user() -> bool {
        unsafe { libc::geteuid() != 0 && libc::getuid() == libc::geteuid() }
    }
    pub(super) fn linked(_: &Metadata) -> bool {
        false
    }
    pub(super) fn parent(_: &Path, metadata: &Metadata) -> Result<(), Unavailable> {
        // Root-owned sticky ancestors (notably /tmp) cannot allow other users
        // to replace our owned child. Other writable ancestors are unsupported.
        let sticky_root = metadata.uid() == 0 && metadata.mode() & libc::S_ISVTX != 0;
        if (metadata.uid() != unsafe { libc::geteuid() } && metadata.uid() != 0)
            || (metadata.mode() & 0o022 != 0 && !sticky_root)
        {
            return Err(Unavailable::Storage);
        }
        Ok(())
    }
    pub(super) fn open(path: &Path, directory: bool) -> std::io::Result<File> {
        let mut options = OpenOptions::new();
        options.read(true).custom_flags(
            libc::O_NOFOLLOW
                | libc::O_CLOEXEC
                | libc::O_NONBLOCK
                | if directory { libc::O_DIRECTORY } else { 0 },
        );
        options.open(path)
    }
    pub(super) fn private(file: &File) -> Result<(), Unavailable> {
        let metadata = file.metadata().map_err(|_| Unavailable::Storage)?;
        if !(metadata.is_dir() || metadata.is_file())
            || metadata.uid() != unsafe { libc::geteuid() }
            || metadata.mode() & 0o077 != 0
            || (metadata.is_file() && metadata.nlink() != 1)
        {
            return Err(Unavailable::Storage);
        }
        Ok(())
    }
    pub(super) fn identity(file: &File) -> Result<String, Unavailable> {
        let m = file.metadata().map_err(|_| Unavailable::Storage)?;
        // Directory timestamps change for unrelated siblings. Directory identity
        // uses its object, owner and permissions; file identity includes times.
        let change = if m.is_dir() {
            String::new()
        } else {
            format!(
                ":{}:{}:{}:{}:{}",
                m.len(),
                m.mtime(),
                m.mtime_nsec(),
                m.ctime(),
                m.ctime_nsec()
            )
        };
        Ok(format!(
            "{}:{}:{}:{}{}",
            m.dev(),
            m.ino(),
            m.uid(),
            m.mode(),
            change
        ))
    }
}

#[cfg(windows)]
#[path = "store_windows.rs"]
mod platform;

#[cfg(test)]
mod tests {
    use super::*;

    struct Fixture {
        _root: tempfile::TempDir,
        directory: std::path::PathBuf,
    }

    impl Fixture {
        fn new() -> Self {
            let root = tempfile::tempdir().unwrap();
            let root_path = root.path().canonicalize().unwrap();
            #[cfg(windows)]
            let root_path =
                std::path::PathBuf::from(root_path.to_str().unwrap().trim_start_matches(r"\\?\"));
            secure(&root_path, true, false);
            let directory = root_path.join("project-locations");
            fs::create_dir(&directory).unwrap();
            secure(&directory, true, false);
            Self {
                _root: root,
                directory,
            }
        }
        fn write(&self, bytes: &[u8]) {
            let path = self.directory.join(FILE_NAME);
            fs::write(&path, bytes).unwrap();
            secure(&path, false, false);
        }
        fn bytes(&self) -> Vec<u8> {
            let workspace = if cfg!(windows) {
                r"D:\Disconnected School Drive"
            } else {
                "/unmounted/School Drive"
            };
            serde_json::to_vec(&serde_json::json!({"schema":1,"platform":if cfg!(windows) {"windows"} else {"linux"},
                "revision":1,"workspace":workspace,"projects":[]})).unwrap()
        }
        fn saved(&self) -> Snapshot {
            // Test the actual file checks even on administrator/root CI hosts.
            // The public ordinary-account guard is tested separately below.
            match read_existing(&self.directory).unwrap() {
                Observation::Saved(snapshot) => snapshot,
                other => panic!("Expected Saved, got {other:?}"),
            }
        }
    }

    #[cfg(target_os = "linux")]
    fn secure(path: &Path, directory: bool, public: bool) {
        use std::os::unix::fs::PermissionsExt;
        let mode = if directory {
            if public {
                0o755
            } else {
                0o700
            }
        } else if public {
            0o644
        } else {
            0o600
        };
        fs::set_permissions(path, fs::Permissions::from_mode(mode)).unwrap();
    }

    #[cfg(windows)]
    fn secure(path: &Path, directory: bool, public: bool) {
        // Fixed fixture-only script; the path travels as environment data.
        // Explicit current-SID ownership also covers administrator CI tokens,
        // whose default object owner can otherwise be Administrators.
        let script = r#"
$ErrorActionPreference='Stop'
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$acl=if($env:SDE_REFERENCE_TEST_DIRECTORY -eq '1'){New-Object Security.AccessControl.DirectorySecurity}else{New-Object Security.AccessControl.FileSecurity}
$acl.SetOwner($sid)
$acl.SetAccessRuleProtection($true,$false)
foreach($id in @($sid.Value,'S-1-5-18','S-1-5-32-544')){
  $identity=New-Object Security.Principal.SecurityIdentifier($id)
  $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($identity,'FullControl','Allow')))
}
if($env:SDE_REFERENCE_TEST_PUBLIC -eq '1'){
  $everyone=New-Object Security.Principal.SecurityIdentifier('S-1-1-0')
  $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule($everyone,'ReadAndExecute','Allow')))
}
Set-Acl -LiteralPath $env:SDE_REFERENCE_TEST_PATH -AclObject $acl
"#;
        let output = std::process::Command::new(
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        )
        .args(["-NoProfile", "-NonInteractive", "-Command", script])
        .env("SDE_REFERENCE_TEST_PATH", path)
        .env(
            "SDE_REFERENCE_TEST_DIRECTORY",
            if directory { "1" } else { "0" },
        )
        .env("SDE_REFERENCE_TEST_PUBLIC", if public { "1" } else { "0" })
        .output()
        .unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
    }

    #[test]
    fn absent_record_and_unavailable_directory_are_distinct_and_never_created() {
        let f = Fixture::new();
        assert!(matches!(
            read_existing(&f.directory),
            Ok(Observation::Absent)
        ));
        assert_eq!(fs::read_dir(&f.directory).unwrap().count(), 0);
        let missing = f.directory.join("absent");
        assert!(matches!(read_existing(&missing), Err(Unavailable::Storage)));
        assert!(!missing.exists());
        let path = f.directory.join(FILE_NAME);
        fs::create_dir(&path).unwrap();
        secure(&path, true, false);
        assert!(read_existing(&f.directory).is_err());
        assert!(path.is_dir());
    }

    #[test]
    fn public_reader_refuses_elevation_without_touching_storage() {
        let f = Fixture::new();
        let observation = observe(&f.directory);
        if platform::ordinary_user() {
            assert!(matches!(observation, Observation::Absent));
        } else {
            assert!(matches!(
                observation,
                Observation::Unavailable(Unavailable::NormalUserRequired)
            ));
        }
        assert_eq!(fs::read_dir(&f.directory).unwrap().count(), 0);
    }

    #[test]
    fn valid_reference_retains_unavailable_path_and_stable_local_fingerprint() {
        let f = Fixture::new();
        let bytes = f.bytes();
        f.write(&bytes);
        let a = f.saved();
        let b = f.saved();
        assert_eq!(a.references().revision(), 1);
        assert!(a.references().workspace().contains("School Drive"));
        assert_eq!(a.fingerprint(), b.fingerprint());
        assert_eq!(a.fingerprint().len(), 64);
        assert_eq!(fs::read(f.directory.join(FILE_NAME)).unwrap(), bytes);
        assert_eq!(fs::read_dir(&f.directory).unwrap().count(), 1);
    }

    #[test]
    fn malformed_and_oversized_records_stay_unavailable_and_unchanged() {
        let f = Fixture::new();
        for bytes in [
            b"not json".to_vec(),
            vec![b' '; MAX_BYTES + 1],
            b"{}".to_vec(),
            b"\xff".to_vec(),
        ] {
            f.write(&bytes);
            assert!(matches!(
                read_existing(&f.directory),
                Err(Unavailable::InvalidRecord)
            ));
            assert_eq!(fs::read(f.directory.join(FILE_NAME)).unwrap(), bytes);
        }
    }

    #[test]
    fn unsafe_file_or_directory_permissions_are_not_repaired_or_defaulted() {
        let f = Fixture::new();
        let bytes = f.bytes();
        f.write(&bytes);
        let path = f.directory.join(FILE_NAME);
        secure(&path, false, true);
        assert!(matches!(
            read_existing(&f.directory),
            Err(Unavailable::Storage)
        ));
        assert_eq!(fs::read(&path).unwrap(), bytes);
        secure(&path, false, false);
        secure(&f.directory, true, true);
        assert!(matches!(
            read_existing(&f.directory),
            Err(Unavailable::Storage)
        ));
        assert_eq!(fs::read(path).unwrap(), bytes);
    }

    #[test]
    fn hardlinked_record_is_unavailable_and_both_names_are_preserved() {
        let f = Fixture::new();
        let bytes = f.bytes();
        f.write(&bytes);
        let original = f.directory.join(FILE_NAME);
        let link = f.directory.join("another-name.json");
        fs::hard_link(&original, &link).unwrap();
        assert!(matches!(
            read_existing(&f.directory),
            Err(Unavailable::Storage)
        ));
        assert_eq!(fs::read(original).unwrap(), bytes);
        assert_eq!(fs::read(link).unwrap(), bytes);
    }

    #[test]
    fn identical_replacement_record_changes_fingerprint_without_changing_revision() {
        let f = Fixture::new();
        let bytes = f.bytes();
        f.write(&bytes);
        let before = f.saved();
        fs::rename(
            f.directory.join(FILE_NAME),
            f.directory.join("retained-original.json"),
        )
        .unwrap();
        f.write(&bytes);
        let after = f.saved();
        assert_eq!(
            before.references().revision(),
            after.references().revision()
        );
        assert_ne!(before.fingerprint(), after.fingerprint());
        assert_eq!(
            fs::read(f.directory.join("retained-original.json")).unwrap(),
            bytes
        );
    }

    #[test]
    fn replaced_directory_changes_fingerprint_even_with_identical_record() {
        let f = Fixture::new();
        let bytes = f.bytes();
        f.write(&bytes);
        let before = f.saved();
        let retained = f.directory.with_file_name("retained-directory");
        fs::rename(&f.directory, &retained).unwrap();
        fs::create_dir(&f.directory).unwrap();
        secure(&f.directory, true, false);
        f.write(&bytes);
        assert_ne!(before.fingerprint(), f.saved().fingerprint());
        assert_eq!(fs::read(retained.join(FILE_NAME)).unwrap(), bytes);
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn linked_ancestors_linked_records_and_fifos_never_become_saved_or_absent() {
        use std::{
            ffi::CString,
            os::unix::{ffi::OsStrExt, fs::symlink},
        };
        let f = Fixture::new();
        let bytes = f.bytes();
        f.write(&bytes);
        let alias = f.directory.with_file_name("linked-directory");
        symlink(&f.directory, &alias).unwrap();
        assert!(matches!(read_existing(&alias), Err(Unavailable::Storage)));
        let record = f.directory.join(FILE_NAME);
        let original = f.directory.join("retained.json");
        fs::rename(&record, &original).unwrap();
        symlink(&original, &record).unwrap();
        assert!(matches!(
            read_existing(&f.directory),
            Err(Unavailable::Storage)
        ));
        fs::remove_file(&record).unwrap();
        let name = CString::new(record.as_os_str().as_bytes()).unwrap();
        assert_eq!(unsafe { libc::mkfifo(name.as_ptr(), 0o600) }, 0);
        assert!(matches!(
            read_existing(&f.directory),
            Err(Unavailable::Storage)
        ));
        assert_eq!(fs::read(original).unwrap(), bytes);
    }

    #[cfg(windows)]
    #[test]
    fn junction_directory_is_unavailable_and_target_is_preserved() {
        let f = Fixture::new();
        let bytes = f.bytes();
        f.write(&bytes);
        let alias = f.directory.with_file_name("junction");
        let output = std::process::Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
            .args(["-NoProfile", "-NonInteractive", "-Command", "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:SDE_REFERENCE_TEST_ALIAS -Target $env:SDE_REFERENCE_TEST_TARGET | Out-Null"])
            .env("SDE_REFERENCE_TEST_ALIAS", &alias).env("SDE_REFERENCE_TEST_TARGET", &f.directory)
            .output().unwrap();
        assert!(
            output.status.success(),
            "{}",
            String::from_utf8_lossy(&output.stderr)
        );
        assert!(matches!(read_existing(&alias), Err(Unavailable::Storage)));
        assert_eq!(fs::read(f.directory.join(FILE_NAME)).unwrap(), bytes);
        // Remove only the junction; recursive fixture cleanup keeps its target.
        fs::remove_dir(alias).unwrap();
    }

    #[cfg(target_os = "linux")]
    #[test]
    fn root_fixture_refuses_foreign_owned_record_without_repair() {
        if unsafe { libc::geteuid() } != 0 {
            return; // The existing root-owned trust job exercises this fixture.
        }
        use std::{
            ffi::CString,
            os::unix::{ffi::OsStrExt, fs::MetadataExt},
        };
        let f = Fixture::new();
        let bytes = f.bytes();
        f.write(&bytes);
        let path = f.directory.join(FILE_NAME);
        let name = CString::new(path.as_os_str().as_bytes()).unwrap();
        assert_eq!(unsafe { libc::chown(name.as_ptr(), 65534, 65534) }, 0);
        assert!(matches!(
            read_existing(&f.directory),
            Err(Unavailable::Storage)
        ));
        assert_eq!(fs::metadata(&path).unwrap().uid(), 65534);
        assert_eq!(fs::read(path).unwrap(), bytes);
    }
}
