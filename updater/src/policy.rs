//! Student-editable, fixed-schema pause preference. This is never execution
//! authority: release authentication, package eligibility and all other protected
//! state retain their existing checks. Only this file's data bytes are writable.
use crate::{
    observation::{Policy, ROOT},
    Result,
};
use std::{
    fs::{File, OpenOptions},
    io::{Read, Seek, SeekFrom, Write},
    path::Path,
};

fn open(write: bool) -> Result<File> {
    let path = Path::new(ROOT).join("policy.json");
    crate::observation::trusted(Path::new(ROOT))?;
    let mut options = OpenOptions::new();
    options.read(true).write(write);
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC | libc::O_NONBLOCK);
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        use windows_sys::Win32::Storage::FileSystem::*;
        crate::host::windows::validate_policy(&path)
            .map_err(|_| "Invalid pause setting permissions")?;
        // Deny replacement while validating/reading/writing this handle. Request
        // only data write, never delete, ACL, owner, attribute or append rights.
        options
            .access_mode(FILE_GENERIC_READ | if write { FILE_WRITE_DATA } else { 0 })
            .share_mode(FILE_SHARE_READ | FILE_SHARE_WRITE)
            .custom_flags(FILE_FLAG_OPEN_REPARSE_POINT);
    }
    let file = options
        .open(&path)
        .map_err(|_| "Pause setting unavailable; refresh or ask a mentor")?;
    let metadata = file.metadata().map_err(|_| "Pause setting unavailable")?;
    if !metadata.is_file() || metadata.len() > 128 {
        return Err("Invalid pause setting".into());
    }
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::fs::MetadataExt;
        if metadata.uid() != 0
            || metadata.nlink() != 1
            || !matches!(metadata.mode() & 0o7777, 0o644 | 0o666)
        {
            return Err("Invalid pause setting permissions".into());
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
            return Err("Invalid pause setting file".into());
        }
        crate::host::windows::validate_policy(&path)
            .map_err(|_| "Invalid pause setting permissions")?;
    }
    Ok(file)
}

fn decode(bytes: &[u8]) -> Result<Policy> {
    let policy: Policy =
        serde_json::from_slice(bytes).map_err(|_| "Invalid pause setting; ask a mentor")?;
    if policy.schema_version != 1 {
        return Err("Unsupported pause setting".into());
    }
    Ok(policy)
}

fn read_file(file: &mut File) -> Result<Policy> {
    let mut bytes = Vec::new();
    file.take(129)
        .read_to_end(&mut bytes)
        .map_err(|_| "Pause setting unavailable")?;
    if bytes.len() > 128 {
        return Err("Invalid pause setting".into());
    }
    decode(&bytes)
}

pub(crate) fn read() -> Result<Policy> {
    read_file(&mut open(false)?)
}

/// Fixed boolean only; no path, command, scheduler, installer or elevation input.
/// Interrupted/concurrent writes may be unreadable and therefore fail closed.
/// The protected parent prevents students from replacing this file or its ACL.
pub fn set_paused(paused: bool) -> Result<()> {
    let mut file = open(true)?;
    let _ = read_file(&mut file)?;
    let bytes = serde_json::to_vec(&Policy {
        schema_version: 1,
        paused,
    })
    .map_err(|_| "Pause setting encoding failed")?;
    file.seek(SeekFrom::Start(0))
        .map_err(|_| "Pause setting save failed")?;
    file.write_all(&bytes)
        .and_then(|_| file.set_len(bytes.len() as u64))
        .and_then(|_| file.sync_all())
        .map_err(|_| "Pause setting save failed; refresh to check its current state")?;
    drop(file);
    if read()?.paused != paused {
        return Err("Pause setting changed concurrently; refresh and try again".into());
    }
    Ok(())
}

#[cfg(test)]
pub(crate) fn native_contracts() {
    // SYSTEM scheduled-task fixtures do not inherit the runner user's entire
    // environment; their guarded harness supplies its explicit native marker.
    assert!(
        std::env::var("GITHUB_ACTIONS").as_deref() == Ok("true")
            || cfg!(windows) && std::env::var_os("SDE_NATIVE_UPGRADE_FIXTURE").is_some()
    );
    let path = Path::new(ROOT).join("policy.json");
    let original = std::fs::read(&path).unwrap();
    let history = std::fs::read(Path::new(ROOT).join("status.json")).ok();
    for invalid in [
        b"{}".to_vec(),
        br#"{"schemaVersion":1,"paused":false,"command":"ignored"}"#.to_vec(),
        vec![b' '; 129],
    ] {
        std::fs::write(&path, &invalid).unwrap();
        assert!(read().is_err());
        assert!(set_paused(false).is_err());
        assert_eq!(std::fs::read(&path).unwrap(), invalid);
    }
    std::fs::write(&path, &original).unwrap();
    let link = Path::new(ROOT).join(format!("policy-link-{}", uuid::Uuid::new_v4()));
    std::fs::hard_link(&path, &link).unwrap();
    assert!(read().is_err());
    assert!(set_paused(false).is_err());
    std::fs::remove_file(link).unwrap();
    #[cfg(target_os = "linux")]
    {
        use std::os::unix::fs::PermissionsExt;
        let permissions = std::fs::metadata(&path).unwrap().permissions();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o777)).unwrap();
        assert!(read().is_err());
        std::fs::set_permissions(&path, permissions).unwrap();
    }
    assert_eq!(std::fs::read(&path).unwrap(), original);
    assert_eq!(
        std::fs::read(Path::new(ROOT).join("status.json")).ok(),
        history
    );
    assert!(read().is_ok());
    println!("SDE_NATIVE_POLICY_GUARDS_OK: invalid/oversized/linked preferences rejected; history untouched");
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn only_schema_one_boolean_is_accepted() {
        for bytes in [
            b"{}".as_slice(),
            br#"{"schemaVersion":1,"paused":"false"}"#,
            br#"{"schemaVersion":2,"paused":false}"#,
            br#"{"schemaVersion":1,"paused":false,"command":"anything"}"#,
            br#"{"schemaVersion":1,"paused":false,"paused":true}"#,
        ] {
            assert!(decode(bytes).is_err());
        }
        assert!(
            !decode(br#"{"schemaVersion":1,"paused":false}"#)
                .unwrap()
                .paused
        );
        assert!(
            decode(br#"{"schemaVersion":1,"paused":true}"#)
                .unwrap()
                .paused
        );
    }
}
