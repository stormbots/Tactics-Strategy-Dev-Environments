# Self-update acceptance record (#43)

**Owner UAT: Pending. Stable promotion: Not authorized. Classroom resume: Not authorized.**

On 2026-10-12 the owner confirmed the encrypted release key and Bitwarden
passphrase are backed up separately. No secret values or backup paths are recorded
here. USB storage is not required. A later key rotation requires a new recovery
check and owner confirmation.

Signing infrastructure was inspected on 2026-10-12: environment
`sde-release-signing` has reviewer `rdpollard`, administrator bypass disabled, and
both signing secret names configured. Following human environment approval, the
protected candidate workflow successfully signed both distributions, verified them
with the pinned release key, and downloaded and authenticated the published
assets. No signing secrets were exported.

| Evidence | Record |
| --- | --- |
| Native integration before #43 | [PR #51](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/51), exact head c7892980d3e9db0eb5f97be12a04336a938e3666; [successful run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38254978692) |
| Candidate source commit / protected workflow run | `c186e75925e40101e7e36c3d7dfb845e562a017d` ([PR #52](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/52)); [successful protected candidate run](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38266099258); [successful full main CI](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38265778561) |
| Published signed v1.2.2 / v1.2.3 URLs and manifest hashes | [v1.2.2](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.2) and [v1.2.3](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.3); both unaccepted prereleases, hashes below |
| Candidate Windows SYSTEM / actual Mint root pair CI | Passed on the candidate source above in run `38266099258`; both Windows installer exits 0; actual `SDE_UAT_PAIR_WINDOWS_OK` and `SDE_UAT_PAIR_MINT_OK` markers recorded. Versions, paused policy/engine, preserved sample files/settings and legacy baseline checked |
| Windows 11 owner tests and school network | v1.2.5 installation passed on 2026-10-14 after manual remediation; remaining Windows 11 tests and school network pending; [detailed record](SELF-UPDATE-UAT-1.2.5.md#windows-11-installation-uat--october-14-2026) |
| Booted Mint owner tests and school network | Pending |
| Findings and retests | v1.2.5 inherited Logs write grant rejected; targeted administrator ACL correction followed by successful installer retest on 2026-10-14; [diagnosis and follow-up](SELF-UPDATE-UAT-1.2.5.md#deployment-finding-and-engineering-follow-up). Other pending conditions remain open |
| Owner acceptance wording / date / exact target | Pending |
| Explicit stable-promotion authorization / date | Pending |
| Representative pilot results / per-laptop resume | Pending |

Use the [UAT checklist](SELF-UPDATE-UAT.md). Record pass/fail/not-applicable and
reason for each row on each OS, identifying the exact assets tested. Codex may
record the owner's supplied results but must not infer or manufacture acceptance.
Existing acceptance of archived 1.2.1 applies only to that historical release.

## Published candidate verification (2026-10-12)

Both tags point to the exact source commit above. Each release contains exactly
the five canonical assets. After publication, Codex independently downloaded
both complete asset sets, rebuilt the verifier from that reviewed source, and
verified both metadata signatures and both platform installer hashes per release.
SHA256SUMS.txt also passed. A modified metadata copy was rejected for each
version. These checks authenticate the distributions; they do not establish
owner laptop acceptance. Latest stable remains historical v1.2.1.

| Version | Asset | SHA-256 |
| --- | --- | --- |
| 1.2.2 | sde-update.json | `8e76f362b250d954ef502255596f0faa9f70b6da05331a80a63e011b1a4a1e0b` |
| 1.2.2 | Skyview-Dev-Setup-Windows-x64.exe | `c6e64e6042a02572f68e6bc86f151db6955a02fa65b56ae68ff1f98fef09de96` |
| 1.2.2 | Skyview-Dev-Setup-LinuxMint-amd64.deb | `a253724ea358675ab7701d9c2a142f341891e5437b8b5e24de63e610eb5ef1d6` |
| 1.2.3 | sde-update.json | `2272e0dbca6f2354d4aab6a25c47ef709dc46869a8d88787cd34eeb32e8483d1` |
| 1.2.3 | Skyview-Dev-Setup-Windows-x64.exe | `8e86072ad942e320fc9ee180109446003e9724a1749a38334c2df8e939e455a3` |
| 1.2.3 | Skyview-Dev-Setup-LinuxMint-amd64.deb | `303f820d79da391eac7fc9e72d0a9c26319e50339e98acb2bb44dd5fb7f78716` |

## Windows 11 v1.2.5 installation result (2026-10-14)

**PASS — Successful installation with manual remediation required.** The owner
confirmed successful installation on Windows 11 x64 with development-tool
baseline v1.2.1 after the first attempt failed protected maintenance bootstrap.
The [version-specific UAT record](SELF-UPDATE-UAT-1.2.5.md#windows-11-installation-uat--october-14-2026)
preserves the supplied diagnostics, inherited Users write grant on Logs,
targeted ACL correction, retained log and successful retest.

This is an installation-only pass after administrator intervention, not a clean
unattended pass or overall owner acceptance. Subsequent application validation,
scheduled-maintenance verification and automatic-update policy verification
have not been reported. All other pending acceptance conditions remain open.
No unattended student-fleet installation, automatic application-update rollout,
stable promotion or closure of outstanding Windows 11 acceptance tests is
authorized. Keep application updates paused. Prior version-specific acceptance
and published verification evidence remain unchanged.

## v1.2.6 candidate verification (2026-10-14; owner UAT pending)

The [immutable signed v1.2.6 prerelease](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.6)
contains the #59 Logs migration from merged PR #60, source
`741f681c0444a8d44d9430a107c80f2fed95b68e`. Exact-main CI and protected
[candidate run 38608215787](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38608215787)
passed, including Windows SYSTEM/Mint version-chain checks and signed published
asset authentication. Independent downloaded hashes matched the published
checksums, manifest entries and GitHub digests. Windows installer SHA-256:
`15b29e9a3f50787ed05734faf0b480b48825bd88fff349ad944bab72bf2fa690`.

See the [candidate identity, verification evidence and affected-PC checklist](SELF-UPDATE-UAT-1.2.5.md#affected-pc-windows-11-checklist-for-reviewed-commit-7281331).
This completes candidate preparation only. Affected Windows 11 first-attempt
installation without manual remediation, preservation, application, maintenance
and paused-policy checks remain pending. Per-PC pinned verification is required.
Keep application updates and broader rollout paused, #59 open, and all existing
owner acceptance, school-network, automatic-install/recovery and stable-promotion
gates intact. The historical v1.2.5 manual-remediation pass is unchanged.

## Affected Windows 11 v1.2.6 owner result (2026-10-14)

**PASS — Successful installation without manual remediation (owner-reported).**
The owner explicitly confirmed an affected laptop with the failing legacy Logs
permissions installed v1.2.6 on the first attempt without manual ACL correction.
Subsequent GUI development-tool Update reached completion with zero failed
validation checks, retained Node 24.x pinning/Python 3.14.x and reported preserved
editor settings. Pending-reboot and Chocolatey dependency warnings remain in the
[chronological evidence record](SELF-UPDATE-UAT-1.2.5.md#affected-windows-11-owner-retest--october-14-2026).

This is an owner-reported installation pass and interactive Update/validation
result, not completed candidate acceptance. Per-PC artifact authentication,
log/baseline/data/ACL/schedule preservation, app/engine identity, actual paused
policy, scheduled execution and post-reboot evidence remain pending. Keep #59
open and broader rollout/application updates paused; prior acceptance history and
all other release gates remain unchanged.

The owner subsequently supplied standalone GUI Validate output: **PASS**, with
31 passing checks, 2 optional/unconfigured informational checks and zero failures.
Reported tool versions match the preceding Update output. Reboot completion was
not explicitly confirmed; paused application-update policy, app/engine identity,
preservation and actual scheduled execution still require separate evidence.
See the chronological standalone Validate entry in the same UAT record.

The subsequent Schedule page confirms **open app v1.2.6 and application-update
installation paused by administrator**. The weekly Sunday 03:00 task is enabled
and shows historical Scheduler success (`0x00000000`); pre/post preservation and
successful execution with the new engine are not established. Attempt history,
observed installed identity, engine/baseline, tool/native results and signed
recovery remain unavailable/unrecorded. Missing history after manual bootstrap
is allowed, but requires distinguishing absent history from unreadable/invalid
state. See the chronological Schedule observation for displayed local times,
limits and next inspection. Broader rollout and the remaining gates stay paused.

Administrator read-only inspection subsequently confirms the task action targets
the protected SelfUpdate launcher under SYSTEM/Highest, and the installed worker
reports `paused=true`, `coordination=idle`. Those observations pass; attempt
history/engine/baseline/tool/native results remain unavailable and do not establish
a completed invocation. The controlled existing-task run and remaining
preservation/reboot checks are still pending.
