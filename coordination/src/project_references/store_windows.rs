//! Windows handles/ACLs for data-only per-account reference observations.
use super::*;
use std::{
    ffi::c_void,
    os::windows::{
        ffi::OsStrExt,
        fs::{MetadataExt, OpenOptionsExt},
        io::AsRawHandle,
    },
    ptr,
};
use windows_sys::Win32::{
    Foundation::*,
    Security::{Authorization::*, *},
    Storage::FileSystem::*,
    System::Threading::{GetCurrentProcess, OpenProcessToken},
};

fn wide(value: impl AsRef<std::ffi::OsStr>) -> Vec<u16> {
    value.as_ref().encode_wide().chain(Some(0)).collect()
}

fn sid(kind: WELL_KNOWN_SID_TYPE) -> Result<Vec<u32>, Unavailable> {
    let mut value = vec![0u32; 17];
    let mut bytes = 68;
    if unsafe { CreateWellKnownSid(kind, ptr::null_mut(), value.as_mut_ptr().cast(), &mut bytes) }
        == 0
    {
        return Err(Unavailable::Storage);
    }
    Ok(value)
}

pub(super) fn ordinary_user() -> bool {
    let Ok(admins) = sid(WinBuiltinAdministratorsSid) else {
        return false;
    };
    let mut member = 0;
    unsafe {
        CheckTokenMembership(ptr::null_mut(), admins.as_ptr() as PSID, &mut member) != 0
            && member == 0
    }
}

fn user() -> Result<Vec<usize>, Unavailable> {
    let mut token = ptr::null_mut();
    if unsafe { OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &mut token) } == 0 {
        return Err(Unavailable::Storage);
    }
    let mut bytes = 0;
    unsafe { GetTokenInformation(token, TokenUser, ptr::null_mut(), 0, &mut bytes) };
    if bytes == 0 || bytes > 65536 {
        unsafe { CloseHandle(token) };
        return Err(Unavailable::Storage);
    }
    let mut value = vec![0usize; (bytes as usize).div_ceil(std::mem::size_of::<usize>())];
    let ok = unsafe {
        GetTokenInformation(
            token,
            TokenUser,
            value.as_mut_ptr().cast(),
            bytes,
            &mut bytes,
        )
    };
    unsafe { CloseHandle(token) };
    if ok == 0 {
        return Err(Unavailable::Storage);
    }
    Ok(value)
}

fn equal(a: PSID, b: PSID) -> bool {
    !a.is_null() && !b.is_null() && unsafe { EqualSid(a, b) != 0 }
}

