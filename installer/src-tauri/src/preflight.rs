use serde::{Deserialize, Serialize};
use std::time::Duration;
#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Check {
    pub name: String,
    pub status: String,
    pub detail: String,
}
pub fn inspect(root: &std::path::Path) -> Result<Vec<Check>, String> {
    #[cfg(windows)]
    let cmd = crate::process::script(root, "chocolatey/tools/Test-SkyviewUpdatePreflight.ps1");
    #[cfg(not(windows))]
    let cmd = {
        let mut c = std::process::Command::new("/usr/bin/python3");
        c.arg(root.join("linux/lib/update_preflight.py"));
        c
    };
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
        || !rows.iter().all(|r| {
            ["pass", "blocking", "warning", "unavailable"].contains(&r.status.as_str())
                && r.name.len() < 120
                && r.detail.len() < 500
        })
    {
        return Err("Invalid preflight results. Check again.".into());
    }
    let (status, detail) = match sde_coordination::operation() {
        Ok(_lease) => ("pass", "No conflicting operation or unresolved transaction was detected. The native backend acquires the operation gate again before changes.".to_string()),
        Err(error) => ("blocking", format!("{} No changes have been started; ask a mentor about an interrupted or untrusted state.", error)),
    };
    rows.push(Check {
        name: "Operation coordination".into(),
        status: status.into(),
        detail,
    });
    if !crate::platform().supported {
        rows.insert(
            0,
            Check {
                name: "Supported platform".into(),
                status: "blocking".into(),
                detail: "Update requires Windows 11 x64 or Linux Mint Cinnamon 22.x amd64.".into(),
            },
        );
    }
    Ok(rows)
}
#[tauri::command]
pub async fn check_update_preflight(
    app: tauri::AppHandle,
    state: tauri::State<'_, crate::updates::Checks>,
) -> Result<Vec<Check>, String> {
    let lease = crate::updates::enter(&state.preflight)?;
    let root = crate::backend(&app)?;
    tauri::async_runtime::spawn_blocking(move || {
        let _lease = lease;
        inspect(&root)
    })
    .await
    .map_err(|_| "Preflight stopped. Check again.".to_string())?
}

/// Called independently by the GUI runner and installed privileged helper.
/// All results are logged before returning, including a stop before package launch.
pub fn before_update(root: &std::path::Path, mut emit: impl FnMut(String)) -> bool {
    emit("SKYVIEW_EVENT|phase|preflight|Rechecking update prerequisites".into());
    match inspect(root) {
        Ok(rows) if !rows.iter().any(|r| r.status == "blocking") => true,
        Ok(_) => {
            emit("SKYVIEW_EVENT|error|preflight|Update preflight found a blocker. No package changes were started. Check again in the preview.".into());
            false
        }
        Err(_) => {
            emit("SKYVIEW_EVENT|error|preflight|Update preflight could not be completed. No package changes were started. Check again in the preview.".into());
            false
        }
    }
}
