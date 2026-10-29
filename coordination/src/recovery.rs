//! Production storage foundation. Intent is NOT an execution capability.
//! Ordinary storage APIs never remove/replace transaction.json. Retirement is
//! crate-private and requires a lease-borrowed permit from the mutation module.
//! Bootstrap/GUI/execution consumers will be integrated only after native review.
pub(crate) mod acknowledgment;
pub(crate) mod restart;
use crate::{acquire_at, Error, Result};
pub use acknowledgment::{inspect_acknowledgment, record_acknowledgment, Acknowledgment};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File},
    io::{Read, Write},
    path::Path,
};
use uuid::Uuid;

const PUBLIC: &str = "recovery-incident.json";
const BINDING: &str = "recovery-binding.json";
const INTENT: &str = "recovery-acknowledgment.json";
const MAX_RECORD: u64 = 4096;
const MAX_JOURNAL: u64 = 64 * 1024;

#[derive(Clone, Copy)]
pub(crate) enum Kind {
    Private,
    Public,
    Intent,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Incident {
    schema: u8,
    pub incident_id: String,
}

impl Incident {
    fn valid(&self) -> bool {
        self.schema == 1
            && Uuid::parse_str(&self.incident_id).is_ok_and(|id| id.to_string() == self.incident_id)
    }
    fn parse(bytes: &[u8]) -> Result<Self> {
        if bytes.len() as u64 > MAX_RECORD {
            return Err(Error::Untrusted);
        }
        let value: Self = serde_json::from_slice(bytes).map_err(|_| Error::Untrusted)?;
        if !value.valid() {
            return Err(Error::Untrusted);
        }
        Ok(value)
    }
}

#[derive(Clone, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Binding {
    schema: u8,
    incident_id: String,
    journal_sha256: String,
    journal_identity: String,
}

/// Provision only from a normally privileged context. This does not initialize
/// coordination, elevate, inspect packages, or clear the old interruption.
pub fn prepare() -> Result<Option<Incident>> {
    prepare_at(&crate::root())
}

/// Read only sanitized state. None means no current transaction, not "healthy".
pub fn inspect() -> Result<Option<Incident>> {
    inspect_at(&crate::root())
}

/// Write a bounded decision to the fixed, pre-created slot. No elevation and no
/// creation of caller-controlled files. Partial/concurrent writes are invalid
/// until a privileged consumer revalidates the exact private evidence binding.
pub fn submit(incident_id: &str) -> Result<()> {
    submit_at(&crate::root(), incident_id)
}

/// Privileged diagnostic only. The result is not an execution lease and must
/// never be cached as authorization to start a later transaction.
pub fn verify_submission() -> Result<bool> {
    let dir = crate::root();
    let _lease = acquire_at(&dir, "operations.gate", false)?;
    pending_at(&dir)
}

pub(crate) fn prepare_at(dir: &Path) -> Result<Option<Incident>> {
    let _lease = acquire_at(dir, "operations.gate", false)?;
    prepare_locked(dir)
}

pub(crate) fn prepare_locked(dir: &Path) -> Result<Option<Incident>> {
    let (journal, journal_identity) = match read_journal(dir)? {
        Some(record) => record,
        None => return Ok(None),
    };
    let digest = format!("{:x}", Sha256::digest(&journal));
    let old = read_optional(dir, BINDING, Kind::Private, MAX_RECORD)?
        .map(|bytes| serde_json::from_slice::<Binding>(&bytes).map_err(|_| Error::Untrusted))
        .transpose()?;
    if old.as_ref().is_some_and(|record| {
        record.schema != 1
            || !Incident {
                schema: 1,
                incident_id: record.incident_id.clone(),
            }
            .valid()
            || record.journal_sha256.len() != 64
            || !record
                .journal_sha256
                .bytes()
                .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
    }) {
        return Err(Error::Untrusted);
    }
    let id = old
        .as_ref()
        .filter(|record| {
            record.journal_sha256 == digest && record.journal_identity == journal_identity
        })
        .map(|record| record.incident_id.clone())
        .unwrap_or_else(|| Uuid::new_v4().to_string());
    let incident = Incident {
        schema: 1,
        incident_id: id.clone(),
    };
    let binding = Binding {
        schema: 1,
        incident_id: id,
        journal_sha256: digest,
        journal_identity,
    };
    // Private binding first: a stale public marker can never authorize a new
    // generation. Re-running after interruption reconstructs the same marker.
    if old
        .as_ref()
        .is_none_or(|record| record.incident_id != incident.incident_id)
    {
        persist(
            dir,
            BINDING,
            Kind::Private,
            &serde_json::to_vec(&binding).map_err(|_| Error::Unavailable)?,
        )?;
    }
    persist(
        dir,
        PUBLIC,
        Kind::Public,
        &serde_json::to_vec(&incident).map_err(|_| Error::Unavailable)?,
    )?;
    match read_optional(dir, INTENT, Kind::Intent, MAX_RECORD) {
        Ok(Some(_)) => (), // Never silently clear a student's earlier intent.
        Ok(None) => {
            let mut file = open(dir, INTENT, Kind::Intent, true, true)?;
            file.write_all(b"{}")
                .and_then(|_| file.sync_all())
                .map_err(|_| Error::Unavailable)?;
            crate::sync_directory(dir)?;
        }
        Err(error) => return Err(error),
    }
    restart::prepare_context(dir, &incident)?;
    Ok(Some(incident))
}

