// Reuse the protected native fixture and its serialization lock. None of these
// paths/API overrides ship in the CLI.
use super::*;
use crate::recovery::acknowledgment::{self, Phase};
use crate::tests::{interrupted_fixture, Fixture};
use std::{
    io::Read,
    process::{Command, Stdio},
};

fn submitted_ack_fixture(f: &Fixture) -> (Vec<u8>, String) {
    let original = interrupted_fixture(f);
    let incident = recovery::prepare_at(&f.path).unwrap().unwrap();
    recovery::submit_at(&f.path, &incident.incident_id).unwrap();
    (original, incident.incident_id)
}

fn archive_path(f: &Fixture, id: &str, extension: &str) -> PathBuf {
    f.path
        .join("recovery-archive")
        .join(format!("{id}.{extension}"))
}

fn controller_summary(id: &str) -> crate::recovery_report_store_tests::Summary {
    use crate::recovery_report_store_tests::{Safety, Summary};
    Summary {
        schema: 1,
        report_id: uuid::Uuid::new_v4().to_string(),
        incident_id: id.into(),
        captured_at: 100,
        application_version: "CI".into(),
        platform: "Synthetic native fixture".into(),
        device_name: "CI".into(),
        safety: Safety {
            observed_at: 99,
            trust: "unknown".into(),
            activity: "unknown".into(),
            package_health: "unknown".into(),
            activity_reason: "native_inspection_unavailable".into(),
            decision: "block_trust_unknown".into(),
        },
        validation: None,
        context: None,
    }
}

#[test]
fn acknowledgment_controller_native_report_and_storage_failure_preserve_gate_and_evidence() {
    use crate::{recovery_acknowledgment_flow_tests as flow, recovery_report_store_tests::Store};
    for fail_save in [false, true] {
        let Some(f) = Fixture::new() else { return };
        let original = interrupted_fixture(&f);
        let incident = recovery::prepare_at(&f.path).unwrap().unwrap();
        let store = Store::new(f.path.join("diagnostic-reports")).unwrap();
        let result = flow::run(
            incident.incident_id.clone(),
            true,
            || {
                assert_eq!(
                    recovery::inspect_at(&f.path).unwrap(),
                    Some(incident.clone())
                );
                Ok(controller_summary(&incident.incident_id))
            },
            |summary| {
                if fail_save {
                    Err("simulated disk full".into())
                } else {
                    store.save(summary)
                }
            },
            |id| recovery::submit_at(&f.path, id).map_err(|_| "Submission unconfirmed".into()),
        )
        .unwrap();
        assert_eq!(result.intent_status, flow::IntentStatus::Submitted);
        assert_eq!(result.report_warning.is_some(), fail_save);
        if let Some(report) = result.report_id {
            assert_eq!(
                store.load(&report).unwrap().incident_id,
                incident.incident_id
            );
        } else {
            assert!(fail_save);
        }
        assert!(recovery::pending_at(&f.path).unwrap());
        assert!(acknowledgment::inspect_at(&f.path).unwrap().is_none());
        assert!(!f.path.join("recovery-archive").exists());
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
        assert_eq!(no_interruption(&f.path).unwrap_err(), Error::Interrupted);
    }
}

#[test]
fn acknowledgment_controller_native_live_gate_after_report_retains_report_without_consent() {
    use crate::{recovery_acknowledgment_flow_tests as flow, recovery_report_store_tests::Store};
    let Some(f) = Fixture::new() else { return };
    let original = interrupted_fixture(&f);
    let incident = recovery::prepare_at(&f.path).unwrap().unwrap();
    let store = Store::new(f.path.join("diagnostic-reports")).unwrap();
    let held = std::cell::RefCell::new(None);
    let result = flow::run(
        incident.incident_id.clone(),
        true,
        || Ok(controller_summary(&incident.incident_id)),
        |summary| {
            let id = store.save(summary)?;
            *held.borrow_mut() = Some(acquire_at(&f.path, "operations.gate", false).unwrap());
            Ok(id)
        },
        |id| {
            assert_eq!(recovery::submit_at(&f.path, id).unwrap_err(), Error::Busy);
            Err("Submission unconfirmed; Check Again".into())
        },
    )
    .unwrap();
    drop(held);
    assert_eq!(result.intent_status, flow::IntentStatus::Unconfirmed);
    assert_eq!(
        store.load(&result.report_id.unwrap()).unwrap().incident_id,
        incident.incident_id
    );
    assert!(!recovery::pending_at(&f.path).unwrap());
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
    assert!(!f.path.join("recovery-archive").exists());
    assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
}

