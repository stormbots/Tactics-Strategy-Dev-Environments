//! Diagnostic provenance only. Never used to acknowledge or authorize work.
use serde::{Deserialize, Serialize};
use std::{fs, io::Read, path::Path};

type Result<T> = std::result::Result<T, String>;
const MAX_RECORD: u64 = 16 * 1024;

#[derive(Clone, Copy, Default, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Source {
    #[default]
    Machine,
    User,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct UserIncident {
    pub id: String,
    pub operation: String,
    pub stage: String,
    pub started_at: u64,
    pub observed_at: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "source", rename_all = "snake_case", deny_unknown_fields)]
pub enum Context {
    Machine {
        #[serde(rename = "incidentId")]
        incident_id: String,
    },
    User {
        incident: UserIncident,
    },
}

fn canonical(id: &str) -> bool {
    uuid::Uuid::parse_str(id).is_ok_and(|value| value.to_string() == id)
}
impl Context {
    pub fn validate(&self, expected: &str, captured_at: u64) -> Result<()> {
        let valid = match self {
            Self::Machine { incident_id } => canonical(incident_id) && incident_id == expected,
            Self::User { incident } => {
                canonical(&incident.id)
                    && incident.id == expected
                    && ["install", "repair", "update"].contains(&incident.operation.as_str())
                    && ["starting", "system", "profile", "validation", "unknown"]
                        .contains(&incident.stage.as_str())
                    && incident.started_at != 0
                    && incident.started_at <= incident.observed_at
                    && incident.observed_at <= captured_at
            }
        };
        if valid {
            Ok(())
        } else {
            Err("Incident provenance is invalid or changed; Check Again.".into())
        }
    }
}

// Read the existing user journal schema without ever exporting its raw bytes or
// logPath. Field bounds apply even though this is same-account diagnostic data.
#[derive(Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Record {
    schema: u8,
    id: String,
    operation: String,
    stage: String,
    started_at: u64,
    observed_at: u64,
    log_path: Option<String>,
    acknowledged: bool,
}

pub fn read_user(directory: &Path, expected: &str, captured_at: u64) -> Result<Context> {
    if !canonical(expected) || !directory.is_absolute() {
        return Err("Invalid user incident request.".into());
    }
    for parent in directory.ancestors() {
        let metadata = fs::symlink_metadata(parent).map_err(|_| "User evidence is unavailable.")?;
        if !metadata.is_dir() || linked(&metadata) {
            return Err("Linked user evidence paths are not supported.".into());
        }
    }
    let path = directory.join("operation-journal.json");
    let metadata = fs::symlink_metadata(&path).map_err(|_| "User evidence is unavailable.")?;
    if !metadata.is_file() || linked(&metadata) {
        return Err("Linked or unexpected user evidence is not supported.".into());
    }
    let mut options = fs::OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC | libc::O_NONBLOCK);
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        options.custom_flags(0x00200000).share_mode(1);
    }
    let file = options
        .open(path)
        .map_err(|_| "User evidence could not be opened.")?;
    let metadata = file
        .metadata()
        .map_err(|_| "User evidence metadata unavailable.")?;
    if !metadata.is_file() || linked(&metadata) || metadata.len() > MAX_RECORD {
        return Err("User evidence is invalid or oversized.".into());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        // Legacy journals may be 0644; capture must not chmod or rewrite them.
        if metadata.nlink() != 1
            || metadata.uid() != unsafe { libc::geteuid() }
            || metadata.mode() & 0o022 != 0
        {
            return Err("User evidence ownership, links or permissions are unsafe.".into());
        }
    }
    #[cfg(windows)]
    {
        use std::os::windows::io::AsRawHandle;
        use windows_sys::Win32::Storage::FileSystem::*;
        let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
        if unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) } == 0
            || info.nNumberOfLinks != 1
            || info.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT != 0
        {
            return Err("User evidence links are unsafe.".into());
        }
    }
    let mut bytes = Vec::new();
    file.take(MAX_RECORD + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "User evidence read failed.")?;
    if bytes.len() as u64 > MAX_RECORD {
        return Err("User evidence is oversized.".into());
    }
    let record: Record = serde_json::from_slice(&bytes).map_err(|_| "User evidence is invalid.")?;
    if record.schema != 1
        || record.acknowledged
        || record
            .log_path
            .as_ref()
            .is_some_and(|p| p.len() > 4096 || p.contains(['\r', '\n', '\0']))
    {
        return Err("User evidence is invalid or already acknowledged; Check Again.".into());
    }
    let context = Context::User {
        incident: UserIncident {
            id: record.id,
            operation: record.operation,
            stage: record.stage,
            started_at: record.started_at,
            observed_at: record.observed_at,
        },
    };
    context.validate(expected, captured_at)?;
    Ok(context)
}

