//! Read-only authenticated release metadata. No staging, installer transfer,
//! installed-version claim, capability change or installation authorization.
use crate::{
    discovery::{self, Failure, GitHub, Result, Transport},
    AuthenticatedManifest,
};
use serde::Serialize;

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct VerifiedCandidate {
    version: String,
    tag: String,
    sha256: String,
}

pub fn discover(running_version: &str, platform: &str) -> Result<Option<VerifiedCandidate>> {
    verified_with(
        &mut GitHub::notification()?,
        running_version,
        platform,
        |b, s, t| crate::authenticate(b, s, t).map_err(|_| Failure::Untrusted),
    )
}
fn verified_with(
    transport: &mut impl Transport,
    running_version: &str,
    platform: &str,
    authenticate: impl FnOnce(&[u8], &str, &str) -> Result<AuthenticatedManifest>,
) -> Result<Option<VerifiedCandidate>> {
    let Some(candidate) = discovery::discover_with(transport, running_version, platform)? else {
        return Ok(None);
    };
    let mut bytes = Vec::new();
    transport.get(
        &discovery::asset_url(&candidate.tag, "sde-update.json"),
        crate::MAX_METADATA,
        &mut bytes,
    )?;
    let mut signature = Vec::new();
    transport.get(
        &discovery::asset_url(&candidate.tag, "sde-update.json.minisig"),
        8192,
        &mut signature,
    )?;
    if bytes.is_empty() || bytes.len() as u64 > crate::MAX_METADATA || signature.len() > 8192 {
        return Err(Failure::Malformed);
    }
    let signature = std::str::from_utf8(&signature).map_err(|_| Failure::Untrusted)?;
    let manifest = authenticate(&bytes, signature, &candidate.tag)?;
    let metadata = manifest.metadata();
    let asset = metadata
        .platforms
        .get(platform)
        .ok_or(Failure::Unsupported)?;
    if metadata.version != candidate.version
        || metadata.release_tag != candidate.tag
        || asset.filename != candidate.installer
        || asset.size != candidate.installer_size
    {
        return Err(Failure::Untrusted);
    }
    Ok(Some(VerifiedCandidate {
        version: metadata.version.clone(),
        tag: metadata.release_tag.clone(),
        sha256: asset.sha256.clone(),
    }))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;
    struct Mock {
        responses: std::collections::VecDeque<Vec<u8>>,
        urls: Vec<String>,
    }
    impl Transport for Mock {
        fn get(&mut self, url: &str, limit: u64, output: &mut dyn discovery::Sink) -> Result<()> {
            assert!(!crate::PLATFORMS.iter().any(|(_, name)| url.ends_with(name)));
            self.urls.push(url.into());
            let bytes = self.responses.pop_front().expect("unexpected transfer");
            assert!(bytes.len() as u64 <= limit);
            output.write_all(&bytes).map_err(|_| Failure::Offline)
        }
    }
    fn fixture(tamper: bool, mismatch: bool) -> (Mock, minisign::KeyPair) {
        let dir = tempfile::tempdir().unwrap();
        for (_, name) in crate::PLATFORMS {
            std::fs::write(dir.path().join(name), b"fixture").unwrap();
        }
        let mut bytes = crate::create_manifest(dir.path(), "v1.2.2").unwrap();
        let keys = minisign::KeyPair::generate_unencrypted_keypair().unwrap();
        let signature = minisign::sign(
            Some(&keys.pk),
            &keys.sk,
            Cursor::new(&bytes),
            Some("test"),
            None,
        )
        .unwrap()
        .to_string();
        if tamper {
            bytes.push(b' ');
        }
        let assets=[("sde-update.json",bytes.len() as u64),("sde-update.json.minisig",signature.len() as u64),
            (crate::PLATFORMS[0].1,if mismatch {8} else {7}),(crate::PLATFORMS[1].1,7)]
            .into_iter().map(|(name,size)|serde_json::json!({"name":name,"size":size,"browser_download_url":discovery::asset_url("v1.2.2",name)})).collect::<Vec<_>>();
        let releases=serde_json::to_vec(&serde_json::json!([{"tag_name":"v1.2.2","draft":false,"prerelease":false,"assets":assets}])).unwrap();
        (
            Mock {
                responses: [releases, bytes, signature.into_bytes()].into(),
                urls: Vec::new(),
            },
            keys,
        )
    }
    #[test]
    fn authenticates_exact_bytes_and_never_requests_an_installer() {
        let (mut transport, keys) = fixture(false, false);
        let found = verified_with(&mut transport, "1.2.1", crate::PLATFORMS[0].0, |b, s, t| {
            crate::authenticate_with_key(b, s, t, &keys.pk).map_err(|_| Failure::Untrusted)
        })
        .unwrap()
        .unwrap();
        assert_eq!(found.version, "1.2.2");
        assert_eq!(transport.urls.len(), 3);
        assert_eq!(found.sha256.len(), 64);
    }
    #[test]
    fn tampered_signature_and_listing_size_mismatch_fail_closed() {
        for (tamper, mismatch) in [(true, false), (false, true)] {
            let (mut transport, keys) = fixture(tamper, mismatch);
            assert!(
                verified_with(&mut transport, "1.2.1", crate::PLATFORMS[0].0, |b, s, t| {
                    crate::authenticate_with_key(b, s, t, &keys.pk).map_err(|_| Failure::Untrusted)
                })
                .is_err()
            );
        }
    }
    #[test]
    fn no_newer_listing_is_not_a_claim_about_installed_package_or_signed_latest() {
        let mut transport = Mock {
            responses: [b"[]".to_vec()].into(),
            urls: Vec::new(),
        };
        assert!(verified_with(
            &mut transport,
            "1.2.1",
            crate::PLATFORMS[0].0,
            |_, _, _| panic!("no candidate to authenticate")
        )
        .unwrap()
        .is_none());
        assert_eq!(transport.urls.len(), 1);
    }
    #[test]
    fn pinned_key_rejects_an_ephemeral_signer() {
        let (mut transport, _) = fixture(false, false);
        assert!(
            verified_with(&mut transport, "1.2.1", crate::PLATFORMS[0].0, |b, s, t| {
                crate::authenticate(b, s, t).map_err(|_| Failure::Untrusted)
            })
            .is_err()
        );
    }
}
