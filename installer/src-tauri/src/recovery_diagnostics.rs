//! Sanitized read-only support categories, including unparseable source state.
//! Never copy raw journals, paths, generations, restart keys or OS error text.
use crate::{recovery_context, recovery_user};
use sde_coordination::{
    observations::{ActivityReason, Observation, RestartEvidence},
    recovery::PublicState,
    safety::{Activity, Decision, PackageHealth, Trust},
};
use serde::Serialize;
use std::path::Path;

#[derive(Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum SourceStatus {
    Absent,
    Recorded,
    Unavailable,
}
#[derive(Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum AccountDecision {
    NotApplicable,
    NotObserved,
    Observed,
    Unavailable,
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Snapshot {
    pub observed_at: Option<u64>,
    pub machine_evidence: SourceStatus,
    pub account_evidence: SourceStatus,
    pub account_decision: AccountDecision,
    pub machine_activity: Activity,
    pub machine_activity_reason: ActivityReason,
    pub machine_package_health: PackageHealth,
    pub machine_trust: Trust,
    pub machine_restart: RestartEvidence,
    pub machine_safety_decision: Decision,
}
pub fn capture(
    directory: Option<&Path>,
    now: Option<u64>,
    native: Observation,
    machine: sde_coordination::Result<Option<PublicState>>,
) -> Snapshot {
    let machine_evidence = match machine {
        Ok(Some(_)) => SourceStatus::Recorded,
        Ok(None) => SourceStatus::Absent,
        Err(_) => SourceStatus::Unavailable,
    };
    let (account_evidence, account_decision) = match (directory, now.filter(|time| *time > 0)) {
        (Some(directory), Some(now)) => {
            match recovery_context::read_current_evidence(directory, now) {
                Ok(None) => (SourceStatus::Absent, AccountDecision::NotApplicable),
                Ok(Some(evidence)) => (
                    SourceStatus::Recorded,
                    match recovery_user::Store::new(directory.to_path_buf()).inspect(&evidence, now)
                    {
                        Ok(Some(_)) => AccountDecision::Observed,
                        Ok(None) => AccountDecision::NotObserved,
                        Err(_) => AccountDecision::Unavailable,
                    },
                ),
                Err(_) => (SourceStatus::Unavailable, AccountDecision::Unavailable),
            }
        }
        _ => (SourceStatus::Unavailable, AccountDecision::Unavailable),
    };
    Snapshot {
        observed_at: now,
        machine_evidence,
        account_evidence,
        account_decision,
        machine_activity: native.activity,
        machine_activity_reason: native.activity_reason,
        machine_package_health: native.package_health,
        machine_trust: native.trust,
        machine_restart: native.restart,
        machine_safety_decision: native.decision,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn native() -> Observation {
        Observation {
            observed_at: 100,
            trust: Trust::Unknown,
            activity: Activity::Unknown,
            activity_reason: ActivityReason::NativeInspectionUnavailable,
            package_health: PackageHealth::Unknown,
            health_reason: sde_coordination::inspection::Reason::PackageHealthy,
            diagnostics: vec![],
            restart: RestartEvidence::Unavailable,
            interrupted: false,
            acknowledged: false,
            decision: Decision::BlockTrustUnknown,
        }
    }
    #[test]
    fn unavailable_support_diagnostics_never_conflate_absence_or_export_bad_source_bytes() {
        let directory =
            std::env::temp_dir().join(format!("sde-diagnostic-ci-{}", uuid::Uuid::new_v4()));
        std::fs::create_dir(&directory).unwrap();
        let absent = capture(Some(&directory), Some(100), native(), Ok(None));
        assert_eq!(absent.account_evidence, SourceStatus::Absent);
        assert_eq!(absent.account_decision, AccountDecision::NotApplicable);
        assert!(!directory.join("recovery-state").exists());
        let path = directory.join("operation-journal.json");
        let bytes = b"{broken journal: token=synthetic-private-secret /private/person/file";
        std::fs::write(&path, bytes).unwrap();
        let bad = capture(
            Some(&directory),
            Some(100),
            native(),
            Err(sde_coordination::Error::Unavailable),
        );
        assert_eq!(bad.account_evidence, SourceStatus::Unavailable);
        assert_eq!(bad.machine_evidence, SourceStatus::Unavailable);
        let json = serde_json::to_string(&bad).unwrap();
        for private in [
            "synthetic-private-secret",
            "/private/person",
            "generation",
            "bootKey",
            "viewToken",
        ] {
            assert!(!json.contains(private));
        }
        assert!(std::fs::read(&path).unwrap() == bytes);
        assert!(!directory.join("recovery-state").exists());
        std::fs::remove_file(path).unwrap();
        std::fs::remove_dir(directory).unwrap();
    }
    #[test]
    fn missing_clock_or_location_is_unavailable_not_a_fabricated_observation() {
        let missing = capture(None, None, native(), Ok(None));
        assert!(missing.observed_at.is_none());
        assert_eq!(missing.account_evidence, SourceStatus::Unavailable);
        assert_eq!(missing.machine_safety_decision, Decision::BlockTrustUnknown);
    }
}
