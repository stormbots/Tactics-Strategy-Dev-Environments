use super::*;
use crate::{
    inspection::test_facts,
    mutation::{self, BeginError, Scope},
    recovery::{acknowledgment, restart},
    safety::{Activity, Decision, PackageHealth},
    tests::{interrupted_fixture, Fixture},
};

const OLD: &str = "linux:9fe3858b-58da-4b96-b47d-ec2f1b867353";
const NEW: &str = "linux:52c95da7-e764-405c-84de-a1b435042916";

#[test]
fn mutation_supervised_child_probe() {
    let Some(path) = std::env::var_os("SDE_TEST_MUTATION_CHILD_DIR") else {
        return;
    };
    let dir = std::path::PathBuf::from(path);
    assert_eq!(
        acquire_at(&dir, "operations.gate", false).unwrap_err(),
        Error::Busy
    );
    #[cfg(windows)]
    {
        let value: serde_json::Value =
            serde_json::from_slice(&std::fs::read(dir.join("transaction.json")).unwrap()).unwrap();
        // Do not print either private value, even on assertion failure.
        assert!(
            std::env::var("SKYVIEW_TRANSACTION_TOKEN").ok().as_deref()
                == value.get("token").and_then(|v| v.as_str())
        );
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        for (variable, gate) in [
            ("SKYVIEW_SESSION_FD", "sessions.gate"),
            ("SKYVIEW_OPERATION_FD", "operations.gate"),
        ] {
            let fd: i32 = std::env::var(variable).unwrap().parse().unwrap();
            let mut stat = std::mem::MaybeUninit::<libc::stat>::uninit();
            assert_eq!(unsafe { libc::fstat(fd, stat.as_mut_ptr()) }, 0);
            let stat = unsafe { stat.assume_init() };
            let metadata = std::fs::metadata(dir.join(gate)).unwrap();
            assert_eq!(stat.st_ino, metadata.ino());
            assert_eq!(stat.st_dev, metadata.dev());
            assert_eq!(
                unsafe { libc::fcntl(fd, libc::F_GETFD) } & libc::FD_CLOEXEC,
                0
            );
        }
    }
}

#[test]
fn mutation_supervised_child_inherits_coordination_but_exit_never_clears_intent() {
    let Some(f) = Fixture::new() else { return };
    let mut guard = mutation::begin_at(&f.path, Scope::System, || {
        facts(Activity::Inactive, PackageHealth::Healthy, None)
    })
    .unwrap();
    #[cfg(unix)]
    let before = guard
        .test_lease_fds()
        .map(|fd| unsafe { libc::fcntl(fd, libc::F_GETFD) });
    let mut command = std::process::Command::new(std::env::current_exe().unwrap());
    command
        .args([
            "--exact",
            "mutation_tests::mutation_supervised_child_probe",
            "--nocapture",
        ])
        .env("SDE_TEST_MUTATION_CHILD_DIR", &f.path);
    assert!(guard
        .run_with_probe(command, || facts(
            Activity::Inactive,
            PackageHealth::Unknown,
            None
        ))
        .unwrap()
        .success());
    #[cfg(unix)]
    {
        let after = guard
            .test_lease_fds()
            .map(|fd| unsafe { libc::fcntl(fd, libc::F_GETFD) });
        assert_eq!(before, after);
        assert!(after.iter().all(|flags| flags & libc::FD_CLOEXEC != 0));
    }
    assert_eq!(no_interruption(&f.path).unwrap_err(), Error::Interrupted);
    guard.finish_known().unwrap();
    assert!(!f.path.join("transaction.json").exists());
}

#[test]
fn mutation_retirement_collision_preserves_both_original_and_existing_destination() {
    let Some(f) = Fixture::new() else { return };
    let (original, id) = submitted(&f);
    acknowledgment::record_at(&f.path, |_| Ok(())).unwrap();
    let destination = f
        .path
        .join("recovery-archive")
        .join(format!("{id}.retired-journal"));
    std::fs::copy(f.path.join("transaction.json"), &destination).unwrap();
    assert!(mutation::begin_at(&f.path, Scope::System, || facts(
        Activity::Inactive,
        PackageHealth::Healthy,
        Some(NEW)
    ))
    .is_err());
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
    assert_eq!(std::fs::read(destination).unwrap(), original);
}

