//! Per-user diagnostic artifacts only. Nothing here reads or changes machine
//! coordination, submits acknowledgment, elevates, or authorizes an operation.
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    fs::{self, File, OpenOptions},
    io::{Read, Write},
    path::{Path, PathBuf},
};

const MAX_JSON: u64 = 128 * 1024;
const MAX_HTML: u64 = 512 * 1024;
const FILES: [&str; 3] = ["summary.json", "report.html", "committed.json"];
type Result<T> = std::result::Result<T, String>;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Check {
    pub status: String,
    pub message: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Validation {
    pub collected_at: Option<u64>,
    pub checks: Vec<Check>,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Safety {
    pub observed_at: u64,
    pub trust: String,
    pub activity: String,
    pub package_health: String,
    pub activity_reason: String,
    pub decision: String,
}
#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Summary {
    pub schema: u8,
    pub report_id: String,
    pub incident_id: String,
    pub captured_at: u64,
    pub application_version: String,
    pub platform: String,
    pub device_name: String,
    pub safety: Safety,
    pub validation: Option<Validation>,
}
impl Summary {
    pub(crate) fn validate(&self) -> Result<()> {
        if self.schema != 1
            || !id(&self.report_id)
            || !id(&self.incident_id)
            || self.captured_at == 0
            || self.safety.observed_at == 0
            || self.safety.observed_at > self.captured_at
            || [&self.application_version, &self.platform, &self.device_name]
                .iter()
                .any(|s| s.len() > 512 || s.contains('\0'))
            || [
                &self.safety.trust,
                &self.safety.activity,
                &self.safety.package_health,
                &self.safety.activity_reason,
                &self.safety.decision,
            ]
            .iter()
            .any(|s| {
                s.is_empty()
                    || s.len() > 64
                    || !s.bytes().all(|c| c.is_ascii_lowercase() || c == b'_')
            })
        {
            return Err("Invalid recovery summary.".into());
        }
        if let Some(validation) = &self.validation {
            if validation
                .collected_at
                .is_some_and(|time| time == 0 || time > self.captured_at)
                || validation.checks.len() > 128
                || validation.checks.iter().any(|check| {
                    !["PASS", "WARNING", "FAIL", "INFO"].contains(&check.status.as_str())
                        || check.message.len() > 2048
                        || check.message.contains('\0')
                })
            {
                return Err("Invalid validation snapshot.".into());
            }
        }
        Ok(())
    }
}
#[derive(Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
struct Commit {
    schema: u8,
    json: String,
    html: String,
}
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Entry {
    pub report_id: String,
    pub incident_id: Option<String>,
    pub captured_at: Option<u64>,
    pub status: &'static str,
}
#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Page {
    pub entries: Vec<Entry>,
    pub next_cursor: Option<String>,
}

