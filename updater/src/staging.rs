//! Maintenance entry point. A successful result means authenticated and staged,
//! never installed. Paths, repository, key and native identity are not configurable.
use crate::{
    discovery::{self, Candidate, Failure, GitHub, Result, Transport},
    host, AuthenticatedManifest, MAX_METADATA,
};
use serde::Serialize;
use std::{
    fs::File,
    io::Write,
    path::{Path, PathBuf},
    time::{SystemTime, UNIX_EPOCH},
};
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Report {
    pub status: Status,
    pub checked_at: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub candidate: Option<Candidate>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failure: Option<Failure>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub transaction: Option<String>,
}
#[derive(Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum Status {
    Current,
    Available,
    Staged,
    Unavailable,
}
impl Report {
    fn new(
        status: Status,
        candidate: Option<Candidate>,
        failure: Option<Failure>,
        transaction: Option<String>,
    ) -> Self {
        Self {
            status,
            checked_at: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|v| v.as_secs())
                .unwrap_or(0),
            candidate,
            failure,
            transaction,
        }
    }
}
/// Native maintenance check/stage. Check mode fetches listings only.
pub fn run(download: bool) -> Report {
    let result = (|| {
        let installed = host::installed()?;
        let mut github = GitHub::new()?;
        let Some(candidate) =
            discovery::discover_with(&mut github, &installed.version, installed.platform)?
        else {
            return Ok(Report::new(Status::Current, None, None, None));
        };
        if !download {
            return Ok(Report::new(Status::Available, Some(candidate), None, None));
        }
        let root = host::store()?;
        let staged = stage_with(&mut github, &root, &candidate, |bytes, signed, tag| {
            crate::authenticate(bytes, signed, tag).map_err(|_| Failure::Untrusted)
        })?;
        Ok(Report::new(
            Status::Staged,
            Some(candidate),
            None,
            Some(staged.id),
        ))
    })();
    result.unwrap_or_else(|failure| Report::new(Status::Unavailable, None, Some(failure), None))
}
pub(crate) struct Staged {
    pub(crate) id: String,
}
struct Transaction {
    path: PathBuf,
    names: Vec<&'static str>,
    keep: bool,
}
impl Transaction {
    fn new(root: &Path) -> Result<Self> {
        let path = root.join(uuid::Uuid::new_v4().to_string());
        host::create_private(&path)?;
        Ok(Self {
            path,
            names: Vec::new(),
            keep: false,
        })
    }
    fn file(&mut self, name: &'static str) -> Result<File> {
        self.names.push(name); // Include a file created before a post-open ACL check fails.
        host::exclusive(&self.path.join(name))
    }
    fn cleanup(&mut self) -> Result<()> {
        // This private transaction has only known, exclusive filenames. Never recurse
        // through attacker-supplied paths or remove any other/staged transaction.
        for name in self.names.drain(..).rev() {
            match std::fs::remove_file(self.path.join(name)) {
                Ok(()) => {}
                Err(e) if e.kind() == std::io::ErrorKind::NotFound => {}
                Err(_) => return Err(Failure::Cleanup),
            }
        }
        std::fs::remove_dir(&self.path).map_err(|_| Failure::Cleanup)?;
        self.keep = true;
        Ok(())
    }
}
impl Drop for Transaction {
    fn drop(&mut self) {
        if !self.keep {
            let _ = self.cleanup();
        }
    }
}
pub(crate) fn stage_with(
    transport: &mut impl Transport,
    root: &Path,
    candidate: &Candidate,
    authenticate: impl FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
) -> Result<Staged> {
    let mut transaction = Transaction::new(root)?;
    let result = (|| {
        let metadata_name = "sde-update.json";
        let signature_name = "sde-update.json.minisig";
        let mut metadata = transaction.file(metadata_name)?;
        transport.get(
            &discovery::asset_url(&candidate.tag, metadata_name),
            MAX_METADATA,
            &mut metadata,
        )?;
        metadata.sync_all().map_err(|_| Failure::Staging)?;
        drop(metadata);
        let mut signature = transaction.file(signature_name)?;
        transport.get(
            &discovery::asset_url(&candidate.tag, signature_name),
            8192,
            &mut signature,
        )?;
        signature.sync_all().map_err(|_| Failure::Staging)?;
        drop(signature);
        let bytes = crate::read_bounded(&transaction.path.join(metadata_name), MAX_METADATA)
            .map_err(|_| Failure::Staging)?;
        let signed = String::from_utf8(
            crate::read_bounded(&transaction.path.join(signature_name), 8192)
                .map_err(|_| Failure::Staging)?,
        )
        .map_err(|_| Failure::Untrusted)?;
        let manifest = authenticate(&bytes, &signed, &candidate.tag)?;
        let (platform, filename) = crate::PLATFORMS
            .iter()
            .find(|(p, n)| *p == candidate.platform && *n == candidate.installer)
            .ok_or(Failure::Unsupported)?;
        let expected = manifest
            .metadata()
            .platforms
            .get(*platform)
            .ok_or(Failure::Unsupported)?;
        if expected.size != candidate.installer_size
            || manifest.metadata().version != candidate.version
        {
            return Err(Failure::Untrusted);
        }
        let mut installer = transaction.file(filename)?;
        transport.get(
            &discovery::asset_url(&candidate.tag, filename),
            expected.size,
            &mut installer,
        )?;
        installer.sync_all().map_err(|_| Failure::Staging)?;
        drop(installer);
        host::validate(&transaction.path)?;
        crate::verify_installer(&manifest, platform, &transaction.path.join(filename))
            .map_err(|_| Failure::Untrusted)?;
        // Marker is written last; consumers must still repeat trust checks and inspect
        // current installed identity before execution (#39/#40). Marker alone is no authority.
        let id = transaction
            .path
            .file_name()
            .and_then(|s| s.to_str())
            .ok_or(Failure::Staging)?
            .to_owned();
        let receipt = serde_json::json!({"schemaVersion":1,"transaction":id,"releaseTag":candidate.tag,"version":candidate.version,"platform":platform,"installer":filename,"verifiedAt":SystemTime::now().duration_since(UNIX_EPOCH).map_err(|_|Failure::Staging)?.as_secs()});
        let mut marker = transaction.file("verified.json")?;
        marker
            .write_all(&serde_json::to_vec(&receipt).map_err(|_| Failure::Staging)?)
            .map_err(|_| Failure::Staging)?;
        marker.sync_all().map_err(|_| Failure::Staging)?;
        drop(marker);
        #[cfg(target_os = "linux")]
        File::open(&transaction.path)
            .and_then(|f| f.sync_all())
            .map_err(|_| Failure::Staging)?;
        transaction.keep = true;
        Ok(Staged { id })
    })();
    if result.is_err() {
        transaction.cleanup()?;
    }
    result
}
#[cfg(test)]
mod tests {
    use super::*;
    use crate::discovery::Sink;
    use minisign::KeyPair;
    use std::{collections::VecDeque, io::Cursor};
    struct Downloads(VecDeque<Result<Vec<u8>>>);
    impl Transport for Downloads {
        fn get(&mut self, _: &str, max: u64, out: &mut dyn Sink) -> Result<()> {
            let bytes = self.0.pop_front().unwrap()?;
            if bytes.len() as u64 > max {
                return Err(Failure::Malformed);
            }
            out.write_all(&bytes).unwrap();
            Ok(())
        }
    }
    // Root is private test input only. Neither CLI nor public maintenance API accepts it.
    fn fixture() -> (tempfile::TempDir, Candidate, KeyPair, Vec<u8>, Vec<u8>) {
        let dir = tempfile::tempdir().unwrap();
        for (_, name) in crate::PLATFORMS {
            std::fs::write(dir.path().join(name), b"fixture installer").unwrap();
        }
        let bytes = crate::create_manifest(dir.path(), "v1.2.2").unwrap();
        let keys = KeyPair::generate_unencrypted_keypair().unwrap();
        let signature = minisign::sign(
            Some(&keys.pk),
            &keys.sk,
            Cursor::new(&bytes),
            Some("test-only"),
            None,
        )
        .unwrap()
        .to_string()
        .into_bytes();
        let candidate = Candidate {
            tag: "v1.2.2".into(),
            version: "1.2.2".into(),
            platform: crate::PLATFORMS[0].0.into(),
            installer: crate::PLATFORMS[0].1.into(),
            installer_size: 17,
        };
        (dir, candidate, keys, bytes, signature)
    }
    fn test_root(dir: &Path) -> PathBuf {
        let root = dir.join("staging");
        #[cfg(target_os = "linux")]
        {
            // Security checks deliberately require root, including in CI. Ordinary
            // developer runs skip the root-only stage tests, never bypass validation.
            host::create_private(&root).unwrap();
        }
        #[cfg(windows)]
        host::create_private(&root).unwrap();
        root
    }
    fn privileged() -> bool {
        #[cfg(target_os = "linux")]
        {
            let root = unsafe { libc::geteuid() == 0 };
            assert!(
                root || std::env::var_os("SDE_REQUIRE_PROTECTED_STAGING").is_none(),
                "Protected staging tests require root"
            );
            root
        }
        #[cfg(windows)]
        {
            true
        }
    }
    #[test]
    fn authenticated_stage_and_failed_download_cleanup() {
        if !privileged() {
            return;
        }
        let (dir, candidate, keys, metadata, signed) = fixture();
        let root = test_root(dir.path());
        let stage = |downloads: &mut Downloads| {
            stage_with(downloads, &root, &candidate, |b, s, t| {
                crate::authenticate_with_key(b, s, t, &keys.pk).map_err(|_| Failure::Untrusted)
            })
        };
        for payload in [
            Err(Failure::Offline),
            Ok(b"tamperd installer".to_vec()),
            Ok(b"short".to_vec()),
        ] {
            let mut downloads = Downloads(VecDeque::from([
                Ok(metadata.clone()),
                Ok(signed.clone()),
                payload,
            ]));
            assert!(stage(&mut downloads).is_err());
            assert_eq!(std::fs::read_dir(&root).unwrap().count(), 0);
        }
        let mut changed = metadata.clone();
        changed.push(b' ');
        let mut downloads = Downloads(VecDeque::from([Ok(changed), Ok(signed.clone())]));
        assert!(stage(&mut downloads).is_err());
        assert_eq!(std::fs::read_dir(&root).unwrap().count(), 0);
        let mut downloads = Downloads(VecDeque::from([
            Ok(metadata),
            Ok(signed),
            Ok(b"fixture installer".to_vec()),
        ]));
        let staged = stage(&mut downloads).unwrap();
        let staged = root.join(staged.id);
        assert!(staged.join("verified.json").is_file());
        assert_eq!(
            std::fs::read(staged.join(&candidate.installer)).unwrap(),
            b"fixture installer"
        );
        host::validate(&staged).unwrap();
    }
    #[test]
    fn pinned_key_does_not_accept_test_signature_or_leave_files() {
        if !privileged() {
            return;
        }
        let (dir, candidate, _, metadata, signed) = fixture();
        let root = test_root(dir.path());
        let mut downloads = Downloads(VecDeque::from([Ok(metadata), Ok(signed)]));
        assert!(stage_with(&mut downloads, &root, &candidate, |b, s, t| {
            crate::authenticate(b, s, t).map_err(|_| Failure::Untrusted)
        })
        .is_err());
        assert_eq!(std::fs::read_dir(&root).unwrap().count(), 0);
    }
}
