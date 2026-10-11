//! Authenticated release contract shared by discovery and native installers.
//! Discovery and protected staging never execute a package.
pub mod discovery;
pub mod host;
pub mod staging;
use minisign::{PublicKey, SignatureBox};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    fs::File,
    io::{Cursor, Read},
    path::Path,
};

pub const REPOSITORY: &str = "stormbots/Tactics-Strategy-Dev-Environments";
pub const MAX_METADATA: u64 = 65536;
pub const MAX_INSTALLER: u64 = 512 * 1024 * 1024;
pub const ENGINE_VERSION: u32 = 1;
pub const PLATFORMS: [(&str, &str); 2] = [
    ("windows-x86_64", "Skyview-Dev-Setup-Windows-x64.exe"),
    ("linux-amd64", "Skyview-Dev-Setup-LinuxMint-amd64.deb"),
];
pub type Result<T> = std::result::Result<T, String>;
#[derive(Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Asset {
    pub filename: String,
    pub size: u64,
    pub sha256: String,
}
#[derive(Debug, Serialize, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Manifest {
    pub schema_version: u32,
    pub channel: String,
    pub repository: String,
    pub release_tag: String,
    pub version: String,
    pub minimum_engine_version: u32,
    pub minimum_schema_version: u32,
    pub platforms: BTreeMap<String, Asset>,
}
fn err(message: &str) -> String {
    message.to_owned()
}
pub fn release_version(tag: &str) -> Result<String> {
    let value = tag
        .strip_prefix('v')
        .ok_or_else(|| err("Expected canonical vMAJOR.MINOR.PATCH tag"))?;
    let version = semver::Version::parse(value).map_err(|_| err("Invalid release version"))?;
    if !version.pre.is_empty() || !version.build.is_empty() || version.to_string() != value {
        return Err(err("Only canonical stable semantic versions are supported"));
    }
    Ok(value.to_owned())
}
impl Manifest {
    fn validate(&self, tag: &str) -> Result<()> {
        if self.schema_version != 1
            || self.minimum_schema_version != 1
            || self.minimum_engine_version == 0
            || self.minimum_engine_version > ENGINE_VERSION
        {
            return Err(err("Unsupported manifest or engine version"));
        }
        if self.channel != "stable"
            || self.repository != REPOSITORY
            || self.release_tag != tag
            || self.version != release_version(tag)?
        {
            return Err(err("Release identity mismatch"));
        }
        if self.platforms.len() != PLATFORMS.len() {
            return Err(err("Incomplete platform set"));
        }
        for (platform, filename) in PLATFORMS {
            let asset = self
                .platforms
                .get(platform)
                .ok_or_else(|| err("Unsupported platform set"))?;
            if asset.filename != filename
                || asset.size == 0
                || asset.size > MAX_INSTALLER
                || asset.sha256.len() != 64
                || !asset
                    .sha256
                    .bytes()
                    .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
            {
                return Err(err("Invalid installer identity, size, or checksum"));
            }
        }
        Ok(())
    }
}
/// No runtime/environment key override. An unconfigured embedded key fails closed.
fn pinned_key() -> Result<PublicKey> {
    PublicKey::from_box(include_str!("../keys/release.pub").to_owned().into())
        .map_err(|_| err("Release verification key is not configured"))
}
pub struct AuthenticatedManifest(Manifest);
impl AuthenticatedManifest {
    pub fn metadata(&self) -> &Manifest {
        &self.0
    }
}
fn authenticate_with_key(
    bytes: &[u8],
    signature: &str,
    tag: &str,
    key: &PublicKey,
) -> Result<AuthenticatedManifest> {
    if bytes.is_empty() || bytes.len() as u64 > MAX_METADATA || signature.len() > 8192 {
        return Err(err("Metadata or signature exceeds limits"));
    }
    let signature =
        SignatureBox::from_string(signature).map_err(|_| err("Missing or malformed signature"))?;
    // Verify exact bytes before parsing installation fields. Legacy signatures are rejected.
    minisign::verify(key, &signature, Cursor::new(bytes), true, false, false)
        .map_err(|_| err("Metadata signature verification failed"))?;
    let manifest: Manifest =
        serde_json::from_slice(bytes).map_err(|_| err("Malformed or incomplete metadata"))?;
    manifest.validate(tag)?;
    Ok(AuthenticatedManifest(manifest))
}
pub fn authenticate(bytes: &[u8], signature: &str, tag: &str) -> Result<AuthenticatedManifest> {
    authenticate_with_key(bytes, signature, tag, &pinned_key()?)
}
/// The caller must first exclude GitHub drafts/prereleases and versions <= installed.
/// A signed stable-intent manifest alone never grants production eligibility.
pub fn verify_installer(
    authenticated: &AuthenticatedManifest,
    platform: &str,
    path: &Path,
) -> Result<()> {
    let manifest = authenticated.metadata();
    manifest.validate(&manifest.release_tag)?;
    let asset = manifest
        .platforms
        .get(platform)
        .ok_or_else(|| err("Unsupported platform"))?;
    if path.file_name().and_then(|n| n.to_str()) != Some(&asset.filename) {
        return Err(err("Installer filename mismatch"));
    }
    let (size, hash) = hash_file(path)?;
    if size != asset.size || hash != asset.sha256 {
        return Err(err("Installer length or checksum mismatch"));
    }
    Ok(())
}
fn hash_file(path: &Path) -> Result<(u64, String)> {
    let info = std::fs::symlink_metadata(path).map_err(|_| err("Installer unavailable"))?;
    if !info.is_file()
        || info.file_type().is_symlink()
        || info.len() == 0
        || info.len() > MAX_INSTALLER
    {
        return Err(err("Invalid installer file or size"));
    }
    let mut file = File::open(path).map_err(|_| err("Installer unreadable"))?;
    let mut hash = Sha256::new();
    let mut size = 0u64;
    let mut buffer = [0u8; 65536];
    loop {
        let count = file
            .read(&mut buffer)
            .map_err(|_| err("Installer read failed"))?;
        if count == 0 {
            break;
        }
        size += count as u64;
        if size > MAX_INSTALLER {
            return Err(err("Installer exceeds size limit"));
        }
        hash.update(&buffer[..count]);
    }
    Ok((size, format!("{:x}", hash.finalize())))
}
/// Release-build input, not authenticated update input. Never use this to install.
pub fn create_manifest(dist: &Path, tag: &str) -> Result<Vec<u8>> {
    let mut platforms = BTreeMap::new();
    for (platform, filename) in PLATFORMS {
        let (size, sha256) = hash_file(&dist.join(filename))?;
        platforms.insert(
            platform.to_owned(),
            Asset {
                filename: filename.to_owned(),
                size,
                sha256,
            },
        );
    }
    let manifest = Manifest {
        schema_version: 1,
        channel: "stable".into(),
        repository: REPOSITORY.into(),
        release_tag: tag.into(),
        version: release_version(tag)?,
        minimum_engine_version: 1,
        minimum_schema_version: 1,
        platforms,
    };
    manifest.validate(tag)?;
    let mut bytes =
        serde_json::to_vec_pretty(&manifest).map_err(|_| err("Metadata encoding failed"))?;
    bytes.push(b'\n');
    Ok(bytes)
}
pub fn read_bounded(path: &Path, limit: u64) -> Result<Vec<u8>> {
    let file = File::open(path).map_err(|_| err("Required release file unavailable"))?;
    let mut bytes = Vec::new();
    file.take(limit + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| err("Release file unreadable"))?;
    if bytes.len() as u64 > limit {
        return Err(err("Release file exceeds limit"));
    }
    Ok(bytes)
}
/// Private material is provided only to the approved release-signing process.
/// Errors intentionally exclude library diagnostics that might contain key material.
pub fn sign_manifest(bytes: &[u8], tag: &str, secret: &str, password: String) -> Result<String> {
    sign_with_key(bytes, tag, secret, password, &pinned_key()?)
}
fn sign_with_key(
    bytes: &[u8],
    tag: &str,
    secret: &str,
    password: String,
    key: &PublicKey,
) -> Result<String> {
    let secret = minisign::SecretKey::from_box(secret.to_owned().into(), Some(password))
        .map_err(|_| err("Signing secret unavailable or invalid"))?;
    let signature = minisign::sign(
        Some(key),
        &secret,
        Cursor::new(bytes),
        Some("SDE release metadata schema 1"),
        None,
    )
    .map_err(|_| err("Release signing failed"))?
    .to_string();
    // Reject mismatched keys and invalid manifests before any upload.
    authenticate_with_key(bytes, &signature, tag, key)?;
    Ok(signature)
}

