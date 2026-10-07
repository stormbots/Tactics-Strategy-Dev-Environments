use crate::protocol::redact;
#[cfg(windows)]
use std::io::Write;
use std::{
    io::{BufRead, BufReader},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::mpsc,
};

pub fn hidden(cmd: &mut Command) -> &mut Command {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    cmd
}

pub fn script(root: &Path, name: &str) -> Command {
    #[cfg(windows)]
    {
        let mut c = Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe");
        c.args([
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
        ])
        .arg(root.join("windows").join(name));
        hidden(&mut c);
        c
    }
    #[cfg(not(windows))]
    {
        let mut c = Command::new("/bin/bash");
        c.arg(root.join("linux").join(name));
        c
    }
}

pub fn stream(mut cmd: Command, mut on_line: impl FnMut(String)) -> Result<i32, String> {
    cmd.stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    let mut child = hidden(&mut cmd)
        .spawn()
        .map_err(|e| format!("Could not start the provisioning process: {e}"))?;
    let (tx, rx) = mpsc::channel();
    let out = child.stdout.take().unwrap();
    let err = child.stderr.take().unwrap();
    let a = tx.clone();
    let first = std::thread::spawn(move || {
        for line in BufReader::new(out).split(b'\n') {
            if let Ok(bytes) = line {
                let s = String::from_utf8_lossy(&bytes)
                    .trim_end_matches('\r')
                    .to_owned();
                if a.send(s).is_err() {
                    break;
                }
            }
        }
    });
    let second = std::thread::spawn(move || {
        for line in BufReader::new(err).split(b'\n') {
            if let Ok(bytes) = line {
                let s = String::from_utf8_lossy(&bytes)
                    .trim_end_matches('\r')
                    .to_owned();
                if tx.send(s).is_err() {
                    break;
                }
            }
        }
    });
    for line in rx {
        on_line(redact(&line));
    }
    let _ = first.join();
    let _ = second.join();
    child
        .wait()
        .map(|s| s.code().unwrap_or(1))
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn drains_both_streams_and_reports_child_failure() {
        #[cfg(windows)]
        let mut command = Command::new(r"C:\Windows\System32\cmd.exe");
        #[cfg(windows)]
        command.args(["/d","/c","echo SKYVIEW_EVENT^|progress^|5^|Checking & echo Package download failed 1>&2 & exit /b 7"]);
        #[cfg(not(windows))]
        let mut command = Command::new("/bin/sh");
        #[cfg(not(windows))]
        command.args(["-c","printf 'SKYVIEW_EVENT|progress|5|Checking\\n'; printf 'Package download failed\\n' >&2; exit 7"]);
        let mut lines = Vec::new();
        assert_eq!(stream(command, |s| lines.push(s)).unwrap(), 7);
        assert!(lines.iter().any(|s| s.contains("Package download failed")));
        assert!(lines.iter().any(|s| crate::protocol::parse(s).is_some()));
    }
    #[test]
    fn child_start_errors_are_actionable() {
        let error =
            stream(Command::new("skyview-missing-executable-for-test"), |_| {}).unwrap_err();
        assert!(error.contains("Could not start"));
    }
}

pub fn resource_backend() -> Result<PathBuf, String> {
    #[cfg(windows)]
    {
        let exe = std::env::current_exe()
            .map_err(|e| e.to_string())?
            .canonicalize()
            .map_err(|e| e.to_string())?;
        let program_files = PathBuf::from(r"C:\Program Files")
            .canonicalize()
            .map_err(|e| e.to_string())?;
        if !exe.starts_with(program_files) {
            return Err(
                "Install the packaged application in Program Files before provisioning.".into(),
            );
        }
        Ok(exe.parent().unwrap().join("backend"))
    }
    #[cfg(not(windows))]
    {
        Ok(PathBuf::from("/usr/lib/Skyview Dev Setup/backend"))
    }
}

