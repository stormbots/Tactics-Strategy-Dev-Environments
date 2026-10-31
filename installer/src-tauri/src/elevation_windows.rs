//! Native RunAs: cancellation is classified at the OS call, not by a helper's
//! exit status or a broad PowerShell catch. Handles are closed, never killed.
use crate::launch_outcome::Failure;
use std::{
    os::windows::{
        ffi::OsStrExt,
        io::{AsRawHandle, FromRawHandle, OwnedHandle},
    },
    path::PathBuf,
};
use windows_sys::Win32::{
    Foundation::*,
    System::{Com::*, Threading::*},
    UI::Shell::*,
};

pub struct Child {
    handle: OwnedHandle,
}
impl Child {
    pub fn try_exit(&self) -> Result<Option<i32>, String> {
        let handle = self.handle.as_raw_handle();
        match unsafe { WaitForSingleObject(handle, 0) } {
            WAIT_TIMEOUT => Ok(None),
            WAIT_OBJECT_0 => {
                let mut code = 0;
                if unsafe { GetExitCodeProcess(handle, &mut code) } == 0 {
                    Err("The privileged helper exit could not be confirmed.".into())
                } else {
                    Ok(Some(code as i32))
                }
            }
            _ => Err("The privileged helper lifetime could not be confirmed.".into()),
        }
    }
}
pub fn launch(exe: PathBuf, parameters: String) -> Result<Child, Failure> {
    // Dedicated STA thread avoids COM apartment conflicts on a reused blocking
    // pool thread. The owned process handle can safely move to the caller.
    std::thread::Builder::new()
        .name("sde-elevation".into())
        .spawn(move || native(exe, parameters))
        .map_err(|_| {
            Failure::NotStarted("The authorization launcher could not be started.".into())
        })?
        .join()
        .map_err(|_| {
            Failure::Uncertain(
                "The authorization launcher ended unexpectedly; keep recovery evidence.".into(),
            )
        })?
}
fn native(exe: PathBuf, parameters: String) -> Result<Child, Failure> {
    let initialized = unsafe {
        CoInitializeEx(
            std::ptr::null(),
            (COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE) as u32,
        )
    };
    if initialized < 0 {
        return Err(Failure::NotStarted(
            "Authorization initialization failed before launch.".into(),
        ));
    }
    struct Com;
    impl Drop for Com {
        fn drop(&mut self) {
            unsafe { CoUninitialize() };
        }
    }
    let _com = Com;
    let exe: Vec<u16> = exe.as_os_str().encode_wide().chain(Some(0)).collect();
    let parameters: Vec<u16> = parameters.encode_utf16().chain(Some(0)).collect();
    let verb: Vec<u16> = "runas".encode_utf16().chain(Some(0)).collect();
    let mut info: SHELLEXECUTEINFOW = unsafe { std::mem::zeroed() };
    info.cbSize = std::mem::size_of::<SHELLEXECUTEINFOW>() as u32;
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC | SEE_MASK_FLAG_NO_UI;
    info.lpVerb = verb.as_ptr();
    info.lpFile = exe.as_ptr();
    info.lpParameters = parameters.as_ptr();
    info.nShow = 0;
    if unsafe { ShellExecuteExW(&mut info) } == 0 {
        let error = unsafe { GetLastError() };
        let handle_present = !info.hProcess.is_null();
        if handle_present {
            drop(unsafe { OwnedHandle::from_raw_handle(info.hProcess) });
        }
        return Err(crate::launch_outcome::windows_failure(
            error,
            handle_present,
        ));
    }
    if info.hProcess.is_null() {
        return Err(Failure::Uncertain(
            "Authorization returned no process handle; keep recovery evidence.".into(),
        ));
    }
    Ok(Child {
        handle: unsafe { OwnedHandle::from_raw_handle(info.hProcess) },
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn windows_tracked_child_exit_1223_is_not_native_authorization_cancellation() {
        let mut child = std::process::Command::new(r"C:\Windows\System32\cmd.exe")
            .args(["/d", "/c", "exit /b 1223"])
            .spawn()
            .unwrap();
        let mut duplicate = std::ptr::null_mut();
        let current = unsafe { GetCurrentProcess() };
        assert_ne!(
            unsafe {
                DuplicateHandle(
                    current,
                    child.as_raw_handle(),
                    current,
                    &mut duplicate,
                    0,
                    0,
                    DUPLICATE_SAME_ACCESS,
                )
            },
            0
        );
        let tracked = Child {
            handle: unsafe { OwnedHandle::from_raw_handle(duplicate) },
        };
        child.wait().unwrap();
        assert_eq!(tracked.try_exit().unwrap(), Some(1223));
    }
}
