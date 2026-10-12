# Self-update verification and UAT handoff (#42)

This report describes the required verification gates. Observed results and links
for the current commit belong in its pull request and Actions run; a prior green
run is not proof that a changed commit passed. #43 owns school-laptop UAT and owner
release approval. Production installation remains paused; candidate releases stay
prereleases. Nothing in this test suite authorizes promotion or enables laptops.

## Automated evidence

The test-only `updater/src/e2e.rs` fixture routes official-shaped GitHub release
URLs to in-memory responses and signs metadata with fresh ephemeral keys. It is
compiled only with `cfg(test)`. Production has no injected endpoint/key option.
No fixture release or tag is published; the pinned production key rejects every
test signature. The fixture tests actual discovery, metadata authentication,
installer hash/length checks and private staging, rather than reproducing their
logic. The transport does not prove live GitHub availability or TLS/CDN behavior.
Existing real HTTP stream tests independently exercise complete, chunked and
truncated transfers; URL policy and retries have separate tests.

| Scenario | Evidence |
| --- | --- |
| No update / equal or older version | Shared fixture discovery returns no candidate; native repeat installation returns current without a native exit |
| Prerelease / draft / changed eligibility | Shared discovery ignores candidates; eligibility recheck after staging observes a promotion reversal |
| Missing assets | Shared discovery rejects an incomplete newer release, with no fallback to an older release |
| Offline listing | Shared fixture returns offline; no current result or staged transaction is produced |
| Interrupted transfer | Partial sink writes at metadata, signature and payload phases return failure; recognized files and directory are removed; a clean retry stages successfully |
| Corrupted metadata, signature or payload | Each is changed independently; authentication/staging fail and leave no verified transaction |
| Test-key rejection | Production pinned verifier rejects ephemeral fixture signatures; native retained recovery verification rejects test evidence |
| Status semantics | Strict bounded receipts, six UI outcomes, missing history, current pause versus old results, independent tool failures and interrupted coordination |
| Coordination | Native session and maintenance leases defer installation; cross-process coordination tests cover crash release and durable intent |

Linux protected-staging/E2E tests **require root** in CI using
`SDE_REQUIRE_PROTECTED_STAGING=1`. Ordinary developer runs skip these tests if not
root; a printed `ok` on such a run is not protected-staging evidence. Native tests
also skip without their disposable fixture variables. CI launch scripts enforce
privilege, execute exact native test names and require success markers. Windows
protected-file tests run on the administrator runner; actual installation runs as
SYSTEM. No security validation is disabled for test convenience.

## Native evidence

Required Windows and Mint jobs build both the normal package and an unpublished
newer package. The native test consumes a controlled release listing, downloads
signed metadata and the **real** installer through the test transport, authenticates
and stages it through production code, rechecks eligibility, obtains real
coordination leases, installs and verifies native/resources/engine state. It then
publishes the resulting receipt and reads it through the same reader used by the
GUI. The ordinary packaged maintenance launcher is exercised on its next run.

These tests compose the production components with a test transport/key. They do
not fetch a stable fixture from live GitHub or run the entire networked supervisor
against it. Test-only composition is necessary to avoid publishing an unaccepted
version or sharing production signing credentials with tests. Windows Server is
intentionally unsupported by production discovery; native installer tests use
native identity checks without relaxing that OS gate.

