//! Protected provenance captured once for an incident, never a clock heuristic.
use super::*;

const CONTEXT: &str = "recovery-context.json";

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Context {
    schema: u8,
    incident_id: String,
    boot_key: Option<String>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RestartEvidence {
    SameSession,
    Confirmed,
    Unavailable,
}

pub(crate) fn prepare_context(dir: &Path, incident: &Incident) -> Result<()> {
    let existing = context(dir)?;
    if existing
        .as_ref()
        .is_some_and(|old| old.incident_id == incident.incident_id && old.boot_key.is_some())
    {
        return Ok(()); // Do not replace old provenance when SDE is opened after restart.
    }
    let new = Context {
        schema: 1,
        incident_id: incident.incident_id.clone(),
        boot_key: crate::inspection::boot_key(),
    };
    persist(
        dir,
        CONTEXT,
        Kind::Public,
        &serde_json::to_vec(&new).map_err(|_| Error::Unavailable)?,
    )
}

fn context(dir: &Path) -> Result<Option<Context>> {
    let Some(bytes) = read_optional(dir, CONTEXT, Kind::Public, MAX_RECORD)? else {
        return Ok(None);
    };
    let context: Context = serde_json::from_slice(&bytes).map_err(|_| Error::Untrusted)?;
    if !(Incident {
        schema: context.schema,
        incident_id: context.incident_id.clone(),
    })
    .valid()
        || context
            .boot_key
            .as_ref()
            .is_some_and(|key| !crate::inspection::valid_boot_key(key))
    {
        return Err(Error::Untrusted);
    }
    Ok(Some(context))
}

pub(crate) fn evidence_at(dir: &Path, current: Option<&str>) -> Result<RestartEvidence> {
    let Some(public) = read_optional(dir, PUBLIC, Kind::Public, MAX_RECORD)? else {
        return Ok(RestartEvidence::Unavailable);
    };
    let incident = Incident::parse(&public)?;
    let Some(context) = context(dir)? else {
        return Ok(RestartEvidence::Unavailable);
    };
    if context.incident_id != incident.incident_id {
        return Ok(RestartEvidence::Unavailable);
    }
    Ok(compare(context.boot_key.as_deref(), current))
}

pub(crate) fn compare(old: Option<&str>, current: Option<&str>) -> RestartEvidence {
    let (Some(old), Some(current)) = (old, current) else {
        return RestartEvidence::Unavailable;
    };
    if !crate::inspection::valid_boot_key(old) || !crate::inspection::valid_boot_key(current) {
        return RestartEvidence::Unavailable;
    }
    if old == current {
        return RestartEvidence::SameSession;
    }
    if old.starts_with("linux:") && current.starts_with("linux:") {
        return RestartEvidence::Confirmed;
    }
    if let (Some(old), Some(current)) = (
        old.strip_prefix("windows-session-start:"),
        current.strip_prefix("windows-session-start:"),
    ) {
        let old: Vec<_> = old.split(':').collect();
        let current: Vec<_> = current.split(':').collect();
        // Both the primary boot-lifetime process AND the OS-start record must
        // change. A log reset/replay or a changed time alone is never enough.
        if old[..2] != current[..2] && old[2..] != current[2..] {
            return RestartEvidence::Confirmed;
        }
    }
    RestartEvidence::Unavailable
}

#[cfg(test)]
pub(crate) fn set_test_context(dir: &Path, incident_id: &str, boot_key: Option<String>) {
    let value = Context {
        schema: 1,
        incident_id: incident_id.into(),
        boot_key,
    };
    persist(
        dir,
        CONTEXT,
        Kind::Public,
        &serde_json::to_vec(&value).unwrap(),
    )
    .unwrap();
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn windows_restart_requires_both_independent_signals_and_never_missing_data() {
        let old = Some("windows-session-start:40:100:12:200");
        assert_eq!(compare(old, old), RestartEvidence::SameSession);
        assert_eq!(
            compare(old, Some("windows-session-start:41:101:12:200")),
            RestartEvidence::Unavailable
        );
        assert_eq!(
            compare(old, Some("windows-session-start:40:100:13:201")),
            RestartEvidence::Unavailable
        );
        assert_eq!(
            compare(old, Some("windows-session-start:41:101:13:201")),
            RestartEvidence::Confirmed
        );
        assert_eq!(compare(old, None), RestartEvidence::Unavailable);
        assert_eq!(compare(None, old), RestartEvidence::Unavailable);
    }
}
