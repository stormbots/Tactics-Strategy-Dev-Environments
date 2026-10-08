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
    Unavailable,
}
#[derive(Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Schedule {
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
    serde_json::from_slice(&output.stdout)
        .map_err(|_| "Maintenance returned incomplete information. Please refresh.".into())
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
}