| Native assertion | Windows SYSTEM / NSIS | Mint root / APT + DPKG |
| --- | --- | --- |
| Successful app upgrade | Actual NSIS process, installed registration/file version and bundled/active engine resources | Actual APT execution, package identity and bundled/active engine resources |
| Stale interrupted download | Known unretained partial UUID transaction pruned under operation gate before retry | Same |
| Active GUI / concurrent maintenance | Both native leases defer without native launch | Both leases defer; additional real DPKG lock defers |
| Pause isolation | Admin round-trip changes policy only; next tool action still runs | Same, through installed packaged launcher while paused |
| Student preservation | Project sentinel and `.vscode/settings.json` unchanged | Project sentinel and Code user settings unchanged |
| Baseline separation | Deployed tool script and customized disabled task preserved; app-only bootstrap creates neither baseline nor task | Deployed tool script and custom timer preserved; app-only bootstrap creates no baseline/service |
| Next maintenance invocation | Committed newer engine runs held-lease snapshot of existing tool generation; independent tool result succeeds | Same, plus applied baseline stays at its older version |
| Native failure | Signed synthetic executable exits 23; durable intent blocks retries; failed status cannot conceal interruption | Real DEB postinst fails; partial DPKG state and intent block retry; failed status retains interruption |
| Repeat/older candidate | Native selector returns current before authentication or launch | Same |
| Student permissions | Actual standard user reads policy/status, cannot mutate them or read/create private receipts | Actual `nobody` reads status; resume denied |

Windows failure uses a synthetic executable, not a deliberately damaged NSIS
installation. Mint failure deliberately leaves DPKG damaged inside the disposable
container; it is not repaired or retried automatically. Windows synthetic intent
is cleared only after its process completed, under the operation gate. This does
not implement a production reset or universal rollback. The recovery guide in
[SELF-UPDATE-MENTOR.md](SELF-UPDATE-MENTOR.md) remains the mentor procedure.

Actions must contain all three new markers: `SDE_E2E_DISCOVERY_STAGING_OK`,
`SDE_E2E_NATIVE_WINDOWS_OK`, `SDE_E2E_NATIVE_MINT_OK`, plus existing native/student
markers. The native job uploads `self-update-evidence-Windows` and
`self-update-evidence-Mint` transcripts. They contain fixture/native results, never
signing keys, passphrases or staging directories. Failed runs retain available
transcripts for diagnosis; artifact presence alone is not proof of success.

## Required repository gates and observed-result reporting

The PR must record its exact tested head and successful Actions run. Required
checks include frontend tests/build/audit, browser accessibility/reflow, backend
and metadata contracts, script/static analysis, Rust tests/format/Clippy,
coordination contracts, protected staging tests and both native builds/installations.
Release publication must be skipped for the issue branch/PR. Do not bypass a gate.

Local results must state skipped privilege/native tests separately. This Codex
host cannot supply root installation, Windows SYSTEM, a booted Mint desktop, or a
school-network session. Native CI supplies installation evidence. Mint 22.3 ISO
userland in a container does not prove systemd timer firing on a booted laptop;
Windows Server 2022 does not prove Windows 11 desktop behavior.

## Remaining owner UAT (#43)

After Codex reviews and merges #42, have Codex prepare the #43 laptop checklist and
an owner-approved signed **prerelease** candidate. Keep automatic production
installation paused throughout testing. Do not promote or resume implicitly.

The owner should validate on representative Windows 11 and Linux Mint laptops:

1. Fresh app-only installation, existing customized schedule preservation, and
   student account status visibility/denied controls.
2. Actual school Wi-Fi, proxy/filtering, offline and reconnection behavior against
   GitHub, plus suitable disk space and power conditions.
3. Open SDE and normal development-tool maintenance contention; saved projects,
   Git settings and editor settings remain intact after an approved manual upgrade.
4. A booted weekly task/timer and next maintenance run use the new engine while
   the older applied baseline remains until deliberate tool provisioning.
5. Mentor pause/resume, readable status, protected logs and documented recovery
   assessment. Never interrupt a live package manager just to create a failure.
6. A classroom pilot before the remaining laptops, explicit acceptance, then
   separately authorize stable promotion and per-laptop resumption.

Codex can prepare, automate and review the checklist and diagnose collected
sanitized evidence. Only the owner supplies school-laptop acceptance and promotion
approval. #8/#10/#11 retain broader recovery UI/notices/notifications; #33 retains
baseline policy. This issue verifies their current integration contracts without
claiming those related stories are complete.