fn submitted(f: &Fixture) -> (Vec<u8>, String) {
    let original = interrupted_fixture(f);
    let incident = recovery::prepare_at(&f.path).unwrap().unwrap();
    recovery::submit_at(&f.path, &incident.incident_id).unwrap();
    restart::set_test_context(&f.path, &incident.incident_id, Some(OLD.into()));
    (original, incident.incident_id)
}

fn facts(activity: Activity, health: PackageHealth, boot: Option<&str>) -> inspection::NativeFacts {
    test_facts(activity, health, boot.map(str::to_string))
}

#[test]
fn mutation_restart_does_not_replace_acknowledgment_or_clear_unknown_same_boot_state() {
    for boot in [Some(OLD), None] {
        let Some(f) = Fixture::new() else { return };
        let (original, _) = submitted(&f);
        let error = mutation::begin_at(&f.path, Scope::System, || {
            facts(Activity::Inactive, PackageHealth::Healthy, boot)
        })
        .unwrap_err();
        assert!(
            matches!(error, BeginError::Safety(ref observation) if observation.decision == Decision::BlockActivityUnknown)
        );
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        assert!(!f.path.join("recovery-archive").exists());
    }
    let Some(f) = Fixture::new() else { return };
    let original = interrupted_fixture(&f);
    let incident = recovery::prepare_at(&f.path).unwrap().unwrap();
    restart::set_test_context(&f.path, &incident.incident_id, Some(OLD.into()));
    assert!(matches!(
        mutation::begin_at(&f.path, Scope::System, || facts(
            Activity::Inactive,
            PackageHealth::Healthy,
            Some(NEW)
        )),
        Err(BeginError::Coordination(Error::Interrupted))
    ));
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
}

#[test]
fn mutation_known_activity_unknown_activity_and_incomplete_health_never_retire_evidence() {
    for (activity, health, expected) in [
        (
            Activity::Active,
            PackageHealth::Healthy,
            Decision::BlockActive,
        ),
        (
            Activity::Unknown,
            PackageHealth::Healthy,
            Decision::BlockActivityUnknown,
        ),
        (
            Activity::Inactive,
            PackageHealth::Incomplete,
            Decision::BlockIncomplete,
        ),
    ] {
        let Some(f) = Fixture::new() else { return };
        let (original, _) = submitted(&f);
        let error = mutation::begin_at(&f.path, Scope::System, || {
            facts(activity, health, Some(NEW))
        })
        .unwrap_err();
        assert!(
            matches!(error, BeginError::Safety(ref observation) if observation.decision == expected)
        );
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
    }
}

#[test]
fn mutation_rechecks_after_acknowledgment_persistence_before_retiring_the_original() {
    let Some(f) = Fixture::new() else { return };
    let (original, _) = submitted(&f);
    let mut count = 0;
    let error = mutation::begin_at(&f.path, Scope::System, || {
        count += 1;
        facts(
            if count == 1 {
                Activity::Inactive
            } else {
                Activity::Active
            },
            PackageHealth::Healthy,
            Some(NEW),
        )
    })
    .unwrap_err();
    assert!(
        matches!(error, BeginError::Safety(ref observation) if observation.decision == Decision::BlockActive)
    );
    assert_eq!(count, 2);
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
    assert!(acknowledgment::inspect_at(&f.path).unwrap().is_some());
}

