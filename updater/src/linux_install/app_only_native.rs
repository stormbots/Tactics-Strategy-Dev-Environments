//! Explicitly selected root fixture. No test key/input override reaches product code.
use super::*;
use std::{collections::BTreeMap, path::PathBuf};

const PURPOSE: &str = "unpublished-linux-app-only-core-fixture";
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Pins {
    schema_version: u32,
    purpose: String,
    source_commit: String,
    baseline_version: String,
    candidate_version: String,
    files: BTreeMap<String, String>,
    baseline_installed_files: BTreeMap<String, String>,
    package_hooks: BTreeMap<String, String>,
}

fn validate_pins(pins: &Pins) -> Result<()> {
    let expected = [
        format!("baseline/{INSTALLER}"),
        format!("candidate/{INSTALLER}"),
        "candidate/Skyview-Dev-Setup-Windows-x64.exe".into(),
        "native-tests".into(),
    ];
    let installed = [
        "/usr/bin/skyview-dev-setup".to_owned(),
        format!("{BUNDLE}/self-update/bootstrap.py"),
        format!("{BUNDLE}/self-update/sde-update-trust"),
        format!("{BUNDLE}/lib/coordination.py"),
        format!("{BUNDLE}/Update-SkyviewStudentDev.sh"),
    ];
    let digest = |s: &str| {
        s.len() == 64
            && s.bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    };
    if pins.schema_version != 1
        || pins.purpose != PURPOSE
        || pins.baseline_version != "1.2.1"
        || pins.candidate_version != "1.2.2"
        || pins.source_commit.len() != 40
        || !pins.source_commit.bytes().all(|b| b.is_ascii_hexdigit())
        || pins.files.len() != expected.len()
        || !expected.iter().all(|name| pins.files.contains_key(name))
        || pins.baseline_installed_files.len() != installed.len()
        || !installed
            .iter()
            .all(|name| pins.baseline_installed_files.contains_key(name))
        || pins.package_hooks.len() != 2
        || !["/postinst", "/prerm"]
            .iter()
            .all(|name| pins.package_hooks.contains_key(*name))
        || !pins
            .files
            .values()
            .chain(pins.baseline_installed_files.values())
            .chain(pins.package_hooks.values())
            .all(|value| digest(value))
    {
        return Err("Invalid native fixture pins; no package operation permitted".into());
    }
    Ok(())
}