pub(crate) fn inspect_at(dir: &Path) -> Result<Option<Incident>> {
    let _lease = acquire_at(dir, "operations.gate", false)?;
    inspect_locked(dir)
}

fn inspect_locked(dir: &Path) -> Result<Option<Incident>> {
    // Directory enumeration avoids opening or exposing a private transaction.
    let exists = fs::read_dir(dir)
        .map_err(|_| Error::Unavailable)?
        .take(34)
        .collect::<std::io::Result<Vec<_>>>()
        .map_err(|_| Error::Unavailable)?;
    if exists.len() > 33 {
        return Err(Error::Untrusted);
    }
    if !exists
        .iter()
        .any(|entry| entry.file_name() == "transaction.json")
    {
        return Ok(None);
    }
    let bytes = read_optional(dir, PUBLIC, Kind::Public, MAX_RECORD)?.ok_or(Error::Unavailable)?;
    Incident::parse(&bytes).map(Some)
}

pub(crate) fn submit_at(dir: &Path, incident_id: &str) -> Result<()> {
    let _lease = acquire_at(dir, "operations.gate", false)?;
    let submitted = Incident {
        schema: 1,
        incident_id: incident_id.to_string(),
    };
    if !submitted.valid() {
        return Err(Error::Untrusted);
    }
    let public = read_optional(dir, PUBLIC, Kind::Public, MAX_RECORD)?.ok_or(Error::Unavailable)?;
    if Incident::parse(&public)? != submitted {
        return Err(Error::Interrupted);
    }
    match crate::no_interruption(dir) {
        Err(Error::Interrupted) => (),
        Err(error) => return Err(error),
        Ok(()) => return Err(Error::Interrupted),
    }
    let mut slot = open(dir, INTENT, Kind::Intent, false, true)?;
    let bytes = serde_json::to_vec(&submitted).map_err(|_| Error::Unavailable)?;
    slot.set_len(0)
        .and_then(|_| slot.write_all(&bytes))
        .and_then(|_| slot.sync_all())
        .map_err(|_| Error::Unavailable)
}

/// For privileged reconciliation tests/future consumers. Must be called under
/// the same operation lease as prepare/execute, not used as a cached permission.
pub(crate) fn pending_at(dir: &Path) -> Result<bool> {
    let binding =
        read_optional(dir, BINDING, Kind::Private, MAX_RECORD)?.ok_or(Error::Unavailable)?;
    let binding: Binding = serde_json::from_slice(&binding).map_err(|_| Error::Untrusted)?;
    let (current, identity) = read_journal(dir)?.ok_or(Error::Interrupted)?;
    let intent = read_optional(dir, INTENT, Kind::Intent, MAX_RECORD)?.ok_or(Error::Unavailable)?;
    let public = read_optional(dir, PUBLIC, Kind::Public, MAX_RECORD)?.ok_or(Error::Unavailable)?;
    let Ok(intent) = Incident::parse(&intent) else {
        return Ok(false);
    };
    Ok(binding.schema == 1
        && Incident::parse(&public)? == intent
        && binding.incident_id == intent.incident_id
        && binding.journal_identity == identity
        && binding.journal_sha256 == format!("{:x}", Sha256::digest(&current)))
}

pub(crate) fn read_journal(dir: &Path) -> Result<Option<(Vec<u8>, String)>> {
    match fs::symlink_metadata(dir.join("transaction.json")) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(Error::Unavailable),
        Ok(_) => (),
    }
    let file = open(dir, "transaction.json", Kind::Private, false, false)?;
    let identity = journal_identity(&file)?;
    let mut bytes = Vec::new();
    (&file)
        .take(MAX_JOURNAL + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| Error::Unavailable)?;
    if bytes.len() as u64 > MAX_JOURNAL {
        return Err(Error::Untrusted);
    }
    if journal_identity(&file)? != identity {
        return Err(Error::Busy);
    }
    Ok(Some((bytes, identity)))
}

