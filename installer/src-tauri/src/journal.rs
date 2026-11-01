use serde::{Deserialize, Serialize};
use std::{
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};
use tauri::Manager;

#[cfg(test)]
use std::fs;
#[cfg(test)]
const MAX_JOURNAL_BYTES: u64 = 16 * 1024;

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Stage {
    Starting,
    System,
    Profile,
    Validation,
    Unknown,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Incident {
    pub schema: u8,
    pub id: String,
    pub operation: crate::Operation,
    pub stage: Stage,
    pub started_at: u64,
    pub observed_at: u64,
    pub log_path: Option<String>,
    pub acknowledged: bool,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Observation {
    pub incident: Option<Incident>,
    pub backend_active: bool,
    pub backend_interrupted: bool,
    pub backend_activity: Activity,
}

#[derive(Clone, Copy, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Activity {
    Active,
    Inactive,
    Unknown,
}

pub struct Active {
    store: crate::user_journal_store::Active,
    incident: Incident,
}

fn now() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

fn path(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_data_dir()
        .map(|directory| directory.join("operation-journal.json"))
        .map_err(|_| "Recovery information is unavailable.".to_string())
}

impl Active {
    pub fn begin(
        app: &tauri::AppHandle,
        id: &str,
        operation: crate::Operation,
        log_path: &Path,
    ) -> Result<Self, String> {
        let timestamp = now();
        let incident = Incident {
            schema: 1,
            id: id.to_string(),
            operation,
            stage: Stage::Starting,
            started_at: timestamp,
            observed_at: timestamp,
            log_path: Some(log_path.display().to_string()),
            acknowledged: false,
        };
        let path = path(app)?;
        let directory = path
            .parent()
            .ok_or("Recovery information is unavailable.")?
            .to_path_buf();
        let bytes = serde_json::to_vec(&incident)
            .map_err(|_| "Recovery information could not be encoded.")?;
        let store = crate::user_journal_store::Active::begin(directory, id, bytes, timestamp)?;
        Ok(Self { store, incident })
    }

    pub fn stage(&mut self, stage: Stage) -> Result<(), String> {
        self.incident.stage = stage;
        self.incident.observed_at = now();
        let bytes = serde_json::to_vec(&self.incident)
            .map_err(|_| "Recovery information could not be encoded.")?;
        self.store.stage(bytes, now())
    }

    pub fn complete(self) -> Result<(), String> {
        self.store.finish_known(now())
    }
    pub fn not_started(self) -> Result<(), String> {
        self.store.finish_not_started(now())
    }
}

fn read(path: &Path) -> Result<Option<Incident>, String> {
    let directory = path
        .parent()
        .ok_or("Recovery information is unavailable.")?;
    let Some(evidence) = crate::recovery_context::read_current_evidence(directory, now())? else {
        return Ok(None);
    };
    let mut incident: Incident =
        serde_json::from_slice(&evidence.bytes).map_err(|_| "Recovery information is invalid.")?;
    incident.acknowledged = crate::recovery_user::Store::new(directory.to_path_buf())
        .inspect(&evidence, now())?
        .is_some();
    Ok(Some(incident))
}

#[cfg(test)]
fn valid(incident: &Incident) -> bool {
    let future_limit = now().saturating_add(24 * 60 * 60);
    let invalid_log_path = incident
        .log_path
        .as_ref()
        .is_some_and(|value| value.len() > 4096 || value.contains('\r') || value.contains('\n'));
    !(incident.schema != 1
        || uuid::Uuid::parse_str(&incident.id).is_err()
        || matches!(incident.operation, crate::Operation::Validate)
        || incident.started_at == 0
        || incident.started_at > future_limit
        || incident.observed_at < incident.started_at
        || incident.observed_at > future_limit
        || invalid_log_path)
}

pub fn inspect(app: &tauri::AppHandle) -> Result<Observation, String> {
    let activity = match sde_coordination::operation_active() {
        Ok(true) => Activity::Active,
        Ok(false) => Activity::Inactive,
        Err(_) => Activity::Unknown,
    };
    Ok(Observation {
        incident: read(&path(app)?)?,
        // Conservative legacy compatibility until the final UI consumes the
        // explicit tri-state field. Unknown is never presented as inactive.
        backend_active: !matches!(activity, Activity::Inactive),
        backend_activity: activity,
        backend_interrupted: matches!(
            sde_coordination::status(),
            sde_coordination::Status::Interrupted
        ),
    })
}

pub fn acknowledge(_app: &tauri::AppHandle, _id: &str) -> Result<(), String> {
    Err("Use evidence-preserving acknowledgment in Recovery. The legacy dismiss action cannot delete an incident.".into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn journal_round_trip_is_strict_and_bounded() {
        let root = std::env::temp_dir().join(format!("sde-journal-{}", uuid::Uuid::new_v4()));
        fs::create_dir_all(&root).unwrap();
        let file = root.join("operation-journal.json");
        let incident = Incident {
            schema: 1,
            id: uuid::Uuid::new_v4().to_string(),
            operation: crate::Operation::Update,
            stage: Stage::System,
            started_at: now().saturating_sub(2),
            observed_at: now().saturating_sub(1),
            log_path: None,
            acknowledged: false,
        };
        fs::write(&file, serde_json::to_vec(&incident).unwrap()).unwrap();
        assert!(matches!(read(&file).unwrap().unwrap().stage, Stage::System));
        fs::write(&file, vec![b'x'; MAX_JOURNAL_BYTES as usize + 1]).unwrap();
        assert!(read(&file).is_err());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn rejects_impossible_or_non_mutating_incidents() {
        let candidate = Incident {
            schema: 1,
            id: uuid::Uuid::new_v4().to_string(),
            operation: crate::Operation::Install,
            stage: Stage::Unknown,
            started_at: now(),
            observed_at: now(),
            log_path: None,
            acknowledged: false,
        };
        let mut value = serde_json::to_value(candidate).unwrap();
        value["operation"] = serde_json::json!("validate");
        let parsed: Incident = serde_json::from_value(value).unwrap();
        assert!(!valid(&parsed));
        value = serde_json::to_value(parsed).unwrap();
        value["operation"] = serde_json::json!("install");
        value["observedAt"] = serde_json::json!(0);
        let impossible: Incident = serde_json::from_value(value).unwrap();
        assert!(!valid(&impossible));
    }
}
