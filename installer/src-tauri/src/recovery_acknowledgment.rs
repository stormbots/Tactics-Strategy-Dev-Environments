//! One local action: capture, attempt a report, then submit bounded intent.
//! This controller has no execution, elevation, journal retirement or replay API.
use serde::Serialize;

#[derive(Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum IntentStatus {
    Submitted,
    // A failed write/flush can be ambiguous. Never promise that no bytes landed.
    Unconfirmed,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Outcome {
    pub incident_id: String,
    pub report_id: Option<String>,
    pub report_warning: Option<String>,
    pub intent_status: IntentStatus,
    pub intent_warning: Option<String>,
}

pub fn run<T>(
    incident_id: String,
    confirmed: bool,
    capture: impl FnOnce() -> Result<T, String>,
    save: impl FnOnce(&T) -> Result<String, String>,
    submit: impl FnOnce(&str) -> Result<(), String>,
) -> Result<Outcome, String> {
    if !confirmed {
        return Err("Confirm acknowledgment of this incident before continuing.".into());
    }
    if !uuid::Uuid::parse_str(&incident_id).is_ok_and(|id| id.to_string() == incident_id) {
        return Err("Invalid incident identifier.".into());
    }
    // Source/capture failures are not best-effort storage failures. Do not submit
    // intent for a missing, unreadable, or changed source after failed capture.
    let snapshot = capture()?;
    let (report_id, report_warning) = match save(&snapshot) {
        Ok(id) => (Some(id), None),
        Err(_) => (None, Some("The summary could not be saved. Original operational evidence is separate and has not been cleared. The incident-specific intent submission was still attempted.".into())),
    };
    // The native submission rechecks the current public ID, protected paths,
    // journal presence and held gate. A report, or its failure, grants no permit.
    let (intent_status, intent_warning) = match submit(&incident_id) {
        Ok(()) => (IntentStatus::Submitted, None),
        Err(message) => (IntentStatus::Unconfirmed, Some(message)),
    };
    Ok(Outcome {
        incident_id,
        report_id,
        report_warning,
        intent_status,
        intent_warning,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    #[test]
    fn acknowledgment_controller_attempts_one_report_before_one_submission() {
        let events = RefCell::new(Vec::new());
        let id = uuid::Uuid::new_v4().to_string();
        let report = uuid::Uuid::new_v4().to_string();
        let result = run(
            id.clone(),
            true,
            || {
                events.borrow_mut().push("capture");
                Ok(42)
            },
            |snapshot| {
                assert_eq!(*snapshot, 42);
                events.borrow_mut().push("save");
                Ok(report.clone())
            },
            |submitted| {
                assert_eq!(submitted, id);
                events.borrow_mut().push("submit");
                Ok(())
            },
        )
        .unwrap();
        assert_eq!(*events.borrow(), ["capture", "save", "submit"]);
        assert_eq!(result.report_id, Some(report));
        assert_eq!(result.intent_status, IntentStatus::Submitted);
        assert!(result.report_warning.is_none());
        assert!(result.intent_warning.is_none());
    }

    #[test]
    fn acknowledgment_controller_save_failure_warns_and_still_submits_once() {
        let events = RefCell::new(Vec::new());
        let result = run(
            uuid::Uuid::new_v4().to_string(),
            true,
            || Ok(()),
            |_| {
                events.borrow_mut().push("save");
                Err("sensitive storage error".into())
            },
            |_| {
                events.borrow_mut().push("submit");
                Ok(())
            },
        )
        .unwrap();
        assert_eq!(*events.borrow(), ["save", "submit"]);
        assert!(result.report_id.is_none());
        assert!(!result.report_warning.unwrap().contains("sensitive"));
        assert_eq!(result.intent_status, IntentStatus::Submitted);
    }

    #[test]
    fn acknowledgment_controller_capture_failure_never_saves_or_submits() {
        let result = run::<()>(
            uuid::Uuid::new_v4().to_string(),
            true,
            || Err("Changed evidence; Check Again.".into()),
            |_| panic!("must not save"),
            |_| panic!("must not submit"),
        );
        assert!(result.unwrap_err().contains("Changed evidence"));
    }

    #[test]
    fn acknowledgment_controller_unconfirmed_intent_preserves_saved_report_reference() {
        let report = uuid::Uuid::new_v4().to_string();
        let result = run(
            uuid::Uuid::new_v4().to_string(),
            true,
            || Ok(()),
            |_| Ok(report.clone()),
            |_| Err("Check Again; incident changed.".into()),
        )
        .unwrap();
        assert_eq!(result.report_id, Some(report));
        assert_eq!(result.intent_status, IntentStatus::Unconfirmed);
        assert!(result.intent_warning.unwrap().contains("Check Again"));
    }

    #[test]
    fn acknowledgment_controller_separates_both_failures_without_retry_or_execution() {
        let calls = RefCell::new(0);
        let result = run(
            uuid::Uuid::new_v4().to_string(),
            true,
            || Ok(()),
            |_| Err("disk full".into()),
            |_| {
                *calls.borrow_mut() += 1;
                Err("Submission unconfirmed.".into())
            },
        )
        .unwrap();
        assert_eq!(*calls.borrow(), 1);
        assert!(result.report_warning.is_some());
        assert!(result.intent_warning.is_some());
        assert_eq!(result.intent_status, IntentStatus::Unconfirmed);
    }

    #[test]
    fn acknowledgment_controller_requires_confirmation_and_canonical_id_before_io() {
        for (id, confirmed) in [
            (uuid::Uuid::new_v4().to_string(), false),
            ("../transaction.json".into(), true),
            ("AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA".into(), true),
        ] {
            assert!(run::<()>(
                id,
                confirmed,
                || panic!("no capture"),
                |_| panic!("no save"),
                |_| panic!("no submission")
            )
            .is_err());
        }
    }
}
