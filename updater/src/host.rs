//! Fixed native package identity and administrator-controlled storage.
use crate::discovery::{Failure, Result};
#[cfg(not(windows))]
use std::fs::OpenOptions;
use std::{
    fs::File,
    path::{Path, PathBuf},
};

pub struct Installed {
    pub version: String,
    pub platform: &'static str,
}
fn version(value: &str) -> Result<String> {
    let parsed = semver::Version::parse(value).map_err(|_| Failure::InvalidInstalled)?;
    if !parsed.pre.is_empty() || !parsed.build.is_empty() || parsed.to_string() != value {
        return Err(Failure::InvalidInstalled);
    }
    Ok(value.into())
}
#[cfg(target_os = "linux")]
pub fn installed() -> Result<Installed> {
    if std::env::consts::ARCH != "x86_64" {
        return Err(Failure::Unsupported);
    }
    let os = std::fs::read_to_string("/etc/os-release").map_err(|_| Failure::Unsupported)?;
    if !mint_supported(&os) {
        return Err(Failure::Unsupported);
    }
    let mut command = std::process::Command::new("/usr/bin/dpkg-query");
    command
        .env_clear()
        .env("PATH", "/usr/bin:/bin")
        .env("LC_ALL", "C")
        .args([
            "-W",
            "-f=${db:Status-Status}\n${Version}\n${Architecture}\n",
            "skyview-dev-setup",
        ]);
    let output = bounded_command(command)?;
    let lines: Vec<_> = output.lines().collect();
    if lines.len() != 3 || lines[0] != "installed" || lines[2] != "amd64" {
        return Err(Failure::InvalidInstalled);
    }
    Ok(Installed {
        version: version(lines[1])?,
        platform: "linux-amd64",
    })
}
#[cfg(target_os = "linux")]
fn mint_supported(os: &str) -> bool {
    let field = |name: &str| {
        os.lines()
            .find_map(|line| line.strip_prefix(name))
            .map(|v| v.trim_matches('"'))
    };
    field("ID=") == Some("linuxmint")
        && field("VERSION_ID=").is_some_and(|v| {
            v == "22"
                || v.strip_prefix("22.").is_some_and(|minor| {
                    !minor.is_empty() && minor.bytes().all(|c| c.is_ascii_digit())
                })
        })
}
#[cfg(target_os = "linux")]
fn bounded_command(mut command: std::process::Command) -> Result<String> {
    use std::{
        io::Read,
        process::Stdio,
        time::{Duration, Instant},
    };
    command.stdout(Stdio::piped()).stderr(Stdio::null());
    let mut child = command.spawn().map_err(|_| Failure::InvalidInstalled)?;
    let mut stdout = child.stdout.take().ok_or(Failure::InvalidInstalled)?;
    let reader = std::thread::spawn(move || {
        let mut bytes = Vec::new();
        stdout
            .by_ref()
            .take(4097)
            .read_to_end(&mut bytes)
            .map(|_| bytes)
    });
    let deadline = Instant::now() + Duration::from_secs(10);
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                let bytes = reader
                    .join()
                    .map_err(|_| Failure::InvalidInstalled)?
                    .map_err(|_| Failure::InvalidInstalled)?;
                if !status.success() || bytes.len() > 4096 {
                    return Err(Failure::InvalidInstalled);
                }
                return String::from_utf8(bytes).map_err(|_| Failure::InvalidInstalled);
            }
            Ok(None) if Instant::now() < deadline => std::thread::sleep(Duration::from_millis(20)),
            _ => {
                let _ = child.kill();
                let _ = child.wait();
                let _ = reader.join();
                return Err(Failure::InvalidInstalled);
            }
        }
    }
}
#[cfg(windows)]
pub fn installed() -> Result<Installed> {
    windows::installed()
}
#[cfg(not(any(target_os = "linux", windows)))]
pub fn installed() -> Result<Installed> {
    Err(Failure::Unsupported)
}

#[cfg(target_os = "linux")]
pub(crate) fn validate(path: &Path) -> Result<()> {
    use std::os::unix::fs::MetadataExt;
    let metadata = std::fs::symlink_metadata(path).map_err(|_| Failure::Staging)?;
    if metadata.file_type().is_symlink()
        || metadata.uid() != 0
        || metadata.mode() & 0o022 != 0
        || !(metadata.is_dir() || metadata.is_file())
    {
        return Err(Failure::Staging);
    }
    Ok(())
}
#[cfg(windows)]
pub(crate) fn validate(path: &Path) -> Result<()> {
    windows::validate(path)
}
#[cfg(not(any(target_os = "linux", windows)))]
pub(crate) fn validate(_: &Path) -> Result<()> {
    Err(Failure::Unsupported)
}

