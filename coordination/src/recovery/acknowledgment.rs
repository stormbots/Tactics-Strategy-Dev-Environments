//! Durable user decision and immutable evidence copy. Recording acknowledgment
//! is not permission to execute: no current transaction or old guard is removed.
use super::*;
use std::{
    path::PathBuf,
    time::{SystemTime, UNIX_EPOCH},
};

const DISPOSITION: &str = "recovery-disposition.json";
const ARCHIVE: &str = "recovery-archive";

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Acknowledgment {
    schema: u8,
    pub incident_id: String,
    pub acknowledged_at: u64,
}

impl Acknowledgment {
    fn valid(&self) -> bool {
        self.schema == 1
            && self.acknowledged_at != 0
            && Incident {
                schema: self.schema,
                incident_id: self.incident_id.clone(),
            }
            .valid()
    }
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Receipt {
    schema: u8,
    binding: Binding,
    acknowledgment: Acknowledgment,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Phase {
    Evidence,
    Receipt,
    PublicSnapshot,
}

/// Privileged decision reconciliation only. The original journal remains
/// present and still blocks operation()/installation(). Future execution code
/// must separately preserve/transition it under its own fresh safety checks.
pub fn record_acknowledgment() -> Result<Option<Acknowledgment>> {
    record_at(&crate::root(), |_| Ok(()))
}

/// Sanitized, non-authoritative UI observation. Never cache as execution consent.
pub fn inspect_acknowledgment() -> Result<Option<Acknowledgment>> {
    inspect_at(&crate::root())
}

pub(crate) fn inspect_at(dir: &Path) -> Result<Option<Acknowledgment>> {
    let _lease = acquire_at(dir, "operations.gate", false)?;
    let Some(incident) = inspect_locked(dir)? else {
        return Ok(None);
    };
    let Some(bytes) = read_optional(dir, DISPOSITION, Kind::Public, MAX_RECORD)? else {
        return Ok(None);
    };
    let acknowledgment: Acknowledgment =
        serde_json::from_slice(&bytes).map_err(|_| Error::Untrusted)?;
    if !acknowledgment.valid() {
        return Err(Error::Untrusted);
    }
    Ok((acknowledgment.incident_id == incident.incident_id).then_some(acknowledgment))
}

/// `after` is an internal failure-point hook for native tests, never caller data
/// or a public API argument. All reads/publications stay under one operation lease.
pub(crate) fn record_at(
    dir: &Path,
    mut after: impl FnMut(Phase) -> Result<()>,
) -> Result<Option<Acknowledgment>> {
    let _lease = acquire_at(dir, "operations.gate", false)?;
    let Some((journal, identity)) = read_journal(dir)? else {
        return Ok(None);
    };
    let bytes =
        read_optional(dir, BINDING, Kind::Private, MAX_RECORD)?.ok_or(Error::Unavailable)?;
    let binding: Binding = serde_json::from_slice(&bytes).map_err(|_| Error::Untrusted)?;
    let incident = Incident {
        schema: binding.schema,
        incident_id: binding.incident_id.clone(),
    };
    if !incident.valid() {
        return Err(Error::Untrusted);
    }
    if binding.journal_sha256 != format!("{:x}", Sha256::digest(&journal))
        || binding.journal_identity != identity
    {
        return Err(Error::Interrupted);
    }
    let public = read_optional(dir, PUBLIC, Kind::Public, MAX_RECORD)?.ok_or(Error::Unavailable)?;
    if Incident::parse(&public)? != incident {
        return Err(Error::Interrupted);
    }

    // No archive directories/files are created for an unacknowledged incident.
    let archive = dir.join(ARCHIVE);
    let receipt_name = format!("{}.receipt.json", binding.incident_id);
    let evidence_name = format!("{}.journal", binding.incident_id);
    let existing = match fs::symlink_metadata(&archive) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => None,
        Err(_) => return Err(Error::Unavailable),
        Ok(_) => {
            validate_archive(dir)?;
            read_optional(&archive, &receipt_name, Kind::Private, MAX_RECORD)?
                .map(|bytes| {
                    serde_json::from_slice::<Receipt>(&bytes).map_err(|_| Error::Untrusted)
                })
                .transpose()?
        }
    };
    let acknowledgment = if let Some(receipt) = existing {
        if receipt.schema != 1
            || receipt.binding != binding
            || !receipt.acknowledgment.valid()
            || receipt.acknowledgment.incident_id != binding.incident_id
        {
            return Err(Error::Untrusted);
        }
        receipt.acknowledgment
    } else {
        if !pending_at(dir)? {
            return Ok(None);
        }
        let acknowledged_at = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|_| Error::Unavailable)?
            .as_secs();
        if acknowledged_at == 0 {
            return Err(Error::Unavailable);
        }
        Acknowledgment {
            schema: 1,
            incident_id: binding.incident_id.clone(),
            acknowledged_at,
        }
    };

