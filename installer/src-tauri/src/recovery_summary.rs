//! Fixed per-user summaries and a single-action machine intent controller.
//! Report operations alone never acknowledge; intent is not execution authority.
use crate::{
    recovery_reports::{self, Safety, Store, Summary, Validation},
    support,
};
use serde::Serialize;
use tauri::Manager;

fn store(app: &tauri::AppHandle) -> Result<Store, String> {
    Store::new(
        app.path()
            .app_data_dir()
            .map_err(|_| "Application data is unavailable.")?
            .join("recovery-reports"),
    )
}
fn tag(value: impl Serialize) -> String {
    serde_json::to_value(value)
        .ok()
        .and_then(|value| value.as_str().map(str::to_owned))
        .unwrap_or_else(|| "unknown".into())
}
fn sanitize(app: &tauri::AppHandle, summary: &mut Summary) {
    for text in [
        &mut summary.application_version,
        &mut summary.platform,
        &mut summary.device_name,
    ] {
        *text = support::redact_home(app, text);
    }
    if let Some(validation) = &mut summary.validation {
        for check in &mut validation.checks {
            check.message = support::redact_home(app, &check.message);
        }
    }
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SaveOutcome {
    pub saved: bool,
    pub report_id: Option<String>,
    pub warning: Option<String>,
}

#[tauri::command]
pub async fn save_recovery_summary(
    app: tauri::AppHandle,
    incident_id: String,
    validation: Option<Validation>,
) -> Result<SaveOutcome, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let summary = capture(&app, incident_id, validation)?;
        match store(&app).and_then(|store| store.save(&summary)) {
            Ok(id) => Ok(SaveOutcome { saved:true, report_id:Some(id), warning:None }),
            Err(_) => Ok(SaveOutcome { saved:false, report_id:None, warning:Some("The summary could not be saved. Original machine evidence remains separate; saving failure is not an acknowledgment or execution decision.".into()) }),
        }
    })
        .await
        .map_err(|_| "Recovery summary task is unavailable.".to_string())?
}
fn capture(
    app: &tauri::AppHandle,
    incident_id: String,
    validation: Option<Validation>,
) -> Result<Summary, String> {
    if !uuid::Uuid::parse_str(&incident_id).is_ok_and(|id| id.to_string() == incident_id) {
        return Err("Invalid incident identifier.".into());
    }
    let incident = sde_coordination::recovery::inspect()
        .map_err(|_| "Current recovery evidence is unavailable; Check Again.")?
        .ok_or("No current machine incident was observed.")?;
    if incident.incident_id != incident_id {
        return Err("The incident changed; Check Again before acknowledging it.".into());
    }
    let observation = sde_coordination::observations::inspect();
    let captured_at = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|_| "Capture time unavailable.")?
        .as_secs();
    let mut summary = Summary {
        schema: 1,
        report_id: uuid::Uuid::new_v4().to_string(),
        incident_id,
        captured_at,
        application_version: app.package_info().version.to_string(),
        platform: crate::platform().label,
        device_name: support::device_name(),
        validation,
        safety: Safety {
            observed_at: observation.observed_at,
            trust: tag(observation.trust),
            activity: tag(observation.activity),
            package_health: tag(observation.package_health),
            activity_reason: tag(observation.activity_reason),
            decision: tag(observation.decision),
        },
    };
    sanitize(app, &mut summary);
    // Invalid diagnostic input is not a report-storage failure to waive.
    summary.validate()?;
    Ok(summary)
}

fn submission_error(error: sde_coordination::Error) -> String {
    use sde_coordination::Error;
    match error {
        Error::Busy => "SDE is currently in use. Submission is unconfirmed; Check Again when it finishes.",
        Error::Interrupted => "The incident changed. Submission is unconfirmed; Check Again before acknowledging it.",
        Error::Untrusted => "Recovery storage failed its security checks. Submission is unconfirmed; retain the evidence and review diagnostics.",
        Error::Unavailable | Error::NeedsRepair => "Recovery submission is unavailable or could not be confirmed. Check Again; the original incident has not been dismissed by this action.",
    }.into()
}

#[tauri::command]
pub async fn acknowledge_recovery_incident(
    app: tauri::AppHandle,
    incident_id: String,
    confirmed: bool,
    validation: Option<Validation>,
) -> Result<crate::recovery_acknowledgment::Outcome, String> {
    // Share the application operation lock: no overlapping GUI operation or
    // duplicate acknowledgment task. Native gates still arbitrate other apps.
    let guard = app.state::<crate::Busy>().enter()?;
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = guard;
        crate::recovery_acknowledgment::run(
            incident_id.clone(),
            confirmed,
            || capture(&app, incident_id, validation),
            |summary| store(&app)?.save(summary),
            |id| sde_coordination::recovery::submit(id).map_err(submission_error),
        )
    })
    .await
    .map_err(|_| "Acknowledgment task ended without a confirmed result. Check Again; do not assume acknowledgment or completion.".to_string())?
}
#[tauri::command]
pub async fn list_recovery_reports(
    app: tauri::AppHandle,
    cursor: Option<String>,
    limit: usize,
) -> Result<recovery_reports::Page, String> {
    tauri::async_runtime::spawn_blocking(move || store(&app)?.list(cursor.as_deref(), limit))
        .await
        .map_err(|_| "Report history task is unavailable.".to_string())?
}
#[tauri::command]
pub async fn read_recovery_report(
    app: tauri::AppHandle,
    report_id: String,
) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let mut summary = store(&app)?.load(&report_id)?;
        sanitize(&app, &mut summary);
        Ok(recovery_reports::html(&summary))
    })
    .await
    .map_err(|_| "Report read task is unavailable.".to_string())?
}
#[tauri::command]
pub async fn delete_recovery_report(
    app: tauri::AppHandle,
    report_id: String,
    confirmed: bool,
) -> Result<(), String> {
    if !confirmed {
        return Err("Confirm deletion of the selected local report. Operational recovery state will remain.".into());
    }
    tauri::async_runtime::spawn_blocking(move || store(&app)?.delete(&report_id))
        .await
        .map_err(|_| "Report deletion task is unavailable.".to_string())?
}
