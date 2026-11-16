//! Ordinary Windows/Linux editor launch only. Never an elevated command or update permit.
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::{
    fs::File,
    io::Read,
    path::{Path, PathBuf},
    process::{Command, Stdio},
    sync::{mpsc, Mutex},
    time::{Duration, Instant},
};

#[cfg(unix)]
use std::os::unix::fs::PermissionsExt;
#[cfg(windows)]
const EXECUTABLE: &str = "VSCodium.exe";
#[cfg(not(windows))]
const EXECUTABLE: &str = "codium";
#[cfg(windows)]
const PLATFORM: &str = "windows";
#[cfg(not(windows))]
const PLATFORM: &str = "linux";

const FILES: [&str; 3] = [
    "resources/app/product.json",
    "resources/app/package.json",
    "resources/app/out/cli.js",
];
const LIMITS: [u64; 4] = [536_870_912, 1_048_576, 1_048_576, 16_777_216];
static OPEN_REQUEST: Mutex<()> = Mutex::new(());

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Observation {
    schema: u32,
    component: String,
    platform: String,
    status: String,
    reason: String,
    root: Option<String>,
    executable: Option<String>,
    cli: Option<String>,
    version: Option<String>,
    electron_version: Option<String>,
    selection_id: Option<String>,
    maintenance_eligibility: String,
}

