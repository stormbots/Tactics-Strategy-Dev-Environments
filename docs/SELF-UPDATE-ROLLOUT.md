# Candidate preparation, migration and rollout (#43)

Current accepted downloads: [official stable/latest](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/releases/latest).
October 24, 2026: stable is v1.2.14. v1.2.15 is an immutable authenticated
prerelease with both desktop UAT passes recorded. The fresh
v1.2.17 candidate fixes the student-toggle native permission omission after
v1.2.16 Windows UAT failed persistence. Published v1.2.16 remains an immutable
prerelease; other Windows focused rows passed, Mint v1.2.16 is unreported. Historical v1.2.2/v1.2.3
pair procedures are retained in [the original source](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/b0f6a43e85b8ae5bbf72b87b4ee5f2d92bfd40ba/docs/SELF-UPDATE-ROLLOUT.md);
they are not current dispatch or laptop installation instructions.

## Current release gates

Use the [execution ledger/matrix](DEPLOYMENT-READINESS-EXECUTION.md),
[focused owner sheet](SELF-UPDATE-UAT.md) and [pilot packet](SELF-UPDATE-PILOT.md).
Reserve existing actual v1.2.14 Windows/Mint installations before candidate UAT.
Separate test PCs may receive the new candidate; never downgrade a daily/student
PC or create insecure legacy ACLs for a test. Additional VMs/media/host access
need their own authorization. App installation, signing, stable visibility and
device resume are separate scopes.

## Prepare the immutable candidate

1. Recheck official main, unused tag/release v1.2.17, open PRs and live signing
   environment. Review/merge the next-version recipe; do not dispatch old main's
   `update_discovery` or default pair. Historical options have been removed from
   the current recipe to avoid selecting already published versions.
2. Full **Build Skyview Dev Setup** CI must pass on the exact merged main source.
   Preserve all repository/native/trust jobs, including Chromium/WebKit/sidebar
   checks. PR pair verification builds real Windows SYSTEM and actual Mint
   userland packages without signing or publishing. These are not owner desktops.
3. Fast-forward `release/v1.2.uat` to that reviewed main commit without force or
   tag changes. Dispatch **Prepare signed self-update UAT pair** with only
   `deployment_readiness=true`. Its source guard requires exact main equality,
   successful exact-main push CI and an unused target before native builds and
   human signing review. A false/default input fails closed.
4. Disposable application identities are **1.2.16 and 1.2.17**; source app identity
   and managed-tool baseline remain 1.2.1. Lock dependencies are unchanged. The
   rebuilt 1.2.16 is an **unpublished same-source fixture**, not the exact published
   v1.2.16 bytes. The pair tests real install/upgrade, enabled defaults from paused/enabled policies, saved files,
   no app-only provisioning/schedule and preserved incompatible legacy sentinel
   with `needs_repair`. Full native CI separately covers the recognized Logs
   layout, custom disabled schedules, standard-user denial and failure/recovery.
5. Before asking the owner to review `sde-release-signing`, prepare exact source,
   workflow/ref/input, successful full/native run links and both input artifact
   IDs, sizes and digests. Check configured human reviewer, disabled admin bypass,
   restricted refs and both secret **names**; never read/export their values or
   approve on the owner's behalf. October 12 key-backup confirmation remains
   applicable unless a key/configuration change exposes a genuine recovery gap.
6. After human signing approval the protected job rechecks exact main/CI, package
   identities, creates/signs/verifies the manifest, and publishes **only v1.2.17**
   as nondraft prerelease with `latest=false` and exactly five canonical assets.
   The ordinary release workflow excludes this candidate tag to avoid a duplicate
   publication from the unchanged source app identity. Never overwrite assets,
   retarget tags, re-sign releases or rerun a partial publication blindly.
7. Independently download all five published assets into a fresh folder; build
   the pinned verifier from reviewed source (or use a trusted installed one)
   outside it. Verify exact manifest/signature, both installers and checksums,
   asset IDs/sizes/digests before/after download, tag/source, package identity and
   prerelease flags. Record the receipt in the PR. Then hand off exact URLs,
   trusted verifier paths and the focused desktop UAT sheet. A changed published
   package requires another unused version.

