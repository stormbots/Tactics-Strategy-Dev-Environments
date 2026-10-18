//! Shared discovery policy: notification callers may use `discover` without staging.
use crate::{release_version, PLATFORMS, REPOSITORY};
use reqwest::{blocking::Client, redirect::Policy, Url};
use semver::Version;
use serde::{Deserialize, Serialize};
use std::{
    io::{Read, Write},
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

pub const MAX_PAGES: usize = 10;
const PAGE_SIZE: usize = 100;
const MAX_PAGE: u64 = 4 * 1024 * 1024;
const MAX_REDIRECTS: usize = 5;
const DEADLINE: Duration = Duration::from_secs(600);
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub enum Failure {
    Offline,
    RateLimited,
    Malformed,
    Incomplete,
    Untrusted,
    Unsupported,
    InvalidInstalled,
    Staging,
    Cleanup,
}
pub type Result<T> = std::result::Result<T, Failure>;
#[derive(Debug, Clone, Deserialize)]
pub struct ReleaseAsset {
    pub name: String,
    pub size: u64,
    pub browser_download_url: String,
}
#[derive(Debug, Clone, Deserialize)]
pub struct Release {
    pub tag_name: String,
    pub draft: bool,
    pub prerelease: bool,
    pub assets: Vec<ReleaseAsset>,
}
#[derive(Debug, Clone, Serialize)]
pub struct Candidate {
    pub tag: String,
    pub version: String,
    pub platform: String,
    pub installer: String,
    #[serde(skip)]
    pub installer_size: u64,
}
/// Select by semantic version only. Validate the highest candidate before returning it;
/// an incomplete/untrusted newer release never permits fallback to an older one.
pub fn select(releases: &[Release], installed: &str, platform: &str) -> Result<Option<Candidate>> {
    let installed_text = installed;
    let installed = Version::parse(installed).map_err(|_| Failure::InvalidInstalled)?;
    if !installed.build.is_empty() || installed.to_string() != installed_text {
        return Err(Failure::InvalidInstalled);
    }
    let filename = PLATFORMS
        .iter()
        .find(|(p, _)| *p == platform)
        .map(|(_, n)| *n)
        .ok_or(Failure::Unsupported)?;
    let mut selected: Option<(&Release, Version)> = None;
    for release in releases {
        if release.draft || release.prerelease {
            continue;
        }
        let Ok(version) = release_version(&release.tag_name) else {
            continue;
        };
        let version = Version::parse(&version).map_err(|_| Failure::Malformed)?;
        if version <= installed {
            continue;
        }
        if let Some((_, previous)) = &selected {
            if version == *previous {
                return Err(Failure::Malformed);
            }
            if version < *previous {
                continue;
            }
        }
        selected = Some((release, version));
    }
    let Some((release, version)) = selected else {
        return Ok(None);
    };
    asset(release, "sde-update.json", crate::MAX_METADATA)?;
    asset(release, "sde-update.json.minisig", 8192)?;
    let installer = asset(release, filename, crate::MAX_INSTALLER)?;
    Ok(Some(Candidate {
        tag: release.tag_name.clone(),
        version: version.to_string(),
        platform: platform.into(),
        installer: filename.into(),
        installer_size: installer.size,
    }))
}
fn asset<'a>(release: &'a Release, name: &str, max: u64) -> Result<&'a ReleaseAsset> {
    let matching: Vec<_> = release.assets.iter().filter(|a| a.name == name).collect();
    if matching.len() != 1 {
        return Err(Failure::Incomplete);
    }
    let a = matching[0];
    if a.size == 0 || a.size > max {
        return Err(Failure::Malformed);
    }
    if a.browser_download_url != asset_url(&release.tag_name, name) {
        return Err(Failure::Untrusted);
    }
    Ok(a)
}
pub(crate) fn asset_url(tag: &str, filename: &str) -> String {
    format!("https://github.com/{REPOSITORY}/releases/download/{tag}/{filename}")
}
fn safe_url(url: &Url, initial: &Url) -> bool {
    if url.scheme() != "https"
        || !url.username().is_empty()
        || url.password().is_some()
        || url.port().is_some()
        || url.fragment().is_some()
    {
        return false;
    }
    if url == initial {
        return true;
    }
    // Asset requests may redirect only to GitHub's release-asset CDN. API redirects
    // and redirects back to unrelated github.com routes are rejected.
    initial.host_str() == Some("github.com")
        && url.host_str() == Some("release-assets.githubusercontent.com")
        && url.path().starts_with("/github-production-release-asset/")
}
pub(crate) trait Sink: Write {
    fn reset(&mut self) -> Result<()>;
}
impl Sink for Vec<u8> {
    fn reset(&mut self) -> Result<()> {
        self.clear();
        Ok(())
    }
}
impl Sink for std::fs::File {
    fn reset(&mut self) -> Result<()> {
        use std::io::{Seek, SeekFrom};
        self.set_len(0)
            .and_then(|_| self.seek(SeekFrom::Start(0)))
            .map_err(|_| Failure::Staging)?;
        Ok(())
    }
}
pub(crate) trait Transport {
    fn get(&mut self, url: &str, limit: u64, output: &mut dyn Sink) -> Result<()>;
}
pub struct GitHub {
    client: Client,
    deadline: Instant,
}
impl GitHub {
    pub fn new() -> Result<Self> {
        Ok(Self {
            client: Client::builder()
                .redirect(Policy::none())
                .no_proxy()
                .user_agent("Skyview-SDE-update/1")
                .connect_timeout(Duration::from_secs(10))
                .build()
                .map_err(|_| Failure::Offline)?,
            deadline: Instant::now() + DEADLINE,
        })
    }
    /// Notification metadata only: preserve transport policy, shorten total budget.
    pub(crate) fn notification() -> Result<Self> {
        let mut client = Self::new()?;
        client.deadline = Instant::now() + Duration::from_secs(15);
        Ok(client)
    }
    fn remaining(&self) -> Result<Duration> {
        self.deadline
            .checked_duration_since(Instant::now())
            .filter(|d| !d.is_zero())
            .ok_or(Failure::Offline)
    }
    fn pause(&self, delay: Duration, failure: Failure) -> Result<()> {
        if delay >= self.remaining().map_err(|_| failure)? {
            return Err(failure);
        }
        std::thread::sleep(delay);
        Ok(())
    }
    fn request(
        &self,
        initial: &Url,
    ) -> std::result::Result<reqwest::blocking::Response, RequestError> {
        let mut url = initial.clone();
        for hop in 0..=MAX_REDIRECTS {
            if !safe_url(&url, initial) {
                return Err(RequestError::Abort(Failure::Untrusted));
            }
            let response = self
                .client
                .get(url.clone())
                .header(
                    "Accept",
                    if initial.host_str() == Some("api.github.com") {
                        "application/vnd.github+json"
                    } else {
                        "application/octet-stream"
                    },
                )
                .header("X-GitHub-Api-Version", "2022-11-28")
                .timeout(
                    self.remaining()
                        .map_err(RequestError::Abort)?
                        .min(Duration::from_secs(30)),
                )
                .send()
                .map_err(|_| RequestError::Retry(Failure::Offline, None))?;
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map_err(|_| RequestError::Abort(Failure::Offline))?
                .as_secs();
            match response_action(response.status().as_u16(), response.headers(), now) {
                Action::Ready => return Ok(response),
                Action::Abort(failure) => return Err(RequestError::Abort(failure)),
                Action::Retry(failure, delay) => return Err(RequestError::Retry(failure, delay)),
                Action::Redirect => {
                    if hop == MAX_REDIRECTS {
                        return Err(RequestError::Abort(Failure::Untrusted));
                    }
                    let location = response
                        .headers()
                        .get("location")
                        .and_then(|s| s.to_str().ok())
                        .ok_or(RequestError::Abort(Failure::Untrusted))?;
                    url = url
                        .join(location)
                        .map_err(|_| RequestError::Abort(Failure::Untrusted))?;
                }
            }
        }
        Err(RequestError::Abort(Failure::Untrusted))
    }
}
#[derive(Debug)]
enum RequestError {
    Abort(Failure),
    Retry(Failure, Option<Duration>),
}
#[derive(Debug, PartialEq, Eq)]
enum Action {
    Ready,
    Redirect,
    Abort(Failure),
    Retry(Failure, Option<Duration>),
}
fn response_action(status: u16, headers: &reqwest::header::HeaderMap, now: u64) -> Action {
    if (300..400).contains(&status) {
        return Action::Redirect;
    }
    if status == 429
        || (status == 403
            && (headers
                .get("x-ratelimit-remaining")
                .and_then(|v| v.to_str().ok())
                == Some("0")
                || headers.contains_key("retry-after")))
    {
        let delay = headers
            .get("retry-after")
            .and_then(|v| v.to_str().ok())
            .and_then(|v| v.parse::<u64>().ok())
            .or_else(|| {
                headers
                    .get("x-ratelimit-reset")
                    .and_then(|v| v.to_str().ok())
                    .and_then(|v| v.parse::<u64>().ok())
                    .map(|reset| reset.saturating_sub(now).saturating_add(1))
            });
        return match delay {
            Some(delay) => Action::Retry(
                Failure::RateLimited,
                Some(Duration::from_secs(delay.max(1))),
            ),
            None => Action::Abort(Failure::RateLimited),
        };
    }
    if (500..600).contains(&status) || status == 408 {
        return Action::Retry(Failure::Offline, None);
    }
    if status == 200 {
        Action::Ready
    } else {
        Action::Abort(if status == 404 {
            Failure::Incomplete
        } else {
            Failure::Offline
        })
    }
}
fn copy_bounded(
    reader: &mut impl Read,
    output: &mut dyn Sink,
    limit: u64,
    deadline: Instant,
) -> Result<u64> {
    let mut count = 0u64;
    let mut buffer = [0u8; 65536];
    loop {
        if Instant::now() >= deadline {
            return Err(Failure::Offline);
        }
        let n = reader.read(&mut buffer).map_err(|_| Failure::Offline)?;
        if n == 0 {
            break;
        }
        count = count.checked_add(n as u64).ok_or(Failure::Malformed)?;
        if count > limit {
            return Err(Failure::Malformed);
        }
        output
            .write_all(&buffer[..n])
            .map_err(|_| Failure::Staging)?;
    }
    if count == 0 {
        return Err(Failure::Incomplete);
    }
    Ok(count)
}
fn receive_response(
    mut response: reqwest::blocking::Response,
    output: &mut dyn Sink,
    limit: u64,
    deadline: Instant,
) -> std::result::Result<(), RequestError> {
    // Reqwest's content_length is the remaining body's size hint, not an immutable
    // header value. Capture it before streaming; it can be zero after consumption.
    let expected_length = response.content_length();
    if expected_length.is_some_and(|len| len > limit) {
        return Err(RequestError::Abort(Failure::Malformed));
    }
    match copy_bounded(&mut response, output, limit, deadline) {
        Ok(count) if expected_length.is_some_and(|len| len != count) => {
            Err(RequestError::Retry(Failure::Offline, None))
        }
        Ok(_) => Ok(()),
        Err(Failure::Offline) => Err(RequestError::Retry(Failure::Offline, None)),
        Err(failure) => Err(RequestError::Abort(failure)),
    }
}
impl Transport for GitHub {
    fn get(&mut self, url: &str, limit: u64, output: &mut dyn Sink) -> Result<()> {
        let initial = Url::parse(url).map_err(|_| Failure::Untrusted)?;
        if !(url.starts_with(&format!(
            "https://api.github.com/repos/{REPOSITORY}/releases?per_page=100&page="
        )) || url.starts_with(&format!(
            "https://github.com/{REPOSITORY}/releases/download/"
        ))) {
            return Err(Failure::Untrusted);
        }
        for attempt in 0..3 {
            output.reset()?;
            let result = match self.request(&initial) {
                Ok(response) => receive_response(response, output, limit, self.deadline),
                Err(error) => Err(error),
            };
            match result {
                Err(RequestError::Abort(failure)) => return Err(failure),
                Err(RequestError::Retry(failure, delay)) => {
                    if attempt == 2 {
                        return Err(failure);
                    }
                    self.pause(delay.unwrap_or(Duration::from_secs(1 << attempt)), failure)?;
                }
                Ok(()) => return Ok(()),
            }
        }
        Err(Failure::Offline)
    }
}