#[test]
fn durable_acknowledgment_preserves_evidence_and_survives_intent_loss_and_restart() {
    let Some(f) = Fixture::new() else { return };
    let (original, id) = submitted_ack_fixture(&f);
    let first = acknowledgment::record_at(&f.path, |_| Ok(()))
        .unwrap()
        .unwrap();
    assert_eq!(first.incident_id, id);
    assert_eq!(
        std::fs::read(archive_path(&f, &id, "journal")).unwrap(),
        original
    );
    let receipt = std::fs::read(archive_path(&f, &id, "receipt.json")).unwrap();
    std::fs::write(f.path.join("recovery-acknowledgment.json"), b"{}").unwrap();
    initialize_at(&f.path).unwrap();
    let second = acknowledgment::record_at(&f.path, |_| Ok(()))
        .unwrap()
        .unwrap();
    assert_eq!(first, second);
    assert_eq!(acknowledgment::inspect_at(&f.path).unwrap(), Some(first));
    assert_eq!(
        std::fs::read(archive_path(&f, &id, "receipt.json")).unwrap(),
        receipt
    );
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
    assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
    assert_eq!(no_interruption(&f.path).unwrap_err(), Error::Interrupted);
}

#[test]
fn durable_acknowledgment_is_not_created_without_a_valid_submission() {
    let Some(f) = Fixture::new() else { return };
    interrupted_fixture(&f);
    recovery::prepare_at(&f.path).unwrap();
    assert_eq!(
        acknowledgment::record_at(&f.path, |_| Ok(())).unwrap(),
        None
    );
    assert!(!f.path.join("recovery-archive").exists());
    assert!(!f.path.join("recovery-disposition.json").exists());
    assert_eq!(acknowledgment::inspect_at(&f.path).unwrap(), None);
}

#[test]
fn durable_acknowledgment_recovers_each_failed_publication_checkpoint() {
    for phase in [Phase::Evidence, Phase::Receipt, Phase::PublicSnapshot] {
        let Some(f) = Fixture::new() else { return };
        let (original, id) = submitted_ack_fixture(&f);
        assert_eq!(
            acknowledgment::record_at(&f.path, |current| {
                if current == phase {
                    Err(Error::Unavailable)
                } else {
                    Ok(())
                }
            })
            .unwrap_err(),
            Error::Unavailable
        );
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
        if phase != Phase::Evidence {
            // A committed receipt, not a mutable slot, retains the decision.
            std::fs::write(f.path.join("recovery-acknowledgment.json"), b"{").unwrap();
        }
        let recovered = acknowledgment::record_at(&f.path, |_| Ok(()))
            .unwrap()
            .unwrap();
        assert_eq!(recovered.incident_id, id);
        assert_eq!(
            acknowledgment::inspect_at(&f.path).unwrap(),
            Some(recovered)
        );
        assert_eq!(
            std::fs::read(archive_path(&f, &id, "journal")).unwrap(),
            original
        );
    }
}

