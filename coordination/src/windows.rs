use super::*;
use std::{
    ffi::c_void,
    os::windows::{
        ffi::OsStrExt,
        fs::MetadataExt,
        io::{AsRawHandle, FromRawHandle},
    },
    ptr,
};
use windows_sys::Win32::{
    Foundation::*,
    Security::{Authorization::*, *},
    Storage::FileSystem::*,
};
fn wide(value: impl AsRef<std::ffi::OsStr>) -> Vec<u16> {
    value.as_ref().encode_wide().chain(Some(0)).collect()
}
fn sid(kind: WELL_KNOWN_SID_TYPE) -> Result<Vec<u32>> {
    let mut buffer = vec![0u32; 17];
    let mut size = 68;
    if unsafe { CreateWellKnownSid(kind, ptr::null_mut(), buffer.as_mut_ptr().cast(), &mut size) }
        == 0
    {
        return Err(Error::Untrusted);
    }
    Ok(buffer)
}
fn sid_from_string(value: &str) -> Result<Vec<u32>> {
    let mut raw = ptr::null_mut();
    if unsafe { ConvertStringSidToSidW(wide(value).as_ptr(), &mut raw) } == 0 {
        return Err(Error::Untrusted);
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
pub(crate) fn validate(path: &Path) -> Result<()> {
    validate_acl(path, false)
}
pub(crate) fn validate_acl(path: &Path, anchor: bool) -> Result<()> {
    let info = std::fs::symlink_metadata(path).map_err(|_| Error::Untrusted)?;
    if info.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0
        || !(info.is_dir() || info.is_file())
    {
        return Err(Error::Untrusted);
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
        return Err(Error::Untrusted);
    }
    let result = check_acl(owner, acl, anchor);
    unsafe {
        LocalFree(descriptor);
    }
    result
}
fn check_acl(owner: PSID, acl: *mut ACL, anchor: bool) -> Result<()> {
    let system = sid(WinLocalSystemSid)?;
    let admins = sid(WinBuiltinAdministratorsSid)?;
    // The servicing identity is allowed only at Windows system anchors.
    let servicing =
        sid_from_string("S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464")?;
    let trusted_here = |value: PSID| {
        trusted(value, &system, &admins)
            || (anchor && unsafe { EqualSid(value, servicing.as_ptr() as PSID) != 0 })
    };
    if !trusted_here(owner) || acl.is_null() {
        return Err(Error::Untrusted);
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
            return Err(Error::Untrusted);
        }
        let header = unsafe { &*ace.cast::<ACE_HEADER>() };
        if anchor && u32::from(header.AceFlags) & INHERIT_ONLY_ACE != 0 {
            continue;
        }
        if header.AceType == 1 {
            continue;
        } // Deny ACEs cannot grant write access.
        if header.AceType != 0 {
            return Err(Error::Untrusted);
        }
        let allow = unsafe { &*ace.cast::<ACCESS_ALLOWED_ACE>() };
        let trustee = ptr::addr_of!(allow.SidStart) as PSID;
        if allow.Mask & write != 0 && !trusted_here(trustee) {
            return Err(Error::Untrusted);
        }
    }
    Ok(())
}

fn validate_parents(dir: &Path) -> Result<()> {
    validate_acl(Path::new(r"C:\"), true)?;
    validate_acl(Path::new(r"C:\ProgramData"), true)?;
    validate(dir)
}
fn create(path: &Path, directory: bool) -> Result<()> {
    // Existing gates may be held exclusively during a package post-install hook.
    // Validate them through metadata/security handles without taking another lease.
    if unsafe { GetFileAttributesW(wide(path).as_ptr()) } != INVALID_FILE_ATTRIBUTES {
        return Ok(());
    }
    let mut descriptor = ptr::null_mut();
    let sddl = if directory {
        "O:BAG:BAD:P(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)(A;OICI;FRFX;;;BU)"
    } else {
        "O:BAG:BAD:P(A;;FA;;;SY)(A;;FA;;;BA)(A;;FR;;;BU)"
    };
    if unsafe {
        ConvertStringSecurityDescriptorToSecurityDescriptorW(
            wide(sddl).as_ptr(),
            1,
            &mut descriptor,
            ptr::null_mut(),
        )
    } == 0
    {
        return Err(Error::Untrusted);
    }
    let security = SECURITY_ATTRIBUTES {
        nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
        lpSecurityDescriptor: descriptor,
        bInheritHandle: 0,
    };
    let code = if directory {
        if unsafe { CreateDirectoryW(wide(path).as_ptr(), &security) } != 0 {
            0
        } else {
            unsafe { GetLastError() }
        }
    } else {
        let handle = unsafe {
            CreateFileW(
                wide(path).as_ptr(),
                GENERIC_WRITE,
                FILE_SHARE_READ,
                &security,
                CREATE_NEW,
                FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
                ptr::null_mut(),
            )
        };
        if handle == INVALID_HANDLE_VALUE {
            unsafe { GetLastError() }
        } else {
            let file = unsafe { File::from_raw_handle(handle) };
            file.sync_all().map_err(|_| Error::Unavailable)?;
            0
        }
    };
    unsafe {
        LocalFree(descriptor);
    }
    match code {
        0 | ERROR_ALREADY_EXISTS | ERROR_FILE_EXISTS => Ok(()),
        _ => Err(Error::Untrusted),
    }
}
pub(super) fn initialize(dir: &Path) -> Result<()> {
    validate_acl(Path::new(r"C:\"), true)?;
    validate_acl(Path::new(r"C:\ProgramData"), true)?;
    create(dir, true)?;
    validate_parents(dir)?;
    for name in ["sessions.gate", "operations.gate", "admission.gate"] {
        create(&dir.join(name), false)?;
        drop(open_checked(
            dir,
            name,
            READ_CONTROL | FILE_READ_ATTRIBUTES,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        )?);
    }
    Ok(())
}
pub(super) fn acquire(dir: &Path, name: &str, shared: bool) -> Result<File> {
    open_checked(
        dir,
        name,
        GENERIC_READ | READ_CONTROL,
        if shared { FILE_SHARE_READ } else { 0 },
    )
}
fn open_checked(dir: &Path, name: &str, access: u32, sharing: u32) -> Result<File> {
    validate_parents(dir)?;
    let handle = unsafe {
        CreateFileW(
            wide(dir.join(name)).as_ptr(),
            access,
            sharing,
            ptr::null(),
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
            ptr::null_mut(),
        )
    };
    if handle == INVALID_HANDLE_VALUE {
        return Err(if unsafe { GetLastError() } == ERROR_SHARING_VIOLATION {
            Error::Busy
        } else {
            Error::Unavailable
        });
    }
    let file = unsafe { File::from_raw_handle(handle) };
    let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
    if unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) } == 0
        || info.dwFileAttributes & (FILE_ATTRIBUTE_REPARSE_POINT | FILE_ATTRIBUTE_DIRECTORY) != 0
        || info.nNumberOfLinks != 1
        || info.nFileSizeHigh != 0
        || info.nFileSizeLow != 0
    {
        return Err(Error::Untrusted);
    }
    let mut owner = ptr::null_mut();
    let mut acl = ptr::null_mut();
    let mut descriptor = ptr::null_mut();
    if unsafe {
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
    } != ERROR_SUCCESS
    {
        return Err(Error::Untrusted);
    }
    let result = check_acl(owner, acl, false);
    unsafe {
        LocalFree(descriptor);
    }
    result?;
    Ok(file)
}

pub(super) fn journal(path: &Path) -> Result<File> {
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
        return Err(Error::Untrusted);
    }
    let security = SECURITY_ATTRIBUTES {
        nLength: std::mem::size_of::<SECURITY_ATTRIBUTES>() as u32,
        lpSecurityDescriptor: descriptor,
        bInheritHandle: 0,
    };
    let handle = unsafe {
        CreateFileW(
            wide(path).as_ptr(),
            GENERIC_WRITE,
            0,
            &security,
            CREATE_NEW,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT | FILE_FLAG_WRITE_THROUGH,
            ptr::null_mut(),
        )
    };
    unsafe {
        LocalFree(descriptor);
    }
    if handle == INVALID_HANDLE_VALUE {
        return Err(Error::Interrupted);
    }
    Ok(unsafe { File::from_raw_handle(handle) })
}
