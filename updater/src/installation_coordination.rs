//! Application-installation policy adapter. Eligibility/authentication and
//! native identity/postchecks remain the platform installer's responsibility.
use sde_coordination::{
    inspection, mutation,
    safety::{known_backend_completion, Decision, PackageHealth},
};

pub(crate) fn outcome(error: &mutation::BeginError) -> &'static str {
    match error {
        mutation::BeginError::Coordination(
            sde_coordination::Error::Busy | sde_coordination::Error::Interrupted,
        ) => "deferred",
        mutation::BeginError::Coordination(sde_coordination::Error::NeedsRepair) => "failed",
        mutation::BeginError::Safety(observation) => decision_outcome(observation.decision),
        _ => "unavailable",
    }
}

fn decision_outcome(decision: Decision) -> &'static str {
    match decision {
        Decision::BlockActive | Decision::BlockActivityUnknown | Decision::NeedsAcknowledgment => {
            "deferred"
        }
        Decision::BlockIncomplete => "failed",
        _ => "unavailable",
    }
}

pub(crate) fn detail(error: &mutation::BeginError) -> String {
    serde_json::to_string(error).unwrap_or_else(|_| "Installation coordination unavailable".into())
}

pub(crate) fn finish(guard: mutation::Mutation) -> crate::Result<()> {
    let facts = inspection::collect();
    if facts.health == PackageHealth::Unknown {
        eprintln!("SKYVIEW_EVENT|warning|package-health|Application package health remains unverified; native activity, identity and postchecks remain required.");
    }
    // Called only after native success AND all platform postchecks/receipts.
    // Any uncertainty keeps the new journal, including a nominal zero exit.
    if !known_backend_completion(true, facts.activity, facts.health) {
        return Err("Application installation completion remains uncertain; review Recovery and Check Again. No package process was terminated.".into());
    }
    guard.finish_known().map_err(|error| error.to_string())
}

#[cfg(all(test, any(target_os = "linux", windows)))]
pub(crate) fn native_contracts(mut install: impl FnMut(bool) -> crate::Result<()>) {
    use sde_coordination as coordination;
    assert_eq!(std::env::var("GITHUB_ACTIONS").as_deref(), Ok("true"));
    crate::tool_coordination::await_native_fixture_inactivity(
        std::time::Duration::from_secs(15 * 60),
        std::time::Duration::from_secs(10),
        || {
            let facts = inspection::collect();
            (facts.activity, facts.health)
        },
    )
    .expect("Application recovery fixture requires independently observed inactivity");
    // Only the existing disposable signed native package fixtures call this.
    // No real journal, package process, lock or owner evidence is removed.
    let root = coordination::root();
    assert!(!root.join("transaction.json").exists());
    let lease = coordination::installation().unwrap();
    drop(lease.begin_transaction().unwrap());
    drop(lease);
    coordination::initialize().unwrap();
    let original = std::fs::read(root.join("transaction.json")).unwrap();
    let incident = coordination::recovery::inspect().unwrap().unwrap();
    let archived = root
        .join("recovery-archive")
        .join(format!("{}.journal", incident.incident_id));
    let unchanged = || {
        assert_eq!(
            std::fs::read(root.join("transaction.json")).unwrap(),
            original
        );
        assert!(!archived.exists());
    };
    // A rejected authenticated candidate cannot consume the incident or consent.
    assert!(install(false).is_err());
    unchanged();
    assert!(install(true).is_err());
    unchanged();
    coordination::recovery::submit(&incident.incident_id).unwrap();
    assert!(
        install(true).is_err(),
        "Consent alone cannot prove the old process lifetime ended"
    );
    unchanged();
    // Simulate earlier boot provenance ONLY in this synthetic disposable record.
    // Actual reboot/resumption remains owner UAT, not a CI override or claim.
    let context_path = root.join("recovery-context.json");
    let mut context: serde_json::Value =
        serde_json::from_slice(&std::fs::read(&context_path).unwrap()).unwrap();
    let current = context["bootKey"]
        .as_str()
        .expect("Native restart provenance required");
    #[cfg(target_os = "linux")]
    let previous = {
        assert!(current.starts_with("linux:"));
        format!("linux:{}", uuid::Uuid::new_v4())
    };
    #[cfg(windows)]
    let previous = {
        let values: Vec<u64> = current
            .strip_prefix("windows-session-start:")
            .unwrap()
            .split(':')
            .map(|part| part.parse().unwrap())
            .collect();
        assert_eq!(values.len(), 4);
        format!(
            "windows-session-start:{}:{}:{}:{}",
            values[0] + 1,
            values[1] + 1,
            values[2] + 1,
            values[3] + 1
        )
    };
    assert_ne!(current, previous);
    context["bootKey"] = serde_json::json!(previous);
    std::fs::write(context_path, serde_json::to_vec(&context).unwrap()).unwrap();
    std::fs::write(root.join("recovery-acknowledgment.json"), b"{}").unwrap();
    assert!(
        install(true).is_err(),
        "Restart alone cannot replace consent"
    );
    unchanged();
    coordination::recovery::submit(&incident.incident_id).unwrap();
    assert!(
        install(false).is_err(),
        "Consent must not override candidate authentication"
    );
    unchanged();
    install(true).expect("Acknowledged signed native application upgrade must complete");
    assert!(!root.join("transaction.json").exists());
    for extension in ["journal", "retired-journal"] {
        assert_eq!(
            std::fs::read(
                root.join("recovery-archive")
                    .join(format!("{}.{extension}", incident.incident_id))
            )
            .unwrap(),
            original
        );
    }
    assert!(root
        .join("recovery-archive")
        .join(format!("{}.receipt.json", incident.incident_id))
        .exists());
    println!("SDE_RECOVERY_APPLICATION_INSTALL_CONTRACT_OK");
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn installation_safety_outcomes_distinguish_deferral_damage_and_unavailable_trust() {
        for (decision, expected) in [
            (Decision::BlockActive, "deferred"),
            (Decision::BlockActivityUnknown, "deferred"),
            (Decision::NeedsAcknowledgment, "deferred"),
            (Decision::BlockIncomplete, "failed"),
            (Decision::BlockUntrusted, "unavailable"),
            (Decision::BlockTrustUnknown, "unavailable"),
            (Decision::Allow, "unavailable"),
            (Decision::AllowWithHealthWarning, "unavailable"),
        ] {
            assert_eq!(decision_outcome(decision), expected);
        }
        for (error, expected) in [
            (sde_coordination::Error::Busy, "deferred"),
            (sde_coordination::Error::Interrupted, "deferred"),
            (sde_coordination::Error::NeedsRepair, "failed"),
            (sde_coordination::Error::Untrusted, "unavailable"),
        ] {
            assert_eq!(outcome(&error.into()), expected);
        }
    }
}