#[test]
fn durable_acknowledgment_rejects_corrupted_or_missing_committed_evidence() {
    for remove in [false, true] {
        let Some(f) = Fixture::new() else { return };
        let (original, id) = submitted_ack_fixture(&f);
        acknowledgment::record_at(&f.path, |_| Ok(())).unwrap();
        let evidence = archive_path(&f, &id, "journal");
        if remove {
            std::fs::remove_file(&evidence).unwrap();
        } else {
            std::fs::write(&evidence, b"corrupted archive fixture").unwrap();
        }
        assert_eq!(
            acknowledgment::record_at(&f.path, |_| Ok(())).unwrap_err(),
            Error::Untrusted
        );
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
        if !remove {
            assert_eq!(
                std::fs::read(evidence).unwrap(),
                b"corrupted archive fixture"
            );
        }
    }
}

#[test]
fn durable_acknowledgment_archive_publication_never_replaces_existing_evidence() {
    let Some(f) = Fixture::new() else { return };
    let (original, id) = submitted_ack_fixture(&f);
    acknowledgment::record_at(&f.path, |_| Ok(())).unwrap();
    assert!(acknowledgment::publish_once(
        &f.path.join("recovery-archive"),
        &format!("{id}.journal"),
        b"must never replace the evidence"
    )
    .is_err());
    assert_eq!(
        std::fs::read(archive_path(&f, &id, "journal")).unwrap(),
        original
    );
}

#[test]
fn durable_acknowledgment_old_receipt_cannot_acknowledge_a_replacement_generation() {
    let Some(f) = Fixture::new() else { return };
    let (original, id) = submitted_ack_fixture(&f);
    acknowledgment::record_at(&f.path, |_| Ok(())).unwrap();
    std::fs::rename(
        f.path.join("transaction.json"),
        f.path.join("old-fixture.json"),
    )
    .unwrap();
    assert_eq!(interrupted_fixture(&f), original);
    assert_eq!(
        acknowledgment::record_at(&f.path, |_| Ok(())).unwrap_err(),
        Error::Interrupted
    );
    let new = recovery::prepare_at(&f.path).unwrap().unwrap();
    assert_ne!(id, new.incident_id);
    assert_eq!(acknowledgment::inspect_at(&f.path).unwrap(), None);
    assert_eq!(
        acknowledgment::record_at(&f.path, |_| Ok(())).unwrap(),
        None
    );
    assert_eq!(
        std::fs::read(archive_path(&f, &id, "journal")).unwrap(),
        original
    );
}

#[test]
fn durable_acknowledgment_blocks_while_an_operation_owns_the_gate() {
    let Some(f) = Fixture::new() else { return };
    submitted_ack_fixture(&f);
    let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
    assert_eq!(
        acknowledgment::record_at(&f.path, |_| Ok(())).unwrap_err(),
        Error::Busy
    );
    assert_eq!(
        acknowledgment::inspect_at(&f.path).unwrap_err(),
        Error::Busy
    );
    assert!(!f.path.join("recovery-archive").exists());
}

#[cfg(unix)]
#[test]
fn durable_acknowledgment_archive_cannot_be_a_link_or_writable_directory() {
    use std::os::unix::fs::{symlink, PermissionsExt};
    let Some(f) = Fixture::new() else { return };
    let (original, _) = submitted_ack_fixture(&f);
    let target = f.path.join("unrelated-directory");
    std::fs::create_dir(&target).unwrap();
    let archive = f.path.join("recovery-archive");
    symlink(&target, &archive).unwrap();
    assert_eq!(
        acknowledgment::record_at(&f.path, |_| Ok(())).unwrap_err(),
        Error::Untrusted
    );
    assert_eq!(std::fs::read_dir(&target).unwrap().count(), 0);
    std::fs::remove_file(&archive).unwrap();
    std::fs::create_dir(&archive).unwrap();
    std::fs::set_permissions(&archive, std::fs::Permissions::from_mode(0o777)).unwrap();
    assert_eq!(
        acknowledgment::record_at(&f.path, |_| Ok(())).unwrap_err(),
        Error::Untrusted
    );
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
}

