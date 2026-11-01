//! Per-account display suppression only. Never imported by mutation/admission.
//! Native fingerprints and bindings are not serializable IPC permits.
use crate::recovery_reports as files;
use serde::{Deserialize, Serialize};
use std::{
    collections::BTreeMap,
    fs,
    path::{Path, PathBuf},
    sync::Mutex,
};
type Result<T> = std::result::Result<T, String>;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Binding {
    pub source: String,
    pub id: String,
    pub fingerprint: String,
}
impl Binding {
    fn validate(&self) -> Result<()> {
        if !["machine", "user"].contains(&self.source.as_str())
            || !canonical(&self.id)
            || self.fingerprint.len() != 64
            || !self
                .fingerprint
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err(
                "History view is unavailable. Refresh history before deleting its view.".into(),
            );
        }
        Ok(())
    }
}
#[derive(Default)]
pub struct Views {
    bindings: Mutex<BTreeMap<String, Binding>>,
}
impl Views {
    pub fn bind(&self, binding: Binding) -> Result<String> {
        binding.validate()?;
        let mut bindings = self
            .bindings
            .lock()
            .map_err(|_| "History views are unavailable.")?;
        if let Some((token, _)) = bindings.iter().find(|(_, old)| **old == binding) {
            return Ok(token.clone());
        }
        if bindings.len() >= 512 {
            bindings.clear();
        } // Old views expire, never authorize anything.
        let token = uuid::Uuid::new_v4().to_string();
        bindings.insert(token.clone(), binding);
        Ok(token)
    }
    pub fn resolve(&self, token: &str) -> Result<Binding> {
        if !canonical(token) {
            return Err("Invalid history view. Refresh history.".into());
        }
        self.bindings
            .lock()
            .map_err(|_| "History views are unavailable.")?
            .get(token)
            .cloned()
            .ok_or_else(|| "History view expired. Refresh before deleting its view.".into())
    }
}
fn canonical(value: &str) -> bool {
    uuid::Uuid::parse_str(value).is_ok_and(|id| id.to_string() == value)
}
#[derive(Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
struct Marker {
    schema: u8,
    source: String,
    incident_id: String,
    fingerprint: String,
    deleted_at: u64,
}
pub struct Store {
    root: PathBuf,
}
impl Store {
    pub fn new(app_data: &Path) -> Self {
        Self {
            root: app_data.join("recovery-history-views"),
        }
    }
    fn directory(&self, binding: &Binding) -> Result<PathBuf> {
        binding.validate()?;
        Ok(self.root.join(&binding.source).join(&binding.id))
    }
    pub fn hidden(&self, binding: &Binding) -> Result<bool> {
        let directory = self.directory(binding)?;
        for path in [&self.root, &self.root.join(&binding.source), &directory] {
            match fs::symlink_metadata(path) {
                Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(false),
                Err(_) => return Err("History view state is unavailable.".into()),
                Ok(_) => files::existing_private_directory(path)?,
            }
        }
        let path = directory.join(format!("{}.json", binding.fingerprint));
        match fs::symlink_metadata(&path) {
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(false),
            Err(_) => return Err("History view state is unavailable.".into()),
            Ok(_) => (),
        }
        let record: Marker = serde_json::from_slice(&files::read(&path, 4096)?)
            .map_err(|_| "History view state is invalid.")?;
        if record.schema != 1
            || record.source != binding.source
            || record.incident_id != binding.id
            || record.fingerprint != binding.fingerprint
            || record.deleted_at == 0
        {
            return Err("History view state is invalid or changed.".into());
        }
        Ok(true)
    }
    pub fn hide(&self, binding: &Binding, now: u64) -> Result<()> {
        self.hide_at(binding, now, |_| Ok(()))
    }
    fn hide_at(
        &self,
        binding: &Binding,
        now: u64,
        mut after: impl FnMut(u8) -> Result<()>,
    ) -> Result<()> {
        let directory = self.directory(binding)?;
        if now == 0 {
            return Err("History deletion time is unavailable.".into());
        }
        if self.hidden(binding)? {
            return Ok(());
        }
        files::private_directory(&directory)?;
        let bytes = serde_json::to_vec(&Marker {
            schema: 1,
            source: binding.source.clone(),
            incident_id: binding.id.clone(),
            fingerprint: binding.fingerprint.clone(),
            deleted_at: now,
        })
        .map_err(|_| "History view could not be encoded.")?;
        let stage = directory.join(format!(".tmp-{}", uuid::Uuid::new_v4()));
        files::write(&stage, &bytes)?;
        after(0)?;
        let target = directory.join(format!("{}.json", binding.fingerprint));
        if fs::rename(&stage, &target).is_err() {
            if !self.hidden(binding)? {
                return Err(
                    "History view deletion could not be confirmed. Refresh history.".into(),
                );
            }
            // Only our exact newly created staging file is removed on a race.
            fs::remove_file(&stage)
                .map_err(|_| "History staging cleanup could not be confirmed.")?;
        }
        after(1)?;
        files::sync(&directory)?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn binding() -> Binding {
        Binding {
            source: "user".into(),
            id: uuid::Uuid::new_v4().to_string(),
            fingerprint: "a".repeat(64),
        }
    }
    struct Fixture(PathBuf);
    impl Fixture {
        fn new() -> Self {
            let path =
                std::env::temp_dir().join(format!("sde-history-view-ci-{}", uuid::Uuid::new_v4()));
            fs::create_dir(&path).unwrap();
            Self(path)
        }
    }
    impl Drop for Fixture {
        fn drop(&mut self) {
            fs::remove_dir_all(&self.0).unwrap();
        }
    }
    #[test]
    fn history_view_tokens_bind_source_identity_and_native_snapshot_not_frontend_input() {
        let views = Views::default();
        let one = binding();
        let token = views.bind(one.clone()).unwrap();
        assert_eq!(views.bind(one.clone()).unwrap(), token);
        assert_eq!(views.resolve(&token).unwrap(), one);
        let mut changed = one.clone();
        changed.fingerprint = "b".repeat(64);
        assert_ne!(views.bind(changed.clone()).unwrap(), token);
        assert_ne!(views.resolve(&token).unwrap(), changed);
        assert!(Views::default().resolve(&token).is_err());
        assert!(views.resolve("../escape").is_err());
    }
    #[test]
    fn history_view_deletion_persists_but_does_not_apply_to_new_evidence_or_other_sources() {
        let f = Fixture::new();
        let store = Store::new(&f.0);
        let one = binding();
        assert!(!store.hidden(&one).unwrap());
        assert!(!f.0.join("recovery-history-views").exists());
        let sentinel = f.0.join("operation-journal.json");
        fs::write(&sentinel, b"original evidence").unwrap();
        store.hide(&one, 100).unwrap();
        assert!(Store::new(&f.0).hidden(&one).unwrap());
        let mut newer = one.clone();
        newer.fingerprint = "b".repeat(64);
        assert!(!store.hidden(&newer).unwrap());
        newer = one.clone();
        newer.source = "machine".into();
        assert!(!store.hidden(&newer).unwrap());
        store.hide(&one, 101).unwrap();
        assert_eq!(fs::read(sentinel).unwrap(), b"original evidence");
    }
    #[test]
    fn history_view_staging_and_commit_failures_replay_without_touching_operational_state() {
        for phase in [0, 1] {
            let f = Fixture::new();
            let store = Store::new(&f.0);
            let one = binding();
            assert!(store
                .hide_at(&one, 100, |at| if at == phase {
                    Err("synthetic failure".into())
                } else {
                    Ok(())
                })
                .is_err());
            assert_eq!(store.hidden(&one).unwrap(), phase == 1);
            store.hide(&one, 101).unwrap();
            assert!(store.hidden(&one).unwrap());
        }
    }
    #[test]
    fn history_view_unsafe_paths_and_corrupt_markers_never_hide_an_incident() {
        let f = Fixture::new();
        let store = Store::new(&f.0);
        let mut one = binding();
        one.id = "../escape".into();
        assert!(store.hide(&one, 100).is_err());
        one = binding();
        store.hide(&one, 100).unwrap();
        let marker = store
            .directory(&one)
            .unwrap()
            .join(format!("{}.json", one.fingerprint));
        fs::write(&marker, b"corrupt").unwrap();
        assert!(store.hidden(&one).is_err());
        assert!(store.hide(&one, 101).is_err());
        assert_eq!(fs::read(marker).unwrap(), b"corrupt");
    }
}
