//! Already-elevated direct system setup and maintenance. Not application installation,
//! elevation, or a frontend command. Reuses installed-path ACL validation and
//! the same coordinator/completion policy as the Linux manual adapter.
pub use sde_coordination::manual::Failure;
use std::{
    ffi::OsString,
    fs::File,
    path::{Component, Path},
    process::Command,
};
use windows_sys::Win32::{Security::*, Storage::FileSystem::*};

fn token_member(kind: WELL_KNOWN_SID_TYPE) -> Option<bool> {
    let mut sid = [0u32; 17];
    let mut size = 68;
    let mut member = 0;
    let success = unsafe {
        CreateWellKnownSid(
            kind,
            std::ptr::null_mut(),
            sid.as_mut_ptr().cast(),
            &mut size,
        ) != 0
            && CheckTokenMembership(std::ptr::null_mut(), sid.as_ptr() as _, &mut member) != 0
    };
    success.then_some(member != 0)
}

fn elevated() -> bool {
    token_member(WinBuiltinAdministratorsSid) == Some(true)
}

fn arguments_allowed(script: &Path, args: &[OsString]) -> bool {
    match script
        .file_name()
        .and_then(|name| name.to_str())
        .map(str::to_ascii_lowercase)
        .as_deref()
    {
        Some("update-skyviewtools.ps1") => args.is_empty(),
        Some("install-skyviewstudentdev.ps1") => {
            args.len() <= 2
                && args
                    .iter()
                    .all(|arg| arg == "-SystemOnly" || arg == "-Repair")
                && (args.len() != 2 || args[0] != args[1])
        }
        Some("update-node24.ps1") => {
            args.is_empty()
                || (args.len() == 2
                    && args[0] == "-Version"
                    && args[1].to_str().is_some_and(|version| {
                        let parts: Vec<_> = version.split('.').collect();
                        parts.len() == 3
                            && parts[0] == "24"
                            && parts[1..].iter().all(|part| {
                                !part.is_empty()
                                    && part.len() <= 8
                                    && part.bytes().all(|c| c.is_ascii_digit())
                            })
                    }))
        }
        _ => false,
    }
}

fn trusted_script(script: &Path) -> bool {
    use std::os::windows::io::AsRawHandle;
    if !script.is_absolute() {
        return false;
    }
    let Some(text) = script.to_str() else {
        return false;
    };
    let Some(base_text) = [r"C:\ProgramData", r"C:\Program Files"]
        .into_iter()
        .find(|base| {
            text.get(..base.len())
                .is_some_and(|prefix| prefix.eq_ignore_ascii_case(base))
                && text
                    .get(base.len()..)
                    .is_some_and(|rest| rest.starts_with('\\'))
        })
    else {
        return false;
    };
    let base = Path::new(base_text);
    if crate::host::windows::validate_acl(Path::new(r"C:\"), true).is_err()
        || crate::host::windows::validate_acl(base, true).is_err()
    {
        return false;
    }
    // Normalize only the known ASCII anchor's spelling. Validate every original
    // relative component before opening; never canonicalize away a reparse point.
    let relative = Path::new(&text[base_text.len() + 1..]);
    let mut current = base.to_path_buf();
    for component in relative.components() {
        let Component::Normal(name) = component else {
            return false;
        };
        // Reject alternate streams, not just traversal/UNC/device spellings.
        if name.to_string_lossy().contains(':') {
            return false;
        }
        current.push(name);
        if crate::host::validate(&current).is_err() {
            return false;
        }
    }
    let Ok(file) = File::open(script) else {
        return false;
    };
    let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
    (unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) != 0 })
        && info.dwFileAttributes & (FILE_ATTRIBUTE_DIRECTORY | FILE_ATTRIBUTE_REPARSE_POINT) == 0
        && info.nNumberOfLinks == 1
}

fn profile_environment(system_only: bool) -> Result<[OsString; 3], Failure> {
    use std::os::windows::ffi::OsStringExt;
    use windows_sys::Win32::{
        Foundation::{CloseHandle, HANDLE},
        System::{
            Com::CoTaskMemFree,
            Threading::{GetCurrentProcess, OpenProcessToken},
        },
        UI::Shell::*,
    };
    if system_only {
        return Ok([
            r"C:\Windows\System32\config\systemprofile".into(),
            r"C:\Windows\System32\config\systemprofile\AppData\Roaming".into(),
            r"C:\Windows\System32\config\systemprofile\AppData\Local".into(),
        ]);
    }
    if token_member(WinLocalSystemSid) != Some(false) {
        return Err(Failure::InvalidInvocation);
    }
    struct Token(HANDLE);
    impl Drop for Token {
        fn drop(&mut self) {
            unsafe {
                CloseHandle(self.0);
            }
        }
    }
    let mut handle = std::ptr::null_mut();
    if unsafe {
        OpenProcessToken(
            GetCurrentProcess(),
            TOKEN_QUERY | TOKEN_IMPERSONATE,
            &mut handle,
        )
    } == 0
    {
        return Err(Failure::InvalidInvocation);
    }
    let token = Token(handle);
    // Resolve the effective account through Windows, not caller-controlled
    // environment variables. Preserve redirected known folders; do not invent
    // AppData paths by appending to USERPROFILE. No directory is created here.
    let folder = |id: &windows_sys::core::GUID| -> Result<OsString, Failure> {
        let mut pointer = std::ptr::null_mut();
        let result =
            unsafe { SHGetKnownFolderPath(id, KF_FLAG_DONT_VERIFY as u32, token.0, &mut pointer) };
        let value = if result >= 0 && !pointer.is_null() {
            let mut length = 0;
            unsafe {
                while *pointer.add(length) != 0 {
                    length += 1;
                }
                Some(OsString::from_wide(std::slice::from_raw_parts(
                    pointer, length,
                )))
            }
        } else {
            None
        };
        unsafe {
            CoTaskMemFree(pointer.cast());
        }
        value
            .filter(|value| Path::new(value).is_absolute())
            .ok_or(Failure::InvalidInvocation)
    };
    let profile = folder(&FOLDERID_Profile)?;
    // SYSTEM has no desktop user phase. Its callers must request SystemOnly;
    // a bare invocation must never configure systemprofile as a student profile.
    if profile
        .to_string_lossy()
        .eq_ignore_ascii_case(r"C:\Windows\System32\config\systemprofile")
    {
        return Err(Failure::InvalidInvocation);
    }
    Ok([
        profile,
        folder(&FOLDERID_RoamingAppData)?,
        folder(&FOLDERID_LocalAppData)?,
    ])
}

