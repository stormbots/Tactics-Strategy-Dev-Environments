//! Fixed per-user summaries and a single-action machine intent controller.
//! Report operations alone never acknowledge; intent is not execution authority.
use crate::{
    recovery_context::{self, Context, Source},
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
    source: Option<Source>,
) -> Result<SaveOutcome, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let summary = capture(&app, incident_id, validation, source.unwrap_or_default())?;
        match store(&app).and_then(|store| store.save(&summary)) {
            Ok(id) => Ok(SaveOutcome { saved:true, report_id:Some(id), warning:None }),
            Err(_) => Ok(SaveOutcome { saved:false, report_id:None, warning:Some("The summary could not be saved. Original operational evidence remains separate; saving failure is not an acknowledgment or execution decision.".into()) }),
        }
    })
        .await
        .map_err(|_| "Recovery summary task is unavailable.".to_string())?
}
fn capture(
    app: &tauri::AppHandle,
    incident_id: String,
    validation: Option<Validation>,
    source: Source,
) -> Result<Summary, String> {
    if !uuid::Uuid::parse_str(&incident_id).is_ok_and(|id| id.to_string() == incident_id) {
        return Err("Invalid incident identifier.".into());
    }
    let observation = sde_coordination::observations::inspect();
    let captured_at = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|_| "Capture time unavailable.")?
        .as_secs();
    let context = match source {
        Source::Machine => {
            let incident = sde_coordination::recovery::inspect()
                .map_err(|_| "Current recovery evidence is unavailable; Check Again.")?
                .ok_or("No current machine incident was observed.")?;
            if incident.incident_id != incident_id {
                return Err("The incident changed; Check Again before acknowledging it.".into());
            }
            Context::Machine {
                incident_id: incident_id.clone(),
            }
        }
        Source::User => recovery_context::read_user(
            &app.path()
                .app_data_dir()
                .map_err(|_| "Application data is unavailable.")?,
            &incident_id,
            captured_at,
        )?,
    };
    let mut summary = Summary {
        schema: 1,
        report_id: uuid::Uuid::new_v4().to_string(),
        incident_id,
        captured_at,
        application_version: app.package_info().version.to_string(),
        platform: crate::platform().label,
        device_name: support::device_name(),
        validation,
        context: Some(context),
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
            || capture(&app, incident_id, validation, Source::Machine),
            |summary| store(&app)?.save(summary),
            |id| sde_coordination::recovery::submit(id).map_err(submission_error),
        )
    })
    .await
    .map_err(|_| "Acknowledgment task ended without a confirmed result. Check Again; do not assume acknowledgment or completion.".to_string())?
}
#[tauri::command]
pub async fn acknowledge_user_recovery_incident(
    app: tauri::AppHandle,
    incident_id: String,
    view_token: String,
    confirmed: bool,
    validation: Option<Validation>,
) -> Result<crate::recovery_user::Outcome, String> {
    if !confirmed {
        return Err("Confirm acknowledgment of this user incident before continuing.".into());
    }
    let guard = app.state::<crate::Busy>().enter()?;
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = guard;
        let directory = app.path().app_data_dir().map_err(|_| "Application data is unavailable.")?;
        let _user_lock = crate::user_journal_store::Lock::acquire(&directory)?;
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| "Observation time unavailable.")?.as_secs();
        // Keep this exact opened source while capturing a sanitized report.
        // Raw bytes/native generation never enter IPC or the shareable report.
        let evidence = recovery_context::read_evidence(&directory, &incident_id, now)?;
        app.state::<crate::recovery_state::Views>().verify(&view_token, &incident_id, &evidence.generation)?;
        crate::user_journal_store::prepare_incident_session(&directory, &evidence)?;
        let summary = capture(&app, incident_id, validation, Source::User)?;
        if summary.context.as_ref() != Some(&evidence.context) {
            return Err("User evidence changed; Check Again before acknowledging it.".into());
        }
        crate::recovery_user::Store::new(directory).with_report(&evidence, summary.captured_at,
            || store(&app)?.save(&summary))
    }).await.map_err(|_| "User acknowledgment task ended without a confirmed result. Check Again; no operation was launched.".to_string())?
}

