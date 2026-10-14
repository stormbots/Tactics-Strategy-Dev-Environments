# SDE 1.2.5 permission-migration candidate

This signed prerelease contains the Windows legacy parent-permission migration
merged in PR #55 and the Linux history correction accepted in 1.2.4 UAT.
Existing releases and assets remain immutable. App/engine identity is 1.2.5;
the development-tool baseline remains 1.2.1. Keep application updates paused.
No stable promotion or classroom resume is authorized by candidate publication.

## Included correction and validation

An elevated application installation can remove the reported legacy BUILTIN
Users Write grant from the fixed Skyview ProgramData parent, including its
container-inherited form, only when existing descendants are already protected.
It pins the directory during validation/migration, preserves private child
permissions and baseline contents, and rejects broader grants, writable files,
links and unexpected owners. Unknown layouts still require mentor review.
The unattended worker continues to reject an untrusted parent; its trust checks
are not bypassed to perform this migration.

CI reproduces the owner's legacy DACL for actual SYSTEM application installation,
then tests the protected signed native upgrade, customized task preservation and
student write denial. Candidate CI additionally upgrades native Windows and Mint
packages through 1.2.2, 1.2.3, 1.2.4 and 1.2.5 without changing the tool baseline.
Private signing keys remain in the existing protected signing environment.
Only new 1.2.5 assets are published; earlier builds are unpublished CI fixtures.

## Owner candidate verification

Download all five release assets into a separate v1.2.5 folder on each known-good
PC. Verify the complete folder using the installed pinned worker and tag v1.2.5.
Keep both PCs at their accepted 1.2.4 version and application policy paused until
the automatic pilot plan is approved. Do not recreate writable legacy permissions
on the owner PCs; the adversarial migration tests belong on disposable CI runners.
Windows browser download warnings remain separate from Minisign verification.

## Windows 11 installation UAT — October 14, 2026

**PASS — Successful installation with manual remediation required.**

Owner-reported test: Windows 11 x64, SDE v1.2.5, development-tool baseline
v1.2.1. The first attempt failed; this is not a clean, unattended installation
pass. This record preserves prior acceptance decisions and CI evidence.

### Initial failure and diagnosis

The installer stopped during protected maintenance bootstrap with:

```text
SDE maintenance bootstrap failed; mentor review is required.
```

Diagnostic output:

```makefile
coordination=0
maintenance=1
Untrusted maintenance writers.
native64=True
```

Coordination initialization succeeded, but maintenance bootstrap rejected an
existing NTFS permission configuration. Inspection of
`C:\ProgramData\SkyviewRobotics` found this inherited write grant:

```text
BUILTIN\Users:(I)(CI)(WD,AD,WEA,WA)
```

A recursive ACL inspection identified one descendant with an untrusted
effective write permission:

```yaml
Path      : C:\ProgramData\SkyviewRobotics\Logs
WriterSID : S-1-5-32-545
Rights    : Write
Inherited : True
```

The Logs directory contained one existing maintenance log,
`AutoUpdate-20261014-051807.log`.

### Manual remediation and retest

An administrator applied to the Logs directory the NTFS ACL explicitly defined
in stage 1 of the repository's
[Windows Chocolatey provisioning script](../windows/chocolatey/tools/chocolateyInstall.ps1).
The resulting permissions were:

```makefile
NT AUTHORITY\SYSTEM:(OI)(CI)(F)
BUILTIN\Administrators:(OI)(CI)(F)
BUILTIN\Users:(OI)(CI)(RX)
```

No files were deleted, no development tools were reinstalled, and no broad
permissions reset was performed. After this targeted ACL correction, the
SDE v1.2.5 installer was executed again and completed successfully. The user
confirmed successful installation. No native exit code or subsequent application
validation result was supplied; none is inferred from that confirmation.

### Deployment finding and engineering follow-up

The observed deployment problem required manual remediation and is no longer an
unresolved installation failure on this workstation. v1.2.5 handles the
recognized legacy permission configuration on the SkyviewRobotics parent only
when all existing descendants are already protected. It does not automatically
remediate an existing child directory with an inherited untrusted write grant.

