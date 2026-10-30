//! Fixed per-user summary commands. Saving or deleting a report never submits
//! an acknowledgment or changes protected operational state. T8 owns that flow.
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
    tauri::async_runtime::spawn_blocking(move || save(app, incident_id, validation))
        .await
        .map_err(|_| "Recovery summary task is unavailable.".to_string())?
}
fn save(
    app: tauri::AppHandle,
    incident_id: String,
    validation: Option<Validation>,
) -> Result<SaveOutcome, String> {
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
    sanitize(&app, &mut summary);
    // No chooser, preview, log opt-in or OS-privilege prompt. The report records
    // actual unavailable fields and original validation time, never a fake run.
    match store(&app).and_then(|store| store.save(&summary)) {
        Ok(id) => Ok(SaveOutcome { saved:true, report_id:Some(id), warning:None }),
        Err(_) => Ok(SaveOutcome { saved:false, report_id:None, warning:Some("The summary could not be saved. Original machine evidence remains separate; saving failure is not an acknowledgment or execution decision.".into()) }),
    }
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
