//! Already-root Linux shell entry points. No elevation, IPC or consent override.
//! The app dispatches this mode before starting a GUI; nested shell scripts still
//! prove their real inherited descriptors through the existing Python checker.
use crate::{inspection, mutation, safety::known_backend_completion};
use std::{ffi::OsString, path::Path, process::Command};

#[derive(Debug, serde::Serialize)]
#[serde(rename_all = "snake_case", tag = "kind", content = "detail")]
pub enum Failure {
    InvalidInvocation,
    UntrustedEntryPoint,
    Coordination(mutation::BeginError),
    UncertainCompletion,
}

impl Failure {
    pub fn exit_code(&self) -> i32 {
        match self {
            Self::Coordination(mutation::BeginError::Safety(_))
            | Self::Coordination(mutation::BeginError::Coordination(
                crate::Error::Busy | crate::Error::Interrupted,
            )) => 75,
            _ => 76,
        }
    }
}

fn arguments_allowed(script: &Path, args: &[OsString]) -> bool {
    if !script.is_absolute() {
        return false;
    }
    match script.file_name().and_then(|name| name.to_str()) {
        Some("Update-SkyviewStudentDev.sh" | "skyview-student-dev-update") => args.is_empty(),
        Some("Install-SkyviewStudentDev.sh") => {
            if !(1..=2).contains(&args.len()) || args[0] != "--system-only" {
                return false;
            }
            args.get(1).is_none_or(|user| {
                user.to_str().is_some_and(|user| {
                    // Same account grammar as the shell entry point. No shell
                    // interpolation and no extra options or command strings.
                    let name = user.strip_suffix('$').unwrap_or(user);
                    !name.is_empty()
                        && name.bytes().enumerate().all(|(index, c)| {
                            c.is_ascii_alphabetic()
                                || c == b'_'
                                || (index > 0 && (c.is_ascii_digit() || b".-".contains(&c)))
                        })
                })
            })
        }
        _ => false,
    }
}

fn command(script: &Path, args: &[OsString]) -> Result<Command, Failure> {
    use std::os::unix::fs::MetadataExt;
    // Before inspecting private state, executing diagnostics, or launching any
    // script. Student admin/sudo membership alone is NOT an elevated token.
    if unsafe { libc::geteuid() } != 0 || !arguments_allowed(script, args) {
        return Err(Failure::InvalidInvocation);
    }
    crate::validate_dir(script.parent().ok_or(Failure::UntrustedEntryPoint)?)
        .map_err(|_| Failure::UntrustedEntryPoint)?;
    let info = std::fs::symlink_metadata(script).map_err(|_| Failure::UntrustedEntryPoint)?;
    if !info.is_file()
        || info.file_type().is_symlink()
        || info.uid() != 0
        || info.mode() & 0o022 != 0
        || info.nlink() != 1
    {
        return Err(Failure::UntrustedEntryPoint);
    }
    let mut command = Command::new("/bin/bash");
    command
        .arg(script)
        .args(args)
        .env_clear()
        .env("PATH", "/usr/sbin:/usr/bin:/sbin:/bin")
        .env("HOME", "/root")
        .env("LANG", "C.UTF-8");
    Ok(command)
}

/// Only root may select an absolute protected backend file with a supported
/// name/argument shape. There is no privileged GUI handler for caller paths.
/// Normal sudo authentication remains in the original shell workflow.
pub fn run(script: &Path, args: &[OsString]) -> Result<i32, Failure> {
    let command = command(script, args)?;
    run_at(&crate::root(), command, inspection::collect)
}

