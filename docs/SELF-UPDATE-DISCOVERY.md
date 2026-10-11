# Approved release discovery and staging (#37)

This component checks for an approved SDE application update and stages a verified
installer. It never executes the installer, launches the GUI, changes the
provisioning baseline, provisions student tools, schedules a task, or promotes a
release. The signing workflow still creates prereleases; those remain invisible
to production discovery until the owner explicitly approves promotion.

## Maintenance interface

The protected maintenance host can invoke its reviewed, administrator-owned
`sde-update-trust` binary with one of these commands:

- `check`: query release listings only; no installer or metadata download.
- `stage`: query release listings, authenticate metadata, download and verify the
  matching installer, and leave a fresh protected transaction for a later installer.

Neither command accepts a version, repository, key, platform, staging root, or
URL argument. Maintenance gets its installed application version from the native
package record. Windows uses the 64-bit HKLM NSIS uninstall record for
`Skyview Dev Setup`, requires its executable under `C:\Program Files`, verifies
protected path ownership/ACLs, and cross-checks its product version. Linux uses
`/usr/bin/dpkg-query` for the installed `skyview-dev-setup` package and requires
`amd64`. Unknown, missing, noncanonical or inconsistent identity fails closed.
The supported hosts are native x64 Windows 11 workstations and Mint 22.x amd64;
unsupported hosts get an explicit outcome before network access.

Each command prints one JSON report with `checkedAt` (UTC Unix seconds), `status`,
and optional `candidate`, `failure`, and `transaction` fields. Successful checks
exit 0; unavailable checks exit 2. Reports do not contain credentials, redirects,
CDN signed query strings, response bodies, private keys or caller-supplied paths.

| Status | Meaning |
| --- | --- |
| `current` | A complete successful release scan found no newer shared stable release. |
| `available` | A newer published stable release has the required official asset identities. It has not yet been authenticated or downloaded. |
| `staged` | Signed metadata and this platform's installer passed authentication and integrity checks in protected storage. Nothing was installed. |
| `unavailable` | The check or staging failed. `failure` distinguishes `offline`, `rateLimited`, `malformed`, `incomplete`, `untrusted`, `unsupported`, `invalidInstalled`, `staging`, and `cleanup`. Never interpret this as current. |

## Shared selection for #11

`discovery::discover(installed_version, platform)` queries release listings and
returns a candidate or a typed failure. `discovery::select` exposes the same pure
selection policy for already fetched listings. A future notification UI (#11)
should supply Tauri's actual running package version (`app.package_info().version`),
not its applied provisioning baseline or a hardcoded constant. It must use its
supported platform identity, display unavailable checks honestly, and must not
call the privileged staging path simply to display an update notice.

Only `stormbots/Tactics-Strategy-Dev-Environments` is queried. The selector ignores
drafts, prereleases, prerelease/build tags and legacy `windows-v…`/`linux-v…` tags.
Canonical `vMAJOR.MINOR.PATCH` tags are compared with semantic-version ordering.
Equal or older releases are never selected. The highest newer stable candidate
must have one metadata file, one signature, and exactly one matching installer
asset with the expected official download URL and bounded nonzero size. A
missing, duplicate, malformed or untrusted asset on that candidate fails the
check; it does not enable fallback to an older release.

## Network boundaries

- The fixed GitHub releases API is paged with 100 entries per page, at most 10
  pages, with at most 4 MiB per page. A full final page returns `incomplete` because
  the bounded scan cannot establish the highest version or that the app is current.
- HTTPS is required. Ambient proxies are disabled. Requests carry no credentials.
  Redirects are inspected before sending, limited to five per attempt, and release
  downloads can redirect only to `release-assets.githubusercontent.com` under
  `/github-production-release-asset/`. API redirects and unrelated GitHub routes,
  other hosts, credentials, nonstandard ports and fragments are rejected.
- Each request has a 10-second connection limit and at most a 30-second overall
  timeout. The entire discovery/download operation has a 10-minute deadline.
- Transient connection, body-read, timeout, HTTP 408 and server failures get at most
  two retries with 1/2-second backoff. Partial output is truncated before each retry.
  Rate limits wait only when GitHub provides a numeric retry/reset delay that fits
  the remaining deadline; otherwise the report is `rateLimited`. No infinite waits.
- Metadata is limited to 64 KiB, signatures to 8 KiB, and installers to 512 MiB.
  Installer output also cannot exceed its signed declared size. Streaming avoids
  loading an installer into memory. Unexpected HTTP partial content is rejected.

## Protected staging and installer handoff

Staging requires root on Linux or an elevated administrator/SYSTEM on Windows.
Its root is fixed: `/var/lib/skyview-robotics/self-update/staging` or
`C:\ProgramData\SkyviewRobotics\SelfUpdate\staging`. Linux validates root ownership,
rejects group/other write permissions and symlinks, and creates directories 0700
and exclusive files 0600 with no-follow. Windows validates ownership and DACLs,
rejects reparse points, and creates protected noninheriting owner/ACL descriptors
restricted to SYSTEM and Administrators. System anchors are checked against
unprivileged deletion/ACL replacement; ordinary folder-creation rights on
ProgramData do not grant access to a protected child.

A UUID transaction contains fixed filenames:

1. `sde-update.json` and `sde-update.json.minisig`: close/flush their bounded
   downloads and authenticate the exact metadata bytes with the compiled public
   key before interpreting installation fields.
2. The platform's named installer: verify the GitHub declared size agrees with
   signed metadata, stream to an exclusive file, close/flush, then verify its full
   signed length and SHA-256.
3. `verified.json`: written last, containing the transaction, release tag,
   version, platform, filename and verification timestamp. A marker alone is
   never permission to execute.

An ordinary failed transaction removes only its own known files and empty
transaction directory. Cleanup failure is explicit. An abruptly killed process
can leave an incomplete transaction with no valid completed marker; such a
transaction is never eligible. Existing verified or interrupted transactions are
not recursively deleted by discovery. Safe orphan retention/recovery belongs to
#41.

The future #39/#40 installer must acquire the maintenance lock (#38), re-check
current native installed identity and supported host, reconfirm stable release
eligibility, reauthenticate preserved metadata/signature, and reverify the
installer immediately before use while retaining protected storage. It must not
trust this receipt alone or accept an arbitrary user path. Scheduling, durable
maintenance history and installation/reboot decisions are outside #37.

## Automated verification and UAT

CI runs the trust/discovery tests, Rust formatting/static analysis, and verifier
build on Windows and Linux. Linux additionally runs staging tests as root with
`SDE_REQUIRE_PROTECTED_STAGING=1`, so these tests cannot silently skip. Windows
runs real protected ACL/exclusive-file/junction checks. Fixtures use ephemeral
keys and inert bytes; no production key signs test fixtures and no installer runs.

Tests cover semantic ordering, drafts/prereleases/legacy/equal/older tags,
incomplete newest candidates, wrong URLs and unsupported platforms, pagination,
offline/rate-limit/malformed outcomes, redirects, HTTP status policy, deadlines,
stream limits, altered signatures/metadata, wrong key, tampered/truncated installers,
protected files and cleanup, plus native Minisign interoperability on Linux.

Owner UAT later uses a Windows 11 x64 laptop and a Mint 22.x amd64 laptop to confirm
native package identity and the final scheduled update flow. An approved newer
signed stable release is needed for a live successful stage; candidate prereleases
must continue to be ignored until explicit approval. #42 covers classroom rollout
and end-to-end acceptance; do not promote a release just to test this component.