    let archive = ensure_archive(dir)?;
    // An existing final archive is immutable. Mismatched bytes are corruption,
    // not a reason to overwrite it or to accept only the mutable intent slot.
    let evidence = read_optional(&archive, &evidence_name, Kind::Private, MAX_JOURNAL)?;
    if let Some(bytes) = evidence {
        if bytes != journal {
            return Err(Error::Untrusted);
        }
    } else {
        // A committed receipt without its evidence cannot be silently rebuilt:
        // explicit history-deletion semantics are a separate later feature.
        if read_optional(&archive, &receipt_name, Kind::Private, MAX_RECORD)?.is_some() {
            return Err(Error::Untrusted);
        }
        publish_once(&archive, &evidence_name, &journal)?;
    }
    after(Phase::Evidence)?;
    if read_optional(&archive, &receipt_name, Kind::Private, MAX_RECORD)?.is_none() {
        let receipt = Receipt {
            schema: 1,
            binding,
            acknowledgment: acknowledgment.clone(),
        };
        let bytes = serde_json::to_vec(&receipt).map_err(|_| Error::Unavailable)?;
        publish_once(&archive, &receipt_name, &bytes)?;
    }
    after(Phase::Receipt)?;
    // Public acknowledgment is published only after the durable private receipt
    // and byte-identical evidence copy exist. A restart can reconstruct this view
    // from the receipt even if someone clears the mutable intent in the meantime.
    persist(
        dir,
        DISPOSITION,
        Kind::Public,
        &serde_json::to_vec(&acknowledgment).map_err(|_| Error::Unavailable)?,
    )?;
    after(Phase::PublicSnapshot)?;
    Ok(Some(acknowledgment))
}

#[cfg(unix)]
fn validate_archive(dir: &Path) -> Result<()> {
    use std::os::unix::fs::MetadataExt;
    let path = dir.join(ARCHIVE);
    crate::validate_dir(&path)?;
    let m = fs::symlink_metadata(path).map_err(|_| Error::Unavailable)?;
    if m.mode() & 0o7777 != 0o755 {
        return Err(Error::Untrusted);
    }
    Ok(())
}

#[cfg(windows)]
fn validate_archive(dir: &Path) -> Result<()> {
    crate::windows::validate_recovery_archive(dir)
}

fn ensure_archive(dir: &Path) -> Result<PathBuf> {
    #[cfg(unix)]
    {
        use std::os::unix::fs::{DirBuilderExt, PermissionsExt};
        crate::validate_dir(dir)?;
        let path = dir.join(ARCHIVE);
        match fs::DirBuilder::new().mode(0o755).create(&path) {
            Ok(()) => fs::set_permissions(&path, fs::Permissions::from_mode(0o755))
                .map_err(|_| Error::Unavailable)?,
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => (),
            Err(_) => return Err(Error::Unavailable),
        }
    }
    #[cfg(windows)]
    crate::windows::recovery_archive(dir)?;
    validate_archive(dir)?;
    crate::sync_directory(dir)?;
    Ok(dir.join(ARCHIVE))
}

pub(crate) fn publish_once(dir: &Path, name: &str, bytes: &[u8]) -> Result<()> {
    if bytes.len() as u64 > MAX_JOURNAL {
        return Err(Error::Untrusted);
    }
    let temporary = format!("{name}.tmp-{}", Uuid::new_v4());
    let mut created = false;
    let result = (|| {
        let mut file = open(dir, &temporary, Kind::Private, true, true)?;
        created = true;
        file.write_all(bytes)
            .and_then(|_| file.sync_all())
            .map_err(|_| Error::Unavailable)?;
        drop(file);
        publish_no_replace(dir, &temporary, name)?;
        crate::sync_directory(dir)
    })();
    if result.is_err() && created {
        let _ = fs::remove_file(dir.join(&temporary));
    }
    result
}

#[cfg(target_os = "linux")]
fn publish_no_replace(dir: &Path, source: &str, destination: &str) -> Result<()> {
    use std::os::unix::ffi::OsStrExt;
    let source = std::ffi::CString::new(dir.join(source).as_os_str().as_bytes())
        .map_err(|_| Error::Untrusted)?;
    let destination = std::ffi::CString::new(dir.join(destination).as_os_str().as_bytes())
        .map_err(|_| Error::Untrusted)?;
    if unsafe {
        libc::renameat2(
            libc::AT_FDCWD,
            source.as_ptr(),
            libc::AT_FDCWD,
            destination.as_ptr(),
            libc::RENAME_NOREPLACE,
        )
    } != 0
    {
        return Err(Error::Unavailable);
    }
    Ok(())
}

#[cfg(windows)]
fn publish_no_replace(dir: &Path, source: &str, destination: &str) -> Result<()> {
    crate::windows::publish_recovery(dir, source, destination, false)
}

#[cfg(all(unix, not(target_os = "linux")))]
fn publish_no_replace(_dir: &Path, _source: &str, _destination: &str) -> Result<()> {
    // This operation is supported only on the approved Windows/Mint platforms.
    Err(Error::Unavailable)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn public_acknowledgment_is_strict_and_contains_no_private_binding() {
        let id = "9fe3858b-58da-4b96-b47d-ec2f1b867353";
        let acknowledgment = Acknowledgment {
            schema: 1,
            incident_id: id.into(),
            acknowledged_at: 123,
        };
        let value = serde_json::to_value(&acknowledgment).unwrap();
        assert_eq!(value.as_object().unwrap().len(), 3);
        assert!(value.get("binding").is_none());
        assert!(acknowledgment.valid());
        for text in [
            format!(r#"{{"schema":1,"incidentId":"{id}","acknowledgedAt":0}}"#),
            format!(r#"{{"schema":2,"incidentId":"{id}","acknowledgedAt":123}}"#),
            format!(r#"{{"schema":true,"incidentId":"{id}","acknowledgedAt":123}}"#),
            format!(r#"{{"schema":1,"incidentId":"{id}","acknowledgedAt":1.0}}"#),
            format!(r#"{{"schema":1,"incidentId":"{id}","acknowledgedAt":123,"binding":{{}}}}"#),
            format!(
                r#"{{"schema":1,"incidentId":"{id}","acknowledgedAt":123,"acknowledgedAt":123}}"#
            ),
        ] {
            assert!(!serde_json::from_str::<Acknowledgment>(&text).is_ok_and(|a| a.valid()));
        }
    }
}
