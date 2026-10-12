//! Test-only transport with official-shaped release URLs and ephemeral signing
//! keys. No endpoint/key override is compiled into the production worker.
use crate::{
    discovery::{self, Candidate, Failure, Sink, Transport},
    host, staging,
};
use minisign::KeyPair;
use std::{collections::HashMap, io::Cursor, path::Path};

pub(crate) struct Fixture {
    pub key: minisign::PublicKey,
    pub releases: serde_json::Value,
    pub assets: HashMap<String, Vec<u8>>,
    pub fail: Option<String>,
    pub requests: Vec<String>,
}
impl Fixture {
    pub fn new(build: &Path, version: &str, keys: &KeyPair) -> Self {
        let tag = format!("v{version}");
        let metadata = crate::create_manifest(build, &tag).unwrap();
        let signature = minisign::sign(
            Some(&keys.pk),
            &keys.sk,
            Cursor::new(&metadata),
            Some("unpublished test fixture"),
            None,
        )
        .unwrap()
        .to_string()
        .into_bytes();
        let mut assets: HashMap<String, Vec<u8>> = HashMap::from([
            ("sde-update.json".into(), metadata),
            ("sde-update.json.minisig".into(), signature),
        ]);
        for (_, name) in crate::PLATFORMS {
            assets.insert(name.into(), std::fs::read(build.join(name)).unwrap());
        }
        let listing: Vec<_> = assets.iter().map(|(name, bytes)| serde_json::json!({"name":name,"size":bytes.len(),"browser_download_url":discovery::asset_url(&tag,name)})).collect();
        Self {
            key: keys.pk.clone(),
            releases: serde_json::json!([{"tag_name":tag,"draft":false,"prerelease":false,"assets":listing}]),
            assets,
            fail: None,
            requests: Vec::new(),
        }
    }
    pub fn discover(
        &mut self,
        installed: &str,
        platform: &str,
    ) -> discovery::Result<Option<Candidate>> {
        discovery::discover_with(self, installed, platform)
    }
    pub fn stage(
        &mut self,
        root: &Path,
        candidate: &Candidate,
    ) -> discovery::Result<staging::Staged> {
        let key = self.key.clone();
        staging::stage_with(self, root, candidate, |b, s, t| {
            crate::authenticate_with_key(b, s, t, &key).map_err(|_| Failure::Untrusted)
        })
    }
}
impl Transport for Fixture {
    fn get(&mut self, url: &str, limit: u64, output: &mut dyn Sink) -> discovery::Result<()> {
        self.requests.push(url.into());
        let listing = format!(
            "https://api.github.com/repos/{}/releases?per_page=100&page=1",
            crate::REPOSITORY
        );
        let bytes = if url == listing {
            if self.fail.as_deref() == Some("listing") {
                return Err(Failure::Offline);
            }
            serde_json::to_vec(&self.releases).unwrap()
        } else {
            let tag = self.releases[0]["tag_name"].as_str().unwrap();
            let name = self
                .assets
                .keys()
                .find(|name| discovery::asset_url(tag, name) == url)
                .ok_or(Failure::Untrusted)?;
            let bytes = self.assets[name].clone();
            if self.fail.as_ref() == Some(name) {
                // Real partial sink writes before a connection failure: no marker
                // or incomplete transaction may survive normal error cleanup.
                output
                    .write_all(&bytes[..bytes.len() / 2])
                    .map_err(|_| Failure::Staging)?;
                return Err(Failure::Offline);
            }
            bytes
        };
        if bytes.len() as u64 > limit {
            return Err(Failure::Malformed);
        }
        output.write_all(&bytes).map_err(|_| Failure::Staging)
    }
}
#[test]
fn discovery_authentication_staging_failure_matrix() {
    #[cfg(unix)]
    if unsafe { libc::geteuid() } != 0 {
        assert!(
            std::env::var_os("SDE_REQUIRE_PROTECTED_STAGING").is_none(),
            "Root E2E evidence required"
        );
        return;
    }
    for (platform, installer) in crate::PLATFORMS {
        let build = tempfile::tempdir().unwrap();
        for (_, name) in crate::PLATFORMS {
            std::fs::write(build.path().join(name), b"unpublished fixture installer").unwrap();
        }
        let root = build.path().join("staging");
        host::create_private(&root).unwrap();
        let mut f = Fixture::new(
            build.path(),
            "1.2.2",
            &KeyPair::generate_unencrypted_keypair().unwrap(),
        );
        assert!(f.discover("1.2.2", platform).unwrap().is_none());
        assert!(f.discover("1.3.0", platform).unwrap().is_none());
        f.releases[0]["prerelease"] = true.into();
        assert!(f.discover("1.2.1", platform).unwrap().is_none());
        f.releases[0]["prerelease"] = false.into();
        f.releases[0]["draft"] = true.into();
        assert!(f.discover("1.2.1", platform).unwrap().is_none());
        f.releases[0]["draft"] = false.into();
        let listing = f.releases.clone();
        f.releases[0]["assets"] = serde_json::json!([]);
        assert_eq!(
            f.discover("1.2.1", platform).unwrap_err(),
            Failure::Incomplete
        );
        f.releases = listing;
        f.fail = Some("listing".into());
        assert_eq!(f.discover("1.2.1", platform).unwrap_err(), Failure::Offline);
        assert_eq!(std::fs::read_dir(&root).unwrap().count(), 0);
        f.fail = None;
        let c = f.discover("1.2.1", platform).unwrap().unwrap();
        for name in ["sde-update.json", "sde-update.json.minisig", installer] {
            f.fail = Some(name.into());
            assert!(matches!(f.stage(&root, &c), Err(Failure::Offline)));
            assert_eq!(std::fs::read_dir(&root).unwrap().count(), 0);
        }
        f.fail = None;
        for name in ["sde-update.json", "sde-update.json.minisig", installer] {
            let saved = f.assets[name].clone();
            let corrupt = f.assets.get_mut(name).unwrap();
            corrupt[0] ^= 1;
            assert!(f.stage(&root, &c).is_err());
            assert_eq!(std::fs::read_dir(&root).unwrap().count(), 0);
            f.assets.insert(name.into(), saved);
        }
        let metadata = &f.assets["sde-update.json"];
        let signature = std::str::from_utf8(&f.assets["sde-update.json.minisig"]).unwrap();
        assert!(
            crate::authenticate(metadata, signature, &c.tag).is_err(),
            "Production key must reject unpublished test fixtures"
        );
        let staged = f.stage(&root, &c).unwrap();
        assert!(root.join(staged.id).join("verified.json").is_file());
        // Recheck eligibility after staging: promotion reversal is observable.
        f.releases[0]["prerelease"] = true.into();
        assert!(f.discover("1.2.1", platform).unwrap().is_none());
        assert!(f
            .requests
            .iter()
            .all(|u| u.starts_with("https://api.github.com/")
                || u.starts_with(&format!(
                    "https://github.com/{}/releases/download/",
                    crate::REPOSITORY
                ))));
    }
    println!("SDE_E2E_DISCOVERY_STAGING_OK");
}