#[cfg(unix)]
fn journal_identity(file: &File) -> Result<String> {
    use std::os::unix::fs::MetadataExt;
    let m = file.metadata().map_err(|_| Error::Unavailable)?;
    Ok(format!(
        "{}:{}:{}:{}:{}:{}:{}",
        m.dev(),
        m.ino(),
        m.ctime(),
        m.ctime_nsec(),
        m.mtime(),
        m.mtime_nsec(),
        m.len()
    ))
}

#[cfg(windows)]
fn journal_identity(file: &File) -> Result<String> {
    crate::windows::recovery_file_identity(file)
}

fn read_optional(dir: &Path, name: &str, kind: Kind, max: u64) -> Result<Option<Vec<u8>>> {
    match fs::symlink_metadata(dir.join(name)) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(Error::Unavailable),
        Ok(_) => (),
    }
    let file = open(dir, name, kind, false, false)?;
    let mut bytes = Vec::new();
    file.take(max + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| Error::Unavailable)?;
    if bytes.len() as u64 > max {
        return Err(Error::Untrusted);
    }
    Ok(Some(bytes))
}

fn persist(dir: &Path, name: &str, kind: Kind, bytes: &[u8]) -> Result<()> {
    // Validate an existing destination without following links; do not repair a
    // hostile layout. Only a file created by this invocation can be cleaned up.
    read_optional(dir, name, kind, MAX_RECORD)?;
    let temporary = format!("{name}.tmp-{}", Uuid::new_v4());
    let mut created = false;
    let result = (|| {
        let mut file = open(dir, &temporary, kind, true, true)?;
        created = true;
        file.write_all(bytes)
            .and_then(|_| file.sync_all())
            .map_err(|_| Error::Unavailable)?;
        drop(file);
        #[cfg(unix)]
        fs::rename(dir.join(&temporary), dir.join(name)).map_err(|_| Error::Unavailable)?;
        #[cfg(windows)]
        crate::windows::replace_recovery(dir, &temporary, name)?;
        crate::sync_directory(dir)
    })();
    if result.is_err() && created {
        let _ = fs::remove_file(dir.join(&temporary));
    }
    result
}

#[cfg(unix)]
pub(crate) fn open(dir: &Path, name: &str, kind: Kind, create: bool, write: bool) -> Result<File> {
    use std::os::unix::fs::{MetadataExt, OpenOptionsExt, PermissionsExt};
    crate::validate_dir(dir)?;
    let mode = match kind {
        Kind::Private => 0o600,
        Kind::Public => 0o644,
        Kind::Intent => 0o666,
    };
    let file = fs::OpenOptions::new()
        .read(true)
        .write(write)
        .create_new(create)
        .mode(mode)
        .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC | libc::O_NONBLOCK)
        .open(dir.join(name))
        .map_err(|_| Error::Unavailable)?;
    // Override only the mode of this newly created, still-pinned file; never
    // chmod an existing path or assume the caller's umask permits a student write.
    if create {
        file.set_permissions(fs::Permissions::from_mode(mode))
            .map_err(|_| Error::Unavailable)?;
    }
    let m = file.metadata().map_err(|_| Error::Unavailable)?;
    if !m.is_file() || m.uid() != 0 || m.nlink() != 1 || m.mode() & 0o7777 != mode {
        return Err(Error::Untrusted);
    }
    Ok(file)
}

#[cfg(windows)]
pub(crate) fn open(dir: &Path, name: &str, kind: Kind, create: bool, write: bool) -> Result<File> {
    crate::windows::open_recovery(dir, name, kind, create, write)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn intent_is_strict_canonical_bounded_and_contains_no_execution_arguments() {
        let id = "9fe3858b-58da-4b96-b47d-ec2f1b867353";
        let good = format!(r#"{{"schema":1,"incidentId":"{id}"}}"#);
        assert_eq!(Incident::parse(good.as_bytes()).unwrap().incident_id, id);
        for bytes in [
            b"{}".to_vec(),
            b"\xff".to_vec(),
            vec![b' '; 4097],
            format!(r#"{{"schema":true,"incidentId":"{id}"}}"#).into_bytes(),
            format!(r#"{{"schema":1.0,"incidentId":"{id}"}}"#).into_bytes(),
            format!(r#"{{"schema":2,"incidentId":"{id}"}}"#).into_bytes(),
            format!(r#"{{"schema":1,"incidentId":"{id}","path":"ignored"}}"#).into_bytes(),
            format!(r#"{{"schema":1,"schema":1,"incidentId":"{id}"}}"#).into_bytes(),
            format!(r#"{{"schema":1,"incidentId":"{}"}}"#, id.to_uppercase()).into_bytes(),
        ] {
            assert!(Incident::parse(&bytes).is_err());
        }
    }
}
