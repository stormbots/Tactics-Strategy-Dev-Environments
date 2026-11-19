use serde::{Deserialize, Serialize};
use std::process::Stdio;

#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    Enabled,
    Disabled,
    Missing,
    Unavailable,
}
#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum LastResult {
    Success,
    Failure,
    Never,
    Running,
    Deferred,
    Unavailable,
}
#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum InspectionReason {
    Verified,
    NotInstalled,
    AccessDenied,
    TimedOut,
    ReadFailed,
    Unknown,
}
#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum InspectionScope {
    Schedule,
    History,
}
#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct ChoiceContext {
    pub machine_id: String,
    pub identifier: String,
    pub definition_id: String,
}

#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Schedule {
    #[serde(
        default,
        skip_serializing_if = "Option::is_none",
        deserialize_with = "present"
    )]
    pub choice_context: Option<ChoiceContext>,
    #[serde(
        default,
        skip_serializing_if = "Option::is_none",
        deserialize_with = "present"
    )]
    pub inspection_reason: Option<InspectionReason>,
    #[serde(
        default,
        skip_serializing_if = "Option::is_none",
        deserialize_with = "present"
    )]
    pub inspection_scope: Option<InspectionScope>,
    pub status: Status,
    pub active: bool,
    pub identifier: String,
    pub frequency: String,
    pub next_run: Option<String>,
    pub last_run: Option<String>,
    pub last_result: LastResult,
    pub result_detail: String,
    pub catch_up: Option<bool>,
    pub log_folder: String,
    pub logs_available: bool,
    pub note: String,
    pub observed_at: String,
    pub created_at: Option<String>,
    pub last_success: Option<String>,
}

// An omitted legacy field is allowed; an explicitly null/new malformed field is not.
fn present<'de, D, T>(deserializer: D) -> Result<Option<T>, D::Error>
where
    D: serde::Deserializer<'de>,
    T: Deserialize<'de>,
{
    T::deserialize(deserializer).map(Some)
}

pub fn inspect(root: &std::path::Path) -> Result<Schedule, String> {
    #[cfg(windows)]
    let mut command = crate::process::script(root, "chocolatey/tools/Inspect-SkyviewSchedule.ps1");
    #[cfg(not(windows))]
    let mut command = {
        let mut c = std::process::Command::new("/usr/bin/python3");
        c.arg(root.join("linux/lib/schedule.py"));
        c
    };
    let output = crate::process::hidden(&mut command)
        .stdin(Stdio::null())
        .output()
        .map_err(|_| "Maintenance information could not be read. Please refresh.".to_string())?;
    if !output.status.success() {
        return Err("Maintenance inspection failed. Please refresh.".into());
    }
    let record: Schedule = serde_json::from_slice(&output.stdout)
        .map_err(|_| "Maintenance returned incomplete information. Please refresh.".to_string())?;
    validate_inspection(&record)?;
    Ok(record)
}