This is intentional security enforcement in
[`Protect-LegacyMaintenanceParent` and `Assert-TrustedItem`](../windows/self-update/Bootstrap-SkyviewSelfUpdate.ps1),
consistent with the [legacy Windows permission requirements](SELF-UPDATE-MENTOR.md#legacy-windows-parent-permissions):
the descendant scan precedes the parent ACL change, and recursively hardening
writable children would incorrectly bless potentially modified contents.
It nevertheless exposes a migration coverage limitation for legacy deployment
layouts; the protected-descendant CI case does not establish unattended migration
of this Logs configuration.

A future engineering improvement is warranted before broader deployment:
provide targeted preflight diagnostics and an explicit mentor-controlled
remediation path for the recognized legacy Logs layout. Any automated ACL
correction needs separate security design and disposable Windows tests covering
inherited child writes, writable files, unexpected owners, reparse points and
concurrent mutation. Preserve diagnostic logs as potentially untrusted evidence;
review or replace suspect executable/configuration content from the approved
distribution before retrying. Changing an ACL alone does not authenticate prior
contents. Keep bootstrap rejection and unattended-worker trust checks intact;
do not automatically trust previously writable files. This record authorizes
no implementation or security-policy change.

### Disposition and outstanding validation

Only installation after administrator intervention is passed. Subsequent
application validation, scheduled-maintenance verification and automatic-update
policy verification have not been reported and remain pending for v1.2.5.
Application/engine identity, preserved student settings/data, baseline and
schedule preservation, and actual paused-policy state still need evidence under
the [UAT checklist](SELF-UPDATE-UAT.md). Signed recovery, automatic installation
and school student-account/network acceptance retain their existing gates;
earlier v1.2.4 results remain historical evidence for that version.

This result does not approve unattended student-fleet installation, automatic
application-update rollout, stable release promotion, or closure of outstanding
Windows 11 acceptance tests. Keep application updates paused and preserve all
existing release gates and separate approval requirements below.

## Automatic installation and recovery pilot — separate approval required

Production discovery and recovery retention exclude GitHub prereleases. Merely
resuming policy while 1.2.5 is a prerelease cannot demonstrate its installation.
CI covers signed automatic installation and native failure handling, but actual
laptop acceptance remains outstanding.

With only the two known-good PCs, preserve both at 1.2.4 for a reserved 1.2.4→1.2.5
pilot. That was the original reservation plan; the October 14 manual Windows
installation above means that workstation is no longer a reserved 1.2.4 source.
Reassess pilot availability without downgrading it or treating its manual install
as an automatic pilot result. Before any release edits, obtain explicit owner
approval for promoting the
accepted signed 1.2.4 release as historical (not latest) recovery source and
promoting the exact verified 1.2.5 assets as the latest stable pilot target.
Explain that GitHub stable release visibility is repository-wide even though
only the reserved PCs are resumed. Existing signed bytes must not be rebuilt or
replaced during promotion. School machines remain paused.

After approval, resume only one reserved PC at a time and use the existing
coordinated maintenance task/service. First test open-SDE deferral, then close
SDE and test the actual discovery, signed staging, native upgrade and next-run
engine. Capture maintenance outcome, native exit, application/engine identity,
baseline, settings and schedule. Verify retained signed installers using
`verify-recovery`, including exact current 1.2.5 and previous 1.2.4 evidence.
Pause again after each pilot. Do not kill native installers, manufacture broken
packages, delete locks or force a downgrade on the owner PCs; CI owns failure
injection. Unexpected results require protected-log diagnosis before proceeding.

Successful reserved-PC installation and recovery verification still do not
establish school-network/student-account acceptance or approve classroom resume.
Record those remaining checks explicitly before broader rollout. If stable
promotion is not approved, stop at signed candidate verification and CI evidence.

## Engineering follow-up #59 — new-candidate retest required

The owner subsequently reported the same condition on other Windows 11 PCs.
[Issue #59](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/59)
is the top-priority installer migration follow-up. The source change targets only
the recognized inherited Logs-directory write grant with already protected,
flat AutoUpdate log files. It preserves those bytes as diagnostic evidence and
does not accept writable files or relax unattended-worker trust checks. See the
[extended migration contract](SELF-UPDATE-MENTOR.md#legacy-windows-parent-permissions).
This does not change the published v1.2.5 assets or the historical result above.

Before broader deployment, test a new immutable candidate on representative
affected Windows 11 PCs without manually correcting ACLs first. Expect successful
first-attempt installation, preserved log evidence/private file permissions,
baseline v1.2.1 and preserved schedule/policy. Separately report application
validation, scheduled maintenance and actual paused-policy state. An initial
failure followed by manual intervention does not accept the new migration.
Native CI and owner retest results must be recorded when available; no new
candidate acceptance or release authorization is inferred from this source work.

### Affected-PC Windows 11 checklist for reviewed commit 7281331

**Status: NOT RUN; broader rollout remains paused.** Complete a separate record
for each representative affected PC. A pass on one machine does not pass another.
Do not manufacture the legacy ACL on owner PCs or repair it before the first
attempt. The October 14 installation pass above remains historical and does not
pass this checklist.

#### Candidate identity — required before installation

| Evidence | Exact value / required entry |
| --- | --- |
| Reviewed migration source | `72813311d62615f3870d40e758824808f214dce7`, [PR #60](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/60) |
| Passing source CI | [run 38586204871](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38586204871); Windows Server 2022 evidence, not Windows 11 acceptance |
| Existing CI artifact | [Windows artifact 11907130742](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38586204871/artifacts/11907130742); development fixture, not an approved workstation candidate |
| CI artifact archive SHA-256 | `4bdf792117ea46a8b06a777b9654744efa1f71f409a80996ec955de110a11415` (GitHub-reported archive digest; **not the installer hash**) |
| New immutable candidate version / source commit | **v1.2.6 signed prerelease**, `741f681c0444a8d44d9430a107c80f2fed95b68e` (merged PR #60); migration source unchanged from reviewed `7281331`, with documented candidate recipe/identity and UAT documentation changes |
| Protected candidate build run / immutable asset URL | [run 38608215787](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38608215787), [v1.2.6 prerelease](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/tag/v1.2.6); all source, Windows/Mint build-pair and sign-publish jobs passed |
| Candidate Windows installer SHA-256 | `15b29e9a3f50787ed05734faf0b480b48825bd88fff349ad944bab72bf2fa690`; actual `.exe`, 4,095,109 bytes; independently downloaded and hash-checked |
| Signed manifest / signature verification | Protected signing and post-publication pinned-key verification passed; manifest SHA-256 `746b517cffd6c68b2cd24a05fb2f4104c7dca8a48f716eb69efc4cd3eec2ff30`. Repeat full-set verification with the installed pinned worker on each test PC using the [owner UAT procedure](SELF-UPDATE-UAT.md) |

The new signed candidate and installer hash were verified on October 14, 2026.
Affected-PC acceptance is still NOT RUN. Do not substitute the published v1.2.5 assets, reuse their tag with changed bytes, install
the CI development fixture on school workstations, or treat an archive digest as
release authentication. Candidate preparation/publication retains its separate
authorization gate. After obtaining the approved candidate, verify its installer
locally and compare with the recorded signed manifest:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '.\Skyview-Dev-Setup-Windows-x64.exe'
```

The prepared [v1.2.6 recipe](RELEASE-NOTES-1.2.6.md) adds only candidate identity
support, a mutually exclusive `logs_migration` dispatch option, native pair
coverage through 1.2.6 and these documentation changes beyond the reviewed
migration. Signing requires the reviewed merged main commit, successful full
main CI, successful Windows SYSTEM/Mint candidate tests and human approval in
`sde-release-signing`. Do not dispatch from the unmerged PR or bypass these
guards. Record the verified published installer hash emitted by the workflow's
final download/authentication step, then confirm it locally before testing.

#### Signed candidate verification — October 14, 2026

[Protected run 38608215787](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38608215787)
used `release/v1.2.uat` at `741f681c0444a8d44d9430a107c80f2fed95b68e`,
with `logs_migration=true`, `migration=false`, `correction=false`. Exact-main
[CI 38600886692](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38600886692)
passed before signing. Windows SYSTEM and actual Mint candidate tests passed
through 1.2.6 (`SDE_UAT_PAIR_WINDOWS_OK`, `SDE_UAT_PAIR_MINT_OK`); the Windows
1.2.6 native installer exited 0. These are CI results, not affected-PC owner UAT.

The protected `sign-publish` job completed signing, pinned-key authentication,
immutable prerelease publication and download/authentication of all five
published assets. Tag v1.2.6 points to the exact source above; the release is
nondraft and remains a prerelease. Existing v1.2.5 assets were not replaced.
The signed manifest's stable-intent channel does not override GitHub prerelease
exclusion or authorize automatic installation.

Codex independently downloaded all five assets. Both installer hashes matched
`SHA256SUMS.txt`, signed-manifest entries and GitHub asset digests; their sizes
matched the manifest. Manifest/signature/checksum hashes also matched GitHub
digests. Pinned-key verification evidence here is from the protected workflow;
the local executor lacked the Rust toolchain to independently rerun the source
verifier. Each PC must still authenticate its complete downloaded folder using
the trusted installed worker before installation.

| Published asset | SHA-256 |
| --- | --- |
| Skyview-Dev-Setup-Windows-x64.exe | `15b29e9a3f50787ed05734faf0b480b48825bd88fff349ad944bab72bf2fa690` |
| Skyview-Dev-Setup-LinuxMint-amd64.deb | `d5018f5ccb8523a011cde88c30ff971c498188308b251978b457a0db5dc9778e` |
| sde-update.json | `746b517cffd6c68b2cd24a05fb2f4104c7dca8a48f716eb69efc4cd3eec2ff30` |
| sde-update.json.minisig | `28965ff6dd31ec09debe50d27a419ae0e4f6b286cd5768ce26f0a0ab8405daeb` |
| SHA256SUMS.txt | `2a179acb7c75df797813722d2c807ecd2c68e19017e369b50abf5ddf499e6894` |

**Disposition: signed-candidate preparation/CI verification complete; affected-PC
Windows 11 installation, preservation, application, scheduled-maintenance and
paused-policy results remain pending.** Keep #59 open and broader rollout paused.
No stable promotion, automatic-update rollout or owner acceptance is inferred.

#### Before the first attempt — capture without changing permissions

- [ ] Record date/time/time zone, tester, private PC identifier, Windows 11 build
  and x64 architecture, starting application/engine versions, candidate identity
  above, and development-tool baseline (expected v1.2.1).
- [ ] Confirm application-update policy is already paused. Save policy bytes,
  SHA-256 and owner/ACL, plus installed-worker status and the GUI paused view.
  If not paused, stop: arrange an authorized pause, document it, then capture the
  baseline before installation. Do not resume policy for this test.
- [ ] Save parent/Logs owner and full ACL/SDDL with SID-based effective-write
  inspection. Confirm the recognized inherited Users (`S-1-5-32-545`) CI-only
  Write grant on Logs. Inventory all existing descendants, including hidden
  entries, links and owners. Logs must be empty or contain flat single-link
  `AutoUpdate-YYYYMMDD-HHMMSS.log` files already free of untrusted effective
  writes. Unknown layouts or writable bytes require diagnosis, not ACL repair
  to make this test pass.
- [ ] Save each existing log's relative name, length, SHA-256, owner and SDDL;
  retain a protected evidence copy. Include `AutoUpdate-20261014-051807.log` if
  present. Logs are diagnostic evidence, not authenticated installation status.
- [ ] Inventory/hash the applied baseline scripts and package baseline record;
  save owners/private ACLs, tool versions, student project/Git state, editor
  settings and representative data hashes. Do not reinstall tools.
- [ ] Export `Skyview Robotics - Dev Tool Updates` task XML and record triggers,
  enabled state, settings, SYSTEM principal, action and task read permissions.
  If absent, record absence; installation must not create a baseline/task.
- [ ] Close SDE normally and confirm coordination is idle. Ensure maintenance
  and log writers have finished; do not kill transactions, delete locks, disable
  security checks or run disposable CI fault-injection scripts on this PC.

Keep evidence in a protected folder outside the migration tree. Capture again if
legitimate maintenance changes logs between the snapshot and installation.

#### Installation and preservation — record separate results

- [ ] Run the approved candidate once using the supported elevated native
  installer. Record Administrator or SYSTEM execution identity, command/UI
  path, start/end times, native exit code, reboot requirement and diagnostics.
  A Windows 11 SYSTEM installation claim requires an actual supported SYSTEM
  test; an elevated interactive install proves only that execution path.
- [ ] Confirm successful **first-attempt installation without manual
  remediation** and no maintenance-bootstrap error. Retain the native exit and
  installer evidence; do not infer success from the application opening alone.
- [ ] Confirm Logs has protected SYSTEM/Administrators full control and Users
  read/execute, with no untrusted effective writer. Confirm the parent grant was
  removed and required private descendants remain protected.
- [ ] Compare every pre-existing log against its inventory: same path, length
  and SHA-256, no deletion/replacement. Protected/private file owner and SDDL
  must remain unchanged. For files with inherited read permissions, record any
  expected inherited ACL change separately; there must be no new write grant or
  unintended disclosure of private content. Explain any newly created logs.
- [ ] Confirm baseline v1.2.1, baseline/package bytes and private permissions,
  tool versions, student data/Git state and editor settings are preserved.
- [ ] Compare task XML: triggers, settings/enabled state and SYSTEM principal
  unchanged; an eligible existing task action may move to the protected
  `SelfUpdate\Invoke-SkyviewMaintenance.ps1` host. Preserve student read access.
  Installation must not start maintenance, provision tools or create a schedule.
- [ ] Compare policy bytes/SHA-256; confirm `paused=true` through the installed
  worker and GUI. No production policy resume or automatic installation occurs.
- [ ] Confirm installed application/engine identity equals the approved new
  candidate, distinct from the preserved v1.2.1 development-tool baseline.

#### Subsequent validation — never infer these from installation

- [ ] As the normal student account, open SDE and check About, project access,
  settings, Schedule and public status; close normally. Verify student inability
  to alter update policy, baseline, retained logs or private installation state
  using the existing supported acceptance procedure.
- [ ] Verify scheduled maintenance separately at an observed scheduled run or
  authorized coordinated test invocation. Record task outcome, active engine,
  separate tool exit and protected status evidence. Keep app-update policy
  paused; do not change the preserved schedule or use logs as proof of success.
- [ ] Reconfirm paused policy after validation and document any reboot/recheck.
  Actual automatic application-update installation/recovery and school-network
  acceptance remain separate gated tests; this checklist does not resume them.

#### Per-PC result and deployment gate

Record: PC identifier; candidate source/version/installer SHA-256; evidence
location; initial ACL classification; execution identity/native exit; manual
intervention (none or exact action); installation result; log/baseline/task/data
preservation results; application result; maintenance result; policy result;
tester/date; outstanding conditions. Use PASS, FAIL or NOT RUN for each result.

Only a successful first attempt with all required preservation checks is
**PASS — Successful installation without manual remediation**. If intervention
is needed, preserve both attempts and mark this migration acceptance test failed,
even if the PC is subsequently installed. On failure, retain diagnostics and
stop further affected-PC deployment; do not relax trust checks or bless files.

Broader rollout remains paused until representative affected-PC results pass,
remaining acceptance conditions are satisfied and the owner explicitly
authorizes deployment. Passing this checklist alone does not authorize student
fleet unattended installation, automatic-update rollout, stable promotion,
closing #59 or closing other Windows 11 acceptance gates. No merge, release
publication or policy change is performed by preparing this checklist.

## Affected Windows 11 owner retest — October 14, 2026

**PASS — Successful installation without manual remediation (owner-reported).**
The owner reported that SDE v1.2.6 installed successfully and explicitly confirmed
this was an affected laptop still carrying the failing legacy Logs permissions,
on the first attempt, without manual ACL correction. This is a new result,
distinct from the historical v1.2.5 pass after manual remediation. The PC
identifier, Windows build, native installer exit code, per-PC pinned verification
and downloaded installer hash were not supplied. The expected candidate is the
immutable v1.2.6/source/hash recorded above; the report does not independently
establish the exact bytes used on this PC.

### Subsequent GUI Update and validation evidence

After installation, the owner ran **Update in SDE** and supplied `Pasted text.txt`
(25,106 bytes; SHA-256
`37f61338ba8232e2ef331d11f3d2237a65a3c3c2aa0d94d1a687d15d4a6fe766`).
The attachment records development-tool updates and subsequent environment
validation, not automatic SDE application installation or a SYSTEM scheduled run.
GUI Update is a separate tool-changing action after the application installation;
its results must not be used to infer pre/post installer preservation.

The output reaches:

```text
SKYVIEW_EVENT|summary|0|Validation completed with 0 failed checks
SKYVIEW_EVENT|progress|100|Development environment ready
```

**PASS — GUI development-tool Update reached completion and its reported
validation checks passed, with warnings.** No overall helper/native exit code
was included in the supplied output. Node.js remained 24.21.0, with the
`nodejs-lts` pin restored; Python remained in the python314 family at 3.14.8.
VSCodium, Firefox, PowerShell Core and 7-Zip upgrades reported success.
Other package checks reported current versions. All listed tools, required editor
extensions, development folder and configured Windows/Git settings passed
validation. The output reports existing editor settings were preserved.
Git identity and GitHub authentication were optional/unconfigured, and no
repositories were configured, so repository checkout/work preservation was not
exercised by this Update run.

Warnings and limitations retained from the attachment:

- Chocolatey repeatedly reported a pending reboot, including before package
  updates began. Its configuration allowed updates to continue. Reboot completion
  and post-reboot validation have not been reported.
- Updates for VSCodium, Firefox, PowerShell Core and 7-Zip emitted
  `Unable to find the parent package 'skyview-student-dev'.` and NuGet dependency
  constraint warnings referencing `skyview-student-dev 1.2.1`. The corresponding
  upgrades subsequently succeeded; this is a package-metadata diagnostic finding,
  not evidence that the Logs migration or installation failed. Investigate package
  metadata if persistent; no package deletion/reinstall or new issue is authorized
  by this record.
- VSCodium emitted DEP0169 `url.parse()` deprecation warnings, and Firefox warned
  about an uninstall registry-key lookup. Neither prevented reported completion.
- `PASS Weekly maintenance enabled` checks task presence/readability and enabled
  state only. It does not check an actual scheduled invocation, exact trigger,
  SYSTEM principal, action migration or unchanged task XML.
- Tool records show `updateCheck=notChecked` after this run. Their
  `updateAvailable=false` values are not an independent fresh update-availability
  check or application-update policy evidence.

### Remaining acceptance gates

Installation without manual remediation is confirmed by the owner, and the
interactive GUI Update/validation result is recorded. Log bytes/private ACLs,
parent/Logs post-install ACLs, applied baseline bytes/version, student data and
schedule preservation still need their own evidence. The dependency warning's
v1.2.1 reference does not prove baseline preservation. Actual application/engine
identity, paused-policy state/preservation, student read-only access, scheduled
maintenance execution and post-reboot validation also remain pending.

This report supports the #59 migration fix on one affected PC; it does not fully
pass the preservation checklist or establish fleet acceptance. Keep #59 open,
application updates and broader rollout paused, and existing release/automatic
installation/recovery/school-network acceptance gates intact. No stable promotion,
additional-PC installation or issue closure is inferred from this result.

### Subsequent standalone Validate output — October 14, 2026

**PASS — Standalone development-environment validation.** The owner supplied a
second `Pasted text.txt` containing the GUI Validate output (5,629 bytes; SHA-256
`bb9baaa63544da61067285a8dc60f540b073e5585973cd22080f248ae883d1a3`).
It records 31 PASS validation events, 2 optional INFO events, no FAIL events,
`Validation completed with 0 failed checks` and `Development environment ready`.
Reported installed tool versions match the preceding Update output, including
Node.js 24.21.0, Python 3.14.8 and PowerShell 7.6.7. Required tools, editor
extensions, settings presence, development folder, Git defaults and configured
Windows settings pass. Git identity and GitHub authentication remain optional
and unconfigured. `Weekly maintenance enabled` again confirms enabled/readable
task state, not a scheduled execution or schedule-preservation comparison.

No package upgrade output or pending-reboot/dependency warning appears in this
Validate-only attachment; those Chocolatey conditions were not checked by this
operation. Reboot completion was not explicitly reported, so this is not yet a
confirmed post-reboot result and does not establish that prior warnings cleared.
Tool records still use `updateCheck=notChecked`. Native/helper exit, app/engine
identity, actual paused application-update policy and the outstanding
preservation/scheduled-execution checks remain unverified by this attachment.
Broader rollout remains paused; the historical installation and Update evidence
above remain unchanged.

### Schedule page observation — October 14, 2026

The owner supplied the Schedule page text after the installation/Update/Validate
reports. **PASS — open application reports v1.2.6 and current application-update
installation setting is paused by administrator.** The UI lists pause-setting
change time as October 14, 2026, 05:43 in the workstation's displayed local time.
This confirms the observed paused setting, not byte-for-byte policy preservation
or a completed automatic-update attempt.

The page reports `\\Skyview Robotics - Dev Tool Updates` enabled, every week on
Sunday at 03:00 local time, with missed-run catch-up enabled. Displayed last run:
October 14, 2026, 05:18; last Scheduler result: Succeeded (`0x00000000`). Displayed
next run: October 18, 2026, 03:00. These are workstation-local displayed times;
no UTC conversion or execution guarantee is inferred. Pre-install task XML and
run chronology were not supplied, so neither unchanged schedule nor a successful
post-v1.2.6 SYSTEM maintenance invocation is established by this historical result.

The observed installed application, candidate, attempt outcome/times, maintenance
engine, applied baseline, tool/native results and signed recovery are unavailable
or unrecorded. Coordination is `SDE or maintenance is active`, which is expected
while SDE is open and does not itself prove maintenance is executing.

Missing attempt history is allowed after a manual bootstrap: the installer
activates an engine but does not fabricate a maintenance attempt or recovery
receipt. See [manual-install expectations](SELF-UPDATE-UAT.md#immediate-checks-and-maintenance-no-weekly-wait).
This display is consistent with missing history, but also covers unreadable or
invalid history; distinguish these by checking the trusted task action, installed
worker status and protected logs. It does not reverse the owner-reported install
pass, prove engine/baseline absence or establish successful automatic installation.
Unconfirmed signed recovery after manual bootstrap remains a known reduced
recovery capability, not proof that signed-candidate verification failed.

Next inspection: close SDE normally, read the existing task action/SYSTEM
principal and active engine receipt/status from an administrator terminal.
Before any immediate maintenance test, verify the task targets the protected
maintenance host and that other package/maintenance work is idle. An authorized
existing SYSTEM task invocation keeps application policy paused but also runs
development-tool maintenance; capture its fresh independent results and logs.
Do not resume application updates, use Repair to manufacture a result, alter
task settings, delete receipts or infer that old log bytes were preserved from
this page. Other preservation, post-reboot and acceptance gates remain pending;
#59 stays open and broader rollout remains paused.

### Administrator task/worker inspection — October 14, 2026

The owner's read-only inspection confirms the existing task executes
`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` with
`-NoProfile -NonInteractive -ExecutionPolicy Bypass -File`
`C:\ProgramData\SkyviewRobotics\SelfUpdate\Invoke-SkyviewMaintenance.ps1`.
Principal is SYSTEM, RunLevel Highest. **PASS — observed task routes to the
protected maintenance host under the required principal.** Pre/post trigger,
settings or task ACL preservation is not established by this inspection.

The trusted installed `sde-update-trust.exe self-update-status` reports
`paused=true`, `coordination=idle`, `outcome=unavailable`, `phase=unknown` and
`policyChangedAt=1791981810`. Attempt times, observed application/engine/baseline,
tool/native exits and log reference remain null; `recoveryAvailable=false`.
**PASS — installed-worker observation of paused policy and idle coordination.**
Unavailable history remains unclassified (absent, unreadable or invalid); no
completed task invocation is claimed. False/default reboot and recovery fields
in this unavailable status do not clear the earlier pending-reboot warning or
prove recovery material was checked.

The next maintenance acceptance step is one controlled invocation of this
existing enabled SYSTEM task, with SDE closed normally and other work idle,
following the [immediate UAT procedure](SELF-UPDATE-UAT.md#immediate-checks-and-maintenance-no-weekly-wait).
It really runs development-tool maintenance while application updates remain
paused. Wait for native/package work to finish, then capture the fresh task run
time/result and installed-worker/Schedule status. Expected evidence includes
engine 1.2.6, independent tool outcome, baseline identity and paused app outcome.
Do not terminate work, resume policy, alter the schedule or synthesize history.
Other preservation, reboot and deployment gates remain open.

### Completed controlled SYSTEM maintenance run — October 14, 2026

**PASS — existing SYSTEM maintenance task completed using engine v1.2.6,
reported baseline v1.2.1 and independent tool exit 0, with application updates
remaining paused.** The owner supplied fresh task and installed-worker output
after the controlled invocation. Task state is Ready, LastTaskResult is 0,
LastRunTime is October 14, 2026, 15:46:38 in the workstation's displayed local
time, and NextRunTime remains October 18, 2026, 03:00. Earlier inspection
established the protected launcher and SYSTEM/Highest principal. This proves a
controlled invocation of the provisioned task, not a natural weekly firing.

The installed worker reports:

```json
{"paused":true,"policyChangedAt":1791981810,"outcome":"paused","phase":"policy","checkedAt":1792018003,"completedAt":1792018042,"applicationVersion":"1.2.6","candidateVersion":null,"maintenanceEngineVersion":"1.2.6","appliedBaselineVersion":"1.2.1","toolExit":0,"nativeExit":null,"rebootRequired":false,"recoveryAvailable":false,"logReference":"logs/f375cf06-faad-4aec-98aa-5e52fdbea161.log","coordination":"idle"}
```

Fresh completed history now reports matching application/engine identities and
the older applied development baseline, resolving the earlier unavailable
observations for this run. The reported pause-change timestamp is unchanged from
the preceding installed-worker inspection; policy byte/ACL preservation across
installation still requires its own comparison. `outcome=paused`, `phase=policy`
is the expected application result, separate from `toolExit=0`. No native SDE
installer ran in this attempt (`nativeExit=null`), and no automatic installation
or signed recovery pass is claimed. `recoveryAvailable=false` remains the known
reduced recovery capability after manual bootstrap. This worker result's
`rebootRequired=false` does not by itself clear the earlier Chocolatey/Windows
pending-reboot condition; no post-reboot confirmation was supplied.

Retain the referenced protected log under
`C:\ProgramData\SkyviewRobotics\SelfUpdate\logs` for diagnostics. Baseline version
identity, successful controlled maintenance and paused application behavior pass;
baseline/log bytes and private ACL preservation, per-PC downloaded-asset
authentication, student data/settings comparison, pre/post schedule comparison,
actual weekly firing, post-reboot and other acceptance conditions remain open.
Keep #59 open, application updates and broader rollout paused. This result
authorizes no stable promotion, automatic-update pilot or fleet acceptance.
