use super::*;
use crate::tests::{interrupted_fixture, Fixture};

#[test]
fn bootstrap_clean_install_creates_no_incident_or_acknowledgment() {
    let Some(f) = Fixture::new() else { return };
    bootstrap_at(&f.path).unwrap();
    bootstrap_at(&f.path).unwrap();
    assert_eq!(std::fs::read_dir(&f.path).unwrap().count(), 2);
    assert!(recovery::inspect_at(&f.path).unwrap().is_none());
}

#[test]
fn bootstrap_legacy_journal_is_prepared_once_without_acknowledgment_or_retirement() {
    let Some(f) = Fixture::new() else { return };
    let original = interrupted_fixture(&f);
    let identity = recovery::read_journal(&f.path).unwrap().unwrap().1;
    bootstrap_at(&f.path).unwrap();
    let first = recovery::inspect_at(&f.path).unwrap().unwrap();
    let context = std::fs::read(f.path.join("recovery-context.json")).unwrap();
    recovery::submit_at(&f.path, &first.incident_id).unwrap();
    bootstrap_at(&f.path).unwrap();
    assert_eq!(recovery::inspect_at(&f.path).unwrap(), Some(first));
    assert_eq!(
        std::fs::read(f.path.join("recovery-context.json")).unwrap(),
        context
    );
    let (after, after_identity) = recovery::read_journal(&f.path).unwrap().unwrap();
    assert_eq!(after, original);
    assert!(
        identity == after_identity,
        "Bootstrap must not replace the original journal object"
    );
    let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
    assert!(recovery::pending_at(&f.path).unwrap());
    assert_eq!(no_interruption(&f.path).unwrap_err(), Error::Interrupted);
    assert!(!f.path.join("recovery-archive").exists());
    assert!(!f.path.join("recovery-disposition.json").exists());
}

#[test]
fn bootstrap_live_package_hook_defers_preparation_without_replacing_gates() {
    let Some(f) = Fixture::new() else { return };
    let install = installation_at(&f.path).unwrap();
    let transaction = install.begin_transaction().unwrap();
    let original = std::fs::read(f.path.join("transaction.json")).unwrap();
    bootstrap_at(&f.path).unwrap();
    // Inspection acquires its own exclusive operation lease. While the live
    // installation owns that lease, Busy is required, not an empty snapshot.
    assert_eq!(recovery::inspect_at(&f.path).unwrap_err(), Error::Busy);
    for name in [
        "recovery-incident.json",
        "recovery-binding.json",
        "recovery-acknowledgment.json",
        "recovery-context.json",
        "recovery-disposition.json",
        "recovery-archive",
    ] {
        assert!(
            !f.path.join(name).exists(),
            "Live work must not be published as an interruption: {name}"
        );
    }
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
    assert_eq!(
        acquire_at(&f.path, "operations.gate", false).unwrap_err(),
        Error::Busy
    );
    assert_eq!(
        acquire_at(&f.path, "sessions.gate", true).unwrap_err(),
        Error::Busy
    );
    transaction.complete().unwrap();
    drop(install);
    bootstrap_at(&f.path).unwrap();
    assert!(recovery::inspect_at(&f.path).unwrap().is_none());
}

#[test]
fn bootstrap_changed_legacy_generation_requires_new_intent() {
    let Some(f) = Fixture::new() else { return };
    let original = interrupted_fixture(&f);
    bootstrap_at(&f.path).unwrap();
    let old = recovery::inspect_at(&f.path).unwrap().unwrap();
    recovery::submit_at(&f.path, &old.incident_id).unwrap();
    std::fs::remove_file(f.path.join("transaction.json")).unwrap();
    // Recreate identical bytes with the same protected production writer, not
    // an untrusted mode/ACL. A hash-only binding would incorrectly reuse consent.
    let mut file = recovery::open(
        &f.path,
        "transaction.json",
        recovery::Kind::Private,
        true,
        true,
    )
    .unwrap();
    use std::io::Write;
    file.write_all(&original).unwrap();
    file.sync_all().unwrap();
    drop(file);
    bootstrap_at(&f.path).unwrap();
    let new = recovery::inspect_at(&f.path).unwrap().unwrap();
    assert_ne!(old.incident_id, new.incident_id);
    let _lease = acquire_at(&f.path, "operations.gate", false).unwrap();
    assert!(!recovery::pending_at(&f.path).unwrap());
    assert_eq!(no_interruption(&f.path).unwrap_err(), Error::Interrupted);
}

#[test]
fn bootstrap_does_not_repair_untrusted_metadata_or_discard_original_evidence() {
    let Some(f) = Fixture::new() else { return };
    let original = interrupted_fixture(&f);
    bootstrap_at(&f.path).unwrap();
    let context = f.path.join("recovery-context.json");
    std::fs::write(&context, b"malformed protected metadata").unwrap();
    assert_eq!(bootstrap_at(&f.path).unwrap_err(), Error::Untrusted);
    assert_eq!(
        std::fs::read(context).unwrap(),
        b"malformed protected metadata"
    );
    assert_eq!(
        std::fs::read(f.path.join("transaction.json")).unwrap(),
        original
    );
    assert_eq!(no_interruption(&f.path).unwrap_err(), Error::Interrupted);
}
