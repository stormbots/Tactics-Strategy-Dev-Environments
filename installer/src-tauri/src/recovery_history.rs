//! Report-linked observations, never authority or operation-completion claims.
use crate::{
    recovery_context::{Context, UserIncident},
    recovery_reports::Summary,
    recovery_user::Decision,
};
use serde::Serialize;

#[derive(Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Observed,
    Unknown,
    Unavailable,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Observation {
    pub source: Option<&'static str>,
    pub status: Status,
    pub acknowledged_at: Option<u64>,
    pub observed_at: u64,
    pub note: &'static str,
    pub continuation: &'static str,
}
pub fn observe(
    report: &Summary,
    now: u64,
    machine: impl FnOnce() -> Result<Option<(String, u64)>, ()>,
    user: impl FnOnce(&str, &UserIncident) -> Result<Option<Decision>, ()>,
) -> Observation {
    let result = match &report.context {
        Some(Context::Machine { .. }) => machine().map(|value| {
            value
                .filter(|(id, _)| id == &report.incident_id)
                .map(|(_, time)| time)
        }),
        Some(Context::User { incident }) => user(&report.report_id, incident).map(|value| {
            value
                .filter(|decision| {
                    decision.incident_id == report.incident_id
                        && decision.report_id.as_deref() == Some(report.report_id.as_str())
                })
                .map(|decision| decision.acknowledged_at)
        }),
        None => Ok(None),
    };
    let (status, acknowledged_at, note) = match result {
        Ok(Some(time)) if time != 0 && time <= now => (Status::Observed, Some(time),
            "A matching acknowledgment record was observed. This is not an execution permit, private machine-evidence verification, or proof of completion."),
        Ok(None) => (Status::Unknown, None,
            "No matching acknowledgment was established for this report. Missing/currently different state does not prove that it was never acknowledged or that the earlier operation completed."),
        _ => (Status::Unavailable, None,
            "Acknowledgment status could not be read or verified. Keep the evidence; this observation does not change operational state."),
    };
    Observation {
        source: match &report.context {
            Some(Context::Machine { .. }) => Some("machine"),
            Some(Context::User { .. }) => Some("user"),
            None => None,
        },
        status,
        acknowledged_at,
        observed_at: now,
        note,
        continuation: "not_recorded",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn report(user: bool) -> Summary {
        let id = uuid::Uuid::new_v4().to_string();
        Summary {
            schema: 1,
            report_id: uuid::Uuid::new_v4().to_string(),
            incident_id: id.clone(),
            captured_at: 100,
            application_version: "CI".into(),
            platform: "CI".into(),
            device_name: "CI".into(),
            validation: None,
            safety: crate::recovery_reports::Safety {
                observed_at: 99,
                trust: "unknown".into(),
                activity: "unknown".into(),
                package_health: "unknown".into(),
                activity_reason: "unknown".into(),
                decision: "unknown".into(),
            },
            context: Some(if user {
                Context::User {
                    incident: UserIncident {
                        id,
                        operation: "update".into(),
                        stage: "profile".into(),
                        started_at: 10,
                        observed_at: 20,
                    },
                }
            } else {
                Context::Machine { incident_id: id }
            }),
        }
    }
    #[test]
    fn report_history_requires_matching_machine_identity_and_never_infers_completion() {
        let report = report(false);
        let matching = observe(
            &report,
            200,
            || Ok(Some((report.incident_id.clone(), 150))),
            |_, _| panic!("wrong scope"),
        );
        assert_eq!(matching.status, Status::Observed);
        assert_eq!(matching.acknowledged_at, Some(150));
        assert_eq!(matching.continuation, "not_recorded");
        for result in [None, Some((uuid::Uuid::new_v4().to_string(), 150))] {
            assert_eq!(
                observe(&report, 200, || Ok(result), |_, _| panic!("wrong scope")).status,
                Status::Unknown
            );
        }
    }
    #[test]
    fn report_history_user_decision_must_reference_this_report_not_just_its_incident() {
        let report = report(true);
        let decision = Decision {
            incident_id: report.incident_id.clone(),
            acknowledged_at: 150,
            report_id: Some(report.report_id.clone()),
        };
        assert_eq!(
            observe(
                &report,
                200,
                || panic!("wrong scope"),
                |_, _| Ok(Some(decision.clone()))
            )
            .status,
            Status::Observed
        );
        let mut unrelated = decision.clone();
        unrelated.report_id = Some(uuid::Uuid::new_v4().to_string());
        assert_eq!(
            observe(
                &report,
                200,
                || panic!("wrong scope"),
                |_, _| Ok(Some(unrelated))
            )
            .status,
            Status::Unknown
        );
        let mut unrelated = decision;
        unrelated.incident_id = uuid::Uuid::new_v4().to_string();
        assert_eq!(
            observe(
                &report,
                200,
                || panic!("wrong scope"),
                |_, _| Ok(Some(unrelated))
            )
            .status,
            Status::Unknown
        );
    }
    #[test]
    fn report_history_missing_legacy_provenance_never_selects_a_source() {
        let mut report = report(false);
        report.context = None;
        assert_eq!(
            observe(
                &report,
                200,
                || panic!("no source"),
                |_, _| panic!("no source")
            )
            .status,
            Status::Unknown
        );
    }
    #[test]
    fn report_history_failed_or_impossible_observations_are_unavailable_not_unacknowledged() {
        let report = report(false);
        for result in [
            Err(()),
            Ok(Some((report.incident_id.clone(), 0))),
            Ok(Some((report.incident_id.clone(), 201))),
        ] {
            let observed = observe(&report, 200, || result, |_, _| panic!("wrong scope"));
            assert_eq!(observed.status, Status::Unavailable);
            assert!(observed.acknowledged_at.is_none());
            assert_eq!(observed.continuation, "not_recorded");
        }
    }
}