#[cfg(test)]
mod tests {
    use super::*;
    use minisign::KeyPair;
    use serde_json::{json, Value};
    fn fixture() -> (tempfile::TempDir, Vec<u8>, KeyPair) {
        let dir = tempfile::tempdir().unwrap();
        for (_, name) in PLATFORMS {
            std::fs::write(dir.path().join(name), b"disposable installer fixture").unwrap();
        }
        (
            dir,
            Vec::new(),
            KeyPair::generate_unencrypted_keypair().unwrap(),
        )
    }
    fn signed(bytes: &[u8], keys: &KeyPair) -> String {
        minisign::sign(
            Some(&keys.pk),
            &keys.sk,
            Cursor::new(bytes),
            Some("test-only ephemeral key"),
            None,
        )
        .unwrap()
        .to_string()
    }
    #[test]
    fn valid_signed_release_and_both_installers() {
        let (dir, _, keys) = fixture();
        let bytes = create_manifest(dir.path(), "v1.2.2").unwrap();
        let manifest =
            authenticate_with_key(&bytes, &signed(&bytes, &keys), "v1.2.2", &keys.pk).unwrap();
        for (platform, name) in PLATFORMS {
            verify_installer(&manifest, platform, &dir.path().join(name)).unwrap();
        }
        assert!(
            verify_installer(&manifest, "windows-arm64", &dir.path().join(PLATFORMS[0].1)).is_err()
        );
    }
    #[test]
    fn modified_metadata_signature_wrong_key_and_candidate_tag_rejected() {
        let (dir, _, keys) = fixture();
        let bytes = create_manifest(dir.path(), "v1.2.2").unwrap();
        let signature = signed(&bytes, &keys);
        let mut changed = bytes.clone();
        changed.push(b' ');
        assert!(authenticate_with_key(&changed, &signature, "v1.2.2", &keys.pk).is_err());
        assert!(authenticate_with_key(&bytes, "", "v1.2.2", &keys.pk).is_err());
        assert!(authenticate_with_key(
            &bytes,
            &signature.replace("test-only", "tampered"),
            "v1.2.2",
            &keys.pk
        )
        .is_err());
        assert!(authenticate_with_key(&bytes, &signature, "v1.2.3", &keys.pk).is_err());
        let other = KeyPair::generate_unencrypted_keypair().unwrap();
        assert!(authenticate_with_key(&bytes, &signature, "v1.2.2", &other.pk).is_err());
    }
    #[test]
    fn even_authentic_incomplete_or_unsupported_metadata_is_rejected() {
        let (dir, _, keys) = fixture();
        let bytes = create_manifest(dir.path(), "v1.2.2").unwrap();
        let original: Value = serde_json::from_slice(&bytes).unwrap();
        let cases = [
            ("schemaVersion", json!(2)),
            ("minimumEngineVersion", json!(2)),
            ("minimumSchemaVersion", json!(2)),
            ("repository", json!("attacker/repo")),
            ("channel", json!("candidate")),
            ("version", json!("1.2.3")),
            ("platforms", json!({})),
            ("unexpected", json!(true)),
        ];
        for (field, value) in cases {
            let mut changed = original.clone();
            changed[field] = value;
            let changed = serde_json::to_vec(&changed).unwrap();
            assert!(
                authenticate_with_key(&changed, &signed(&changed, &keys), "v1.2.2", &keys.pk)
                    .is_err(),
                "{field}"
            );
        }
        for field in original.as_object().unwrap().keys() {
            let mut changed = original.clone();
            changed.as_object_mut().unwrap().remove(field);
            let changed = serde_json::to_vec(&changed).unwrap();
            assert!(
                authenticate_with_key(&changed, &signed(&changed, &keys), "v1.2.2", &keys.pk)
                    .is_err(),
                "missing {field}"
            );
        }
        for (field, value) in [
            ("filename", json!("../evil.exe")),
            ("size", json!(0)),
            ("size", json!(MAX_INSTALLER + 1)),
            ("sha256", json!("BAD")),
        ] {
            let mut changed = original.clone();
            changed["platforms"]["windows-x86_64"][field] = value;
            let changed = serde_json::to_vec(&changed).unwrap();
            assert!(
                authenticate_with_key(&changed, &signed(&changed, &keys), "v1.2.2", &keys.pk)
                    .is_err()
            );
        }
    }
    #[test]
    fn changed_truncated_missing_and_renamed_installers_rejected() {
        let (dir, _, keys) = fixture();
        let bytes = create_manifest(dir.path(), "v1.2.2").unwrap();
        let manifest =
            authenticate_with_key(&bytes, &signed(&bytes, &keys), "v1.2.2", &keys.pk).unwrap();
        let path = dir.path().join(PLATFORMS[0].1);
        let mut altered = std::fs::read(&path).unwrap();
        altered[0] ^= 1;
        std::fs::write(&path, altered).unwrap();
        assert!(verify_installer(&manifest, PLATFORMS[0].0, &path).is_err());
        std::fs::write(&path, b"short").unwrap();
        assert!(verify_installer(&manifest, PLATFORMS[0].0, &path).is_err());
        std::fs::rename(&path, dir.path().join("renamed.exe")).unwrap();
        assert!(verify_installer(&manifest, PLATFORMS[0].0, &path).is_err());
        assert!(
            verify_installer(&manifest, PLATFORMS[0].0, &dir.path().join("renamed.exe")).is_err()
        );
        assert!(create_manifest(dir.path(), "v1.2.2").is_err());
    }
    #[test]
    fn encrypted_release_signing_and_wrong_password_fail_closed() {
        let (dir, _, _) = fixture();
        let bytes = create_manifest(dir.path(), "v1.2.2").unwrap();
        let password = "disposable-test-password".to_owned();
        let keys = KeyPair::generate_encrypted_keypair(Some(password.clone())).unwrap();
        let secret = keys.sk.to_box(None).unwrap().to_string();
        let signature = sign_with_key(&bytes, "v1.2.2", &secret, password, &keys.pk).unwrap();
        authenticate_with_key(&bytes, &signature, "v1.2.2", &keys.pk).unwrap();
        let failure =
            sign_with_key(&bytes, "v1.2.2", &secret, "wrong".into(), &keys.pk).unwrap_err();
        assert_eq!(failure, "Signing secret unavailable or invalid");
        assert!(!failure.contains(&secret));
    }
    #[test]
    fn release_tag_and_input_limits() {
        for tag in [
            "v1.2.2-rc.1",
            "v1.2.2+build",
            "windows-v1.2.2",
            "1.2.2",
            "v01.2.2",
        ] {
            assert!(release_version(tag).is_err());
        }
        let (_, _, keys) = fixture();
        assert!(authenticate_with_key(
            &vec![b' '; MAX_METADATA as usize + 1],
            "",
            "v1.2.2",
            &keys.pk
        )
        .is_err());
    }
    #[test]
    #[cfg(unix)]
    fn official_minisign_interoperability() {
        use std::process::Command;
        if Command::new("minisign").arg("-v").output().is_err() {
            assert!(
                std::env::var("SDE_REQUIRE_MINISIGN_INTEROP").is_err(),
                "Native Minisign required on this runner"
            );
            return;
        }
        let (dir, _, keys) = fixture();
        let bytes = create_manifest(dir.path(), "v1.2.2").unwrap();
        let message = dir.path().join("sde-update.json");
        let public = dir.path().join("test.pub");
        let secret = dir.path().join("test.key");
        std::fs::write(&message, &bytes).unwrap();
        std::fs::write(&public, keys.pk.to_box().unwrap().to_bytes()).unwrap();
        std::fs::write(&secret, keys.sk.to_box(None).unwrap().to_bytes()).unwrap();
        std::fs::write(
            dir.path().join("sde-update.json.minisig"),
            signed(&bytes, &keys),
        )
        .unwrap();
        assert!(Command::new("minisign")
            .args(["-V", "-H", "-q", "-p"])
            .arg(&public)
            .arg("-m")
            .arg(&message)
            .status()
            .unwrap()
            .success());
        assert!(Command::new("minisign")
            .args(["-S", "-W", "-q", "-s"])
            .arg(&secret)
            .arg("-m")
            .arg(&message)
            .status()
            .unwrap()
            .success());
        let signature =
            std::fs::read_to_string(dir.path().join("sde-update.json.minisig")).unwrap();
        authenticate_with_key(&bytes, &signature, "v1.2.2", &keys.pk).unwrap();
        // Native legacy signatures must be rejected even if cryptographically valid.
        assert!(Command::new("minisign")
            .args(["-S", "-W", "-l", "-q", "-s"])
            .arg(&secret)
            .arg("-m")
            .arg(&message)
            .status()
            .unwrap()
            .success());
        let signature =
            std::fs::read_to_string(dir.path().join("sde-update.json.minisig")).unwrap();
        assert!(authenticate_with_key(&bytes, &signature, "v1.2.2", &keys.pk).is_err());
    }
    #[test]
    fn production_key_cannot_be_overridden_by_fixture_key() {
        let (dir, _, keys) = fixture();
        let bytes = create_manifest(dir.path(), "v1.2.2").unwrap();
        assert!(authenticate(&bytes, &signed(&bytes, &keys), "v1.2.2").is_err());
    }
}
