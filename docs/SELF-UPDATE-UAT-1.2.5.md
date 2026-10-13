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

## Automatic installation and recovery pilot — separate approval required

Production discovery and recovery retention exclude GitHub prereleases. Merely
resuming policy while 1.2.5 is a prerelease cannot demonstrate its installation.
CI covers signed automatic installation and native failure handling, but actual
laptop acceptance remains outstanding.

With only the two known-good PCs, preserve both at 1.2.4 for a reserved 1.2.4→1.2.5
pilot. Before any release edits, obtain explicit owner approval for promoting the
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
