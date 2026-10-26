use serde::{Deserialize, Serialize};
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};
use tauri::Manager;

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
}

pub struct Active {
    path: PathBuf,
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

fn persist(path: &Path, incident: &Incident) -> Result<(), String> {
    let directory = path
        .parent()
        .ok_or_else(|| "Recovery information is unavailable.".to_string())?;
    fs::create_dir_all(directory)
        .map_err(|_| "Recovery information could not be saved.".to_string())?;
    let bytes = serde_json::to_vec(incident)
        .map_err(|_| "Recovery information could not be saved.".to_string())?;
    let temporary = path.with_extension(format!("tmp-{}", uuid::Uuid::new_v4()));
    let mut file = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&temporary)
        .map_err(|_| "Recovery information could not be saved.".to_string())?;
    file.write_all(&bytes)
        .and_then(|_| file.sync_all())
        .map_err(|_| "Recovery information could not be saved.".to_string())?;
    replace(&temporary, path).map_err(|_| "Recovery information could not be saved.".to_string())
}

#[cfg(not(windows))]
fn replace(source: &Path, destination: &Path) -> std::io::Result<()> {
    fs::rename(source, destination)
}

#[cfg(windows)]
fn replace(source: &Path, destination: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::{
        MoveFileExW, MOVEFILE_REPLACE_EXISTING, MOVEFILE_WRITE_THROUGH,
    };
    let source: Vec<u16> = source.as_os_str().encode_wide().chain(Some(0)).collect();
    let destination: Vec<u16> = destination
        .as_os_str()
        .encode_wide()
        .chain(Some(0))
        .collect();
    if unsafe {
        MoveFileExW(
            source.as_ptr(),
            destination.as_ptr(),
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH,
        )
    } == 0
    {
        Err(std::io::Error::last_os_error())
    } else {
        Ok(())
    }
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
        persist(&path, &incident)?;
        Ok(Self { path, incident })
    }

    pub fn stage(&mut self, stage: Stage) -> Result<(), String> {
        self.incident.stage = stage;
        self.incident.observed_at = now();
        persist(&self.path, &self.incident)
    }

    pub fn complete(self) -> Result<(), String> {
        match fs::remove_file(self.path) {
            Ok(()) => Ok(()),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
            Err(_) => Err("Recovery information could not be cleared.".into()),
        }
    }
}

fn read(path: &Path) -> Result<Option<Incident>, String> {
    let metadata = match fs::metadata(path) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err("Recovery information could not be read.".into()),
    };
    if metadata.len() > MAX_JOURNAL_BYTES {
        return Err("Recovery information is invalid.".into());
    }
    let bytes = fs::read(path).map_err(|_| "Recovery information could not be read.")?;
    let incident: Incident =
        serde_json::from_slice(&bytes).map_err(|_| "Recovery information is invalid.")?;
    if !valid(&incident) {
        return Err("Recovery information is invalid.".into());
    }
    Ok(Some(incident))
}

fn valid(incident: &Incident) -> bool {
    let future_limit = now().saturating_add(24 * 60 * 60);
    let invalid_log_path = incident.log_path.as_ref().is_some_and(|value| {
        value.len() > 4096 || value.contains('\r') || value.contains('\n')
    });
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
    Ok(Observation {
        incident: read(&path(app)?)?,
        backend_active: sde_coordination::operation_active().unwrap_or(false),
    })
}

pub fn acknowledge(app: &tauri::AppHandle, id: &str) -> Result<(), String> {
    let path = path(app)?;
    let incident = read(&path)?
        .ok_or_else(|| "There is no interrupted operation to acknowledge.".to_string())?;
    if incident.id != id {
        return Err("The interrupted operation changed. Refresh and try again.".into());
    }
    fs::remove_file(path).map_err(|_| "Recovery information could not be dismissed.".into())
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
        persist(&file, &incident).unwrap();
        assert!(matches!(read(&file).unwrap().unwrap().stage, Stage::System));
        fs::write(&file, vec![b'x'; MAX_JOURNAL_BYTES as usize + 1]).unwrap();
        assert!(read(&file).is_err());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn rejects_impossible_or_non_mutating_incidents() {
        let valid = Incident {
            schema: 1,
            id: uuid::Uuid::new_v4().to_string(),
            operation: crate::Operation::Install,
            stage: Stage::Unknown,
            started_at: now(),
            observed_at: now(),
            log_path: None,
            acknowledged: false,
        };
        let mut value = serde_json::to_value(valid).unwrap();
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