pub(crate) fn create_private(path: &Path) -> Result<()> {
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::fs::DirBuilderExt;
        std::fs::DirBuilder::new()
            .mode(0o700)
            .create(path)
            .map_err(|_| Failure::Staging)?;
    }
    #[cfg(windows)]
    {
        windows::create_private(path)?;
    }
    #[cfg(not(any(target_os = "linux", windows)))]
    {
        let _ = path;
        return Err(Failure::Unsupported);
    }
    validate(path)
}
pub(crate) fn exclusive(path: &Path) -> Result<File> {
    #[cfg(windows)]
    {
        windows::exclusive(path)
    }
    #[cfg(not(windows))]
    {
        let mut options = OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(target_os = "linux")]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options
                .mode(0o600)
                .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC);
        }
        let file = options.open(path).map_err(|_| Failure::Staging)?;
        validate(path)?;
        Ok(file)
    }
}
pub(crate) fn store() -> Result<PathBuf> {
    #[cfg(target_os = "linux")]
    {
        if unsafe { libc::geteuid() } != 0 {
            return Err(Failure::Staging);
        }
        for parent in ["/", "/var", "/var/lib"] {
            validate(Path::new(parent))?;
        }
        let mut path = PathBuf::from("/var/lib");
        for child in ["skyview-robotics", "self-update", "staging"] {
            path.push(child);
            if !path.try_exists().map_err(|_| Failure::Staging)? {
                create_private(&path)?;
            }
            validate(&path)?;
        }
        Ok(path)
    }
    #[cfg(windows)]
    {
        windows::store()
    }
    #[cfg(not(any(target_os = "linux", windows)))]
    {
        Err(Failure::Unsupported)
    }
}
#[cfg(windows)]
pub(crate) mod windows {
    use super::*;
    use std::{
        ffi::c_void,
        os::windows::{ffi::OsStrExt, fs::MetadataExt},
        ptr,
    };
    use windows_sys::Win32::{
        Foundation::*,
        Security::{Authorization::*, *},
        Storage::FileSystem::*,
        System::{Registry::*, Threading::*},
    };
    fn wide(value: impl AsRef<std::ffi::OsStr>) -> Vec<u16> {
        value.as_ref().encode_wide().chain(Some(0)).collect()
    }
    fn sid(kind: WELL_KNOWN_SID_TYPE) -> Result<Vec<u32>> {
        let mut buffer = vec![0u32; 17];
        let mut size = 68;
        if unsafe {
            CreateWellKnownSid(kind, ptr::null_mut(), buffer.as_mut_ptr().cast(), &mut size)
        } == 0
        {
            return Err(Failure::Staging);
        }
        Ok(buffer)
    }
    fn sid_from_string(value: &str) -> Result<Vec<u32>> {
        let mut raw = ptr::null_mut();
        if unsafe { ConvertStringSidToSidW(wide(value).as_ptr(), &mut raw) } == 0 {
            return Err(Failure::Staging);
        }
        let bytes = unsafe { GetLengthSid(raw) } as usize;
        let mut result = vec![0u32; bytes.div_ceil(4)];
        unsafe {
            ptr::copy_nonoverlapping(raw.cast::<u8>(), result.as_mut_ptr().cast::<u8>(), bytes);
            LocalFree(raw);
        }
        Ok(result)
    }
    fn trusted(value: PSID, system: &[u32], admins: &[u32]) -> bool {
        !value.is_null()
            && unsafe {
                EqualSid(value, system.as_ptr() as PSID) != 0
                    || EqualSid(value, admins.as_ptr() as PSID) != 0
            }
    }
    pub(super) fn validate(path: &Path) -> Result<()> {
        validate_acl(path, false)
    }
    pub(crate) fn validate_acl(path: &Path, anchor: bool) -> Result<()> {
        let info = std::fs::symlink_metadata(path).map_err(|_| Failure::Staging)?;
        if info.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0
            || !(info.is_dir() || info.is_file())
        {
            return Err(Failure::Staging);
        }
        let name = wide(path);
        let mut owner = ptr::null_mut();
        let mut acl: *mut ACL = ptr::null_mut();
        let mut descriptor = ptr::null_mut();
        let status = unsafe {
            GetNamedSecurityInfoW(
                name.as_ptr(),
                SE_FILE_OBJECT,
                OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
                &mut owner,
                ptr::null_mut(),
                &mut acl,
                ptr::null_mut(),
                &mut descriptor,
            )
        };
        if status != ERROR_SUCCESS {
            return Err(Failure::Staging);
        }
        // Windows inherits TrustedInstaller control onto Program Files
        // directories. This does not relax user-write checks or private stores.
        let installed_directory = info.is_dir()
            && path.is_absolute()
            && path.starts_with(r"C:\Program Files")
            && !path
                .components()
                .any(|c| matches!(c, std::path::Component::ParentDir));
        let result = check_acl(owner, acl, anchor, anchor || installed_directory);
        unsafe {
            LocalFree(descriptor);
        }
        result
    }
    fn check_acl(owner: PSID, acl: *mut ACL, anchor: bool, allow_servicing: bool) -> Result<()> {
        let system = sid(WinLocalSystemSid)?;
        let admins = sid(WinBuiltinAdministratorsSid)?;
        // Servicing is limited to platform anchors and installed directories;
        // executable files and private state keep administrator/SYSTEM rules.
        let servicing =
            sid_from_string("S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464")?;
        let trusted_here = |value: PSID| {
            trusted(value, &system, &admins)
                || (allow_servicing
                    && !value.is_null()
                    && unsafe { EqualSid(value, servicing.as_ptr() as PSID) != 0 })
        };
        if !trusted_here(owner) || acl.is_null() {
            #[cfg(test)]
            eprintln!(
                "ACL ownership rejected: anchor={anchor}, servicing={}",
                unsafe { !owner.is_null() && EqualSid(owner, servicing.as_ptr() as PSID) != 0 }
            );
            return Err(Failure::Staging);
        }
        let write = (if anchor {
            0
        } else {
            FILE_WRITE_DATA | FILE_APPEND_DATA | FILE_WRITE_EA | FILE_WRITE_ATTRIBUTES
        }) | FILE_DELETE_CHILD
            | DELETE
            | WRITE_DAC
            | WRITE_OWNER
            | GENERIC_WRITE
            | GENERIC_ALL;
        for index in 0..unsafe { (*acl).AceCount } as u32 {
            let mut ace: *mut c_void = ptr::null_mut();
            if unsafe { GetAce(acl, index, &mut ace) } == 0 || ace.is_null() {
                return Err(Failure::Staging);
            }
            let header = unsafe { &*ace.cast::<ACE_HEADER>() };
            // Inherit-only entries grant no access to this object. Check each
            // descendant separately so effective student-write grants fail.
            if u32::from(header.AceFlags) & INHERIT_ONLY_ACE != 0 {
                continue;
            }
            if header.AceType == 1 {
                continue;
            } // Deny ACEs cannot grant write access.
            if header.AceType != 0 {
                #[cfg(test)]
                eprintln!("ACL ACE type rejected: {}", header.AceType);
                return Err(Failure::Staging);
            }
            let allow = unsafe { &*ace.cast::<ACCESS_ALLOWED_ACE>() };
            let trustee = ptr::addr_of!(allow.SidStart) as PSID;
            if allow.Mask & write != 0 && !trusted_here(trustee) {
                #[cfg(test)]
                eprintln!(
                    "ACL write ACE rejected: mask={:#x}, flags={:#x}",
                    allow.Mask, header.AceFlags
                );
                return Err(Failure::Staging);
            }
        }
        Ok(())
    }
    pub(super) fn create_private(path: &Path) -> Result<()> {
        let sddl = wide("O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)");
        let mut descriptor = ptr::null_mut();
        if unsafe {
            ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl.as_ptr(),
                1,
                &mut descriptor,
                ptr::null_mut(),
            )
        } == 0
        {
            return Err(Failure::Staging);
        }
        let attributes = SECURITY_ATTRIBUTES {
            nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
            lpSecurityDescriptor: descriptor,
            bInheritHandle: 0,
        };
        let result = unsafe { CreateDirectoryW(wide(path).as_ptr(), &attributes) };
        unsafe {
            LocalFree(descriptor);
        }
        if result == 0 {
            return Err(Failure::Staging);
        }
        validate(path)
    }
    pub(super) fn exclusive(path: &Path) -> Result<File> {
        use std::os::windows::io::FromRawHandle;
        let mut descriptor = ptr::null_mut();
        if unsafe {
            ConvertStringSecurityDescriptorToSecurityDescriptorW(
                wide("O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)").as_ptr(),
                1,
                &mut descriptor,
                ptr::null_mut(),
            )
        } == 0
        {
            #[cfg(test)]
            eprintln!("Exclusive security descriptor failed: {}", unsafe {
                GetLastError()
            });
            return Err(Failure::Staging);
        }
        let attributes = SECURITY_ATTRIBUTES {
            nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
            lpSecurityDescriptor: descriptor,
            bInheritHandle: 0,
        };
        let handle = unsafe {
            CreateFileW(
                wide(path).as_ptr(),
                GENERIC_WRITE | READ_CONTROL | FILE_READ_ATTRIBUTES,
                0,
                &attributes,
                CREATE_NEW,
                FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
                ptr::null_mut(),
            )
        };
        unsafe {
            LocalFree(descriptor);
        }
        if handle == INVALID_HANDLE_VALUE {
            #[cfg(test)]
            eprintln!("Exclusive CreateFileW failed: {}", unsafe {
                GetLastError()
            });
            return Err(Failure::Staging);
        }
        let file = unsafe { File::from_raw_handle(handle) };
        // Query the existing exclusive handle; reopening its pathname would fail
        // Windows sharing checks and is unnecessary for owner/ACL validation.
        let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
        if unsafe { GetFileInformationByHandle(handle, &mut info) } == 0
            || info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY)
                != 0
        {
            #[cfg(test)]
            eprintln!("Exclusive handle metadata failed: {}", unsafe {
                GetLastError()
            });
            return Err(Failure::Staging);
        }
        let mut owner = ptr::null_mut();
        let mut acl = ptr::null_mut();
        let mut descriptor = ptr::null_mut();
        let security_status = unsafe {
            GetSecurityInfo(
                handle,
                SE_FILE_OBJECT,
                OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
                &mut owner,
                ptr::null_mut(),
                &mut acl,
                ptr::null_mut(),
                &mut descriptor,
            )
        };
        if security_status != ERROR_SUCCESS {
            #[cfg(test)]
            eprintln!("Exclusive GetSecurityInfo failed: {security_status}");
            return Err(Failure::Staging);
        }
        let result = check_acl(owner, acl, false, false);
        #[cfg(test)]
        if result.is_err() {
            eprintln!("Exclusive file ACL check failed");
        }
        unsafe {
            LocalFree(descriptor);
        }
        result?;
        Ok(file)
    }
    pub(super) fn store() -> Result<PathBuf> {
        // The supported Windows installation contract uses this fixed machine path.
        // Never accept an environment, working-directory, or caller-supplied root.
        let mut root = PathBuf::from(r"C:\ProgramData");
        validate_acl(Path::new(r"C:\"), true)?;
        validate_acl(&root, true)?;
        if std::fs::symlink_metadata(&root)
            .map_err(|_| Failure::Staging)?
            .file_attributes()
            & FILE_ATTRIBUTE_REPARSE_POINT
            != 0
        {
            return Err(Failure::Staging);
        }
        for component in ["SkyviewRobotics", "SelfUpdate", "staging"] {
            root.push(component);
            if !root.try_exists().map_err(|_| Failure::Staging)? {
                create_private(&root)?;
            }
            validate(&root)?;
        }
        Ok(root)
    }
    fn registry(name: &str) -> Result<String> {
        let key = wide(r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Skyview Dev Setup");
        let name = wide(name);
        let mut buffer = [0u16; 2048];
        let mut bytes = (buffer.len() * 2) as u32;
        if unsafe {
            RegGetValueW(
                HKEY_LOCAL_MACHINE,
                key.as_ptr(),
                name.as_ptr(),
                RRF_RT_REG_SZ | RRF_SUBKEY_WOW6464KEY,
                ptr::null_mut(),
                buffer.as_mut_ptr().cast(),
                &mut bytes,
            )
        } != ERROR_SUCCESS
            || bytes < 2
            || bytes as usize > buffer.len() * 2
        {
            return Err(Failure::InvalidInstalled);
        }
        let len = bytes as usize / 2;
        if buffer[len - 1] != 0 {
            return Err(Failure::InvalidInstalled);
        }
        String::from_utf16(&buffer[..len - 1]).map_err(|_| Failure::InvalidInstalled)
    }
    pub(super) fn installed() -> Result<Installed> {
        supported()?;
        installed_identity()
    }
    fn supported() -> Result<()> {
        if std::env::consts::ARCH != "x86_64" {
            return Err(Failure::Unsupported);
        }
        let mut process_machine = 0u16;
        let mut native_machine = 0u16;
        if unsafe {
            IsWow64Process2(
                GetCurrentProcess(),
                &mut process_machine,
                &mut native_machine,
            )
        } == 0
            || native_machine != 0x8664
        {
            return Err(Failure::Unsupported);
        }
        // RtlGetVersion avoids manifest-dependent version virtualization.
        #[repr(C)]
        struct OsVersion {
            size: u32,
            major: u32,
            minor: u32,
            build: u32,
            platform: u32,
            service: [u16; 128],
            service_pack_major: u16,
            service_pack_minor: u16,
            suite: u16,
            product_type: u8,
            reserved: u8,
        }
        #[link(name = "ntdll")]
        unsafe extern "system" {
            fn RtlGetVersion(version: *mut OsVersion) -> i32;
        }
        let mut os: OsVersion = unsafe { std::mem::zeroed() };
        os.size = std::mem::size_of::<OsVersion>() as u32;
        if unsafe { RtlGetVersion(&mut os) } != 0
            || os.major != 10
            || os.build < 22000
            || os.product_type != 1
        {
            return Err(Failure::Unsupported);
        }
        Ok(())
    }
    pub(crate) fn install_location() -> Result<PathBuf> {
        let path = PathBuf::from(registry("InstallLocation")?.trim_matches('"'));
        if !path.is_absolute()
            || !path.starts_with(r"C:\Program Files")
            || path
                .components()
                .any(|c| matches!(c, std::path::Component::ParentDir))
        {
            return Err(Failure::InvalidInstalled);
        }
        for ancestor in path.ancestors() {
            validate_acl(
                ancestor,
                ancestor == Path::new(r"C:\") || ancestor == Path::new(r"C:\Program Files"),
            )
            .map_err(|_| {
                #[cfg(test)]
                eprintln!("Installed ancestor ACL rejected: {}", ancestor.display());
                Failure::InvalidInstalled
            })?;
        }
        Ok(path)
    }
    pub(crate) fn installed_identity() -> Result<Installed> {
        let registered = version(&registry("DisplayVersion")?)?;
        let path = install_location()?;
        if registry("MainBinaryName")? != "skyview-dev-setup.exe" {
            return Err(Failure::InvalidInstalled);
        }
        let binary = path.join("skyview-dev-setup.exe");
        validate(&binary).map_err(|_| {
            #[cfg(test)]
            eprintln!("Installed executable ACL rejected: {}", binary.display());
            Failure::InvalidInstalled
        })?;
        let binary = wide(&binary);
        let mut handle = 0;
        let size = unsafe { GetFileVersionInfoSizeW(binary.as_ptr(), &mut handle) };
        if size == 0 || size > 1024 * 1024 {
            return Err(Failure::InvalidInstalled);
        }
        let mut data = vec![0u32; (size as usize).div_ceil(4)];
        if unsafe { GetFileVersionInfoW(binary.as_ptr(), 0, size, data.as_mut_ptr().cast()) } == 0 {
            return Err(Failure::InvalidInstalled);
        }
        let mut value: *mut c_void = ptr::null_mut();
        let mut len = 0;
        if unsafe {
            VerQueryValueW(
                data.as_ptr().cast(),
                wide("\\").as_ptr(),
                &mut value,
                &mut len,
            )
        } == 0
            || len < std::mem::size_of::<VS_FIXEDFILEINFO>() as u32
            || value.is_null()
        {
            return Err(Failure::InvalidInstalled);
        }
        let fixed = unsafe { &*value.cast::<VS_FIXEDFILEINFO>() };
        if fixed.dwSignature != 0xfeef04bd || fixed.dwProductVersionLS & 0xffff != 0 {
            return Err(Failure::InvalidInstalled);
        }
        let actual = format!(
            "{}.{}.{}",
            fixed.dwProductVersionMS >> 16,
            fixed.dwProductVersionMS & 0xffff,
            fixed.dwProductVersionLS >> 16
        );
        if actual != registered {
            #[cfg(test)]
            eprintln!("Installed PE version {actual} differs from registry {registered}");
            return Err(Failure::InvalidInstalled);
        }
        Ok(Installed {
            version: registered,
            platform: "windows-x86_64",
        })
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[cfg(target_os = "linux")]
    #[test]
    fn mint_version_gate() {
        for value in [
            "ID=ubuntu\nVERSION_ID=22",
            "ID=linuxmint\nVERSION_ID=220",
            "ID=linuxmint\nVERSION_ID=22.evil",
            "ID=linuxmint\nVERSION_ID=21.3",
        ] {
            assert!(!mint_supported(value));
        }
        assert!(mint_supported("ID=linuxmint\nVERSION_ID=\"22.1\""));
    }
    #[test]
    fn installed_version_is_canonical() {
        for v in ["", "bad", "1.2", "01.2.3", "1.2.3+old", "1.2.3-rc.1"] {
            assert_eq!(version(v).unwrap_err(), Failure::InvalidInstalled);
        }
        assert_eq!(version("1.2.1").unwrap(), "1.2.1");
    }
    #[cfg(target_os = "linux")]
    #[test]
    fn unsafe_unix_files_and_links_rejected() {
        use std::os::unix::fs::{symlink, PermissionsExt};
        let dir = tempfile::tempdir().unwrap();
        let file = dir.path().join("writable");
        std::fs::write(&file, b"x").unwrap();
        std::fs::set_permissions(&file, std::fs::Permissions::from_mode(0o666)).unwrap();
        assert_eq!(validate(&file), Err(Failure::Staging));
        let link = dir.path().join("link");
        symlink(&file, &link).unwrap();
        assert_eq!(validate(&link), Err(Failure::Staging));
    }
    #[cfg(windows)]
    #[test]
    fn installed_native_fixture_identity() {
        if std::env::var_os("SDE_APPONLY_IDENTITY_FIXTURE").is_none() {
            return;
        }
        assert_eq!(windows::installed_identity().unwrap().version, "1.2.1");
    }
    #[cfg(windows)]
    #[test]
    fn windows_private_acl_and_reparse_rejection() {
        for anchor in [r"C:\", r"C:\Program Files", r"C:\ProgramData"] {
            windows::validate_acl(Path::new(anchor), true).unwrap();
        }
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(validate(dir.path()), Err(Failure::Staging));
        let private = dir.path().join("protected");
        create_private(&private).unwrap();
        validate(&private).unwrap();
        let file = exclusive(&private.join("installer")).unwrap();
        file.sync_all().unwrap();
        assert!(exclusive(&private.join("installer")).is_err());
        drop(file);
        // Inherit-only rights cannot write the parent, but effective inherited
        // rights on a child must be rejected. Exercise actual Windows ACLs.
        let status = std::process::Command::new(r"C:\Windows\System32\icacls.exe")
            .arg(&private)
            .args(["/grant", "*S-1-5-32-545:(OI)(CI)(IO)(F)"])
            .status()
            .unwrap();
        assert!(status.success());
        validate(&private).unwrap();
        let unsafe_child = private.join("inherited-student-write");
        std::fs::write(&unsafe_child, b"fixture").unwrap();
        assert_eq!(validate(&unsafe_child), Err(Failure::Staging));
        // Servicing control must not be accepted on private payload/state roots.
        let status = std::process::Command::new(r"C:\Windows\System32\icacls.exe")
            .arg(&private)
            .args([
                "/grant",
                "*S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464:(F)",
            ])
            .status()
            .unwrap();
        assert!(status.success());
        assert_eq!(validate(&private), Err(Failure::Staging));
        // Junctions are available without Developer Mode or symlink privilege.
        let junction = dir.path().join("junction");
        let status = std::process::Command::new(r"C:\Windows\System32\cmd.exe")
            .args(["/c", "mklink", "/J"])
            .arg(&junction)
            .arg(&private)
            .status()
            .unwrap();
        assert!(status.success());
        assert_eq!(validate(&junction), Err(Failure::Staging));
        std::fs::remove_dir(junction).unwrap();
    }
}