pub fn helper(operation: &str, session: &str) -> Result<i32, String> {
    if !["install", "repair", "update"].contains(&operation)
        || uuid::Uuid::parse_str(session).is_err()
    {
        return Err("Invalid privileged operation.".into());
    }
    // Never elevate a development checkout or accept frontend script paths.
    if cfg!(debug_assertions) {
        return Err("Privileged operations require an installed release build.".into());
    }
    let backend = resource_backend()?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        if unsafe { libc::geteuid() } != 0 {
            return Err("Administrator authentication is required.".into());
        }
        fn trusted(path: &Path) -> Result<(), String> {
            let m = std::fs::symlink_metadata(path).map_err(|e| e.to_string())?;
            if m.uid() != 0 || m.mode() & 0o022 != 0 || m.file_type().is_symlink() {
                return Err(format!("Untrusted installed file: {}", path.display()));
            }
            if m.is_dir() {
                for e in std::fs::read_dir(path).map_err(|e| e.to_string())? {
                    trusted(&e.map_err(|e| e.to_string())?.path())?;
                }
            }
            Ok(())
        }
        trusted(&std::env::current_exe().map_err(|e| e.to_string())?)?;
        trusted(&backend)?;
    }
    let mut cmd = match operation {
        "install" | "repair" => {
            #[cfg(windows)]
            let mut c = script(&backend, "Install-SkyviewStudentDev.ps1");
            #[cfg(not(windows))]
            let mut c = script(&backend, "Install-SkyviewStudentDev.sh");
            #[cfg(windows)]
            {
                c.arg("-SystemOnly");
                if operation == "repair" {
                    c.arg("-Repair");
                }
            }
            #[cfg(not(windows))]
            {
                c.arg("--system-only");
            }
            c
        }
        "update" => {
            #[cfg(windows)]
            let c = script(&backend, "chocolatey/tools/Update-SkyviewTools.ps1");
            #[cfg(not(windows))]
            let c = script(&backend, "Update-SkyviewStudentDev.sh");
            c
        }
        _ => unreachable!(),
    };
    // Privileged commands use a system-only search path and no user startup code.
    #[cfg(windows)]
    {
        cmd.env("PATH",r"C:\Windows\System32;C:\Windows;C:\ProgramData\chocolatey\bin;C:\Program Files\Git\cmd");
    }
    #[cfg(unix)]
    {
        cmd.env_clear()
            .env("PATH", "/usr/sbin:/usr/bin:/sbin:/bin")
            .env("HOME", "/root")
            .env("LANG", "C.UTF-8");
    }
    #[cfg(windows)]
    {
        let log_dir = backend.parent().unwrap().join("operation-logs");
        std::fs::create_dir_all(&log_dir).map_err(|e| e.to_string())?;
        let mut file = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(log_dir.join(format!("{session}.log")))
            .map_err(|e| e.to_string())?;
        let code = stream(cmd, |line| {
            let _ = writeln!(file, "{line}");
            let _ = file.flush();
        })?;
        writeln!(file, "SKYVIEW_HELPER_EXIT|{code}").map_err(|e| e.to_string())?;
        Ok(code)
    }
    #[cfg(not(windows))]
    {
        stream(cmd, |line| println!("{line}"))
    }
}

pub fn elevated(
    operation: &str,
    session: &str,
    on_line: impl FnMut(String),
) -> Result<i32, String> {
    let exe = std::env::current_exe().map_err(|e| e.to_string())?;
    #[cfg(not(windows))]
    {
        let mut cmd = Command::new("/usr/bin/pkexec");
        cmd.arg(exe).args(["--privileged", operation, session]);
        let code = stream(cmd, on_line)?;
        if [126, 127].contains(&code) {
            return Err("Administrator authentication was cancelled or denied. Click Retry when you are ready.".into());
        }
        Ok(code)
    }
    #[cfg(windows)]
    {
        use base64::Engine;
        use std::io::{Read, Seek, SeekFrom};
        let mut on_line = on_line;
        let literal = exe.to_string_lossy().replace('\'', "''");
        let command=format!("$ErrorActionPreference='Stop'; try {{ $p=Start-Process -FilePath '{literal}' -ArgumentList '--privileged {operation} {session}' -Verb RunAs -WindowStyle Hidden -PassThru; $h=$p.Handle; $p.WaitForExit(); exit $p.ExitCode }} catch {{ exit 1223 }}");
        let bytes: Vec<u8> = command.encode_utf16().flat_map(u16::to_le_bytes).collect();
        let encoded = base64::engine::general_purpose::STANDARD.encode(bytes);
        let mut cmd = Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe");
        cmd.args(["-NoProfile", "-NonInteractive", "-EncodedCommand", &encoded])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null());
        let mut launcher = hidden(&mut cmd).spawn().map_err(|e| e.to_string())?;
        let log = resource_backend()?
            .parent()
            .unwrap()
            .join("operation-logs")
            .join(format!("{session}.log"));
        let mut offset = 0;
        let mut pending = String::new();
        let mut helper_exit = None;
        loop {
            if let Ok(mut file) = std::fs::File::open(&log) {
                file.seek(SeekFrom::Start(offset))
                    .map_err(|e| e.to_string())?;
                let mut chunk = String::new();
                file.read_to_string(&mut chunk).map_err(|e| e.to_string())?;
                offset += chunk.len() as u64;
                pending.push_str(&chunk);
                while let Some(end) = pending.find('\n') {
                    let line = pending[..end].trim_end_matches('\r').to_string();
                    pending.drain(..=end);
                    if let Some(n) = line.strip_prefix("SKYVIEW_HELPER_EXIT|") {
                        helper_exit = n.parse::<i32>().ok();
                    } else {
                        on_line(redact(&line));
                    }
                }
            }
            if let Some(status) = launcher.try_wait().map_err(|e| e.to_string())? {
                // Process completion happens after the protected log is flushed.
                if let Some(code) = helper_exit {
                    return Ok(code);
                }
                if status.code() == Some(1223) {
                    return Err("Administrator approval was cancelled or denied. Click Retry when you are ready.".into());
                }
                // One final iteration drains data written between the read and exit.
                if log.exists() {
                    let text = std::fs::read_to_string(&log).map_err(|e| e.to_string())?;
                    for line in text[offset as usize..].lines() {
                        if let Some(n) = line.strip_prefix("SKYVIEW_HELPER_EXIT|") {
                            helper_exit = n.parse::<i32>().ok();
                        } else {
                            on_line(redact(line));
                        }
                    }
                }
                return helper_exit.ok_or_else(||"The privileged helper stopped before reporting a result. Review details and retry.".into());
            }
            std::thread::sleep(std::time::Duration::from_millis(150));
        }
    }
}