fn valid_id(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}
#[cfg(windows)]
fn ordinary_role() -> bool {
    use windows_sys::Win32::Security::*;
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
            && member == 0
    }
}
#[cfg(not(windows))]
fn ordinary_role() -> bool {
    (unsafe { libc::geteuid() }) != 0
}
fn ordinary_user() -> Result<(), String> {
    if ordinary_role() {
        Ok(())
    } else {
        Err("Open SDE from your normal desktop account to open the editor. Administrator privileges are not used for this action.".into())
    }
}
fn canonical(path: &Path) -> std::io::Result<PathBuf> {
    let canonical = path.canonicalize()?;
    #[cfg(windows)]
    {
        // Match the local-drive spelling emitted by Electron; UNC is unsupported.
        let value = canonical.to_str().ok_or(std::io::ErrorKind::InvalidData)?;
        let value = value.strip_prefix(r"\\?\").unwrap_or(value);
        if value.as_bytes().get(1) != Some(&b':') || !value.as_bytes()[0].is_ascii_alphabetic() {
            return Err(std::io::ErrorKind::InvalidData.into());
        }
        return Ok(PathBuf::from(value));
    }
    #[cfg(not(windows))]
    Ok(canonical)
}
fn launcher_signature(executable: &Path) -> Result<(), String> {
    let mut file = File::open(executable).map_err(|_| "The editor launcher could not be read.")?;
    #[cfg(windows)]
    {
        use std::io::{Seek, SeekFrom};
        let mut header = [0u8; 64];
        file.read_exact(&mut header)
            .map_err(|_| "The editor launcher is incomplete.")?;
        let offset = u32::from_le_bytes(header[60..64].try_into().unwrap()) as u64;
        if &header[..2] != b"MZ" || !(64..=4096).contains(&offset) {
            return Err("The editor launcher could not be verified.".into());
        }
        file.seek(SeekFrom::Start(offset))
            .map_err(|_| "The editor launcher is incomplete.")?;
        let mut signature = [0u8; 4];
        file.read_exact(&mut signature)
            .map_err(|_| "The editor launcher is incomplete.")?;
        if signature != *b"PE\0\0" {
            return Err("The editor launcher could not be verified.".into());
        }
    }
    #[cfg(not(windows))]
    {
        let mut signature = [0u8; 4];
        file.read_exact(&mut signature)
            .map_err(|_| "The editor launcher could not be read.")?;
        if signature != *b"\x7fELF"
            || executable
                .metadata()
                .map_err(|_| "The editor launcher is unavailable.")?
                .permissions()
                .mode()
                & 0o111
                == 0
        {
            return Err("The editor launcher could not be verified.".into());
        }
    }
    Ok(())
}
fn path(value: &Option<String>) -> Result<PathBuf, String> {
    let value = value.as_deref().ok_or("Editor location is incomplete.")?;
    if value.len() > 4096 || value.chars().any(|c| c.is_control() || c == '|') {
        return Err("Editor location is unsupported.".into());
    }
    let path = PathBuf::from(value);
    if !path.is_absolute() || canonical(&path).ok().as_ref() != Some(&path) {
        return Err(
            "The editor location changed. Check the editor again before opening it.".into(),
        );
    }
    Ok(path)
}
fn limited(path: &Path, maximum: u64) -> Result<Vec<u8>, String> {
    let file = File::open(path).map_err(|_| "The editor files could not be read.")?;
    if !file
        .metadata()
        .map_err(|_| "Editor file information is unavailable.")?
        .is_file()
    {
        return Err("The editor files could not be verified.".into());
    }
    let mut bytes = Vec::new();
    file.take(maximum + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "The editor files could not be read.")?;
    if bytes.len() as u64 > maximum {
        return Err("Editor inspection reached its file limit.".into());
    }
    Ok(bytes)
}
fn hash(path: &Path, maximum: u64) -> Result<String, String> {
    let mut file = File::open(path).map_err(|_| "The editor files could not be read.")?;
    let info = file
        .metadata()
        .map_err(|_| "Editor file information is unavailable.")?;
    if !info.is_file() || info.len() > maximum {
        return Err("Editor inspection reached its file limit.".into());
    }
    let mut digest = Sha256::new();
    let mut bytes = [0u8; 65536];
    let mut total = 0u64;
    loop {
        let count = file
            .read(&mut bytes)
            .map_err(|_| "The editor files could not be read.")?;
        if count == 0 {
            break;
        }
        total += count as u64;
        if total > maximum {
            return Err("Editor inspection reached its file limit.".into());
        }
        digest.update(&bytes[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn verify_current(record: &Observation) -> Result<PathBuf, String> {
    if record.schema != 1
        || record.component != "VSCodium"
        || record.platform != PLATFORM
        || record.status != "verified"
        || record.reason != "verified"
        || record.maintenance_eligibility != "notEvaluated"
    {
        return Err("SDE could not verify an editor installation. Open it from your desktop, or check the editor again.".into());
    }
    let root = path(&record.root)?;
    let executable = path(&record.executable)?;
    let cli = path(&record.cli)?;
    if executable != root.join(EXECUTABLE) || cli != root.join(FILES[2]) {
        return Err("The editor launch target did not match its checked installation.".into());
    }
    for relative in FILES {
        let expected = root.join(relative);
        if canonical(&expected).ok().as_ref() != Some(&expected) {
            return Err("The editor files changed. Check the editor again.".into());
        }
    }
    launcher_signature(&executable)?;
    let product: serde_json::Value =
        serde_json::from_slice(&limited(&root.join(FILES[0]), LIMITS[1])?)
            .map_err(|_| "The editor product record could not be read.")?;
    let package: serde_json::Value =
        serde_json::from_slice(&limited(&root.join(FILES[1]), LIMITS[2])?)
            .map_err(|_| "The editor version record could not be read.")?;
    let version = record
        .version
        .as_deref()
        .ok_or("The editor version is unavailable.")?;
    let electron = record
        .electron_version
        .as_deref()
        .ok_or("The editor runtime is unavailable.")?;
    if product["nameShort"] != "VSCodium"
        || product["applicationName"] != "codium"
        || product["quality"] != "stable"
        || package["version"].as_str() != Some(version)
        || version.len() > 80
        || electron.len() > 80
        || !regex::Regex::new(r"^\d+\.\d+\.\d+(?:\.\d+)?$")
            .unwrap()
            .is_match(version)
        || !regex::Regex::new(r"^\d+\.\d+\.\d+(?:[-+][\w.-]+)?$")
            .unwrap()
            .is_match(electron)
    {
        return Err("The checked files do not identify the expected VSCodium installation.".into());
    }
    let id = record
        .selection_id
        .as_deref()
        .filter(|id| valid_id(id))
        .ok_or("The editor selection is incomplete.")?;
    let mut hashes = vec![hash(&executable, LIMITS[0])?];
    for (relative, limit) in FILES.iter().zip(&LIMITS[1..]) {
        hashes.push(hash(&root.join(relative), *limit)?);
    }
    let material = format!(
        "{}\n{}",
        hashes.join("\n"),
        executable.to_str().ok_or("Unsupported editor path.")?
    );
    if format!("{:x}", Sha256::digest(material.as_bytes())) != id {
        return Err(
            "The editor installation changed. Check the editor again before opening it.".into(),
        );
    }
    Ok(executable)
}

fn lookup(root: &Path) -> Result<Observation, String> {
    #[cfg(windows)]
    let mut command =
        crate::process::script(root, "chocolatey/tools/Inspect-SkyviewEditorLocation.ps1");
    #[cfg(not(windows))]
    let mut command = {
        let mut command = Command::new("/usr/bin/python3");
        command
            .arg(root.join("linux/lib/editor_location.py"))
            .arg("--json");
        command
    };
    let mut child = command
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|_| "SDE could not start the editor check.")?;
    let (sender, receiver) = mpsc::channel();
    let stdout = child
        .stdout
        .take()
        .ok_or("Editor check output is unavailable.")?;
    let stderr = child
        .stderr
        .take()
        .ok_or("Editor check output is unavailable.")?;
    for (index, pipe) in [
        (0, Box::new(stdout) as Box<dyn Read + Send>),
        (1, Box::new(stderr) as Box<dyn Read + Send>),
    ] {
        let sender = sender.clone();
        std::thread::spawn(move || {
            let mut bytes = Vec::new();
            let result = pipe.take(32769).read_to_end(&mut bytes);
            let _ = sender.send((index, result.is_ok().then_some(bytes)));
        });
    }
    drop(sender);
    let deadline = Instant::now() + Duration::from_secs(25);
    let mut buffers = [None, None];
    let mut finished = None;
    loop {
        while let Ok((index, bytes)) = receiver.try_recv() {
            buffers[index] = bytes;
        }
        if finished.is_none() {
            finished = child
                .try_wait()
                .map_err(|_| "The editor check could not be observed.")?;
        }
        if finished.is_some() && buffers.iter().all(Option::is_some) {
            break;
        }
        if Instant::now() >= deadline || buffers.iter().flatten().any(|bytes| bytes.len() > 32768) {
            if finished.is_none() {
                // Only our fixed read-only helper, never a package worker.
                let _ = child.kill();
                for _ in 0..25 {
                    if child.try_wait().ok().flatten().is_some() {
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(20));
                }
            }
            return Err("The editor check could not finish. Check the editor again or open it from your desktop.".into());
        }
        std::thread::sleep(Duration::from_millis(20));
    }
    if !finished.is_some_and(|status| status.success()) {
        return Err("SDE could not finish checking the editor installation.".into());
    }
    serde_json::from_slice(
        buffers[0]
            .as_ref()
            .ok_or("Editor check output is unavailable.")?,
    )
    .map_err(|_| "The editor check returned incomplete information.".into())
}

pub fn open(root: &Path, expected: Option<&str>) -> Result<(), String> {
    let _guard = OPEN_REQUEST
        .try_lock()
        .map_err(|_| "An editor open request is already running.")?;
    ordinary_user()?;
    if expected.is_some_and(|id| !valid_id(id)) {
        return Err("The editor selection is invalid. Check the editor again.".into());
    }
    let record = lookup(root)?;
    if expected.is_some_and(|id| record.selection_id.as_deref() != Some(id)) {
        return Err("The editor selection changed or is no longer available. Check the editor again before opening it.".into());
    }
    let executable = verify_current(&record)?;
    Command::new(executable)
        .env_remove("ELECTRON_RUN_AS_NODE")
        .env_remove("NODE_OPTIONS")
        .env_remove("NODE_PATH")
        .env_remove("VSCODE_DEV")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|_| {
            "The checked editor could not be opened. It may have moved or changed; check it again."
        })?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Fixture(PathBuf);
    impl Drop for Fixture {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.0);
        }
    }
    impl Fixture {
        fn new() -> (Self, Observation) {
            let root =
                std::env::temp_dir().join(format!("sde editor café {}", uuid::Uuid::new_v4()));
            std::fs::create_dir_all(root.join("resources/app/out")).unwrap();
            let root = canonical(&root).unwrap();
            #[cfg(not(windows))]
            std::fs::write(root.join(EXECUTABLE), b"\x7fELFfixture-never-executed").unwrap();
            #[cfg(windows)]
            {
                let mut bytes = [0u8; 68];
                bytes[..2].copy_from_slice(b"MZ");
                bytes[60] = 64;
                bytes[64..].copy_from_slice(b"PE\0\0");
                std::fs::write(root.join(EXECUTABLE), bytes).unwrap();
            }
            #[cfg(unix)]
            std::fs::set_permissions(
                root.join(EXECUTABLE),
                std::fs::Permissions::from_mode(0o700),
            )
            .unwrap();
            std::fs::write(
                root.join(FILES[0]),
                br#"{"nameShort":"VSCodium","applicationName":"codium","quality":"stable"}"#,
            )
            .unwrap();
            std::fs::write(root.join(FILES[1]), br#"{"version":"1.106.0.25351"}"#).unwrap();
            std::fs::write(root.join(FILES[2]), b"// fixture, never executed").unwrap();
            // Independently compute the documented cross-language fingerprint.
            let hashes: Vec<_> = [EXECUTABLE, FILES[0], FILES[1], FILES[2]]
                .iter()
                .map(|name| {
                    format!(
                        "{:x}",
                        Sha256::digest(std::fs::read(root.join(name)).unwrap())
                    )
                })
                .collect();
            let material = format!("{}\n{}", hashes.join("\n"), root.join(EXECUTABLE).display());
            let record: Observation = serde_json::from_value(serde_json::json!({
                "schema": 1, "component": "VSCodium", "platform": PLATFORM, "status": "verified", "reason": "verified",
                "root": root.to_str(), "executable": root.join(EXECUTABLE).to_str(), "cli": root.join(FILES[2]).to_str(),
                "version": "1.106.0.25351", "electronVersion": "38.0.0", "maintenanceEligibility": "notEvaluated",
                "selectionId": format!("{:x}", Sha256::digest(material.as_bytes()))
            })).unwrap();
            (Self(root), record)
        }
    }
    #[test]
    fn current_selection_rechecks_fixed_files_without_executing_fixture() {
        let (fixture, record) = Fixture::new();
        assert_eq!(verify_current(&record).unwrap(), fixture.0.join(EXECUTABLE));
        std::fs::write(fixture.0.join(FILES[2]), b"changed").unwrap();
        assert!(verify_current(&record).unwrap_err().contains("changed"));
    }
    #[test]
    fn disappeared_target_and_resource_escape_fail_closed() {
        let (fixture, record) = Fixture::new();
        let cli = fixture.0.join(FILES[2]);
        std::fs::remove_file(&cli).unwrap();
        assert!(verify_current(&record).is_err());
        #[cfg(unix)]
        std::os::unix::fs::symlink(fixture.0.join(FILES[1]), cli).unwrap();
        #[cfg(windows)]
        std::os::windows::fs::symlink_file(fixture.0.join(FILES[1]), cli).unwrap();
        assert!(verify_current(&record).is_err());
    }
    #[test]
    fn product_status_and_frontend_path_do_not_authorize_launch() {
        let (fixture, mut record) = Fixture::new();
        record.maintenance_eligibility = "allowed".into();
        assert!(verify_current(&record).is_err());
        record.maintenance_eligibility = "notEvaluated".into();
        record.executable = Some("/bin/sh".into());
        assert!(verify_current(&record).is_err());
        record.executable = Some(fixture.0.join(EXECUTABLE).to_string_lossy().into());
        std::fs::write(fixture.0.join(FILES[0]), br#"{"nameShort":"Other"}"#).unwrap();
        assert!(verify_current(&record).is_err());
    }
    #[test]
    fn selection_is_an_id_not_a_command_or_path() {
        assert!(valid_id(&"a".repeat(64)));
        for value in [
            "/opt/codium",
            "$(codium)",
            "",
            &"A".repeat(64),
            &"a".repeat(65),
        ] {
            assert!(!valid_id(value));
        }
    }
    #[test]
    fn ordinary_user_check_matches_effective_role() {
        assert_eq!(ordinary_user().is_ok(), ordinary_role());
    }
    #[cfg(not(windows))]
    #[test]
    fn helper_output_is_strictly_parsed_and_bounded() {
        let (fixture, _) = Fixture::new();
        let lib = fixture.0.join("linux/lib");
        std::fs::create_dir_all(&lib).unwrap();
        let helper = lib.join("editor_location.py");
        for source in ["print('{}')", "print('x' * 40000)", "raise SystemExit(7)"] {
            std::fs::write(&helper, source).unwrap();
            assert!(lookup(&fixture.0).is_err());
        }
    }
    #[cfg(windows)]
    #[test]
    fn windows_helper_output_is_strictly_parsed_and_bounded() {
        let (fixture, _) = Fixture::new();
        let tools = fixture.0.join("windows/chocolatey/tools");
        std::fs::create_dir_all(&tools).unwrap();
        let helper = tools.join("Inspect-SkyviewEditorLocation.ps1");
        for source in ["Write-Output '{}'", "Write-Output ('x'*40000)", "exit 7"] {
            std::fs::write(&helper, source).unwrap();
            assert!(lookup(&fixture.0).is_err());
        }
    }
}