fn id(value: &str) -> bool {
    uuid::Uuid::parse_str(value).is_ok_and(|id| id.to_string() == value)
}
fn plain(path: &Path, directory: bool) -> Result<fs::Metadata> {
    let m = fs::symlink_metadata(path).map_err(|_| "Recovery report storage is unavailable.")?;
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        if m.file_attributes() & 0x400 != 0 {
            return Err("Linked report paths are not supported.".into());
        }
    }
    if m.file_type().is_symlink() || (directory && !m.is_dir()) || (!directory && !m.is_file()) {
        return Err("Linked or unexpected report paths are not supported.".into());
    }
    Ok(m)
}
fn ancestors(path: &Path) -> Result<()> {
    if !path.is_absolute() {
        return Err("Invalid report storage path.".into());
    }
    for parent in path.ancestors() {
        if parent.exists() || parent.is_symlink() {
            plain(parent, true)?;
        }
    }
    Ok(())
}
fn private_directory(path: &Path) -> Result<()> {
    ancestors(path)?;
    if !path.exists() {
        let mut builder = fs::DirBuilder::new();
        builder.recursive(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::DirBuilderExt;
            builder.mode(0o700);
        }
        builder
            .create(path)
            .map_err(|_| "Recovery report directory could not be created.")?;
    }
    let m = plain(path, true)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        if m.uid() != unsafe { libc::geteuid() } || m.mode() & 0o077 != 0 {
            return Err("Recovery report directory is not private to this account.".into());
        }
    }
    #[cfg(not(unix))]
    let _ = m;
    Ok(())
}
fn open(path: &Path, create: bool) -> Result<File> {
    let mut options = OpenOptions::new();
    if create {
        options.write(true).create_new(true);
    } else {
        options.read(true);
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options
            .mode(0o600)
            .custom_flags(libc::O_NOFOLLOW | libc::O_CLOEXEC);
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::OpenOptionsExt;
        options.custom_flags(0x00200000).share_mode(1);
    }
    let file = options
        .open(path)
        .map_err(|_| "Recovery report file could not be opened.")?;
    let m = file
        .metadata()
        .map_err(|_| "Recovery report metadata unavailable.")?;
    if !m.is_file() {
        return Err("Unexpected report file type.".into());
    }
    #[cfg(unix)]
    {
        use std::os::unix::fs::MetadataExt;
        if m.nlink() != 1 || m.uid() != unsafe { libc::geteuid() } || m.mode() & 0o077 != 0 {
            return Err("Unsafe report file permissions or links.".into());
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
            return Err("Unsafe report file links.".into());
        }
    }
    Ok(file)
}
fn read(path: &Path, max: u64) -> Result<Vec<u8>> {
    let mut bytes = Vec::new();
    open(path, false)?
        .take(max + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| "Recovery report read failed.")?;
    if bytes.len() as u64 > max {
        return Err("Recovery report exceeds its size limit.".into());
    }
    Ok(bytes)
}
fn write(path: &Path, bytes: &[u8]) -> Result<()> {
    let mut file = open(path, true)?;
    file.write_all(bytes)
        .and_then(|_| file.sync_all())
        .map_err(|_| "Recovery report save failed.".into())
}
fn sync(path: &Path) -> Result<()> {
    #[cfg(unix)]
    {
        File::open(path)
            .and_then(|f| f.sync_all())
            .map_err(|_| "Recovery report directory flush failed.")?;
    }
    #[cfg(not(unix))]
    let _ = path;
    Ok(())
}
fn digest(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}
fn escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#39;")
}
pub fn html(summary: &Summary) -> String {
    let mut body = String::from("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'none'; base-uri 'none'; form-action 'none'\"><title>SDE recovery summary</title></head><body><h1>SDE recovery summary</h1><p>This local summary may contain identifying information. Sharing is your choice; SDE does not upload it.</p><p>Captured before acknowledgment submission. This report is not an execution permit and does not prove the interrupted operation completed. No detailed logs or private journal bytes are included.</p>");
    body.push_str("<p>Original private journal, operation stage and completion evidence were not collected. Read-only findings are best-effort observations, not privileged verification.</p>");
    for (label, value) in [
        ("Report", summary.report_id.clone()),
        ("Incident", summary.incident_id.clone()),
        (
            "Captured at (Unix seconds)",
            summary.captured_at.to_string(),
        ),
        ("Device", summary.device_name.clone()),
        ("Platform", summary.platform.clone()),
        ("SDE version", summary.application_version.clone()),
        (
            "Safety observed at (Unix seconds)",
            summary.safety.observed_at.to_string(),
        ),
        ("Trust", summary.safety.trust.clone()),
        ("Activity", summary.safety.activity.clone()),
        ("Activity reason", summary.safety.activity_reason.clone()),
        ("Package health", summary.safety.package_health.clone()),
        ("Decision", summary.safety.decision.clone()),
    ] {
        body.push_str(&format!("<p>{}: {}</p>", label, escape(&value)));
    }
    body.push_str("<h2>Available Validation</h2>");
    if let Some(validation) = &summary.validation {
        body.push_str(&format!(
            "<p>Actual collection time: {}</p>",
            validation
                .collected_at
                .map(|v| v.to_string())
                .unwrap_or_else(|| "Unavailable; not inferred from report capture time".into())
        ));
        for check in &validation.checks {
            body.push_str(&format!(
                "<p>{}: {}</p>",
                escape(&check.status),
                escape(&check.message)
            ));
        }
    } else {
        body.push_str(
            "<p>No Validation snapshot was supplied. No check was run to create this report.</p>",
        );
    }
    body.push_str("</body></html>");
    body
}