fn security(file: &File, private: bool) -> Result<(), Unavailable> {
    let user = user()?;
    let user_sid = unsafe { (*user.as_ptr().cast::<TOKEN_USER>()).User.Sid };
    let system = sid(WinLocalSystemSid)?;
    let admins = sid(WinBuiltinAdministratorsSid)?;
    let trusted = |value| {
        equal(value, user_sid)
            || equal(value, system.as_ptr() as PSID)
            || equal(value, admins.as_ptr() as PSID)
    };
    let mut owner = ptr::null_mut();
    let mut acl: *mut ACL = ptr::null_mut();
    let mut descriptor = ptr::null_mut();
    if unsafe {
        GetSecurityInfo(
            file.as_raw_handle(),
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
        return Err(Unavailable::Storage);
    }
    let checked = (|| {
        let mut servicing = ptr::null_mut();
        if unsafe {
            ConvertStringSidToSidW(
                wide("S-1-5-80-956008885-3418522649-1831038044-1853292631-2271478464").as_ptr(),
                &mut servicing,
            )
        } == 0
        {
            return Err(Unavailable::Storage);
        }
        let trusted_parent = |value| trusted(value) || equal(value, servicing);
        let owner_ok = if private {
            equal(owner, user_sid)
        } else {
            trusted_parent(owner)
        };
        // Make a separate result so the allocated SID is freed on every refusal.
        let result = (|| {
            if !owner_ok || acl.is_null() {
                return Err(Unavailable::Storage);
            }
            let relevant = DELETE
                | WRITE_DAC
                | WRITE_OWNER
                | FILE_DELETE_CHILD
                | GENERIC_WRITE
                | GENERIC_ALL
                | if private {
                    FILE_WRITE_DATA
                        | FILE_APPEND_DATA
                        | FILE_WRITE_EA
                        | FILE_WRITE_ATTRIBUTES
                        | FILE_READ_DATA
                        | GENERIC_READ
                } else {
                    0
                };
            for index in 0..unsafe { (*acl).AceCount } as u32 {
                let mut ace: *mut c_void = ptr::null_mut();
                if unsafe { GetAce(acl, index, &mut ace) } == 0 || ace.is_null() {
                    return Err(Unavailable::Storage);
                }
                let header = unsafe { &*ace.cast::<ACE_HEADER>() };
                if u32::from(header.AceFlags) & INHERIT_ONLY_ACE != 0 || header.AceType == 1 {
                    continue;
                }
                if header.AceType != 0 {
                    return Err(Unavailable::Storage);
                }
                let allow = unsafe { &*ace.cast::<ACCESS_ALLOWED_ACE>() };
                let trustee = ptr::addr_of!(allow.SidStart) as PSID;
                let allowed = if private {
                    trusted(trustee)
                } else {
                    trusted_parent(trustee)
                };
                if allow.Mask & relevant != 0 && !allowed {
                    return Err(Unavailable::Storage);
                }
            }
            Ok(())
        })();
        unsafe { LocalFree(servicing) };
        result
    })();
    unsafe { LocalFree(descriptor) };
    checked
}

pub(super) fn linked(metadata: &Metadata) -> bool {
    metadata.file_attributes() & FILE_ATTRIBUTE_REPARSE_POINT != 0
}

pub(super) fn parent(path: &Path, _: &Metadata) -> Result<(), Unavailable> {
    let file = open(path, true).map_err(|_| Unavailable::Storage)?;
    security(&file, false)
}

pub(super) fn open(path: &Path, directory: bool) -> std::io::Result<File> {
    let mut options = OpenOptions::new();
    options
        .access_mode(FILE_GENERIC_READ)
        .share_mode(FILE_SHARE_READ)
        .custom_flags(
            FILE_FLAG_OPEN_REPARSE_POINT
                | if directory {
                    FILE_FLAG_BACKUP_SEMANTICS
                } else {
                    0
                },
        );
    options.open(path)
}

fn info(file: &File) -> Result<BY_HANDLE_FILE_INFORMATION, Unavailable> {
    let mut info = unsafe { std::mem::zeroed::<BY_HANDLE_FILE_INFORMATION>() };
    if unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) } == 0
        || info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT != 0
    {
        return Err(Unavailable::Storage);
    }
    Ok(info)
}

pub(super) fn private(file: &File) -> Result<(), Unavailable> {
    let info = info(file)?;
    if info.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY == 0 && info.nNumberOfLinks != 1 {
        return Err(Unavailable::Storage);
    }
    security(file, true)
}

pub(super) fn identity(file: &File) -> Result<String, Unavailable> {
    let i = info(file)?;
    let change = if i.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY != 0 {
        String::new()
    } else {
        format!(
            ":{}:{}:{}:{}",
            i.nFileSizeHigh,
            i.nFileSizeLow,
            i.ftLastWriteTime.dwHighDateTime,
            i.ftLastWriteTime.dwLowDateTime
        )
    };
    Ok(format!(
        "{}:{}:{}:{}:{}{}",
        i.dwVolumeSerialNumber,
        i.nFileIndexHigh,
        i.nFileIndexLow,
        i.ftCreationTime.dwHighDateTime,
        i.ftCreationTime.dwLowDateTime,
        change
    ))
}
