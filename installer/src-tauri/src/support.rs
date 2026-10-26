use serde::Serialize;
use std::{
    fs::{self, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
    process::{Command, Stdio},
    time::{SystemTime, UNIX_EPOCH},
};
use tauri::Manager;

const MAX_LOG_BYTES: u64 = 200 * 1024;
const MAX_REPORT_BYTES: usize = 512 * 1024;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Context {
    device_name: String,
    logs: Option<String>,
}

fn device_name() -> String {
    #[cfg(windows)]
    let candidate = std::env::var("COMPUTERNAME").ok();
    #[cfg(not(windows))]
    let candidate = fs::read_to_string("/etc/hostname").ok();
    candidate
        .map(|value| value.trim().to_string())
        .filter(|value| {
            !value.is_empty()
                && value.len() <= 255
                && !value.contains('\r')
                && !value.contains('\n')
        })
        .unwrap_or_else(|| "Unavailable".to_string())
}

fn newest_log(directory: &Path) -> Option<PathBuf> {
    let mut candidates = fs::read_dir(directory)
        .ok()?
        .take(128)
        .filter_map(Result::ok)
        .filter_map(|entry| {
            let path = entry.path();
            let metadata = fs::symlink_metadata(&path).ok()?;
            if !metadata.file_type().is_file() || metadata.len() > MAX_LOG_BYTES {
                return None;
            }
            Some((metadata.modified().ok()?, path))
        })
        .collect::<Vec<_>>();
    candidates.sort_by_key(|(modified, _)| *modified);
    candidates.pop().map(|(_, path)| path)
}

fn redact_home(app: &tauri::AppHandle, value: &str) -> String {
    let redacted = crate::protocol::redact(value);
    let Ok(home) = app.path().home_dir() else {
        return redacted;
    };
    redact_personal_path(&redacted, &home.to_string_lossy(), cfg!(windows))
}

fn redact_personal_path(value: &str, home: &str, case_insensitive: bool) -> String {
    if home.is_empty() {
        return value.to_string();
    }
    regex::RegexBuilder::new(&regex::escape(home))
        .case_insensitive(case_insensitive)
        .build()
        .map(|pattern| pattern.replace_all(value, "[HOME]").into_owned())
        .unwrap_or_else(|_| value.to_string())
}

pub fn context(app: &tauri::AppHandle, include_logs: bool) -> Result<Context, String> {
    let logs = if include_logs {
        let directory = app
            .path()
            .app_log_dir()
            .map_err(|_| "Logs are unavailable.")?;
        newest_log(&directory).and_then(|path| {
            let mut bytes = Vec::new();
            fs::File::open(path)
                .and_then(|file| file.take(MAX_LOG_BYTES + 1).read_to_end(&mut bytes))
                .ok()?;
            if bytes.len() as u64 > MAX_LOG_BYTES {
                return None;
            }
            Some(redact_home(app, &String::from_utf8_lossy(&bytes)))
        })
    } else {
        None
    };
    Ok(Context {
        device_name: device_name(),
        logs,
    })
}

fn choose_path(app: &tauri::AppHandle, filename: &str) -> Result<Option<PathBuf>, String> {
    #[cfg(windows)]
    let mut command = {
        let mut command = Command::new(
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        );
        command.args([
            "-NoProfile",
            "-NonInteractive",
            "-STA",
            "-Command",
            "Add-Type -AssemblyName System.Windows.Forms; $dialog=New-Object System.Windows.Forms.SaveFileDialog; $dialog.Title='Save Skyview SDE support report'; $dialog.Filter='HTML report (*.html)|*.html'; $dialog.DefaultExt='html'; $dialog.AddExtension=$true; $dialog.OverwritePrompt=$true; $dialog.FileName=$args[0]; if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { [Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false); [Console]::Write($dialog.FileName) }",
            filename,
        ]);
        command
    };
    #[cfg(not(windows))]
    let mut command = {
        let initial = app
            .path()
            .download_dir()
            .map_err(|_| "The Downloads folder is unavailable.".to_string())?
            .join(filename);
        let mut command = Command::new("/usr/bin/zenity");
        command.args([
            "--file-selection",
            "--save",
            "--confirm-overwrite",
            "--title=Save Skyview SDE support report",
            "--file-filter=HTML report | *.html",
            &format!("--filename={}", initial.display()),
        ]);
        command
    };
    let output = crate::process::hidden(&mut command)
        .stdin(Stdio::null())
        .output()
        .map_err(|_| "The save window could not be opened.".to_string())?;
    if !output.status.success() {
        return Ok(None);
    }
    let value = String::from_utf8(output.stdout)
        .map_err(|_| "The selected report path is invalid.".to_string())?;
    let value = value.trim();
    if value.is_empty() {
        return Ok(None);
    }
    let path = PathBuf::from(value);
    if !path.is_absolute()
        || !path
            .extension()
            .and_then(|value| value.to_str())
            .is_some_and(|value| value.eq_ignore_ascii_case("html"))
    {
        return Err("Choose a local file ending in .html.".into());
    }
    Ok(Some(path))
}

pub fn save(app: &tauri::AppHandle, html: &str) -> Result<Option<String>, String> {
    let lower = html.to_ascii_lowercase();
    if !valid_html(html, &lower) {
        return Err("The support report content is invalid.".into());
    }
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let filename = format!("skyview-sde-support-{timestamp}.html");
    let Some(path) = choose_path(app, &filename)? else {
        return Ok(None);
    };
    if fs::symlink_metadata(&path)
        .map(|metadata| metadata.file_type().is_symlink())
        .unwrap_or(false)
    {
        return Err("The selected report path cannot be a link.".into());
    }
    let mut file = OpenOptions::new()
        .create(true)
        .truncate(true)
        .write(true)
        .open(&path)
        .map_err(|_| "The support report could not be created.".to_string())?;
    file.write_all(html.as_bytes())
        .and_then(|_| file.sync_all())
        .map_err(|_| "The support report could not be saved.".to_string())?;
    Ok(Some(path.display().to_string()))
}

fn valid_html(html: &str, lower: &str) -> bool {
    !(html.is_empty()
        || html.len() > MAX_REPORT_BYTES
        || !html.starts_with("<!doctype html>")
        || [
            "<script",
            "javascript:",
            "<iframe",
            "<object",
            "<embed",
            "<link",
            "src=",
            "href=",
            "url(",
        ]
        .iter()
        .any(|needle| lower.contains(needle)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_active_or_oversized_content_before_writing() {
        let valid = "<!doctype html><html><body>https://example.com is text</body></html>";
        assert!(valid_html(valid, &valid.to_ascii_lowercase()));
        for active in ["<script", "<iframe", "href=", "url("] {
            let html = format!("<!doctype html><html>{active}</html>");
            assert!(!valid_html(&html, &html.to_ascii_lowercase()));
        }
        let oversized = format!("<!doctype html>{}", "x".repeat(MAX_REPORT_BYTES));
        assert!(!valid_html(&oversized, &oversized.to_ascii_lowercase()));
    }

    #[test]
    fn removes_personal_home_paths_from_report_logs() {
        let value = redact_personal_path(
            "Failure under C:\\Users\\Student Name\\Development",
            "c:\\users\\student name",
            true,
        );
        assert_eq!(value, "Failure under [HOME]\\Development");
    }
}
