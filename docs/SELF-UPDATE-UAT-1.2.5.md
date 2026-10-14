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