#[test]
fn mutation_retains_original_object_and_receipt_then_creates_distinct_new_intent_under_the_lease() {
    for health in [PackageHealth::Healthy, PackageHealth::Unknown] {
        let Some(f) = Fixture::new() else { return };
        let (original, id) = submitted(&f);
        let guard = mutation::begin_at(&f.path, Scope::System, || {
            facts(Activity::Inactive, health, Some(NEW))
        })
        .unwrap();
        assert_eq!(
            std::fs::read(
                f.path
                    .join("recovery-archive")
                    .join(format!("{id}.retired-journal"))
            )
            .unwrap(),
            original
        );
        assert_eq!(
            std::fs::read(
                f.path
                    .join("recovery-archive")
                    .join(format!("{id}.journal"))
            )
            .unwrap(),
            original
        );
        assert_eq!(
            acquire_at(&f.path, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        let current: serde_json::Value =
            serde_json::from_slice(&std::fs::read(f.path.join("transaction.json")).unwrap())
                .unwrap();
        assert_ne!(current.get("id"), current.get("token"));
        assert!(current.get("id").is_some());
        drop(guard);
        assert_eq!(no_interruption(&f.path).unwrap_err(), Error::Interrupted);
        let next = recovery::prepare_at(&f.path).unwrap().unwrap();
        assert_ne!(next.incident_id, id);
        let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
        assert!(!recovery::pending_at(&f.path).unwrap());
    }
}

#[test]
fn mutation_installation_scope_respects_gui_sessions_and_system_scope_does_not_exclude_them() {
    let Some(f) = Fixture::new() else { return };
    let _gui = acquire_at(&f.path, "sessions.gate", true).unwrap();
    assert!(matches!(
        mutation::begin_at(&f.path, Scope::Installation, || facts(
            Activity::Inactive,
            PackageHealth::Healthy,
            None
        )),
        Err(BeginError::Coordination(Error::Busy))
    ));
    let guard = mutation::begin_at(&f.path, Scope::System, || {
        facts(Activity::Inactive, PackageHealth::Healthy, None)
    })
    .unwrap();
    guard.finish_known().unwrap();
    assert!(!f.path.join("transaction.json").exists());
}

#[test]
fn mutation_finish_known_cannot_remove_a_different_transaction() {
    let Some(f) = Fixture::new() else { return };
    let guard = mutation::begin_at(&f.path, Scope::System, || {
        facts(Activity::Inactive, PackageHealth::Healthy, None)
    })
    .unwrap();
    let path = f.path.join("transaction.json");
    let mut value: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
    value["id"] = serde_json::json!("changed by another privileged fixture actor");
    std::fs::write(&path, serde_json::to_vec(&value).unwrap()).unwrap();
    assert_eq!(guard.finish_known().unwrap_err(), Error::Interrupted);
    assert!(path.exists());
}

#[test]
fn mutation_run_rechecks_current_native_activity_and_aborts_before_any_child_is_started() {
    let Some(f) = Fixture::new() else { return };
    let mut guard = mutation::begin_at(&f.path, Scope::System, || {
        facts(Activity::Inactive, PackageHealth::Healthy, None)
    })
    .unwrap();
    let never_run = std::process::Command::new("this-command-must-never-be-started");
    assert!(matches!(
        guard.run_with_probe(never_run, || facts(
            Activity::Active,
            PackageHealth::Unknown,
            None
        )),
        Err(BeginError::Coordination(Error::Busy))
    ));
    assert!(!f.path.join("transaction.json").exists());
}

#[test]
fn mutation_observation_reports_unknown_without_turning_it_into_false_inactivity() {
    let Some(f) = Fixture::new() else { return };
    let (_, id) = submitted(&f);
    let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
    let snapshot = observations::collect_locked(
        &f.path,
        true,
        facts(Activity::Inactive, PackageHealth::Unknown, Some(OLD)),
    )
    .unwrap();
    assert_eq!(snapshot.activity, Activity::Unknown);
    assert_eq!(snapshot.decision, Decision::BlockActivityUnknown);
    restart::set_test_context(&f.path, &id, None);
    let missing = observations::collect_locked(
        &f.path,
        true,
        facts(Activity::Inactive, PackageHealth::Healthy, Some(NEW)),
    )
    .unwrap();
    assert_eq!(missing.activity, Activity::Unknown);
}