#[tauri::command]
pub async fn inspect_recovery_state(
    app: tauri::AppHandle,
) -> Result<crate::recovery_state::State, String> {
    tauri::async_runtime::spawn_blocking(move || {
        use crate::{
            recovery_state::{Machine, User},
            user_journal_store::{inspect_gate, inspect_restart},
        };
        use sde_coordination::observations::RestartEvidence;
        let before = sde_coordination::recovery::inspect_public_state();
        let native = sde_coordination::observations::inspect();
        let after = sde_coordination::recovery::inspect_public_state();
        let consistent = match (&before, &after) {
            (Ok(None), Ok(None)) => true,
            (Ok(Some(before)), Ok(Some(after))) => {
                before.incident.incident_id == after.incident.incident_id
            }
            _ => false,
        };
        let mut machine = Machine::from_public(after);
        machine.available &= consistent;
        let directory = app
            .path()
            .app_data_dir()
            .map_err(|_| "Recovery data location is unavailable.")?;
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| "Recovery observation time is unavailable.")?
            .as_secs();
        let gate = inspect_gate(&directory);
        let mut user = User {
            observed_at: now,
            available: false,
            incident: None,
            acknowledgment: None,
            restart: RestartEvidence::Unavailable,
            gate,
            view_token: None,
        };
        match recovery_context::read_current_evidence(&directory, now) {
            Ok(None) => user.available = true,
            Ok(Some(evidence)) => {
                let Context::User { incident } = &evidence.context else {
                    unreachable!()
                };
                user.restart = inspect_restart(&directory, incident);
                user.incident = Some(incident.clone());
                if let Ok(decision) =
                    crate::recovery_user::Store::new(directory.clone()).inspect(&evidence, now)
                {
                    user.acknowledgment = decision;
                    user.view_token = Some(
                        app.state::<crate::recovery_state::Views>()
                            .bind(&incident.id, &evidence.generation)?,
                    );
                    user.available = true;
                }
            }
            Err(_) => (), // Unavailable is explicit, not an absent incident.
        }
        let after_gate = inspect_gate(&directory);
        user.gate = if gate == crate::user_journal_store::GateActivity::Active
            || after_gate == crate::user_journal_store::GateActivity::Active
        {
            crate::user_journal_store::GateActivity::Active
        } else {
            after_gate
        };
        let platform = if cfg!(windows) {
            sde_coordination::guidance::Platform::Windows
        } else {
            sde_coordination::guidance::Platform::Linux
        };
        Ok(crate::recovery_state::assemble(
            native, machine, user, platform,
        ))
    })
    .await
    .map_err(|_| "Recovery observation task is unavailable.".to_string())?
}

#[tauri::command]
pub async fn inspect_user_recovery_acknowledgment(
    app: tauri::AppHandle,
    incident_id: String,
) -> Result<Option<crate::recovery_user::Decision>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let directory = app
            .path()
            .app_data_dir()
            .map_err(|_| "Application data is unavailable.")?;
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| "Observation time unavailable.")?
            .as_secs();
        let evidence = recovery_context::read_evidence(&directory, &incident_id, now)?;
        crate::recovery_user::Store::new(directory).inspect(&evidence, now)
    })
    .await
    .map_err(|_| "User acknowledgment observation is unavailable.".to_string())?
}

#[tauri::command]
pub async fn list_recovery_incidents(
    app: tauri::AppHandle,
    source: Source,
    cursor: Option<String>,
    limit: usize,
) -> Result<IncidentHistoryPage, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| "History observation time unavailable.")?.as_secs();
        let directory = app.path().app_data_dir().map_err(|_| "Application data is unavailable.")?;
        let views = crate::history_views::Store::new(&directory);
        match source {
            Source::Machine => {
                let mut page = sde_coordination::recovery::history::list(cursor.as_deref(), limit)
                    .map_err(|_| "Machine incident history is unavailable; keep the evidence and Check Again.")?;
                let mut visible = vec![]; let mut hidden_views = 0; let mut view_state_unavailable = false;
                for mut row in page.entries {
                    let binding = crate::history_views::Binding { source: "machine".into(), id: row.incident_id.clone(), fingerprint: row.view_key.clone() };
                    match views.hidden(&binding) {
                        Ok(true) => { hidden_views += 1; continue; }
                        Ok(false) => match app.state::<crate::history_views::Views>().bind(binding) {
                            Ok(token) => row.view_token = Some(token), Err(_) => view_state_unavailable = true,
                        },
                        Err(_) => view_state_unavailable = true,
                    }
                    visible.push(row);
                }
                page.entries = visible;
                Ok(IncidentHistoryPage {
                observed_at: now,
                machine: Some(page), hidden_views, view_state_unavailable,
                user: None,
            })},
            Source::User => {
                let mut page = crate::recovery_user::Store::new(directory.clone()).history(cursor.as_deref(), limit, now)?;
                let mut visible = vec![]; let mut hidden_views = 0; let mut view_state_unavailable = false;
                for mut row in page.entries {
                    if !row.view_key.is_empty() {
                        let binding = crate::history_views::Binding { source: "user".into(), id: row.incident_id.clone(), fingerprint: row.view_key.clone() };
                        match views.hidden(&binding) {
                            Ok(true) => { hidden_views += 1; continue; }
                            Ok(false) => match app.state::<crate::history_views::Views>().bind(binding) {
                                Ok(token) => row.view_token = Some(token), Err(_) => view_state_unavailable = true,
                            },
                            Err(_) => view_state_unavailable = true,
                        }
                    }
                    visible.push(row);
                }
                page.entries = visible;
                Ok(IncidentHistoryPage { observed_at: now, machine: None,
                    user: Some(page), hidden_views, view_state_unavailable })
            }
        }
    }).await.map_err(|_| "Incident history observation is unavailable.".to_string())?
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct IncidentHistoryPage {
    pub observed_at: u64,
    pub machine: Option<sde_coordination::recovery::history::Page>,
    pub user: Option<crate::recovery_user::HistoryPage>,
    pub hidden_views: usize,
    pub view_state_unavailable: bool,
}