pub fn run(script: &Path, args: &[OsString]) -> Result<i32, Failure> {
    use std::os::windows::process::CommandExt;
    // No private-state access, diagnostics, temporary files or child execution
    // before the current effective token and invocation are accepted.
    if !elevated() || !arguments_allowed(script, args) {
        return Err(Failure::InvalidInvocation);
    }
    if !trusted_script(script) {
        return Err(Failure::UntrustedEntryPoint);
    }
    let setup = script
        .file_name()
        .and_then(|name| name.to_str())
        .is_some_and(|name| name.eq_ignore_ascii_case("Install-SkyviewStudentDev.ps1"));
    let [profile, roaming, local] =
        profile_environment(!setup || args.iter().any(|arg| arg == "-SystemOnly"))?;
    let base = sde_coordination::root().join("manual-temp");
    crate::host::validate(&sde_coordination::root()).map_err(|_| Failure::UntrustedEntryPoint)?;
    if base
        .try_exists()
        .map_err(|_| Failure::UntrustedEntryPoint)?
    {
        crate::host::validate(&base).map_err(|_| Failure::UntrustedEntryPoint)?;
    } else {
        crate::host::create_private(&base).map_err(|_| Failure::UntrustedEntryPoint)?;
    }
    let temporary = base.join(uuid::Uuid::new_v4().to_string());
    crate::host::create_private(&temporary).map_err(|_| Failure::UntrustedEntryPoint)?;
    // Preserve uncertain-run temporary evidence; never remove package files on
    // Drop/error. This increment introduces no automatic cleanup or retry.
    let mut command = Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe");
    command
        .creation_flags(0x08000000)
        .current_dir(script.parent().ok_or(Failure::UntrustedEntryPoint)?);
    command.args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"])
        .arg(script).args(args).env_clear()
        .env("PATH", r"C:\Windows\System32;C:\Windows;C:\ProgramData\chocolatey\bin;C:\Program Files\Git\cmd")
        .env("SystemRoot",r"C:\Windows").env("WINDIR",r"C:\Windows").env("SYSTEMDRIVE","C:")
        .env("ComSpec",r"C:\Windows\System32\cmd.exe")
        .env("ProgramData",r"C:\ProgramData").env("ALLUSERSPROFILE",r"C:\ProgramData")
        .env("ProgramFiles",r"C:\Program Files").env("ProgramFiles(x86)",r"C:\Program Files (x86)")
        .env("ChocolateyInstall",r"C:\ProgramData\chocolatey")
        .env("TEMP",&temporary).env("TMP",&temporary)
        .env("USERPROFILE",profile).env("APPDATA",roaming).env("LOCALAPPDATA",local)
        .env("PSModulePath",r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules;C:\Program Files\WindowsPowerShell\Modules")
        .env("PATHEXT",".COM;.EXE;.BAT;.CMD").env("PROCESSOR_ARCHITECTURE","AMD64");
    sde_coordination::manual::run_trusted_backend(command)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn windows_manual_maintenance_arguments_are_not_commands_or_policy_overrides() {
        let script = Path::new(r"C:\ProgramData\SkyviewRobotics\Update-Node24.ps1");
        for (args, allowed) in [
            (vec![], true),
            (vec!["-Version", "24.21.0"], true),
            (vec!["-Version", "26.1.0"], false),
            (vec!["-Version", "24.1.0;exit 0"], false),
            (vec!["-Command", "anything"], false),
            (vec!["-Version"], false),
        ] {
            let args = args.into_iter().map(OsString::from).collect::<Vec<_>>();
            assert_eq!(arguments_allowed(script, &args), allowed);
        }
        let setup = Path::new(r"C:\ProgramData\Install-SkyviewStudentDev.ps1");
        for (args, allowed) in [
            (vec![], true),
            (vec!["-SystemOnly"], true),
            (vec!["-Repair"], true),
            (vec!["-SystemOnly", "-Repair"], true),
            (vec!["-Repair", "-SystemOnly"], true),
            (vec!["-Repair", "-Repair"], false),
            (vec!["-SystemOnly:false"], false),
            (vec!["-Command", "exit 0"], false),
            (vec!["-TargetUser", "student"], false),
        ] {
            assert_eq!(
                arguments_allowed(
                    setup,
                    &args.into_iter().map(OsString::from).collect::<Vec<_>>()
                ),
                allowed
            );
        }
        assert!(!arguments_allowed(
            Path::new(r"C:\ProgramData\Update-SkyviewTools.ps1"),
            &["-Skip".into()]
        ));
        assert!(arguments_allowed(
            Path::new(r"c:\programdata\update-skyviewtools.ps1"),
            &[]
        ));
    }
}