pub(crate) fn discover_with(
    transport: &mut impl Transport,
    installed: &str,
    platform: &str,
) -> Result<Option<Candidate>> {
    select(&list_with(transport)?, installed, platform)
}
pub(crate) fn list_with(transport: &mut impl Transport) -> Result<Vec<Release>> {
    let mut releases = Vec::new();
    for page in 1..=MAX_PAGES {
        let mut bytes = Vec::new();
        transport.get(&format!("https://api.github.com/repos/{REPOSITORY}/releases?per_page={PAGE_SIZE}&page={page}"), MAX_PAGE, &mut bytes)?;
        let batch: Vec<Release> = serde_json::from_slice(&bytes).map_err(|_| Failure::Malformed)?;
        if batch.len() > PAGE_SIZE {
            return Err(Failure::Malformed);
        }
        let complete = batch.len() < PAGE_SIZE;
        releases.extend(batch);
        if complete {
            return Ok(releases);
        }
    }
    Err(Failure::Incomplete)
}
/// Notification-only callers provide their running application's real package version.
/// This function fetches release listings, but never downloads or runs an installer.
pub fn discover(installed: &str, platform: &str) -> Result<Option<Candidate>> {
    discover_with(&mut GitHub::new()?, installed, platform)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn release(tag: &str) -> Release {
        Release {
            tag_name: tag.into(),
            draft: false,
            prerelease: false,
            assets: [
                "sde-update.json",
                "sde-update.json.minisig",
                PLATFORMS[0].1,
                PLATFORMS[1].1,
            ]
            .iter()
            .map(|name| ReleaseAsset {
                name: name.to_string(),
                size: 1,
                browser_download_url: asset_url(tag, name),
            })
            .collect(),
        }
    }
    #[test]
    fn selection_semantic_no_downgrade_and_no_fallback() {
        let mut releases = vec![
            release("v1.9.0"),
            release("v1.10.0"),
            release("windows-v99.0.0"),
            release("v1.11.0-rc.1"),
        ];
        let mut pre = release("v99.0.0");
        pre.prerelease = true;
        releases.push(pre);
        let mut draft = release("v98.0.0");
        draft.draft = true;
        releases.push(draft);
        assert_eq!(
            select(&releases, "1.2.1", "linux-amd64")
                .unwrap()
                .unwrap()
                .version,
            "1.10.0"
        );
        assert!(select(&releases, "1.10.0", "linux-amd64")
            .unwrap()
            .is_none());
        releases[1].assets.clear();
        assert_eq!(
            select(&releases, "1.2.1", "linux-amd64").unwrap_err(),
            Failure::Incomplete
        );
        assert_eq!(
            select(&releases, "bad", "linux-amd64").unwrap_err(),
            Failure::InvalidInstalled
        );
        assert_eq!(
            select(&releases, "1.2.1", "linux-arm64").unwrap_err(),
            Failure::Unsupported
        );
    }
    #[test]
    fn assets_and_redirects_fail_closed() {
        let mut r = release("v1.3.0");
        r.assets[0].browser_download_url = "https://evil.example/sde-update.json".into();
        assert_eq!(
            select(&[r], "1.2.1", "linux-amd64").unwrap_err(),
            Failure::Untrusted
        );
        let initial = Url::parse(&asset_url("v1.3.0", "sde-update.json")).unwrap();
        for unsafe_url in ["http://github.com/x", "https://user@release-assets.githubusercontent.com/github-production-release-asset/1", "https://release-assets.githubusercontent.com/other", "https://evil.example/github-production-release-asset/1", "https://github.com/other", "https://release-assets.githubusercontent.com:444/github-production-release-asset/1", "https://release-assets.githubusercontent.com/github-production-release-asset/1#fragment"] { assert!(!safe_url(&Url::parse(unsafe_url).unwrap(), &initial)); }
        assert!(safe_url(&Url::parse("https://release-assets.githubusercontent.com/github-production-release-asset/1/2?signature=opaque").unwrap(), &initial));
        assert!(!safe_url(
            &initial,
            &Url::parse("https://api.github.com/repos/x/releases").unwrap()
        ));
    }
    #[test]
    fn network_status_retry_deadline_and_size_contracts() {
        use reqwest::header::HeaderMap;
        let empty = HeaderMap::new();
        assert_eq!(response_action(200, &empty, 100), Action::Ready);
        assert_eq!(
            response_action(206, &empty, 100),
            Action::Abort(Failure::Offline)
        );
        assert_eq!(response_action(302, &empty, 100), Action::Redirect);
        assert_eq!(
            response_action(404, &empty, 100),
            Action::Abort(Failure::Incomplete)
        );
        assert_eq!(
            response_action(503, &empty, 100),
            Action::Retry(Failure::Offline, None)
        );
        assert_eq!(
            response_action(429, &empty, 100),
            Action::Abort(Failure::RateLimited)
        );
        let mut limited = HeaderMap::new();
        limited.insert("retry-after", "600".parse().unwrap());
        assert_eq!(
            response_action(429, &limited, 100),
            Action::Retry(Failure::RateLimited, Some(Duration::from_secs(600)))
        );
        limited.clear();
        limited.insert("x-ratelimit-remaining", "0".parse().unwrap());
        limited.insert("x-ratelimit-reset", "130".parse().unwrap());
        assert_eq!(
            response_action(403, &limited, 100),
            Action::Retry(Failure::RateLimited, Some(Duration::from_secs(31)))
        );
        let mut github = GitHub::new().unwrap();
        github.deadline = Instant::now();
        assert_eq!(
            github.pause(Duration::from_secs(1), Failure::RateLimited),
            Err(Failure::RateLimited)
        );
        let mut output = vec![9];
        assert_eq!(
            copy_bounded(
                &mut std::io::Cursor::new(b"abc"),
                &mut output,
                2,
                Instant::now() + Duration::from_secs(1)
            ),
            Err(Failure::Malformed)
        );
        assert_eq!(output, vec![9]);
        assert_eq!(
            copy_bounded(
                &mut std::io::Cursor::new(b"abc"),
                &mut output,
                3,
                Instant::now()
            ),
            Err(Failure::Offline)
        );
        output.reset().unwrap();
        assert!(output.is_empty());
    }
    #[test]
    fn notification_budget_does_not_shorten_scheduled_discovery() {
        let ordinary = GitHub::new().unwrap();
        let notification = GitHub::notification().unwrap();
        assert!(ordinary.remaining().unwrap() > Duration::from_secs(500));
        assert!(notification.remaining().unwrap() <= Duration::from_secs(15));
    }
    #[test]
    fn real_http_stream_preserves_original_length_and_rejects_truncation() {
        use std::net::TcpListener;
        fn response(bytes: &'static [u8]) -> reqwest::blocking::Response {
            let listener = TcpListener::bind("127.0.0.1:0").unwrap();
            let address = listener.local_addr().unwrap();
            let server = std::thread::spawn(move || {
                let (mut stream, _) = listener.accept().unwrap();
                stream
                    .set_read_timeout(Some(Duration::from_secs(2)))
                    .unwrap();
                let mut request = Vec::new();
                let mut buffer = [0u8; 1024];
                while !request.ends_with(b"\r\n\r\n") {
                    let count = stream.read(&mut buffer).unwrap();
                    assert!(count > 0);
                    request.extend_from_slice(&buffer[..count]);
                    assert!(request.len() <= 4096);
                }
                stream.write_all(bytes).unwrap();
            });
            // Loopback HTTP is confined to this private test fixture. Production
            // routing still rejects it and has no endpoint override.
            let response = Client::builder()
                .no_proxy()
                .timeout(Duration::from_secs(2))
                .build()
                .unwrap()
                .get(format!("http://{address}/fixture"))
                .send()
                .unwrap();
            server.join().unwrap();
            response
        }
        let mut output = Vec::new();
        let complete =
            response(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nabc");
        assert_eq!(complete.content_length(), Some(3));
        receive_response(
            complete,
            &mut output,
            3,
            Instant::now() + Duration::from_secs(2),
        )
        .unwrap();
        assert_eq!(output, b"abc");
        output.reset().unwrap();
        let chunked = response(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n3\r\nabc\r\n0\r\n\r\n");
        assert_eq!(chunked.content_length(), None);
        receive_response(
            chunked,
            &mut output,
            3,
            Instant::now() + Duration::from_secs(2),
        )
        .unwrap();
        assert_eq!(output, b"abc");
        output.reset().unwrap();
        let truncated =
            response(b"HTTP/1.1 200 OK\r\nContent-Length: 4\r\nConnection: close\r\n\r\nabc");
        assert!(matches!(
            receive_response(
                truncated,
                &mut output,
                4,
                Instant::now() + Duration::from_secs(2)
            ),
            Err(RequestError::Retry(Failure::Offline, None))
        ));
        output.reset().unwrap();
        let oversized =
            response(b"HTTP/1.1 200 OK\r\nContent-Length: 3\r\nConnection: close\r\n\r\nabc");
        assert!(matches!(
            receive_response(
                oversized,
                &mut output,
                2,
                Instant::now() + Duration::from_secs(2)
            ),
            Err(RequestError::Abort(Failure::Malformed))
        ));
        assert!(output.is_empty());
    }
    struct Pages(Vec<Result<Vec<u8>>>);
    impl Transport for Pages {
        fn get(&mut self, _: &str, _: u64, out: &mut dyn Sink) -> Result<()> {
            out.write_all(&self.0.remove(0)?).unwrap();
            Ok(())
        }
    }
    #[test]
    fn pagination_and_failures_never_report_current() {
        let full = serde_json::to_vec(&vec![serde_json::json!({"tag_name":"legacy", "draft":false, "prerelease":false, "assets":[]}); 100]).unwrap();
        let mut p = Pages(vec![Ok(full.clone()), Ok(serde_json::to_vec(&vec![serde_json::json!({"tag_name":"v1.10.0","draft":false,"prerelease":false,"assets":release("v1.10.0").assets.iter().map(|a|serde_json::json!({"name":a.name,"size":a.size,"browser_download_url":a.browser_download_url})).collect::<Vec<_>>()} )]).unwrap())]);
        assert_eq!(
            discover_with(&mut p, "1.2.1", "linux-amd64")
                .unwrap()
                .unwrap()
                .version,
            "1.10.0"
        );
        assert_eq!(
            discover_with(
                &mut Pages(vec![Ok(full); MAX_PAGES]),
                "1.2.1",
                "linux-amd64"
            )
            .unwrap_err(),
            Failure::Incomplete
        );
        for failure in [Failure::Offline, Failure::RateLimited, Failure::Incomplete] {
            assert_eq!(
                discover_with(&mut Pages(vec![Err(failure)]), "1.2.1", "linux-amd64").unwrap_err(),
                failure
            );
        }
        assert_eq!(
            discover_with(&mut Pages(vec![Ok(b"{}".to_vec())]), "1.2.1", "linux-amd64")
                .unwrap_err(),
            Failure::Malformed
        );
    }
}
