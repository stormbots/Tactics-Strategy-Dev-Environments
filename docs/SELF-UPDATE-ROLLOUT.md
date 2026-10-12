# Candidate preparation, migration and rollout (#43)

## Current gates

The self-update implementation and #42 native integration have merged. The
historical stable v1.2.1 release is unchanged and predates that implementation.
Do not replace its assets, treat its old acceptance as new acceptance, or resume
the classroom fleet yet. New bootstrap installs default to paused; upgrades
preserve an existing policy, so the mentor must verify every pilot laptop.

The owner confirmed separate encrypted-key and Bitwarden-passphrase backups on
2026-10-12. The signing environment has the owner reviewer, no admin bypass,
restricted release refs, and both secret names. Candidate signing still needs a
human environment approval and a successful pinned-key verification. No private
key is needed on student laptops or exported in candidate artifacts.

## Codex prepares the signed pair

1. Review and merge the #43 implementation. Wait for **Build Skyview Dev Setup**
   to pass all checks on that exact main commit. Its Windows SYSTEM and actual
   Mint userland installation evidence is distinct from owner laptop acceptance.
2. Create/update `release/v1.2.uat` to that reviewed main commit, without altering
   main or published tags. Dispatch **Prepare signed self-update UAT pair** on
   that branch. Its guard requires the branch commit to equal current main.
   The signing environment already permits `release/v1.2.*`; do not broaden it.
3. The workflow builds v1.2.2 and v1.2.3 on both platforms. Only application
   identity files are changed in disposable build checkouts; dependencies and
   applied development baselines stay unchanged. Native pair tests install the
   actual packages, verify versions/engine/pause and saved files, and check that
   app-only installation creates no baseline or schedule. PR runs perform these
   builds/tests without signing secrets or publishing releases.
4. Inspect the run/source/diff and native results. The owner approves the pending
   **sde-release-signing** environment in GitHub Actions. Codex must not approve
   on the owner's behalf or weaken protection to bypass this human checkpoint.
   Signing approval permits candidate signing only, not stable promotion.
5. Signing rechecks current main and successful full CI for this exact commit,
   verifies package identities, creates manifests, signs and authenticates both
   complete distributions. Only then does it create **prereleases**, with
   `latest=false`. Both candidates have signed stable-intent metadata, but GitHub
   prerelease status keeps them ineligible for production discovery.
6. Codex downloads the published five assets for each version, authenticates
   them again with the reviewed pinned verifier, checks hashes and prerelease
   flags, and fills in the acceptance record with URLs, exact commit/run and
   manifest hashes. Give the owner the concise laptop checklist and ready assets.

The reserved pair tags are excluded from the ordinary tag-triggered release
workflow to avoid a second publication attempt using the unchanged main build
identity. Reproduce these candidates using this fixed recipe, not a plain build
of their source tag. Do not promote the starting fixture v1.2.2. The workflow
refuses existing tags and never replaces assets. If only one prerelease was
created before a publication error, leave it a prerelease and have Codex assess
the partial publication; do not rerun with overwrite flags. New code/UAT fixes
need new version identities and a reviewed update to this fixed-pair recipe.

## Owner UAT and one-time migration

Use [SELF-UPDATE-UAT.md](SELF-UPDATE-UAT.md) for the controlled manual v1.2.2 →
v1.2.3 upgrade. Production ignores prereleases, so no automatic stable eligibility
is created to test this pair. The manual test does not claim production gating
or automatic-install receipts; #42 CI covers those components. Owner UAT covers
Windows 11, booted Mint, school Wi-Fi/proxies, saved work and real scheduling.

Existing installations cannot obtain the new host automatically before a trusted
bootstrap. A mentor installs the owner-approved authenticated native candidate
once per representative laptop, without clicking GUI Install/Repair/Update.
Windows uses per-machine `/S /UPDATE`; Mint uses the configured APT local-package
installation. This initializes protected coordination/policy and the new engine.
It preserves applied baseline scripts and custom task/timer settings. Existing
provisioned schedules are routed to the protected launcher; app-only installations
create no tool schedule. Verify this behavior on the actual legacy configuration,
including disabled/customized schedules, before extending migration to the fleet.

If no baseline/schedule exists, provisioning is a separate mentor decision and
may change tools; application migration does not authorize it. The older applied
baseline may remain alongside the new engine. Do not interpret that difference as
a failed app upgrade or silently apply the newly bundled baseline.

Record explicit owner acceptance of the exact 1.2.3 target/source/assets on both
systems in [ACCEPTANCE-SELF-UPDATE.md](ACCEPTANCE-SELF-UPDATE.md), with any accepted
limitations. Prepare a small representative pilot (Windows and Mint, including
ordinary student permissions/custom schedules), then report its results before
migrating the remaining approximately 20 laptops. Keep production paused during
manual migration and UAT. Preserve a list of OS, installed app/engine/baseline,
policy, schedule and findings per laptop without personal data.

## Stable promotion and future releases

After explicit owner UAT acceptance, ask for **separate, explicit authorization**
to promote the exact authenticated target and to resume the selected pilot
laptops. Codex rechecks source, successful CI, asset/signature hashes, acceptance,
backup status and absence of unresolved blockers. Promote the existing tested
prerelease without changing its tag or assets. Candidate publication, PR merge,
signing approval and this document do not supply that authorization.

For future ordinary releases, bump all application identity/lock files together,
leave development baseline policy explicit, provide versioned release notes, and
use the existing protected release branch/tag pipeline. Complete both native
builds/tests and trust checks; publish only a signed prerelease first. Obtain
owner acceptance/promotion authorization, then promote those same assets.
Never re-sign or replace assets of an accepted stable release.

Automatic eligibility requires the official repository, canonical compatible
newer version, a nondraft **stable** GitHub release, both complete signed assets,
successful pinned authentication/hash checks, supported OS/architecture, trusted
installed identity/policy, unpaused installation, and idle session/maintenance/
package state. Eligibility is rechecked before native installation. An active SDE
session is deferred, not forcibly closed. Lower/equal versions are ignored.

Resume using the installed administrator `resume` command from the
[mentor guide](SELF-UPDATE-MENTOR.md), per explicitly approved laptop. Confirm the
policy and existing schedule, then use the documented immediate task/service
trigger in an agreed maintenance window instead of waiting a week. That trigger
also runs development-tool maintenance; inspect its independent result. After
pilot acceptance, explicitly authorize any broader resume/migration batch.

## Pause and recovery

Pause each affected laptop with the installed worker if a rollout finding occurs;
refresh status and preserve private logs/receipts. Pause does not stop package
work already in progress. Wait for native children, do not remove locks/journals
or force reboot, and follow the mentor guide for package-state assessment and
retained signed-installer verification. Codex diagnoses sanitized evidence and
prepares fixes; the owner approves recovery that affects student laptops.
There is no universal automatic rollback. Manual bootstrap may have no retained
previous signed installer, especially for unsigned legacy versions. Keep the
accepted installer assets available under mentor control as a recovery input.

If key recovery or signing infrastructure changes, recheck backup and protected
approval before further rollout. See [signing and rotation](SELF-UPDATE-SIGNING.md).
