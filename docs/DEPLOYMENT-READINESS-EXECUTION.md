# Deployment readiness execution record

**Current checkpoint — October 25, 2026:** owner-accepted **v1.2.17** is
stable/latest, release423797225/source7de6d29. Full/native/exact-main/signing,
independent authentication, both focused desktop passes, explicit stable approval,
immutable metadata promotion and public downloads are complete.
[Release/promotion receipt](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/104#issuecomment-6407525155); [current evidence ledger](RELEASE-EXECUTION-1.2.17.md).
#102 and #59 are closed. #99 awaits retained14 live discovery. #43/milestone2
remain open for the separately scoped real automatic pilot or explicit owner
scope disposition. No device/fleet change is authorized by release visibility.

Earlier dated checkpoints below are chronological history; their pending states
are superseded only within the actual scope recorded in the current ledger.

**October 24 update:** v1.2.15 owner desktop UAT passed on both selected platforms.
#59 is closed with explicit owner acceptance of the historical affected-PC pass
plus native fixtures and the unreported additional-PC/private-ACL evidence limit.
The owner selected v1.2.16 for #102 and the student-accessible Inline toggle.
See the [current execution ledger](RELEASE-EXECUTION-1.2.16.md). Earlier dated
checkpoints below remain historical; no stable promotion or pilot is inferred.

Updated October 21, 2026. Scope: milestone 2, #59 and #43; cross-cutting live
transition #99 stays in Part 2. This record distinguishes completed evidence,
engineering work and pending owner decisions. The supplied release plan is a
handoff, not evidence of approval or device authorization.

| Gate | Actual state / next action |
| --- | --- |
| Starting source | Clean clone of official remote; main `b0f6a43e85b8ae5bbf72b87b4ee5f2d92bfd40ba`; no unrelated work changed |
| Branch / PR | `codex/deployment-readiness-1.2.15`; PR preparation in progress |
| Stable / source / release ID | Live read October 21: v1.2.14, same source, release `418991149`, nondraft/non-prerelease; five API asset identities match [PR #98 receipt](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/98) |
| Fresh target | v1.2.15 absent from cloned tags and live release listing at kickoff; recheck exact tag/release before dispatch and publication; not reserved |
| Scope of changes | Current operational documentation and fixed 1.2.14/1.2.15 disposable native preparation; no demonstrated migration defect requiring a production rewrite |
| Test-machine inventory | Owner inventory received privately: Windows 11 and Mint daily PCs currently v1.2.14 reserved in proposed allocation; fresh Windows test PC and existing Mint v1.2.12 test PC available for separate candidate UAT; physical/VM and exact Mint desktop/version confirmation pending |
| Private/representative observations | Requested; school network/student accounts, additional affected PCs and reboot/natural firing evidence pending |
| Pilot allowlist / window / actions | None authorized. Complete [pilot packet](SELF-UPDATE-PILOT.md) before device-changing approval |
| Local checks | 22 local identity/CI-scope/metadata/stable-download tests and 6 backend contracts passed; PowerShell parser, actionlint 1.7.7, workflow/Mint Bash syntax, current stable JSON contract, document links and whitespace passed. Full native/trust CI pending; see receipts below |
| PR/full exact-main/native checks | Not run for this change; historical passing runs below are supporting evidence only |
| Reviewed head / merged main | Pending |
| Candidate workflow | `prepare-self-update-uat.yml`, `release/v1.2.uat`, `deployment_readiness=true` after reviewed merge, exact-main CI and fresh-tag checks |
| Signing protections | Live CLI verification October 21: required human reviewer `rdpollard`, `can_admins_bypass=false`, custom refs limited to tag `v1.1.*`/`v1.2.*` and branch `release/v1.1.*`/`release/v1.2.*`; both expected signing secret names present; no values read |
| Backup | Owner confirmation October 12 is recorded in [signing guide](SELF-UPDATE-SIGNING.md); no key/configuration change proposed |
| Signing input receipt / approval | Pending real native builds; record source, CI, run and both artifact IDs/sizes/digests before human review |
| Published candidate / authentication | Not published; five-asset receipt pending; no hashes fabricated |
| Owner target acceptance / limits | Not run for v1.2.15; [focused sheet](SELF-UPDATE-UAT.md) ready only after authenticated handoff |
| Stable promotion / public links | Not authorized for v1.2.15; prepare exact accepted candidate and unchanged asset receipt first |
| #99 Windows / Mint live transition | Not run; requires retained v1.2.14 and independently accepted newer stable; do not upgrade both starting devices for candidate UAT |
| Pilot app/tool/recovery/preservation/final policy | Not run; separate device authorization pending |
| Closeout | #59/#43/#99 remain open. Live CLI confirms milestone 2 open, exactly #59/#43 assigned and open |
| Access blocker | Resolved: owner completed CLI browser/device authentication; elevated CLI access works. Sandbox CLI cannot access authentication reliably, so network/authenticated operations use approved elevation. Connected GitHub provided read-only kickoff evidence; live CLI issue/main/tag/environment/milestone reads now confirm it. No failed or partial publication exists |

## Reused evidence and its limits

- [PR #60](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/60),
  merged `741f681c0444a8d44d9430a107c80f2fed95b68e`: implemented the narrow
  Logs migration shipped in v1.2.6. [Native run 38586204871](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38586204871)
  covers exact inherited grants, preserved bytes/private ACLs, baseline/policy,
  disabled custom task, SYSTEM installation, trust failures and student denials.
- [PR #61](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/61)
  and [October 14 chronology](SELF-UPDATE-UAT-1.2.5.md): owner affected-PC v1.2.6
  first-attempt installation without manual correction; GUI Update/Validate and
  separate controlled SYSTEM maintenance passed. Baseline 1.2.1, tool exit 0,
  paused app outcome; no native app installation occurred in that maintenance run.
  The v1.2.5 pass after manual remediation is a separate historical result.
- [v1.2.14 owner UAT](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/98#issuecomment-6316233401)
  and [acceptance/promotion receipt](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/98#issuecomment-6316392711):
  accepted Windows/Linux identity, baseline/pause/schedule/preferences/icons,
  readiness/discovery/offline/retry, tool preview/preflight and sidebar/zoom.
  Tool Update was reported jointly without per-platform detail; screen readers
  as available without exact configuration; no actual PowerShell metadata drift.
- v1.2.14 [exact-main full CI](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39512594151)
  and [protected native pair/sign/publication](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39512598219)
  passed. These are not v1.2.15 results. Same-source rebuilt 1.2.14 fixtures will
  be unpublished test inputs, not the published v1.2.14 bytes.

## #59 criterion-by-criterion reconciliation

Numbering follows the live issue's ten acceptance bullets. “Pass” below is scoped
to the named historical source/test; final owner disposition is still pending.

| Criterion | Evidence / status | Remaining owner disposition or genuine gap |
| --- | --- | --- |
| 1. Exact parent plus Logs; existing log; no external repair | Pass: #60 real SYSTEM package fixture; v1.2.6 affected Windows 11 first-attempt owner result | Reuse; do not recreate insecure permissions on real PCs |
| 2. Normal administrator installation | Pass for supported layout in #60 and owner v1.2.6 | Extent across reported additional affected PCs not supplied |
| 3. Logs safety contract | Pass: `Assert-LegacyLogsDirectory`, file guards and mentor migration section; flat named single-link protected files only; contents never executed/authenticated | Keep old diagnostic logs separate from protected status/history |
| 4. Trust enforcement | Pass: bootstrap/worker retain owner/writer/link checks; writable privileged inputs rejected | No rewrite justified by open ticket wording |
| 5. Narrow mutation and preservation | Pass in native fixtures: log bytes/private ACL, baseline script/version, disabled Friday 04:35 task, pause bytes; owner v1.2.14 reports broader preferences/baseline/pause/schedule preservation | Real-PC pre/post legacy log/private ACL/baseline-byte inventories were not reported; require evidence or explicit accepted limitation |
| 6. Unsupported/concurrent fail-closed behavior | Pass: `Test-LegacyMaintenanceAclCI.ps1`; file/writer/addition/link/owner/grant cases; bounded scans and revalidation | Repeat through required fresh CI; no laptop fault injection |
| 7. Idempotence/interruption/retry | Pass: native already-protected, empty/multiple logs, partial Logs protection retry and guards | Current CI pending; no forced real-PC interruption |
| 8. Disposable native coverage and student denial | Pass: #60 native markers and `Test-SelfUpdateReadAccessCI.ps1`; current full CI retains these | Fresh exact-source CI pending |
| 9. Representative Windows 11 retest and separate outcomes | Historical owner v1.2.6 install, GUI Update/Validate and controlled SYSTEM maintenance pass; current v1.2.14 acceptance supports regressions | Additional affected-PC scope, reboot/natural firing and exact unreported preservation limits need owner disposition before #59 closure |
| 10. Migration/security/UAT documentation | Existing #60/#61 contract and chronology retained | Current release instructions are being corrected here |

## #43 criterion-by-criterion reconciliation

| Criterion | Evidence / actual state | Remaining gate |
| --- | --- | --- |
| 1. Complete signed Windows/Mint candidates | Prior distributions authenticated; current recipe prepared | New real native builds, signing approval, publication and independent five-asset authentication |
| 2. Concise UAT covering install/deferral/preservation/policy/failures/maintenance | Current [UAT sheet](SELF-UPDATE-UAT.md) and [pilot packet](SELF-UPDATE-PILOT.md); native failure tests retained | Owner observations per platform; device-changing steps only within approved scope |
| 3. Controlled two-version real install without exposing unaccepted stable | Existing native pair mechanism; fresh unpublished 1.2.14/1.2.15 packages; candidate prerelease only | Fresh native run and separate desktop UAT; retained actual v1.2.14 for later stable transition/pilot |
| 4. Immediate checks | Installed `check`/status separate from actual existing maintenance trigger | Owner window for any trigger; trigger may update real tools |
| 5. Explicit owner UAT | v1.2.14 accepted for its scope; v1.2.6 historical statement retained | Exact new candidate Windows/Mint acceptance and limits |
| 6. One-time migration/future eligibility | [Rollout guide](SELF-UPDATE-ROLLOUT.md), mentor guide and compatibility contract | Apply only to approved devices; incompatible baseline needs separately authorized Repair |
| 7. Signing prerequisites/backup | October 12 backup confirmation retained; no key change | Live protection/ref/secret-name check and human signing approval |
| 8. Representative rollout with pause/recovery | Runbook identifies allowlist, before/after, open/idle paths, stops and final policy | No pilot authorization/results; #43 stays open unless required pilot completes or owner explicitly revises scope with follow-up |
| 9. App versus baseline | Source bootstrap and native tests retain 1.2.1 baseline; app identity remains disposable | Observe preserved baseline separately during UAT/pilot |
| 10. Current accurate documentation | Historical chronology retained; current sheets/notes/matrix updated here | Keep receipts current after each gate |
| 11. Explicit stable approval | New target remains unapproved; signing and old acceptance do not authorize promotion | Exact-target owner promotion disposition after UAT |

## Execution receipts

No v1.2.15 tests, signing, publication, owner acceptance, promotion, pilot or
closure has occurred at kickoff. Append actual results here as gates finish.

### Local verification / environment limits

- 22 tests passed: `test_uat_version.py`, `test_ci_scope.py`, `test_metadata.py`,
  `test_stable_downloads.py`; 6 backend contracts passed. Candidate identity test
  includes 1.2.15 and verifies unchanged Rust/npm dependency records and baseline.
- Initial tests hit the sandbox temporary-directory ACL restriction; reran with
  TEMP/TMP in the authorized workspace successfully. No product fix was required.
- Linux-only preflight test was attempted on Windows and cannot use `os.major`;
  leave native Linux coverage to required CI, not an invented local pass.
- PowerShell parser accepted the modified native probe. Git Bash cannot initialize
  its named objects inside the sandbox; shell syntax/actionlint verification is
  being completed outside that boundary. Native scripts were not executed here.
- Live main remains kickoff source and `git/matching-refs/tags/v1.2.15` returns
  zero; only open PR at kickoff is excluded draft #73, left untouched.

- CI-pinned actionlint 1.7.7 passed both modified workflows; downloaded official
  validator archive matched its published checksum. Mint probe and every extracted
  workflow Bash block passed syntax-only checks outside the sandbox.
- README plus live v1.2.14 latest-release JSON passed `tests/stable_downloads.py`;
  local links and `git diff --check` passed. No UI or production trust code changed.
- Self-review covered current recipe/ref/input, disposable identity/lock preservation,
  native package expectations, protected human signing scope and immutable
  prerelease-only publication. Branch protection enforces administrators; required
  approving-review count is zero, no status contexts configured and no rulesets.
  Regardless, this execution requires all full/native checks before merge.
