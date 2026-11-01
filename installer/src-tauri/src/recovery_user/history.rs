//! Minimal account incident observations independent of report existence.
//! Generations remain local; ambiguous generations never become one consent.
use super::*;
use std::collections::BTreeSet;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Entry {
    pub incident_id: String,
    pub status: &'static str,
    pub context: Option<Context>,
    pub acknowledgment: Option<Decision>,
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
    pub unexpected_entries: bool,
}
pub(super) fn list(app_data: &Path, cursor: Option<&str>, limit: usize, now: u64) -> Result<Page> {
    if !(1..=100).contains(&limit) || now == 0 || cursor.is_some_and(|id| !canonical(id)) {
        return Err("Invalid incident history page.".into());
    }
    let root = app_data.join("recovery-state");
    match fs::symlink_metadata(&root) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(Page {
                entries: vec![],
                next_cursor: None,
                unexpected_entries: false,
            })
        }
        Err(_) => return Err("Account incident history is unavailable.".into()),
        Ok(_) => files::existing_private_directory(&root)?,
    }
    let mut ids = BTreeSet::new();
    let mut unexpected_entries = false;
    for entry in fs::read_dir(&root).map_err(|_| "Account incident history is unavailable.")? {
        let entry = entry.map_err(|_| "Account incident history is unavailable.")?;
        let name = entry.file_name().to_string_lossy().into_owned();
        if ["user-sessions", "user-operation.gate"].contains(&name.as_str()) {
            continue;
        }
        if !canonical(&name) {
            unexpected_entries = true;
            continue;
        }
        if cursor.is_none_or(|cursor| name.as_str() > cursor) {
            ids.insert(name);
            if ids.len() > limit + 1 {
                ids.pop_last();
            }
        }
    }
    let more = ids.len() > limit;
    let entries: Vec<_> = ids
        .into_iter()
        .take(limit)
        .map(|incident_id| {
            let mut entry = Entry {
                incident_id: incident_id.clone(),
                status: "unavailable",
                context: None,
                acknowledgment: None,
                continuation: "not_recorded",
                view_key: String::new(),
                view_token: None,
            };
            if let Ok((status, context, acknowledgment, key)) =
                inspect(&root.join(&incident_id), &incident_id, now)
            {
                entry.status = status;
                entry.context = context;
                entry.acknowledgment = acknowledgment;
                entry.view_key = key;
            }
            entry
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
        unexpected_entries,
    })
}
fn inspect(
    directory: &Path,
    id: &str,
    now: u64,
) -> Result<(&'static str, Option<Context>, Option<Decision>, String)> {
    files::existing_private_directory(directory)?;
    let generations = fs::read_dir(directory)
        .map_err(|_| "Retained generations are unavailable.")?
        .take(129)
        .collect::<std::io::Result<Vec<_>>>()
        .map_err(|_| "Retained generations are unavailable.")?;
    if generations.is_empty() {
        return Ok(("acknowledgment_unknown", None, None, String::new()));
    }
    if generations.len() > 128 {
        return Err("Retained generation lookup is unavailable.".into());
    }
    // A copied UUID is not a generation identity. Do not choose the first or
    // newest matching receipt/context and silently conflate earlier incidents.
    if generations.len() > 1 {
        return Ok(("ambiguous_generations", None, None, String::new()));
    }
    let generation = generations[0].file_name().to_string_lossy().into_owned();
    if generation.len() != 64
        || !generation
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return Err("Invalid retained generation.".into());
    }
    let path = generations[0].path();
    files::existing_private_directory(&path)?;
    let Some(original) = optional(&path.join("evidence.json"), 16 * 1024)? else {
        return Err("Retained evidence is unavailable.".into());
    };
    let context = recovery_context::preserved_context(&original, id, now)?;
    let mut key = Sha256::new();
    key.update(generation.as_bytes());
    key.update(&original);
    let Some(bytes) = optional(&path.join("acknowledged.json"), 4096)? else {
        return Ok((
            "acknowledgment_unknown",
            Some(context),
            None,
            format!("{:x}", key.finalize()),
        ));
    };
    let receipt: Receipt =
        serde_json::from_slice(&bytes).map_err(|_| "Retained decision is invalid.")?;
    key.update(&bytes);
    let Context::User { incident } = &context else {
        return Err("Invalid retained source.".into());
    };
    if receipt.schema != 1
        || receipt.generation != generation
        || receipt.evidence_sha256 != format!("{:x}", Sha256::digest(&original))
        || receipt.decision.incident_id != id
        || receipt.decision.acknowledged_at == 0
        || receipt.decision.acknowledged_at > now
        || receipt.decision.acknowledged_at < incident.observed_at
        || receipt
            .decision
            .report_id
            .as_ref()
            .is_some_and(|id| !canonical(id))
    {
        return Err("Retained decision is invalid or changed.".into());
    }
    Ok((
        "acknowledgment_observed",
        Some(context),
        Some(receipt.decision),
        format!("{:x}", key.finalize()),
    ))
}