fn validate_inspection(record: &Schedule) -> Result<(), String> {
    use InspectionReason as R;
    use InspectionScope as S;
    let valid = match (
        &record.inspection_scope,
        &record.inspection_reason,
        &record.status,
    ) {
        (None, None, _) => true, // Legacy readers: no cause is inferred.
        (Some(S::Schedule), Some(R::Verified), Status::Enabled | Status::Disabled) => true,
        (Some(S::Schedule), Some(R::NotInstalled), Status::Missing) => true,
        (
            Some(S::Schedule),
            Some(R::AccessDenied | R::TimedOut | R::ReadFailed | R::Unknown),
            Status::Unavailable,
        ) => true,
        (
            Some(S::History),
            Some(R::NotInstalled | R::AccessDenied | R::TimedOut | R::ReadFailed | R::Unknown),
            Status::Enabled | Status::Disabled,
        ) => true,
        _ => false,
    };
    let context_valid = record.choice_context.as_ref().map_or(true, |context| {
        let hex = |value: &str| {
            value.len() == 64
                && value
                    .bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        };
        hex(&context.machine_id)
            && hex(&context.definition_id)
            && context.identifier == record.identifier
            && matches!(
                context.identifier.as_str(),
                "skyview-student-dev-update.timer" | "\\Skyview Robotics - Dev Tool Updates"
            )
            && matches!(record.inspection_scope, Some(S::Schedule))
            && matches!(record.inspection_reason, Some(R::Verified))
            && matches!(record.status, Status::Enabled | Status::Disabled)
    });
    if valid && context_valid {
        Ok(())
    } else {
        Err("Maintenance returned conflicting inspection information. Please check again.".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn native_read_only_reader_returns_a_complete_record() {
        let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../..");
        let record = inspect(&root).unwrap();
        assert!(!record.identifier.is_empty());
        assert!(!record.frequency.is_empty());
        let json = serde_json::to_string(&record).unwrap();
        assert!(serde_json::from_str::<Schedule>(&json).is_ok());
    }
    #[test]
    fn does_not_default_unknown_results_to_success() {
        assert!(serde_json::from_str::<LastResult>("\"unknown\"").is_err());
        let result: LastResult = serde_json::from_str("\"unavailable\"").unwrap();
        assert!(matches!(result, LastResult::Unavailable));
        assert!(serde_json::from_str::<Schedule>(r#"{"status":"enabled"}"#).is_err());
    }
    fn fixture(status: &str, scope: &str, reason: &str) -> serde_json::Value {
        serde_json::json!({"status":status,"inspectionScope":scope,"inspectionReason":reason,
            "active":false,"identifier":"fixed fixture","frequency":"Unavailable","nextRun":null,
            "lastRun":null,"lastResult":"unavailable","resultDetail":"Unavailable","catchUp":null,
            "logFolder":"/logs","logsAvailable":false,"note":"","observedAt":"2026-11-18T00:00:00Z",
            "createdAt":null,"lastSuccess":null})
    }
    #[test]
    fn choice_context_is_bounded_and_cannot_change_native_evidence() {
        let mut row = fixture("disabled", "schedule", "verified");
        row["identifier"] = serde_json::json!("skyview-student-dev-update.timer");
        row["choiceContext"] = serde_json::json!({"machineId":"a".repeat(64),
            "identifier":"skyview-student-dev-update.timer", "definitionId":"b".repeat(64)});
        let record: Schedule = serde_json::from_value(row.clone()).unwrap();
        validate_inspection(&record).unwrap();
        for (field, value) in [
            ("machineId", serde_json::json!("bad")),
            ("definitionId", serde_json::json!("B".repeat(64))),
            ("identifier", serde_json::json!("foreign timer")),
        ] {
            let mut invalid = row.clone();
            invalid["choiceContext"][field] = value;
            let record: Schedule = serde_json::from_value(invalid).unwrap();
            assert!(validate_inspection(&record).is_err());
        }
        for field in ["status", "inspectionScope", "inspectionReason"] {
            let mut invalid = row.clone();
            invalid[field] = serde_json::json!(if field == "status" {
                "missing"
            } else if field == "inspectionScope" {
                "history"
            } else {
                "unknown"
            });
            let record: Schedule = serde_json::from_value(invalid).unwrap();
            assert!(validate_inspection(&record).is_err());
        }
        for value in [
            serde_json::Value::Null,
            serde_json::json!({}),
            serde_json::json!({"machineId":"a".repeat(64),"identifier":"skyview-student-dev-update.timer","definitionId":"b".repeat(64),"permit":true}),
        ] {
            let mut invalid = row.clone();
            invalid["choiceContext"] = value;
            assert!(serde_json::from_value::<Schedule>(invalid).is_err());
        }
    }

    #[test]
    fn structured_causes_keep_schedule_and_history_distinct() {
        for (status, scope, reason) in [
            ("enabled", "schedule", "verified"),
            ("disabled", "schedule", "verified"),
            ("missing", "schedule", "notInstalled"),
            ("unavailable", "schedule", "accessDenied"),
            ("unavailable", "schedule", "timedOut"),
            ("unavailable", "schedule", "readFailed"),
            ("disabled", "history", "accessDenied"),
            ("enabled", "history", "notInstalled"),
        ] {
            let record: Schedule = serde_json::from_value(fixture(status, scope, reason)).unwrap();
            validate_inspection(&record).unwrap();
        }
    }
    #[test]
    fn contradictory_or_unbounded_inspection_metadata_is_rejected() {
        for (status, scope, reason) in [
            ("enabled", "schedule", "accessDenied"),
            ("unavailable", "schedule", "verified"),
            ("missing", "history", "notInstalled"),
            ("enabled", "history", "verified"),
        ] {
            let record: Schedule = serde_json::from_value(fixture(status, scope, reason)).unwrap();
            assert!(validate_inspection(&record).is_err());
        }
        for (key, value) in [
            ("inspectionReason", serde_json::json!(["verified"])),
            ("inspectionReason", serde_json::Value::Null),
            ("inspectionScope", serde_json::Value::Null),
            ("inspectionReason", serde_json::json!("enable")),
            ("inspectionScope", serde_json::json!("other")),
        ] {
            let mut row = fixture("enabled", "schedule", "verified");
            row[key] = value;
            assert!(serde_json::from_value::<Schedule>(row).is_err());
        }
    }
    #[test]
    fn legacy_records_do_not_invent_a_cause_and_partial_metadata_is_rejected() {
        let mut row = fixture("disabled", "schedule", "verified");
        row.as_object_mut().unwrap().remove("inspectionReason");
        let partial: Schedule = serde_json::from_value(row.clone()).unwrap();
        assert!(validate_inspection(&partial).is_err());
        row.as_object_mut().unwrap().remove("inspectionScope");
        let legacy: Schedule = serde_json::from_value(row).unwrap();
        assert!(legacy.inspection_reason.is_none());
        validate_inspection(&legacy).unwrap();
    }
}