## One-time migration

Existing pre-updater installations need one mentor-approved authenticated native
app install before the new maintenance host is available. Follow current UAT
commands: Windows per-machine `/S /UPDATE` for upgrades (`/S` for fresh install),
Mint local-package APT. Packaging initializes protected coordination/policy and
activates the engine without applying the bundled tool baseline. Starting with
v1.2.16 every application installation or upgrade intentionally sets the app
update preference to enabled, including previously paused installations. This
does not start maintenance or create/enable a task or timer. Students can pause
or resume using the Schedule page; reapply an approved operational pause after
installation if a pilot/recovery procedure requires it.

The Windows installer supports the narrow parent-plus-Logs migration shipped in
v1.2.6, under normal administrator installation. See [the safety contract](SELF-UPDATE-MENTOR.md#legacy-windows-parent-permissions).
Already protected flat timestamp log files retain bytes/private permissions;
old logs stay potentially untrusted diagnostics. Unsupported grants, writable
files, links, owners, concurrent/busy writers or unexpected contents fail closed.
Do not broaden the migration, delete evidence or reset arbitrary descendants.

Preserve student work/settings, baseline bytes/version, custom timing/enabled
state. The pause preference intentionally resets to enabled under #102; it is
not a preservation failure. An already coordinated provisioned schedule can move to
the protected launcher; an app-only install creates no tool schedule. An old
uncoordinated baseline is preserved, reports `needs_repair`, and blocks automatic
installation. It is not authenticated merely by hardening permissions.

For an incompatible baseline, capture existing tools/schedule/policy and obtain
**separate mentor authorization** for disabling that schedule, waiting for all
work to finish and using GUI **Repair**. Repair is actual baseline/provisioning
work and may change tools and schedule defaults. Compare results, restore approved
custom timing/enabled state and verify protected coordination/launcher. Do not
paste markers, copy scripts silently, delete intent or resume around the gate.
Provisioning an app-only PC likewise requires its own understood decision.

## Stable promotion and public verification

After owner UAT/disposition names the exact authenticated target, obtain explicit
stable/latest authorization for that candidate. Recheck source, successful CI,
release/tag and unchanged five-asset IDs/sizes/digests; promote the **same** existing
prerelease by metadata/notes only. v1.2.14 acceptance and signing review do not
authorize v1.2.17 promotion. Verify live `/releases/latest`, both evergreen public
installer links and `tests/stable_downloads.py` against README and live latest
JSON. Preserve historical recovery links and append the immutable promotion
receipt to PR/release/acceptance records.

Stable visibility is repository-wide; already resumed eligible devices may
discover it. It does not authorize policy changes on any device. Perform #99
read-only GUI transition checks on retained v1.2.14 after the newer target is
accepted stable. Never promote an unaccepted version just to enable that test.

## Controlled pilot, pause and recovery

Use [the device-specific packet](SELF-UPDATE-PILOT.md) only after its named-device,
policy/action/target/window approval. Open-SDE and idle triggers run real tool
maintenance; record tool results separately from app deferral/installation.
Manual app installation and equal-version checks cannot prove automatic install
or signed recovery. Report pilot results before any expansion. Classroom-wide
resume/migration needs a later explicit decision.

On findings retain logs/receipts, pause further installation attempts within the
approved stop response, and let existing package work finish. Follow
[mentor recovery](SELF-UPDATE-MENTOR.md); no forced reboot, process kill, lock
removal, blind journal clearing or universal rollback is supplied. Keep approved
accepted assets available for assessed manual repair; a manual bootstrap may have
no retained signed recovery receipt. Signing/key recovery follows
[the signing guide](SELF-UPDATE-SIGNING.md).

Release completion and milestone completion differ: close #59 only after its
narrow evidence/owner disposition is satisfied (#59 closed October 24 with the
explicit accepted additional-PC/private-ACL evidence limit); close #43 and milestone 2 only
after required representative pilot work or an explicit owner-approved scope
revision with remaining work tracked. #99 closes only on its own real transition
evidence. Verify actual issue states rather than cached milestone counters.
