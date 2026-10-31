//! Read-only opaque archive discovery. Private receipts/journals are never read
//! or made public, and an archive filename is not proof of acknowledgment.
use super::*;
use std::collections::{BTreeMap, BTreeSet};

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Entry {
    pub incident_id: String,
    pub status: &'static str,
    pub continuation: &'static str,
    #[serde(skip)]
    pub view_key: String,
    pub view_token: Option<String>,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Page {
    pub entries: Vec<Entry>,
    pub next_cursor: Option<String>,
}
pub fn list(cursor: Option<&str>, limit: usize) -> Result<Page> {
    list_at(&crate::root(), cursor, limit)
}
pub(crate) fn list_at(dir: &Path, cursor: Option<&str>, limit: usize) -> Result<Page> {
    if !(1..=100).contains(&limit) || cursor.is_some_and(|id| !canonical(id)) {
        return Err(Error::Untrusted);
    }
    let _lease = acquire_at(dir, "operations.gate", false)?;
    let archive = dir.join("recovery-archive");
    match fs::symlink_metadata(&archive) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(Page {
                entries: vec![],
                next_cursor: None,
            })
        }
        Err(_) => return Err(Error::Unavailable),
        Ok(_) => acknowledgment::validate_archive(dir)?,
    }
    let mut ids = BTreeSet::new();
    let mut keys = BTreeMap::<String, Vec<String>>::new();
    for entry in fs::read_dir(&archive).map_err(|_| Error::Unavailable)? {
        let entry = entry.map_err(|_| Error::Unavailable)?;
        let name = entry.file_name();
        let Some(name) = name.to_str() else { continue };
        let id = [".receipt.json", ".retired-journal", ".journal"]
            .iter()
            .find_map(|suffix| name.strip_suffix(suffix));
        let Some(id) = id.filter(|id| canonical(id)) else {
            continue;
        };
        // Windows DirEntry metadata comes from directory enumeration. Do not
        // open a private receipt even for an attribute-only history query.
        let metadata = entry.metadata().map_err(|_| Error::Unavailable)?;
        if !metadata.is_file() || metadata.file_type().is_symlink() {
            return Err(Error::Untrusted);
        }
        #[cfg(windows)]
        {
            use std::os::windows::fs::MetadataExt;
            if metadata.file_attributes() & 0x400 != 0 {
                return Err(Error::Untrusted);
            }
        }
        if cursor.is_none_or(|cursor| id > cursor) {
            ids.insert(id.to_owned());
            if ids.len() > limit + 1 {
                ids.pop_last();
            }
            // Only public enumeration metadata, never private file contents.
            if ids.contains(id) {
                let timestamp = |value: std::io::Result<std::time::SystemTime>| {
                    value
                        .ok()
                        .and_then(|value| value.duration_since(std::time::UNIX_EPOCH).ok())
                        .map(|value| value.as_nanos())
                };
                keys.entry(id.to_owned()).or_default().push(format!(
                    "{name}|{}|{:?}|{:?}",
                    metadata.len(),
                    timestamp(metadata.modified()),
                    timestamp(metadata.created())
                ));
            }
            keys.retain(|id, _| ids.contains(id));
        }
    }
    let more = ids.len() > limit;
    let entries: Vec<_> = ids
        .into_iter()
        .take(limit)
        .map(|incident_id| {
            let mut fields = keys.remove(&incident_id).unwrap_or_default();
            fields.sort();
            Entry {
                view_key: format!("{:x}", Sha256::digest(fields.join("\n").as_bytes())),
                view_token: None,
                incident_id,
                status: "archive_observed_acknowledgment_unknown",
                continuation: "not_recorded",
            }
        })
        .collect();
    let next_cursor = if more {
        entries.last().map(|entry| entry.incident_id.clone())
    } else {
        None
    };
    Ok(Page {
        entries,
        next_cursor,
    })
}
fn canonical(id: &str) -> bool {
    Uuid::parse_str(id).is_ok_and(|value| value.to_string() == id)
}