pub struct Store {
    directory: PathBuf,
}
impl Store {
    /// The application supplies its fixed per-user directory, never an IPC path.
    pub fn new(directory: PathBuf) -> Result<Self> {
        private_directory(&directory)?;
        Ok(Self { directory })
    }
    fn bundle(&self, report_id: &str) -> Result<PathBuf> {
        if !id(report_id) {
            return Err("Invalid report identifier.".into());
        }
        private_directory(&self.directory)?;
        let path = self.directory.join(report_id);
        plain(&path, true)?;
        Ok(path)
    }
    pub fn save(&self, summary: &Summary) -> Result<String> {
        self.save_at(summary, |_| Ok(()))
    }
    fn save_at(
        &self,
        summary: &Summary,
        mut checkpoint: impl FnMut(u8) -> Result<()>,
    ) -> Result<String> {
        summary.validate()?;
        let json = serde_json::to_vec(summary).map_err(|_| "Report encoding failed.")?;
        let html = html(summary).into_bytes();
        if json.len() as u64 > MAX_JSON || html.len() as u64 > MAX_HTML {
            return Err("Report exceeds its size limit.".into());
        }
        private_directory(&self.directory)?;
        let directory = self.directory.join(&summary.report_id);
        let builder = fs::DirBuilder::new();
        #[cfg(unix)]
        let builder = {
            use std::os::unix::fs::DirBuilderExt;
            let mut builder = builder;
            builder.mode(0o700);
            builder
        };
        builder
            .create(&directory)
            .map_err(|_| "Report identifier already exists or storage is unavailable.")?;
        write(&directory.join(FILES[0]), &json)?;
        checkpoint(1)?;
        write(&directory.join(FILES[1]), &html)?;
        checkpoint(2)?;
        let marker = serde_json::to_vec(&Commit {
            schema: 1,
            json: digest(&json),
            html: digest(&html),
        })
        .map_err(|_| "Report commit encoding failed.")?;
        // Commit marker is last: an incomplete bundle is never reported saved.
        sync(&directory)?;
        write(&directory.join(FILES[2]), &marker)?;
        sync(&directory)?;
        sync(&self.directory)?;
        Ok(summary.report_id.clone())
    }
    pub fn load(&self, report_id: &str) -> Result<Summary> {
        let directory = self.bundle(report_id)?;
        let marker: Commit = serde_json::from_slice(&read(&directory.join(FILES[2]), 1024)?)
            .map_err(|_| "Report is incomplete or unreadable.")?;
        let json = read(&directory.join(FILES[0]), MAX_JSON)?;
        let html = read(&directory.join(FILES[1]), MAX_HTML)?;
        if marker.schema != 1 || marker.json != digest(&json) || marker.html != digest(&html) {
            return Err("Report is incomplete or changed.".into());
        }
        let summary: Summary =
            serde_json::from_slice(&json).map_err(|_| "Report summary is invalid.")?;
        summary.validate()?;
        if summary.report_id != report_id {
            return Err("Report identity changed.".into());
        }
        Ok(summary) // Render fresh escaped HTML, never trust stored active content.
    }
    pub fn list(&self, cursor: Option<&str>, limit: usize) -> Result<Page> {
        if !(1..=100).contains(&limit) || cursor.is_some_and(|v| !id(v)) {
            return Err("Invalid history page.".into());
        }
        private_directory(&self.directory)?;
        let mut ids = std::collections::BTreeSet::new();
        for entry in fs::read_dir(&self.directory).map_err(|_| "Report history unavailable.")? {
            let name = entry
                .map_err(|_| "Report history unavailable.")?
                .file_name()
                .to_string_lossy()
                .into_owned();
            if id(&name) && cursor.is_none_or(|cursor| name.as_str() > cursor) {
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
            .map(|report_id| match self.load(&report_id) {
                Ok(summary) => Entry {
                    report_id,
                    incident_id: Some(summary.incident_id),
                    captured_at: Some(summary.captured_at),
                    status: "saved",
                },
                Err(_) => Entry {
                    report_id,
                    incident_id: None,
                    captured_at: None,
                    status: "incomplete_or_unreadable",
                },
            })
            .collect();
        let next_cursor = if more {
            entries.last().map(|entry| entry.report_id.clone())
        } else {
            None
        };
        Ok(Page {
            entries,
            next_cursor,
        })
    }
    pub fn delete(&self, report_id: &str) -> Result<()> {
        let directory = self.bundle(report_id)?;
        for entry in fs::read_dir(&directory).map_err(|_| "Report deletion unavailable.")? {
            let entry = entry.map_err(|_| "Report deletion unavailable.")?;
            if !FILES.contains(&entry.file_name().to_string_lossy().as_ref()) {
                return Err("Unexpected report contents; nothing was deleted.".into());
            }
            open(&entry.path(), false)?;
        }
        // No recursion, path supplied by a client, machine state or history purge.
        for name in [FILES[2], FILES[1], FILES[0]] {
            match fs::remove_file(directory.join(name)) {
                Ok(()) => (),
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => (),
                Err(_) => return Err("Report deletion incomplete; retry explicitly.".into()),
            }
        }
        fs::remove_dir(directory).map_err(|_| "Report directory could not be removed.")?;
        sync(&self.directory)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    struct Fixture {
        root: PathBuf,
        store: Store,
    }
    impl Fixture {
        fn new() -> Self {
            let root = std::env::temp_dir().join(format!("sde-report-ci-{}", uuid::Uuid::new_v4()));
            let store = Store::new(root.join("reports")).unwrap();
            Self { root, store }
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.root).unwrap();
        }
    }
    fn summary() -> Summary {
        Summary {
            schema: 1,
            report_id: uuid::Uuid::new_v4().to_string(),
            incident_id: uuid::Uuid::new_v4().to_string(),
            captured_at: 100,
            application_version: "1.2.19".into(),
            platform: "CI".into(),
            device_name: "TEST".into(),
            safety: Safety {
                observed_at: 99,
                trust: "unknown".into(),
                activity: "unknown".into(),
                package_health: "unknown".into(),
                activity_reason: "native_inspection_unavailable".into(),
                decision: "block_trust_unknown".into(),
            },
            validation: Some(Validation {
                collected_at: Some(50),
                checks: vec![Check {
                    status: "FAIL".into(),
                    message: "<script>not executable</script>".into(),
                }],
            }),
        }
    }
    #[test]
    fn recovery_reports_committed_summary_retains_times_and_renders_passive_content() {
        let f = Fixture::new();
        let s = summary();
        f.store.save(&s).unwrap();
        let loaded = f.store.load(&s.report_id).unwrap();
        assert_eq!(loaded.validation.as_ref().unwrap().collected_at, Some(50));
        assert_eq!(loaded.captured_at, 100);
        let html = html(&loaded);
        assert!(html.contains("&lt;script&gt;") && !html.contains("<script>"));
        assert!(
            html.contains("default-src 'none'") && html.contains("Captured before acknowledgment")
        );
        assert_eq!(f.store.list(None, 50).unwrap().entries[0].status, "saved");
        assert!(f.store.save(&s).is_err(), "Never overwrite a report ID");
    }
    #[test]
    fn recovery_reports_partial_publications_are_retained_but_never_reported_saved() {
        for stage in [1, 2] {
            let f = Fixture::new();
            let s = summary();
            assert!(f
                .store
                .save_at(&s, |reached| if reached == stage {
                    Err("injected disk failure".into())
                } else {
                    Ok(())
                })
                .is_err());
            assert!(f.store.directory.join(&s.report_id).exists());
            assert!(f.store.load(&s.report_id).is_err());
            assert_eq!(
                f.store.list(None, 1).unwrap().entries[0].status,
                "incomplete_or_unreadable"
            );
            f.store.delete(&s.report_id).unwrap();
        }
    }
    #[test]
    fn recovery_reports_delete_only_selected_user_artifacts_never_machine_or_other_history() {
        let f = Fixture::new();
        let a = summary();
        let b = summary();
        let evidence = f.root.join("transaction.json");
        fs::write(&evidence, b"original protected-evidence stand-in").unwrap();
        f.store.save(&a).unwrap();
        f.store.save(&b).unwrap();
        f.store.delete(&a.report_id).unwrap();
        assert!(f.store.load(&b.report_id).is_ok());
        assert_eq!(
            fs::read(&evidence).unwrap(),
            b"original protected-evidence stand-in"
        );
        for invalid in [
            "../transaction.json",
            "..",
            "/",
            "C:\\ProgramData",
            "not-an-id",
        ] {
            assert!(f.store.delete(invalid).is_err());
            assert!(f.store.load(invalid).is_err());
        }
        let unexpected = f.store.directory.join(&b.report_id).join("keep-me");
        fs::write(&unexpected, b"unexpected").unwrap();
        assert!(f.store.delete(&b.report_id).is_err());
        assert!(f.store.load(&b.report_id).is_ok());
    }
    #[test]
    fn recovery_reports_corruption_and_oversized_records_fail_closed() {
        let f = Fixture::new();
        let s = summary();
        f.store.save(&s).unwrap();
        fs::write(f.store.directory.join(&s.report_id).join(FILES[0]), b"{}").unwrap();
        assert!(f.store.load(&s.report_id).is_err());
        let mut bad = summary();
        bad.validation.as_mut().unwrap().collected_at = Some(101);
        assert!(f.store.save(&bad).is_err());
        let mut extra = serde_json::to_value(summary()).unwrap();
        extra["transactionToken"] = serde_json::json!("must-not-be-a-report-field");
        assert!(serde_json::from_value::<Summary>(extra).is_err());
        bad.validation.as_mut().unwrap().collected_at = None;
        bad.validation.as_mut().unwrap().checks[0].message = "x".repeat(2049);
        assert!(f.store.save(&bad).is_err());
    }
    #[test]
    fn recovery_reports_history_pages_do_not_purge_or_silently_truncate() {
        let f = Fixture::new();
        for _ in 0..5 {
            f.store.save(&summary()).unwrap();
        }
        let mut cursor = None;
        let mut count = 0;
        loop {
            let page = f.store.list(cursor.as_deref(), 2).unwrap();
            count += page.entries.len();
            cursor = page.next_cursor;
            if cursor.is_none() {
                break;
            }
        }
        assert_eq!(count, 5);
        assert_eq!(fs::read_dir(&f.store.directory).unwrap().count(), 5);
        assert!(f.store.list(None, 0).is_err());
        assert!(f.store.list(Some("../"), 1).is_err());
    }
    #[test]
    fn recovery_reports_reject_hardlinked_inputs_without_deleting_the_target() {
        let f = Fixture::new();
        let s = summary();
        f.store.save(&s).unwrap();
        let target = f.root.join("untouched");
        fs::write(&target, b"untouched").unwrap();
        let summary_path = f.store.directory.join(&s.report_id).join(FILES[0]);
        fs::remove_file(&summary_path).unwrap();
        fs::hard_link(&target, &summary_path).unwrap();
        assert!(f.store.load(&s.report_id).is_err());
        assert!(f.store.delete(&s.report_id).is_err());
        assert_eq!(fs::read(target).unwrap(), b"untouched");
    }
    #[cfg(unix)]
    #[test]
    fn recovery_reports_reject_links_and_overbroad_user_storage() {
        use std::os::unix::fs::{symlink, PermissionsExt};
        let f = Fixture::new();
        let s = summary();
        f.store.save(&s).unwrap();
        let directory = f.store.directory.join(&s.report_id);
        let target = f.root.join("untouched");
        fs::write(&target, b"untouched").unwrap();
        fs::remove_file(directory.join(FILES[0])).unwrap();
        symlink(&target, directory.join(FILES[0])).unwrap();
        assert!(f.store.load(&s.report_id).is_err());
        assert!(f.store.delete(&s.report_id).is_err());
        assert_eq!(fs::read(&target).unwrap(), b"untouched");
        fs::set_permissions(&f.store.directory, fs::Permissions::from_mode(0o755)).unwrap();
        assert!(f.store.list(None, 1).is_err());
    }
}
