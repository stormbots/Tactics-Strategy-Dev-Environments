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

#[cfg(windows)]
fn powershell_path(path: &Path) -> PathBuf {
    // Rust/Tauri canonical paths use the Win32 verbatim prefix. Windows
    // PowerShell 5.1 treats that spelling as a provider path, breaking
    // $PSScriptRoot + Join-Path in packaged scripts. Keep canonical paths for
    // trust checks and file IO; normalize script and temporary paths passed to
    // Windows PowerShell and older .NET package installers.
    let text = path.to_string_lossy();
    if let Some(unc) = text.strip_prefix(r"\\?\UNC\") {
        PathBuf::from(format!(r"\\{unc}"))
    } else if let Some(disk) = text.strip_prefix(r"\\?\") {
        PathBuf::from(disk)
    } else {
        path.to_path_buf()
    }
}

#[cfg(windows)]
fn windows_system_environment(cmd: &mut Command, private_temp: &Path) {
    let temp = powershell_path(private_temp);
    cmd.env_clear()
        .env("PATH",r"C:\Windows\System32;C:\Windows;C:\ProgramData\chocolatey\bin;C:\Program Files\Git\cmd")
        .env("SystemRoot",r"C:\Windows").env("WINDIR",r"C:\Windows")
        // Windows known-folder lookup needs SYSTEMDRIVE even when ProgramData
        // is explicitly populated. Without it .NET returns an empty common
        // application-data path and Chocolatey creates a relative HTTP cache.
        .env("SYSTEMDRIVE", "C:")
        .env("ComSpec",r"C:\Windows\System32\cmd.exe")
        .env("ProgramData",r"C:\ProgramData").env("ALLUSERSPROFILE",r"C:\ProgramData")
        .env("ProgramFiles",r"C:\Program Files").env("ProgramFiles(x86)",r"C:\Program Files (x86)")
        .env("ChocolateyInstall",r"C:\ProgramData\chocolatey")
        .env("TEMP", &temp).env("TMP", &temp)
        .env("USERPROFILE",r"C:\Windows\System32\config\systemprofile")
        .env("APPDATA",r"C:\Windows\System32\config\systemprofile\AppData\Roaming")
        .env("LOCALAPPDATA",r"C:\Windows\System32\config\systemprofile\AppData\Local")
        .env("PSModulePath",r"C:\Windows\System32\WindowsPowerShell\v1.0\Modules;C:\Program Files\WindowsPowerShell\Modules")
        .env("PATHEXT",".COM;.EXE;.BAT;.CMD").env("PROCESSOR_ARCHITECTURE","AMD64");
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
        .arg(powershell_path(&root.join("windows").join(name)));
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
    #[cfg(windows)]
    static CHOCOLATEY_TEST_LOCK: std::sync::Mutex<()> = std::sync::Mutex::new(());
    #[cfg(windows)]
    #[test]
    fn github_runner_migrates_real_node26_to_node24_with_clean_environment() {
        if std::env::var("GITHUB_ACTIONS").as_deref() != Ok("true") {
            return;
        }
        let _guard = CHOCOLATEY_TEST_LOCK.lock().unwrap();
        let temp =
            std::env::temp_dir().join(format!("Skyview Node migration {}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(&temp).unwrap();
        let test = Path::new(env!("CARGO_MANIFEST_DIR"))
            .join("../../tests/Test-Node24MigrationCI.ps1")
            .canonicalize()
            .unwrap();
        let mut cmd = Command::new(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe");
        cmd.args([
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
        ])
        .arg(powershell_path(&test));
        windows_system_environment(&mut cmd, &temp);
        cmd.env("GITHUB_ACTIONS", "true");
        let mut lines = Vec::new();
        assert_eq!(
            stream(cmd, |line| lines.push(line)).unwrap(),
            0,
            "{lines:?}"
        );
        assert!(lines.iter().any(|line| line == "SKYVIEW_NODE_MIGRATION_OK"));
        assert!(lines.iter().any(|line| line == "SKYVIEW_SYSTEM_SETUP_OK"));
    }
    #[cfg(windows)]
    #[test]
    fn powershell_scripts_use_provider_compatible_paths() {
        let c = script(
            Path::new(r"\\?\C:\Program Files\Skyview Dev Setup\backend"),
            "chocolatey/tools/Test-SkyviewStudentDev.ps1",
        );
        assert_eq!(
            Path::new(c.get_args().last().unwrap()),
            Path::new(
                r"C:\Program Files\Skyview Dev Setup\backend\windows\chocolatey\tools\Test-SkyviewStudentDev.ps1"
            )
        );
        assert_eq!(
            powershell_path(Path::new(r"\\?\UNC\server\share\backend")),
            PathBuf::from(r"\\server\share\backend")
        );
        assert_eq!(
            powershell_path(Path::new(r"C:\Program Files\backend")),
            PathBuf::from(r"C:\Program Files\backend")
        );
    }
    #[cfg(windows)]
    #[test]
    fn packaged_powershell_relative_lookups_work_with_verbatim_roots() {
        let root = std::env::temp_dir().join(format!("Skyview path test {}", uuid::Uuid::new_v4()));
        let scripts = root.join("windows");
        std::fs::create_dir_all(&scripts).unwrap();
        std::fs::write(scripts.join("marker.txt"), "fixture").unwrap();
        std::fs::write(scripts.join("probe.ps1"), "$ErrorActionPreference='Stop'; $marker=Join-Path $PSScriptRoot 'marker.txt'; if (-not (Test-Path $marker)) { exit 1 }; Write-Output 'relative-lookup-ok'; exit 0").unwrap();
        let verbatim = root.canonicalize().unwrap();
        let mut lines = Vec::new();
        assert_eq!(
            stream(script(&verbatim, "probe.ps1"), |line| lines.push(line)).unwrap(),
            0
        );
        assert!(lines.iter().any(|line| line == "relative-lookup-ok"));
    }
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
    #[cfg(windows)]
    #[test]
    fn clean_system_environment_resolves_machine_folders_and_temp() {
        let root =
            std::env::temp_dir().join(format!("Skyview environment test {}", uuid::Uuid::new_v4()));
        let scripts = root.join("windows");
        std::fs::create_dir_all(&scripts).unwrap();
        std::fs::write(scripts.join("environment.ps1"), r#"$ErrorActionPreference='Stop'; $data=[Environment]::GetFolderPath('CommonApplicationData'); if ($data -ne 'C:\ProgramData' -or -not [IO.Path]::IsPathRooted($data)) { throw 'Machine data folder not resolved' }; if ($env:SKYVIEW_UNTRUSTED) { throw 'User environment leaked' }; $marker=Join-Path $env:TEMP 'environment-marker.txt'; [IO.File]::WriteAllText($marker,'probe'); if (-not (Test-Path $marker)) { throw 'Temporary path unusable' }; Write-Output 'machine-environment-ok'; exit 0"#).unwrap();
        let root = root.canonicalize().unwrap();
        let mut cmd = script(&root, "environment.ps1");
        cmd.env("SKYVIEW_UNTRUSTED", "must-not-reach-child");
        windows_system_environment(&mut cmd, &root);
        let mut lines = Vec::new();
        assert_eq!(
            stream(cmd, |line| lines.push(line)).unwrap(),
            0,
            "{lines:?}"
        );
        assert!(lines.iter().any(|line| line == "machine-environment-ok"));
    }
    #[cfg(windows)]
    #[test]
    fn github_runner_installs_chocolatey_fixture_with_clean_environment() {
        // Real package-manager coverage only on the disposable Windows runner,
        // never on a developer/student workstation. The fixture has no tools or
        // dependencies and changes only Chocolatey's own test package records.
        if std::env::var("GITHUB_ACTIONS").as_deref() != Ok("true") {
            return;
        }
        let _guard = CHOCOLATEY_TEST_LOCK.lock().unwrap();
        let root =
            std::env::temp_dir().join(format!("Skyview Chocolatey test {}", uuid::Uuid::new_v4()));
        std::fs::create_dir_all(root.join("tools")).unwrap();
        std::fs::write(root.join("tools/chocolateyInstall.ps1"), "if ([Environment]::GetFolderPath('CommonApplicationData') -ne 'C:\\ProgramData') { throw 'Incorrect machine cache root' }; Write-Host 'SKYVIEW_CI_PACKAGE_OK'").unwrap();
        std::fs::write(root.join("fixture.nuspec"), r#"<?xml version="1.0"?><package><metadata><id>skyview-ci-environment-probe</id><version>1.0.0</version><authors>Skyview Robotics</authors><description>Disposable CI environment probe</description></metadata><files><file src="tools\**" target="tools"/></files></package>"#).unwrap();
        let root = root.canonicalize().unwrap();
        let choco = r"C:\ProgramData\chocolatey\bin\choco.exe";
        let mut pack = Command::new(choco);
        pack.current_dir(&root)
            .arg("pack")
            .arg(powershell_path(&root.join("fixture.nuspec")))
            .arg("--outputdirectory")
            .arg(powershell_path(&root));
        windows_system_environment(&mut pack, &root);
        let mut output = Vec::new();
        assert_eq!(
            stream(pack, |line| output.push(line)).unwrap(),
            0,
            "{output:?}"
        );
        let mut install = Command::new(choco);
        install
            .current_dir(&root)
            .args([
                "install",
                "skyview-ci-environment-probe",
                "--yes",
                "--source",
            ])
            .arg(powershell_path(&root));
        windows_system_environment(&mut install, &root);
        output.clear();
        assert_eq!(
            stream(install, |line| output.push(line)).unwrap(),
            0,
            "{output:?}"
        );
        assert!(
            output
                .iter()
                .any(|line| line.contains("SKYVIEW_CI_PACKAGE_OK")),
            "{output:?}"
        );
        let mut uninstall = Command::new(choco);
        uninstall
            .current_dir(&root)
            .args(["uninstall", "skyview-ci-environment-probe", "--yes"]);
        windows_system_environment(&mut uninstall, &root);
        output.clear();
        assert_eq!(
            stream(uninstall, |line| output.push(line)).unwrap(),
            0,
            "{output:?}"
        );
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
    cmd.current_dir(&backend);
    // Privileged commands use a system-only search path and no user startup code.
    #[cfg(windows)]
    {
        let private_temp = backend
            .parent()
            .unwrap()
            .join("operation-temp")
            .join(session);
        std::fs::create_dir_all(&private_temp).map_err(|e| e.to_string())?;
        windows_system_environment(&mut cmd, &private_temp);
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
        let mut pending = Vec::new();
        let mut helper_exit = None;
        loop {
            if let Ok(mut file) = std::fs::File::open(&log) {
                file.seek(SeekFrom::Start(offset))
                    .map_err(|e| e.to_string())?;
                let mut chunk = Vec::new();
                file.read_to_end(&mut chunk).map_err(|e| e.to_string())?;
                offset += chunk.len() as u64;
                pending.extend(chunk);
                while let Some(end) = pending.iter().position(|b| *b == b'\n') {
                    let bytes: Vec<_> = pending.drain(..=end).collect();
                    let line = String::from_utf8_lossy(&bytes)
                        .trim_end_matches(['\r', '\n'])
                        .to_owned();
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
                    for line in String::from_utf8_lossy(&text.as_bytes()[offset as usize..]).lines()
                    {
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