#[tauri::command]
pub async fn delete_recovery_history_view(
    app: tauri::AppHandle, view_token: String, confirmed: bool,
) -> Result<(), String> {
    if !confirmed { return Err("Confirm deletion of the selected history view. Operational evidence and decisions remain.".into()); }
    let guard = app.state::<crate::Busy>().enter()?;
    tauri::async_runtime::spawn_blocking(move || {
        let _guard = guard;
        let binding = app.state::<crate::history_views::Views>().resolve(&view_token)?;
        let directory = app.path().app_data_dir().map_err(|_| "Application data is unavailable.")?;
        let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).map_err(|_| "History deletion time unavailable.")?.as_secs();
        let id = uuid::Uuid::parse_str(&binding.id).map_err(|_| "Invalid history identity.")?;
        let before = id.as_u128().checked_sub(1).map(|value| uuid::Uuid::from_u128(value).to_string());
        let current = if binding.source == "machine" {
            sde_coordination::recovery::history::list(before.as_deref(), 1).map_err(|_| "Machine history is unavailable; refresh before deleting its view.")?
                .entries.into_iter().find(|row| row.incident_id == binding.id).map(|row| row.view_key)
        } else {
            crate::recovery_user::Store::new(directory.clone()).history(before.as_deref(), 1, now)?
                .entries.into_iter().find(|row| row.incident_id == binding.id).map(|row| row.view_key)
        };
        if current.as_deref() != Some(binding.fingerprint.as_str()) { return Err("The displayed history entry changed. Refresh before deleting its view.".into()); }
        crate::history_views::Store::new(&directory).hide(&binding, now)
    }).await.map_err(|_| "History view deletion is unconfirmed. Refresh history; no operation was authorized.".to_string())?
}

#[tauri::command]
pub async fn list_recovery_reports(
    app: tauri::AppHandle,
    cursor: Option<String>,
    limit: usize,
) -> Result<recovery_reports::Page, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let directory = app.path().app_data_dir().map_err(|_| "Application data is unavailable.")?;
        Store::list_existing(directory.join("recovery-reports"), cursor.as_deref(), limit)
    })
        .await
        .map_err(|_| "Report history task is unavailable.".to_string())?
}
#[tauri::command]
pub async fn read_recovery_report(
    app: tauri::AppHandle,
    report_id: String,
) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let mut summary = existing_store(&app)?.load(&report_id)?;
        sanitize(&app, &mut summary);
        Ok(recovery_reports::html(&summary))
    })
    .await
    .map_err(|_| "Report read task is unavailable.".to_string())?
}

fn existing_store(app: &tauri::AppHandle) -> Result<Store, String> {
    Store::existing(
        app.path().app_data_dir()
            .map_err(|_| "Application data is unavailable.")?
            .join("recovery-reports"),
    )
}

/// Only a selected committed summary is exported. Never accept HTML, an input
/// path, private evidence or an execution argument from the caller.
#[tauri::command]
pub async fn export_recovery_report(
    app: tauri::AppHandle,
    report_id: String,
) -> Result<Option<String>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let mut summary = existing_store(&app)?.load(&report_id)?;
        sanitize(&app, &mut summary);
        support::save_recovery_copy(&app, &summary)
    })
    .await
    .map_err(|_| "Report export task is unavailable.".to_string())?
}
#[tauri::command]
pub async fn read_recovery_report_details(
    app: tauri::AppHandle,
    report_id: String,
) -> Result<ReportDetails, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let directory = app
            .path()
            .app_data_dir()
            .map_err(|_| "Application data is unavailable.")?;
        let reports = Store::existing(directory.join("recovery-reports"))?;
        let mut summary = reports.load(&report_id)?;
        sanitize(&app, &mut summary);
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map_err(|_| "History observation time unavailable.")?
            .as_secs();
        let acknowledgment = crate::recovery_history::observe(
            &summary,
            now,
            || {
                sde_coordination::recovery::inspect_acknowledgment()
                    .map(|record| record.map(|record| (record.incident_id, record.acknowledged_at)))
                    .map_err(|_| ())
            },
            |report, incident| {
                let directory = app.path().app_data_dir().map_err(|_| ())?;
                crate::recovery_user::Store::new(directory)
                    .inspect_report(report, incident, now)
                    .map_err(|_| ())
            },
        );
        Ok(ReportDetails {
            report_id,
            html: recovery_reports::html(&summary),
            acknowledgment,
        })
    })
    .await
    .map_err(|_| "History observation task is unavailable.".to_string())?
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ReportDetails {
    pub report_id: String,
    pub html: String,
    pub acknowledgment: crate::recovery_history::Observation,
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
    tauri::async_runtime::spawn_blocking(move || existing_store(&app)?.delete(&report_id))
        .await
        .map_err(|_| "Report deletion task is unavailable.".to_string())?
}