fn preserved() -> BTreeMap<String, Option<(u64, String)>> {
    [
        "/usr/local/sbin/skyview-student-dev-update",
        "/usr/local/lib/skyview-student-dev/coordination.py",
        "/usr/local/lib/skyview-student-dev/coordination.sh",
        "/usr/local/lib/skyview-student-dev/common.sh",
        "/usr/local/lib/skyview-student-dev/tool_records.py",
        "/var/lib/skyview-robotics/student-dev/version",
        "/var/lib/skyview-robotics/self-update/policy.json",
        "/etc/systemd/system/skyview-student-dev-update.service",
        "/etc/systemd/system/skyview-student-dev-update.timer",
        "/etc/systemd/system/skyview-student-dev-update.service.d/sde-self-update.conf",
    ]
    .into_iter()
    .map(|name| {
        let path = Path::new(name);
        let value = match std::fs::symlink_metadata(path) {
            Ok(_) => {
                trusted_file(path).unwrap();
                Some(crate::hash_file(path).unwrap())
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
            Err(e) => panic!("Preservation state unavailable: {e}"),
        };
        (name.to_owned(), value)
    })
    .collect()
}

fn other_packages() -> Vec<u8> {
    let result = command("/usr/bin/dpkg-query")
        .args([
            "-W",
            "-f=${binary:Package}\t${Version}\t${db:Status-Status}\n",
        ])
        .output()
        .unwrap();
    assert!(result.status.success());
    String::from_utf8(result.stdout)
        .unwrap()
        .lines()
        .filter(|line| !line.starts_with("skyview-dev-setup\t"))
        .collect::<Vec<_>>()
        .join("\n")
        .into_bytes()
}

fn timer_state() -> Vec<u8> {
    // Read-only, bounded inspection. This never starts/enables/reloads a unit.
    let output = command("/usr/bin/timeout")
        .args([
            "10s",
            "/usr/bin/systemctl",
            "show",
            "skyview-student-dev-update.timer",
            "-p",
            "LoadState",
            "-p",
            "ActiveState",
            "-p",
            "UnitFileState",
        ])
        .output()
        .unwrap();
    assert!(
        output.status.success(),
        "Timer state must be observable before the upgrade"
    );
    output.stdout
}

#[test]
#[ignore = "Requires reviewed root deployment, artifact hashes and one native package upgrade authorization"]
fn pinned_app_only_upgrade() {
    assert_eq!(
        std::env::var("SDE_RUN_APP_ONLY_NATIVE").as_deref(),
        Ok(PURPOSE)
    );
    assert_eq!(unsafe { libc::geteuid() }, 0);
    let directory = PathBuf::from(
        std::env::var_os("SDE_APP_ONLY_FIXTURE_DIR").expect("Pinned root-private fixture required"),
    );
    let canonical = directory.canonicalize().unwrap();
    assert_eq!(canonical, directory);
    assert_eq!(
        directory.parent(),
        Some(Path::new("/var/lib/sde-app-only-validation"))
    );
    let id = directory.file_name().unwrap().to_str().unwrap();
    assert_eq!(uuid::Uuid::parse_str(id).unwrap().to_string(), id);
    trusted_file(&directory.join("pins.json")).unwrap();
    assert_eq!(
        crate::hash_file(&directory.join("pins.json")).unwrap().1,
        std::env::var("SDE_APP_ONLY_PINS_SHA256").expect("Reviewed pin-file digest required")
    );
    let pins: Pins =
        serde_json::from_slice(&crate::read_bounded(&directory.join("pins.json"), 16384).unwrap())
            .unwrap();
    validate_pins(&pins).unwrap();
    for (name, digest) in &pins.files {
        let path = directory.join(name);
        trusted_file(&path).unwrap();
        assert_eq!(&crate::hash_file(&path).unwrap().1, digest);
    }
    assert_eq!(
        std::env::current_exe().unwrap(),
        directory.join("native-tests")
    );
    // No baseline installation/downgrade, repair, pause change or migration here.
    assert_eq!(host::installed().unwrap().version, pins.baseline_version);
    resources(&pins.baseline_version).unwrap();
    for (name, digest) in &pins.baseline_installed_files {
        trusted_file(Path::new(name)).unwrap();
        assert_eq!(&crate::hash_file(Path::new(name)).unwrap().1, digest);
    }
    assert!(
        !paused().unwrap(),
        "Admin must separately review unpause; fixture never changes policy"
    );
    assert!(
        matches!(std::fs::symlink_metadata(Path::new(ROOT).join("recovery.json")),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound),
        "Do not replace existing or inaccessible recovery evidence with fixture signatures"
    );
    let preserved_before = preserved();
    let packages_before = other_packages();
    let timer_before = timer_state();
    let (boot, started) = crate::linux_request::now().unwrap();
    let session = sde_coordination::session().unwrap();
    let preparation = sde_coordination::prepare_app_only().unwrap();
    assert!(sde_coordination::operation().is_err());
    drop(sde_coordination::session().unwrap());
    let keys = minisign::KeyPair::generate_unencrypted_keypair().unwrap();
    let mut release =
        crate::e2e::Fixture::new(&directory.join("candidate"), &pins.candidate_version, &keys);
    let candidate = release
        .discover(&pins.baseline_version, "linux-amd64")
        .unwrap()
        .unwrap();
    let store = host::store().unwrap();
    let staged = release.stage(&store, &candidate).unwrap();
    let staged = store.join(staged.id);
    assert!(
        authenticate_staged(&staged, &candidate, crate::authenticate).is_err(),
        "Production key must reject the unpublished fixture"
    );
    let (_, ready) = crate::linux_request::now().unwrap();
    let admission = preparation.close_admission().unwrap();
    assert!(sde_coordination::session().is_err());
    let admission = match admission.try_installation() {
        Err((sde_coordination::Error::Busy, retained)) => retained,
        _ => panic!("Existing S must prevent installation while O/A remain held"),
    };
    drop(session);
    let lease = admission.try_installation().unwrap();
    assert!(sde_coordination::session().is_err());
    let guard = || {
        let (current_boot, now) = crate::linux_request::now()?;
        let deadline = (started + 900_000).min(ready + 120_000);
        if current_boot != boot || now < started || now >= deadline {
            return Err("Native fixture precommit deadline expired".into());
        }
        Ok(Duration::from_millis(deadline - now))
    };
    let mut report = Report {
        schema_version: 1,
        phase: crate::observation::Phase::Verification,
        completed_at: None,
        checked_at: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs(),
        application_version: pins.baseline_version.clone(),
        maintenance_engine_version: pins.baseline_version,
        applied_baseline_version: None,
        tool_exit: None,
        outcome: "failed".into(),
        detail: String::new(),
        candidate_version: Some(pins.candidate_version),
        native_exit: None,
        recovery_available: false,
        log_reference: None,
    };
    let observe = |phase| {
        assert!(sde_coordination::session().is_err());
        if matches!(
            phase,
            crate::observation::Phase::Installer | crate::observation::Phase::Postcheck
        ) {
            let scope =
                std::fs::read(sde_coordination::root().join("installation-scope.json")).unwrap();
            let scope: serde_json::Value = serde_json::from_slice(&scope).unwrap();
            assert_eq!(scope["scope"], "app_only");
        }
    };
    install_in_context(
        crate::install_core::Context::app_only(&lease),
        &staged,
        &candidate,
        &mut report,
        |b, s, t| crate::authenticate_with_key(b, s, t, &keys.pk),
        Some(&guard),
        Some(&observe),
    )
    .unwrap();
    assert_eq!(report.outcome, "updated");
    assert_eq!(report.native_exit, Some(0));
    assert_eq!(report.tool_exit, None);
    assert_eq!(preserved(), preserved_before);
    assert_eq!(other_packages(), packages_before);
    assert_eq!(timer_state(), timer_before);
    assert!(!sde_coordination::root().join("transaction.json").exists());
    assert!(!sde_coordination::root()
        .join("installation-scope.json")
        .exists());
    assert!(
        sde_coordination::session().is_err(),
        "Caller retains O/A/S after the core returns"
    );
    drop(lease);
    drop(sde_coordination::session().unwrap());
    println!("SDE_APP_ONLY_CORE_UPGRADE_OK source={} candidateSha256={} nativeExit=0; fixture-key recovery retained, no capability issued, product worker and desktop unproven",
        pins.source_commit, pins.files[&format!("candidate/{INSTALLER}")]);
}

#[test]
fn fixture_pin_schema_cannot_select_other_paths_or_unreviewed_versions() {
    let mut pins = Pins {
        schema_version: 1,
        purpose: PURPOSE.into(),
        source_commit: "a".repeat(40),
        baseline_version: "1.2.1".into(),
        candidate_version: "1.2.2".into(),
        files: BTreeMap::from([
            (format!("baseline/{INSTALLER}"), "a".repeat(64)),
            (format!("candidate/{INSTALLER}"), "a".repeat(64)),
            (
                "candidate/Skyview-Dev-Setup-Windows-x64.exe".into(),
                "a".repeat(64),
            ),
            ("native-tests".into(), "a".repeat(64)),
        ]),
        baseline_installed_files: [
            "/usr/bin/skyview-dev-setup".into(),
            format!("{BUNDLE}/self-update/bootstrap.py"),
            format!("{BUNDLE}/self-update/sde-update-trust"),
            format!("{BUNDLE}/lib/coordination.py"),
            format!("{BUNDLE}/Update-SkyviewStudentDev.sh"),
        ]
        .into_iter()
        .map(|name| (name, "a".repeat(64)))
        .collect(),
        package_hooks: BTreeMap::from([
            ("/postinst".into(), "a".repeat(64)),
            ("/prerm".into(), "a".repeat(64)),
        ]),
    };
    assert!(validate_pins(&pins).is_ok());
    pins.files.remove("native-tests");
    pins.files.insert("../../command".into(), "a".repeat(64));
    assert!(validate_pins(&pins).is_err());
    pins.files.remove("../../command");
    pins.files.insert("native-tests".into(), "a".repeat(64));
    pins.candidate_version = "1.2.3".into();
    assert!(validate_pins(&pins).is_err());
}