#[cfg(windows)]
#[test]
fn durable_acknowledgment_validates_archive_parent_permissions() {
    let Some(f) = Fixture::new() else { return };
    let (original, _) = submitted_ack_fixture(&f);
    acknowledgment::record_at(&f.path, |_| Ok(())).unwrap();
    assert!(Command::new("icacls.exe")
        .arg(f.path.join("recovery-archive"))
        .args(["/grant", "*S-1-5-32-545:(OI)(CI)M"])
        .output()
        .unwrap()
        .status
        .success());
    assert_eq!(
        acknowledgment::record_at(&f.path, |_| Ok(())).unwrap_err(),
        Error::Untrusted
    );
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
}

#[test]
fn durable_acknowledgment_crash_probe() {
    let Some(dir) = std::env::var_os("SDE_TEST_ACK_DIR") else {
        return;
    };
    let dir = PathBuf::from(dir);
    let name = dir.file_name().unwrap().to_string_lossy();
    assert!(name.starts_with("coordination-test-"));
    #[cfg(unix)]
    assert_eq!(dir.parent().unwrap(), Path::new("/var/lib"));
    #[cfg(windows)]
    assert_eq!(dir.parent().unwrap(), Path::new(r"C:\ProgramData"));
    let phase = match std::env::var("SDE_TEST_ACK_PHASE").unwrap().as_str() {
        "evidence" => Phase::Evidence,
        "receipt" => Phase::Receipt,
        "public" => Phase::PublicSnapshot,
        _ => panic!("Invalid synthetic acknowledgment phase"),
    };
    acknowledgment::record_at(&dir, |current| {
        if current == phase {
            std::fs::write(dir.join("ack-ready"), b"ready").unwrap();
            let mut byte = [0];
            std::io::stdin().read_exact(&mut byte).unwrap();
        }
        Ok(())
    })
    .unwrap();
}

struct SyntheticAckChild(std::process::Child);
impl Drop for SyntheticAckChild {
    fn drop(&mut self) {
        // This is only our disposable test executable, never a package worker.
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

#[test]
fn durable_acknowledgment_survives_process_termination_at_every_commit_boundary() {
    for phase in ["evidence", "receipt", "public"] {
        let Some(f) = Fixture::new() else { return };
        let (original, id) = submitted_ack_fixture(&f);
        let mut child = SyntheticAckChild(
            Command::new(std::env::current_exe().unwrap())
                .args([
                    "--exact",
                    "acknowledgment_tests::durable_acknowledgment_crash_probe",
                    "--nocapture",
                ])
                .env("SDE_TEST_ACK_DIR", &f.path)
                .env("SDE_TEST_ACK_PHASE", phase)
                .stdin(Stdio::piped())
                .stdout(Stdio::null())
                .spawn()
                .unwrap(),
        );
        let deadline = std::time::Instant::now() + std::time::Duration::from_secs(15);
        while !f.path.join("ack-ready").exists() {
            assert!(
                child.0.try_wait().unwrap().is_none(),
                "Synthetic acknowledgment child exited before checkpoint"
            );
            assert!(
                std::time::Instant::now() < deadline,
                "Synthetic acknowledgment checkpoint timed out"
            );
            std::thread::sleep(std::time::Duration::from_millis(25));
        }
        assert_eq!(
            acquire_at(&f.path, "operations.gate", false).unwrap_err(),
            Error::Busy
        );
        child.0.kill().unwrap();
        child.0.wait().unwrap();
        if phase != "evidence" {
            std::fs::write(f.path.join("recovery-acknowledgment.json"), b"{}").unwrap();
        }
        initialize_at(&f.path).unwrap();
        let acknowledgment = acknowledgment::record_at(&f.path, |_| Ok(()))
            .unwrap()
            .unwrap();
        assert_eq!(acknowledgment.incident_id, id);
        assert_eq!(
            std::fs::read(archive_path(&f, &id, "journal")).unwrap(),
            original
        );
        assert_eq!(
            std::fs::read(f.path.join("transaction.json")).unwrap(),
            original
        );
        assert_eq!(installation_at(&f.path).unwrap_err(), Error::Interrupted);
    }
}