fn run_at(
    directory: &Path,
    command: Command,
    mut probe: impl FnMut() -> inspection::NativeFacts,
) -> Result<i32, Failure> {
    let mut guard = mutation::begin_at(directory, mutation::Scope::System, &mut probe)
        .map_err(Failure::Coordination)?;
    let status = guard
        .run_with_probe(command, &mut probe)
        .map_err(Failure::Coordination)?;
    let facts = probe();
    if facts.health == crate::safety::PackageHealth::Unknown {
        eprintln!("SKYVIEW_EVENT|warning|package-health|Native package health remains unverified; activity and completion checks still apply.");
    }
    if known_backend_completion(status.success(), facts.activity, facts.health) {
        guard
            .finish_known()
            .map_err(|error| Failure::Coordination(error.into()))?;
    } else {
        eprintln!("SKYVIEW_EVENT|warning|coordination|System transaction retained: completion or native inactivity was not established. No package process was terminated. Review Recovery and Check Again.");
        if status.success() {
            return Err(Failure::UncertainCompletion);
        }
    }
    Ok(status.code().unwrap_or(1))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{
        inspection::test_facts,
        safety::{Activity, PackageHealth},
        tests::Fixture,
    };

    #[test]
    fn manual_coordination_exit_codes_preserve_deferral_and_hard_errors() {
        for (error, expected) in [
            (crate::Error::Busy, 75),
            (crate::Error::Interrupted, 75),
            (crate::Error::Unavailable, 76),
            (crate::Error::Untrusted, 76),
            (crate::Error::NeedsRepair, 76),
        ] {
            let failure = Failure::Coordination(error.into());
            assert_eq!(failure.exit_code(), expected, "{error:?}");
        }
        for failure in [
            Failure::InvalidInvocation,
            Failure::UntrustedEntryPoint,
            Failure::UncertainCompletion,
        ] {
            assert_eq!(failure.exit_code(), 76);
        }
    }

    #[test]
    fn manual_arguments_never_accept_a_shell_command_or_extra_option() {
        for (path, args, allowed) in [
            (
                "/opt/Install-SkyviewStudentDev.sh",
                vec!["--system-only", "student-1$"],
                true,
            ),
            (
                "/opt/Install-SkyviewStudentDev.sh",
                vec!["--system-only"],
                true,
            ),
            ("/opt/Install-SkyviewStudentDev.sh", vec![], false),
            (
                "/opt/Install-SkyviewStudentDev.sh",
                vec!["--system-only", "-student"],
                false,
            ),
            (
                "/opt/Install-SkyviewStudentDev.sh",
                vec!["--system-only", "x; touch /tmp/unsafe"],
                false,
            ),
            ("/opt/Update-SkyviewStudentDev.sh", vec![], true),
            ("/usr/local/sbin/skyview-student-dev-update", vec![], true),
            ("/opt/Update-SkyviewStudentDev.sh", vec!["--skip"], false),
            ("relative/Update-SkyviewStudentDev.sh", vec![], false),
            ("/bin/bash", vec!["-c", "true"], false),
        ] {
            let args = args.into_iter().map(OsString::from).collect::<Vec<_>>();
            assert_eq!(arguments_allowed(Path::new(path), &args), allowed);
        }
    }

    #[test]
    fn manual_non_root_cannot_reach_coordination_or_launch_a_child() {
        if unsafe { libc::geteuid() } == 0 {
            return;
        }
        assert!(matches!(
            run(Path::new("/opt/Update-SkyviewStudentDev.sh"), &[]),
            Err(Failure::InvalidInvocation)
        ));
    }

    fn facts() -> inspection::NativeFacts {
        test_facts(Activity::Inactive, PackageHealth::Unknown, None)
    }

    fn script(f: &Fixture, text: &str) -> std::path::PathBuf {
        use std::os::unix::fs::PermissionsExt;
        let path = f.path.join("Update-SkyviewStudentDev.sh");
        std::fs::write(&path, text).unwrap();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o644)).unwrap();
        path
    }

    #[test]
    fn manual_native_supervision_proves_nesting_and_clears_only_known_success() {
        let Some(f) = Fixture::new() else { return };
        let checker = Path::new(env!("CARGO_MANIFEST_DIR")).join("../linux/lib/coordination.py");
        let body = format!("set -eu\n[ -z \"${{BASH_ENV:-}}\" ]\n/usr/bin/python3 -I - {} {} <<'PY'\nimport importlib.util,sys\nfrom pathlib import Path\ns=importlib.util.spec_from_file_location('coord',sys.argv[1]); c=importlib.util.module_from_spec(s); s.loader.exec_module(c)\nc.ROOT=Path(sys.argv[2]); c.JOURNAL=c.ROOT/'transaction.json'; c.check()\nassert c.JOURNAL.exists()\ntry: c.gate('operations.gate', False)\nexcept BlockingIOError: pass\nelse: raise AssertionError('Native supervisor lost its gate')\nPY\n", checker.display(), f.path.display());
        let path = script(&f, &body);
        assert_eq!(
            run_at(&f.path, command(&path, &[]).unwrap(), facts).unwrap(),
            0
        );
        assert!(!f.path.join("transaction.json").exists());
    }

    #[test]
    fn manual_nonzero_and_signal_retain_journal_and_block_another_launch() {
        for body in ["exit 17\n", "kill -TERM $$\n"] {
            let Some(f) = Fixture::new() else { return };
            let path = script(&f, body);
            let code = run_at(&f.path, command(&path, &[]).unwrap(), facts).unwrap();
            assert_eq!(code, if body.starts_with("exit") { 17 } else { 1 });
            let original = std::fs::read(f.path.join("transaction.json")).unwrap();
            assert!(run_at(&f.path, command(&path, &[]).unwrap(), facts).is_err());
            assert_eq!(
                std::fs::read(f.path.join("transaction.json")).unwrap(),
                original
            );
        }
    }

    #[test]
    fn manual_zero_with_uncertain_postcheck_is_not_completion() {
        let Some(f) = Fixture::new() else { return };
        let path = script(&f, "exit 0\n");
        let mut count = 0;
        let result = run_at(&f.path, command(&path, &[]).unwrap(), || {
            count += 1;
            if count < 3 {
                facts()
            } else {
                test_facts(Activity::Unknown, PackageHealth::Unknown, None)
            }
        });
        assert!(matches!(result, Err(Failure::UncertainCompletion)));
        assert!(f.path.join("transaction.json").exists());
    }

    #[test]
    fn manual_acknowledged_previous_generation_retains_original_evidence() {
        use std::os::unix::fs::MetadataExt;
        let Some(f) = Fixture::new() else { return };
        let original = crate::tests::interrupted_fixture(&f);
        let original_inode = std::fs::metadata(f.path.join("transaction.json"))
            .unwrap()
            .ino();
        let incident = crate::recovery::prepare_at(&f.path).unwrap().unwrap();
        let context = f.path.join("recovery-context.json");
        let mut value: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&context).unwrap()).unwrap();
        value["bootKey"] = serde_json::json!("linux:9fe3858b-58da-4b96-b47d-ec2f1b867353");
        std::fs::write(context, serde_json::to_vec(&value).unwrap()).unwrap();
        let ready = f.path.join("child-ran");
        let path = script(&f, &format!("printf ran > {}\nexit 0\n", ready.display()));
        let observe = || {
            test_facts(
                Activity::Inactive,
                PackageHealth::Unknown,
                Some("linux:52c95da7-e764-405c-84de-a1b435042916".into()),
            )
        };
        // Independent restart evidence allows the consent check, not execution.
        // No submitted intent becomes Coordination(Interrupted); the outer
        // manual protocol must report deferral without clearing any evidence.
        let blocked = run_at(&f.path, command(&path, &[]).unwrap(), observe).unwrap_err();
        assert!(matches!(
            &blocked,
            Failure::Coordination(mutation::BeginError::Coordination(
                crate::Error::Interrupted
            ))
        ));
        assert_eq!(blocked.exit_code(), 75);
        assert!(!ready.exists());
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        assert_eq!(
            std::fs::metadata(f.path.join("transaction.json"))
                .unwrap()
                .ino(),
            original_inode
        );
        assert!(!f.path.join("recovery-archive").exists());
        crate::recovery::submit_at(&f.path, &incident.incident_id).unwrap();
        assert_eq!(
            run_at(&f.path, command(&path, &[]).unwrap(), observe).unwrap(),
            0
        );
        assert!(ready.exists());
        assert!(!f.path.join("transaction.json").exists());
        for suffix in ["journal", "retired-journal"] {
            assert_eq!(
                std::fs::read(
                    f.path
                        .join("recovery-archive")
                        .join(format!("{}.{suffix}", incident.incident_id))
                )
                .unwrap(),
                original
            );
        }
        assert_eq!(
            std::fs::metadata(
                f.path
                    .join("recovery-archive")
                    .join(format!("{}.retired-journal", incident.incident_id))
            )
            .unwrap()
            .ino(),
            original_inode
        );
        assert!(f
            .path
            .join("recovery-archive")
            .join(format!("{}.receipt.json", incident.incident_id))
            .exists());
    }

    #[test]
    fn manual_untrusted_entrypoint_cannot_create_a_transaction() {
        use std::os::unix::fs::{symlink, PermissionsExt};
        let Some(f) = Fixture::new() else { return };
        let path = script(&f, "exit 0\n");
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o666)).unwrap();
        assert!(matches!(
            command(&path, &[]),
            Err(Failure::UntrustedEntryPoint)
        ));
        std::fs::remove_file(&path).unwrap();
        symlink("operations.gate", &path).unwrap();
        assert!(matches!(
            command(&path, &[]),
            Err(Failure::UntrustedEntryPoint)
        ));
        assert!(!f.path.join("transaction.json").exists());
    }

    #[test]
    fn manual_supervisor_process_probe() {
        let Some(directory) = std::env::var_os("SDE_TEST_MANUAL_PROCESS_DIR") else {
            return;
        };
        assert_eq!(unsafe { libc::geteuid() }, 0);
        let directory = std::path::PathBuf::from(directory);
        let path = directory.join("Update-SkyviewStudentDev.sh");
        run_at(&directory, command(&path, &[]).unwrap(), facts).unwrap();
    }

    #[test]
    fn manual_crashed_supervisor_leaves_child_gate_and_unknown_journal() {
        use std::{
            process::Stdio,
            time::{Duration, Instant},
        };
        let Some(f) = Fixture::new() else { return };
        let ready = f.path.join("ready");
        let stop = f.path.join("stop");
        // Always let the harmless test child end naturally, including on panic.
        struct StopChild {
            stop: std::path::PathBuf,
            done: std::path::PathBuf,
        }
        impl Drop for StopChild {
            fn drop(&mut self) {
                let _ = std::fs::write(&self.stop, b"stop");
                // Do not remove the stop file with the fixture before the
                // harmless child can see it, even when a safety assertion fails.
                let deadline = Instant::now() + Duration::from_secs(2);
                while !self.done.exists() && Instant::now() < deadline {
                    std::thread::sleep(Duration::from_millis(20));
                }
            }
        }
        let done = f.path.join("child-done");
        let _stop_child = StopChild {
            stop: stop.clone(),
            done: done.clone(),
        };
        script(
            &f,
            &format!(
                "set -eu\nprintf ready > {}\nwhile [ ! -e {} ]; do /bin/sleep 0.05; done\nprintf done > {}\n",
                ready.display(),
                stop.display(),
                done.display()
            ),
        );
        let mut supervisor = Command::new(std::env::current_exe().unwrap())
            .args([
                "--exact",
                "manual::tests::manual_supervisor_process_probe",
                "--nocapture",
            ])
            .env("SDE_TEST_MANUAL_PROCESS_DIR", &f.path)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .unwrap();
        let deadline = Instant::now() + Duration::from_secs(10);
        while !ready.exists() && Instant::now() < deadline {
            assert!(supervisor.try_wait().unwrap().is_none());
            std::thread::sleep(Duration::from_millis(20));
        }
        assert!(ready.exists(), "Harmless supervised child did not start");
        let original = std::fs::read(f.path.join("transaction.json")).unwrap();
        // Kill only this Rust test supervisor, never an installer/package child.
        supervisor.kill().unwrap();
        supervisor.wait().unwrap();
        assert_eq!(
            crate::acquire_at(&f.path, "operations.gate", false).unwrap_err(),
            crate::Error::Busy
        );
        std::fs::write(&stop, b"stop").unwrap();
        let deadline = Instant::now() + Duration::from_secs(10);
        loop {
            match crate::acquire_at(&f.path, "operations.gate", false) {
                Ok(lease) => {
                    drop(lease);
                    break;
                }
                Err(crate::Error::Busy) if Instant::now() < deadline => {
                    std::thread::sleep(Duration::from_millis(20))
                }
                _ => panic!("Harmless child did not release its lease naturally"),
            }
        }
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        let path = f.path.join("Update-SkyviewStudentDev.sh");
        assert!(run_at(&f.path, command(&path, &[]).unwrap(), facts).is_err());
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
    }
}
