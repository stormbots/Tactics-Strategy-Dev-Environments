use serde::{Deserialize, Serialize};
use std::time::Duration;

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum Status {
    Pass,
    Blocking,
    Warning,
    Unavailable,
}

#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Check {
    pub name: String,
    pub status: Status,
    pub detail: String,
}
pub fn inspect(
    root: &std::path::Path,
    operation: crate::Operation,
) -> Result<Vec<Check>, String> {
    if !matches!(operation, crate::Operation::Install | crate::Operation::Update) {
        return Err("Preflight is available only for Install and Update.".into());
    }
    #[cfg(windows)]
    let mut cmd = crate::process::script(root, "chocolatey/tools/Test-SkyviewUpdatePreflight.ps1");
    #[cfg(not(windows))]
    let mut cmd = {
        let mut c = std::process::Command::new("/usr/bin/python3");
        c.arg(root.join("linux/lib/update_preflight.py"));
        c
    };
    #[cfg(windows)]
    cmd.args(["-Operation", operation.name()]);
    #[cfg(not(windows))]
    cmd.args(["--operation", operation.name()]);
    let bytes = crate::updates::output(cmd, b"", Duration::from_secs(35))?;
    let mut rows: Vec<Check> = serde_json::from_slice(&bytes)
        .map_err(|_| "Update preflight returned incomplete results. Check again.".to_string())?;
    if !["System disk", "User disk", "Package manager", "Restart"]
        .iter()
        .all(|name| rows.iter().any(|r| r.name == *name))
    {
        return Err("Preflight is missing required observations. Check again.".into());
    }
    if rows.len() > 24
        || !rows
            .iter()
            .all(|r| r.name.len() < 120 && r.detail.len() < 500)
    {
        return Err("Invalid preflight results. Check again.".into());
    }
    let (status, detail) = match sde_coordination::operation() {
        Ok(_lease) => (Status::Pass, "No conflicting operation or unresolved transaction was detected. The native backend acquires the operation gate again before changes.".to_string()),
        Err(error) => (Status::Blocking, format!("{} No changes have been started; ask a mentor about an interrupted or untrusted state.", error)),
    };
    rows.push(Check {
        name: "Operation coordination".into(),
        status,
        detail,
    });
    if !crate::platform().supported {
        rows.insert(
            0,
            Check {
                name: "Supported platform".into(),
                status: Status::Blocking,
                detail: format!(
                    "{} requires Windows 11 x64 or Linux Mint Cinnamon 22.x amd64.",
                    operation.name()
                ),
            },
        );
    }
    Ok(rows)
}
#[tauri::command]
pub async fn check_operation_preflight(
    app: tauri::AppHandle,
    state: tauri::State<'_, crate::updates::Checks>,
    operation: crate::Operation,
) -> Result<Vec<Check>, String> {
    let lease = crate::updates::enter(&state.preflight)?;
    let root = crate::backend(&app)?;
    tauri::async_runtime::spawn_blocking(move || {
        let _lease = lease;
        inspect(&root, operation)
    })
    .await
    .map_err(|_| "Preflight stopped. Check again.".to_string())?
}

/// Called independently by the GUI runner and installed privileged helper.
/// All results are logged before returning, including a stop before package launch.
pub fn before_operation(
    root: &std::path::Path,
    operation: crate::Operation,
    acknowledged_uncertainty: bool,
    mut emit: impl FnMut(String),
) -> bool {
    emit(format!(
        "SKYVIEW_EVENT|phase|preflight|Rechecking {} prerequisites",
        operation.name()
    ));
    match inspect(root, operation) {
        Ok(rows) if can_continue(&rows, acknowledged_uncertainty) => {
            for row in rows {
                emit(format!(
                    "SKYVIEW_EVENT|status|preflight|{} — {:?}: {}",
                    row.name, row.status, row.detail
                ));
            }
            true
        }
        Ok(_) => {
            emit(format!("SKYVIEW_EVENT|error|preflight|{} preflight changed or found a blocker. No package changes were started. Check again in the preview.", operation.name()));
            false
        }
        Err(_) if acknowledged_uncertainty => {
            emit(format!("SKYVIEW_EVENT|warning|preflight|{} preflight was unavailable during the final recheck. Continuing under this attempt's explicit acknowledgement; native package safeguards still apply.", operation.name()));
            true
        }
        Err(_) => {
            emit(format!("SKYVIEW_EVENT|error|preflight|{} preflight became unavailable. No package changes were started. Review and acknowledge the current result before continuing.", operation.name()));
            false
        }
    }
}

fn can_continue(rows: &[Check], acknowledged_uncertainty: bool) -> bool {
    !rows.iter().any(|row| row.status == Status::Blocking)
        && (acknowledged_uncertainty
            || !rows
                .iter()
                .any(|row| matches!(row.status, Status::Warning | Status::Unavailable)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_contract_uses_only_approved_wire_values() {
        for (status, json) in [
            (Status::Pass, "\"pass\""),
            (Status::Blocking, "\"blocking\""),
            (Status::Warning, "\"warning\""),
            (Status::Unavailable, "\"unavailable\""),
        ] {
            assert_eq!(serde_json::to_string(&status).unwrap(), json);
            assert_eq!(serde_json::from_str::<Status>(json).unwrap(), status);
        }
        assert!(serde_json::from_str::<Status>("\"success\"").is_err());
    }

    #[test]
    fn check_contract_rejects_unknown_or_incomplete_fields() {
        let valid = r#"{"name":"System disk","status":"pass","detail":"Enough space"}"#;
        assert!(serde_json::from_str::<Check>(valid).is_ok());
        assert!(serde_json::from_str::<Check>(
            r#"{"name":"System disk","status":"pass"}"#
        )
        .is_err());
        assert!(serde_json::from_str::<Check>(
            r#"{"name":"System disk","status":"pass","detail":"Enough","extra":true}"#
        )
        .is_err());
    }

    #[test]
    fn uncertainty_requires_acknowledgement_but_blockers_have_no_bypass() {
        let check = |status| Check {
            name: "Example".into(),
            status,
            detail: "Detail".into(),
        };
        assert!(can_continue(&[check(Status::Pass)], false));
        assert!(!can_continue(&[check(Status::Unavailable)], false));
        assert!(can_continue(&[check(Status::Unavailable)], true));
        assert!(!can_continue(&[check(Status::Blocking)], true));
    }
}
