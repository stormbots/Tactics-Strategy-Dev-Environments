//! Already-elevated direct maintenance only. Not application installation,
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

fn elevated() -> bool {
    let mut sid = [0u32; 17];
    let mut size = 68;
    let mut member = 0;
    unsafe {
        CreateWellKnownSid(
            WinBuiltinAdministratorsSid,
            std::ptr::null_mut(),
            sid.as_mut_ptr().cast(),
            &mut size,
        ) != 0
            && CheckTokenMembership(std::ptr::null_mut(), sid.as_ptr() as _, &mut member) != 0
            && member != 0
    }
}

fn arguments_allowed(script: &Path, args: &[OsString]) -> bool {
    match script
        .file_name()
        .and_then(|name| name.to_str())
        .map(str::to_ascii_lowercase)
        .as_deref()
    {
        Some("update-skyviewtools.ps1") => args.is_empty(),
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
        .env("USERPROFILE",r"C:\Windows\System32\config\systemprofile")
        .env("APPDATA",r"C:\Windows\System32\config\systemprofile\AppData\Roaming")
        .env("LOCALAPPDATA",r"C:\Windows\System32\config\systemprofile\AppData\Local")
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
        assert!(!arguments_allowed(
            Path::new(r"C:\ProgramData\Install-SkyviewStudentDev.ps1"),
            &[]
        ));
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