fn linked(metadata: &fs::Metadata) -> bool {
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        if metadata.file_attributes() & 0x400 != 0 {
            return true;
        }
    }
    metadata.file_type().is_symlink()
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Fixture {
        directory: std::path::PathBuf,
        id: String,
    }
    impl Fixture {
        fn new() -> Self {
            let directory =
                std::env::temp_dir().join(format!("sde-context-ci-{}", uuid::Uuid::new_v4()));
            fs::create_dir(&directory).unwrap();
            let result = Self {
                directory,
                id: uuid::Uuid::new_v4().to_string(),
            };
            fs::write(result.path(), serde_json::to_vec(&result.record()).unwrap()).unwrap();
            result
        }
        fn path(&self) -> std::path::PathBuf {
            self.directory.join("operation-journal.json")
        }
        fn record(&self) -> serde_json::Value {
            serde_json::json!({"schema":1,"id":self.id,"operation":"update","stage":"profile",
                "startedAt":10,"observedAt":20,"logPath":"/private/student/token.log","acknowledged":false})
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.directory).unwrap();
        }
    }

    #[test]
    fn user_report_context_retains_original_provenance_without_path_or_source_mutation() {
        let f = Fixture::new();
        let before = fs::read(f.path()).unwrap();
        let modified = fs::metadata(f.path()).unwrap().modified().unwrap();
        let context = read_user(&f.directory, &f.id, 100).unwrap();
        let json = serde_json::to_string(&context).unwrap();
        assert!(!json.contains("private"));
        assert!(!json.contains("logPath"));
        let Context::User { incident } = context else {
            panic!("expected user source")
        };
        assert_eq!((incident.started_at, incident.observed_at), (10, 20));
        assert_eq!(incident.stage, "profile");
        assert_eq!(fs::read(f.path()).unwrap(), before);
        assert_eq!(
            fs::metadata(f.path()).unwrap().modified().unwrap(),
            modified
        );
    }

    #[test]
    fn user_report_context_rejects_stale_malformed_oversized_and_impossible_evidence() {
        let f = Fixture::new();
        assert!(read_user(&f.directory, &uuid::Uuid::new_v4().to_string(), 100).is_err());
        for (field, value) in [
            ("schema", serde_json::json!(2)),
            ("operation", serde_json::json!("validate")),
            ("stage", serde_json::json!("<script>")),
            ("observedAt", serde_json::json!(101)),
            ("startedAt", serde_json::json!(21)),
            ("acknowledged", serde_json::json!(true)),
            ("transactionToken", serde_json::json!("not allowed")),
        ] {
            let mut record = f.record();
            record[field] = value;
            fs::write(f.path(), serde_json::to_vec(&record).unwrap()).unwrap();
            assert!(
                read_user(&f.directory, &f.id, 100).is_err(),
                "field {field}"
            );
        }
        fs::write(f.path(), vec![b'x'; MAX_RECORD as usize + 1]).unwrap();
        assert!(read_user(&f.directory, &f.id, 100).is_err());
    }

    #[test]
    fn user_report_context_rejects_hardlinks_without_changing_evidence() {
        let f = Fixture::new();
        let other = f.directory.join("original.json");
        fs::rename(f.path(), &other).unwrap();
        fs::hard_link(&other, f.path()).unwrap();
        let before = fs::read(&other).unwrap();
        assert!(read_user(&f.directory, &f.id, 100).is_err());
        assert_eq!(fs::read(&other).unwrap(), before);
    }

    #[cfg(unix)]
    #[test]
    fn user_report_context_rejects_symlinks_and_writable_source_without_chmod() {
        use std::os::unix::fs::{symlink, PermissionsExt};
        let f = Fixture::new();
        fs::set_permissions(f.path(), fs::Permissions::from_mode(0o666)).unwrap();
        assert!(read_user(&f.directory, &f.id, 100).is_err());
        assert_eq!(
            fs::metadata(f.path()).unwrap().permissions().mode() & 0o777,
            0o666
        );
        fs::rename(f.path(), f.directory.join("original.json")).unwrap();
        symlink("original.json", f.path()).unwrap();
        assert!(read_user(&f.directory, &f.id, 100).is_err());
        let alias = f.directory.join("alias");
        symlink(&f.directory, &alias).unwrap();
        assert!(read_user(&alias, &f.id, 100).is_err());
    }
}
