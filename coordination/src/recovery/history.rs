//! Read-only opaque archive discovery. Private receipts/journals are never read
//! or made public, and an archive filename is not proof of acknowledgment.
use super::*;
use std::collections::BTreeSet;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Entry {
    pub incident_id: String,
    pub status: &'static str,
    pub continuation: &'static str,
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
        }
    }
    let more = ids.len() > limit;
    let entries: Vec<_> = ids
        .into_iter()
        .take(limit)
        .map(|incident_id| Entry {
            incident_id,
            status: "archive_observed_acknowledgment_unknown",
            continuation: "not_recorded",
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
