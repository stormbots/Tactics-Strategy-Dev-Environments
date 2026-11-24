# Maintenance restoration: scope and preservation audit

Part of [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161). Source reviewed: main `7524cf2a3d324d2876585d74249ed8cb9c42a2e4`, after the maintenance-observation and VSCodium access-review increments. Its [full exact-main CI passed](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/44373975267). This document records source findings and the next engineering work. It adds no application action or authority.

The accepted rule remains: keep related steps together, automate required follow-up checks, and update findings in place. Restoration still needs full scope review, explicit approval, normal operating-system permission and fresh native safety checks. A read-only check or a saved leave-disabled choice cannot approve a change.

## Windows file-name visibility exception

Owner decision, November 24, 2026, under [#161](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161): **showing file-name extensions remains required on Windows.** Students and instructors need consistent, complete filenames, such as `robot.py` and `settings.json`.

This is a narrow exception to the general rule that preserves personal preferences
and intentional settings. Every preservation promise in this release must account
for the exception. The required setting is File Explorer’s `HideFileExt=0`.
Other personal settings retain their accepted preservation rules. The exception
does not provide a general permission to reset preferences.

The existing [Windows validator](../windows/chocolatey/tools/Validate-SkyviewEnvironment.ps1)
requires **File extensions visible**. A hidden-extension preference cannot satisfy
that check. Keep the requirement and its existing failure behavior; do not turn it
into an optional recommendation, warning, saved exception or automatic pass.

[Install/Repair profile configuration](../windows/chocolatey/tools/Configure-SkyviewUser.ps1)
and [legacy Windows setup](../windows/chocolatey/tools/chocolateyInstall.ps1)
already set `HideFileExt=0`. The development-tool Update operation also runs the
profile configuration phase. Before approval, the relevant review must state that
Windows will show file-name extensions. General wording about preserving settings
must include this exception. Existing full-operation scope, explicit approval,
normal operating-system permission and fresh native safety checks still apply.
Validation and startup inspection remain read-only. SDE application-only upgrades
retain their separate preservation contract.

A student can satisfy the requirement manually in File Explorer with **View → Show
→ File name extensions**, then check again. A passing visibility check resolves
only that requirement.

This owner decision resolves the Explorer policy question in the original audit
below. The original source review remains historical evidence. Required release
checks include clear pre-approval disclosure, retained validation failure while
extensions are hidden, and successful recheck after visibility is enabled. The
policy record does not claim that the final UI disclosure or owner UAT has passed.
Runtime/default/launch ownership and project-location criteria remain open.

## Finding

**The existing restoration candidate is full Install/Repair, not a schedule-only operation.** Both platforms' setup paths write the managed schedule. Update does not provide that restoration contract. The current source establishes the route, but the required disabled/missing-state restoration and preservation cases still need native proof before the new UI can promise completion.

There are important effects beyond scheduling:

- Windows setup can switch a Chocolatey-managed Node installation to the approved family, change system development settings and configure the current user's editor/workspace.
- Mint setup refreshes package sources and packages, updates application launch links, installs maintenance files and activates the timer.
- Every modifying GUI operation, including Update, runs a user-configuration phase after its system phase succeeds.
- The Mint timer is persistent. Activating it can make missed maintenance due before the next weekly date. Native coordination still applies; the UI must not promise that activation only affects future Sundays.

These are source observations, not approval to change a student's computer or proof that a restoration attempt succeeded.

## Existing routes and boundaries

| Entry | What the current source does | Implication for the new flow |
| --- | --- | --- |
| Schedule inspection | [SchedulePage](../installer/src/DetailsPages.tsx) reads scheduling and SDE app-update status. Windows uses the fixed task inspector; Mint uses the fixed timer/service inspector. | A retry can update observations without enabling or starting anything. A returned Disabled result resolves an unknown inspection, not the disabled state. Keep the two policies distinct. |
| Install/Repair system phase | [Native helper](../installer/src-tauri/src/process.rs) calls Windows setup with `-SystemOnly` (also `-Repair` for Repair) or Mint setup with `--system-only`. | Repair is a full setup route. The Windows Repair flag does not select a schedule-only path; Mint uses the same system setup for both modes. |
| Update system phase | [Windows updater](../windows/chocolatey/tools/Update-SkyviewTools.ps1) and [Mint updater](../linux/Update-SkyviewStudentDev.sh) update managed tools. | Do not promote Update as schedule restoration: these paths do not establish the setup path's task/timer registration contract. |
| GUI profile and validation phases | [Native operation runner](../installer/src-tauri/src/main.rs) runs current-user configuration after every successful modifying system phase, then validation. | The review must include user configuration, even for Update. Required-tool validation alone does not certify schedule restoration. |
| Recovery, admission and permission | Existing installed-helper, coordination, journal and native checks remain in the operation engine. [ADR 0001](adr/0001-interruption-acknowledgment-boundary.md) and [ADR 0002](adr/0002-lease-bound-recovery-transition.md) define recovery boundaries. | Reuse these boundaries. Do not turn an inspection, UI receipt, acknowledgment or saved location into an execution permit. Do not broaden the operation enum to invent Enable. |

## Effects the restoration review must account for

| Area | Windows source | Mint source | Preservation or disclosure still required |
| --- | --- | --- | --- |
| Managed packages and runtime selection | [Setup](../windows/Install-SkyviewStudentDev.ps1) runs Node provisioning and forces the configuration metapackage to rerun. [Node24](../windows/chocolatey/tools/Node24.ps1) can remove conflicting Chocolatey Node registrations; it rejects some external layouts. The [metapackage](../windows/chocolatey/skyview-student-dev.nuspec) has the full baseline dependencies. | [Setup](../linux/Install-SkyviewStudentDev.sh) refreshes sources, installs the approved Node/Python families and the wider tool set, and can install Chrome and PyCharm. | A successful read-only coexistence check is not proof that full setup preserves another default, manager or installation. Inventory ownership and defaults before changes; keep unsupported layouts blocked with useful guidance. Preserve the accepted coexistence rules. |
| Machine configuration and installed helpers | [Configuration stages](../windows/chocolatey/tools/chocolateyInstall.ps1) create/protect directories, copy maintained files, enable Windows long paths and Developer Mode, set system Git long-path support and manage Node pinning. | Setup writes package-source configuration, managed support files and version state. [PyCharm setup](../linux/lib/common.sh) can replace managed launch symlinks and its desktop entry after checksum verification. | Disclose these effects. Verify ownership and foreign objects before replacement. Product discovery alone must not grant maintenance authority over another installation or launch target. |
| Current-user preferences and extensions | [User configuration](../windows/chocolatey/tools/Configure-SkyviewUser.ps1) preserves Git and VSCodium preferences, but writes Explorer's `HideFileExt` and force-installs listed editor extensions. | [User configuration](../linux/Configure-SkyviewUser.sh) preserves Git/VSCodium preferences, installs listed extensions and creates the default workspace. | Keep the verified Git/editor preservation. Apply the Windows file-name visibility exception above. Apply the extension preservation increment below. Include required setting changes in the approval review before making preservation promises. Disclose required changes; do not silently infer ownership from discovery. |
| Projects and workspaces | [Repository setup](../windows/chocolatey/tools/Setup-SkyviewRepositories.ps1) skips existing `.git` entries and preserves other existing destinations, but can clone configured missing destinations under `C:\Development`. | User configuration checks a `.git` directory under the default workspace and otherwise skips an existing destination or clones a missing one. A worktree's `.git` file does not satisfy that directory test. | Neither route implements the accepted saved-location/identity contract. Existing work is not deleted by these branches, but a moved project can be missed and a second clone can be created at the default destination. Verify identities, worktrees, moved/disconnected locations and changed selections before offering the completed workflow. |
| Development-tool scheduling | Configuration re-registers the fixed SYSTEM task with `-Force`, a Sunday 03:00 trigger, catch-up and the existing read-only student ACL. | Setup installs fixed units, reloads systemd and enables/starts the timer. Its [unit](../linux/systemd/skyview-student-dev-update.timer) uses Sunday 03:00, randomized delay and `Persistent=true`. | Account for disabled/customized state, overwritten definitions and catch-up. Confirm behavior on actual disabled/missing fixtures. A leave-disabled UI decision must not silently become permission to re-register or enable later. |
| SDE app-update policy and earlier results | The schedule can point at the installed maintenance launcher. | The service definition depends on the installed maintenance engine. | Inspect protected app-update policy separately before and after. Do not infer resumption from schedule enablement, erase earlier results or claim that a successful full operation proves a successful app update. |

This table lists the first-party branches reviewed, not every possible effect of an upstream package installer. The operation review must disclose package scope without claiming a complete inventory of third-party installer side effects.

## What the UI can and cannot promise yet

A supported read-only retry can remain in the maintenance flow and display the new state. Denied access, a missing task/timer and other failures need distinct evidence and plain explanations. An unknown result must not default to Repair. If the check still fails, keep troubleshooting and support-report actions in the same flow.

An explicit **Leave maintenance disabled** decision can record that the student reviewed the finding. Its storage must be narrowly scoped to the current user/machine/schedule context and remain display-only. It must not write task state, control another user's decision, resume SDE updates or override native checks. Fresh observations still show Disabled. Changed, missing or unreadable evidence must not be treated as Enabled because an earlier decision exists. Define invalidation before wiring persistence.

The new restoration route must remain unavailable until the preservation/ownership gaps and native completion cases are resolved. This does not change existing Install/Repair behavior or the current operation engine. It prevents the new design from promising a narrower or safer operation than the implementation supports.

## Bounded implementation sequence

1. **Maintenance inspection contract and inline retry.** Carry bounded confirmed causes from the existing native readers. Present access denial, missing state, failed collection and unknown cause distinctly. Keep the current finding visible while rechecking; prevent duplicate submissions and late navigation changes. Use normal read authority only.
2. **Explicit leave-disabled decision.** Define the per-user display receipt and its context/invalidation rules. Save only after an explicit choice. Retain truthful scheduler state, history and independent tool readiness. Test record tampering as non-authoritative input.
3. **Full-operation preservation and ownership.** Address the runtime, launch-target, preference and project-reference gaps above using the accepted contracts. Keep unsupported actions unavailable. Do not add a selective repair engine or a privileged schedule-only endpoint to avoid these requirements.
4. **Restoration review and continuation.** Show the real full operation and all affected categories before approval. Reuse ordinary permission, native admission and journals. After completion, automatically read scheduling again in the same flow. Clear the restoration finding only on the required fresh scheduling evidence; operation exit success is insufficient.

The next code increment is item 1. Items 2–4 remain separate completion criteria; a read-only retry does not settle them.

## Required evidence before restoration is complete

- Windows 11 and actual Mint disabled/missing/access-denied/unknown cases; observed enabled-but-inactive state where applicable.
- A resolved unknown inspection that returns Disabled, without automatically restoring or dismissing the newly confirmed disabled state.
- Before/after comparisons for explicit/unset Git preferences, JSONC/absent/unreadable editor preferences, extensions, runtime defaults/managers and foreign application targets.
- Existing clean/dirty projects, worktrees, forks, moved/disconnected locations and changed selections; no duplicate clone or lost work.
- Disabled/custom schedule ownership, catch-up behavior and the protected SDE app-update policy. Keep earlier outcomes visible; do not infer successful updates.
- Cancel, denied permission, native deferral, uncertain launch, failed system/profile phase, incomplete follow-up check, duplicate click and late result. Keep failures in the flow with a useful next action.
- Existing Windows/Mint native, both trust jobs, integrity, acceptance and exact-main gates. Human signing approval, owner UAT of the exact authenticated candidate and separately authorized stable promotion remain required.

## Verification of this audit

This is a source review at the pinned commit, with links to the actual first-party entry points. No provisioning, scheduling change, privileged operation or owner-machine experiment was run for this audit. The successful exact-main run is existing implementation evidence; it does not replace the additional preservation/restoration cases listed above.

Only this Markdown reference changes. Current CI policy assigns it lightweight reference validation. Runtime, dependencies, workflows, versions and all release gates remain unchanged.

## Extension preservation increment

The follow-up profile phase now reads the installed VSCodium extension IDs before
installing a required extension. Both [Windows](../windows/chocolatey/tools/EditorExtensions.ps1)
and [Mint](../linux/lib/common.sh) keep existing IDs, including personal entries,
and compare IDs without regard to case. They install only missing required IDs,
without `--force`. Existing versions and disabled choices are not deliberately
reinstalled, upgraded or enabled by this step. A failed installation stops the
remaining extension work; it does not retry or claim the profile phase completed.

The Windows profile and legacy Chocolatey configuration entries share the same
helper. Deployment copies that helper with the other maintained scripts; the
existing native migration fixture checks its installed presence. Benign CLI stderr
is kept as diagnostic output, while stdout and the process exit code determine
whether inventory succeeded. A legacy extension-install failure now fails its
configuration stage instead of only warning and continuing.

The entire required list and installed inventory are checked before installation.
An unsuccessful query or malformed inventory stops the step, rather than becoming
an empty list. Empty required lists run no extension query. Required lists accept
at most 64 KiB and 256 entries; accepted inventory text is limited to 1 MiB and
bounded IDs. The ordinary Windows profile still refuses elevation. Mint uses the
requested normal user and HOME for its query and installation calls. The existing
CLI selection is unchanged; this is not a new installation-selection or ownership
contract.

This addresses extension reinstallation in the scope table above. The owner’s
Windows file-name visibility exception above resolves Explorer policy; its final
UI disclosure still needs release evidence. Runtime/default/foreign-launch
ownership, saved project locations and maintenance restoration remain open. The existing native required-
extension validation and automatic operation follow-up checks remain required;
an installed ID alone is not proof that every extension feature works. No new
restoration button or narrower Repair promise is introduced.

Local tests execute the production Bash function with an isolated CLI recorder:
existing/foreign and case-varied IDs, missing/duplicate entries, empty policy,
failed/malformed inventory, malformed/oversized policy, failed installation and
the normal-user command path. The eight new cases bring metadata coverage to 76.
Backend contracts 35, CI-policy 35, Bash syntax/static analysis, integrity and
offline documentation checks pass. Windows has the corresponding production-helper
command-recorder tests in its existing metadata checks; native CI must execute
them. Existing real standard-user profile fixtures keep their controlled empty
extension policy and now copy the Windows helper too. Those fixtures verify
profile preservation, not a real marketplace download or installed-extension UAT.
Full Windows/Mint, trust, integrity, acceptance and exact-main gates remain required.

## Windows disclosure in operation review

The application review now uses
[WindowsFilenameDisclosure](../installer/src/WindowsFilenameDisclosure.tsx) before
Install, Repair and development-tool Update approval. It explains why complete
filenames matter, names examples, and says that the profile step enables
extensions if they are hidden. It explicitly identifies the required setting as
an exception that can replace the current preference. The note is visible in the
review, rather than hidden in technical details.

The application supplies its detected platform label. Mint receives no Windows
setting claim. The note is presentation only: it offers no checkbox or setting
writer, acknowledges no uncertainty, changes no preflight or native admission,
and leaves the existing required Windows visibility check intact. Existing
Cancel/Back and explicit approval actions retain their behavior. App-only update
handling is unchanged.

Four new unit cases cover disclosure before explicit Install approval, blocked
Update/cancellation, platform scoping and retained uncertainty acknowledgment.
Two narrow/wide browser cases exercise all three real application review routes,
keyboard navigation, cancellation, order before approval, accessibility/layout
and zero modifying calls; the Mint review is checked separately. Original test
assertions and inventories remain intact. Full required inventory is now 415 unit
and 148 browser cases. Full native/trust/integrity/acceptance and exact-main
validation remain mandatory. This implementation is not exact-candidate owner
UAT or approval to sign or promote the release.

Local evidence: all 415 unit cases, two new disclosure browser cases and four
existing guidance browser cases pass. Build/type check, audit zero, backend
contracts 35, metadata 76, CI-policy 35, offline docs and diff checks pass. Full
148-case browser/native evidence remains a CI requirement.
