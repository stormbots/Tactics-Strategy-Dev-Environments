# Recovery: final integration review and consolidation gate

Branch `codex/recovery-integration-review`. This final bounded T9 review passed
at `d4bb9953f2ea064f50c9cd2088dd8ebe17d9a408` in
[Build 41259004375](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41259004375):
175 frontend/105 browser checks, root Linux 151/151, Windows trust 136/136,
native Tauri Windows 106/106 / Linux 104/104 and all inherited gates passed.
The complete stack was consolidated through #139 as main `f6befee` with the same
tree. Continue with the [v1.2.20 preparation ledger](RECOVERY-CANDIDATE-1.2.20.md);
the historical correction and review below remain the audit trail. This is not
another recovery architecture phase or owner UAT acceptance. The focused owner sheet is
[RECOVERY-FOCUSED-UAT.md](RECOVERY-FOCUSED-UAT.md); historical UAT results and the
old v1.2.19 diagnosis-only guide are not rewritten.

## Accepted baseline

PR #138 is accepted at `bc778cda49287c9f8e07aaac9ac6eb322c27540f` in
[Build 41252483028](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41252483028).
The live head matches that source. All applicable jobs succeeded: 172 frontend,
101 browser, root Linux coordination 151/151, Windows trust coordination 136/136,
and native Tauri Windows 106/106 / Linux 104/104. Both native signed upgrades
passed. Actual Mint 22.3 emitted bootstrap, read-only Validation, manual-supervisor,
scheduled-tool, application-install and signed-upgrade markers; Windows emitted
the corresponding feasibility/bootstrap/manual/Validation/scheduled/application
and signed SYSTEM-upgrade evidence. The separate policy/helper workflows passed;
their scoped fixture skips do not replace the required native Build evidence.

## Integration review

This review follows the existing T1–T8 contracts through their public callers and
tests, with prior exact-head native results retained in the engineering ledger.
It does not treat a UI observation, report, successful unit harness or artifact
name as privileged execution authority.

| Approved requirement | Implementation / review evidence | Remaining gate |
| --- | --- | --- |
| Prompt-free, incident-bound acknowledgment; machine and account stay separate | ADRs 0001/0002; `recovery_state`, `recovery_acknowledgment`, `recovery_user`; real standard-user storage/privileged-consumer tests | Real installed GUI and normal OS dialogs in UAT |
| Retain originals, reject changed generations, preserve across commit crashes | Shared coordinator recovery/acknowledgment/mutation tests; account journal/store tests; immutable evidence precedes retirement | Inherited native CI must stay green on final source |
| Active/unknown activity and known damage block; unknown health alone warns | `safety`, `observations`, `inspection`, `guidance`, `recovery_state`, `recovery_preflight`; all decision rows tested | Actual restart provenance on owner's Windows machine, not inferred from simulated comparisons |
| Manual Install/Repair/Update, scheduled tools and application installer share the protected transition | `manual::run_trusted_backend`, updater `tool_coordination`, `installation_coordination`, Linux/Windows install adapters; required installed/manual/scheduled/application markers and signed upgrades | Final combined-main native workflow; no partial-stack candidate |
| Validation does not acknowledge or clear; diagnoses retained journals when safe | Required Windows and actual Mint read-only Validation markers; App successful-Validation/no-acknowledgment tests | Focused retained-Windows-incident check |
| One acknowledgment automatically attempts the summary; failures remain distinct | Native controller capture/save/submit order, save-failure and unconfirmed-result tests; App simultaneous-source/partial-result tests; actual Validation collection time | Local save, native export chooser and optional sharing UX in UAT |
| Reports/history survive restart; explicit selected deletion never clears operational evidence | `recovery_reports`, `recovery_history`, `history_views`, account history; source-separated browser deletion/cancel/focus/escaping tests | Real exported HTML/open interaction in UAT; limitations below remain explicit |
| Continue only the intended in-memory request through ordinary review | App refreshes findings before review and after confirmation; stale/partial consent stops; Cancel/Check Again never replay; non-start and uncertain-child tests remain required | Final UI fixes below and exact-head CI |
| Reuse Overview status and existing Recovery navigation | Existing single status card and persistent Recovery access; browser themes/compact reflow/axe; summary warnings stay visible outside Recovery | Final warning-reason/startup-return regressions below |

The application-update discovery card opens release notes/download in the browser;
it does not invoke privileged installation or consume consent. Download verification
remains necessary and is described without requiring mentor service.
The actual scheduled application installer uses the protected updater transition
and retains signature, policy/pause, identity, nesting and native postchecks.

### Corrections found in this review

1. Unknown package health made the existing Overview card yellow but supplied no
   reason when the request was otherwise eligible. Show **Package health remains
   unverified — Review Recovery** inside that card. Keep **Ready!** for successful
   Validation and do not revive the old incident warning, including while matching
   machine intent awaits protected commitment. This is a warning, not an extra
   acknowledgment or universal package-health certificate.
2. Successful startup acknowledgment with no requested operation remained on
   Recovery. Return to Overview only after fresh findings admit normal native
   recheck. Do not launch Install, open its preflight or replay a prior request.
   Both source types are tested; report-save warnings remain visible and Recovery
   stays accessible. Blocked/unconfirmed/partial/stale results keep their existing
   safe behavior.
3. Schedule/application-update diagnostic labels and native status guidance still
   instructed users to obtain mentor service. Replace that copy with Recovery,
   refresh, protected-log/support and platform-specific guidance. Keep explicit
   authentication, pause, package-lock, failed-result and unconfirmed-setting
   cautions. Download verification remains mandatory, not delegated to a mentor.
   Remove the unused legacy `recoveryAction` helper and its superseded tests that
   incorrectly treated passing Validation as resolution. The actual native-state
   and App tests continue to require no acknowledgment/clearing from Validation;
   no active safety assertion is weakened.

No native safety policy, gate/nesting semantics, report storage, journal lifetime,
workflow requirements or privileged permissions change in this increment.

## Local validation for this increment

- 175 frontend tests passed, including both startup source types, pending versus
  committed machine acknowledgment, preserved report warnings and three update
  coordination states without mentor-service instructions.
- Production TypeScript/Vite build and selected-file Prettier checks passed.
- Four updater observation tests passed; the new regression keeps authentication,
  package-lock, pause and no-fabricated-success guidance explicit across every
  failure phase. No privileged/package operation was invoked by these tests.
- 35 backend source contracts, four command-permission checks and whitespace
  checks passed. Native/browser reruns remain CI work; local Playwright browser
  binaries are known absent and were not repeatedly probed.

### Initial CI correction

Initial head `5ae004e31c084e8c58962bbaf050202313620d1d` failed
[Build 41256546151](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41256546151).
Four Recovery browser cases expected yellow while using the default partially
installed preview with actual failed Validation rows. The correct red status
must take precedence; this was a fixture/assertion mismatch, not a production
severity defect. The other 97 browser checks, both native/trust jobs and both
signed upgrades passed, but the incomplete full workflow is not accepted.

The correction requires red in those existing cases and separately overrides
only the browser fixture's `inspect()` result with successful Validation to prove
unknown-health-only yellow/Ready! and keyboard access to its reason on both
themes and widths. Every other bridge export remains the original preview.
No production behavior, package/coordination state or inherited gate changes.
Replacement-head complete CI is required; no blind retry or waived assertion.

Fetched `main` at `3b0e8d7ec05d1b6d62535cb5b1368056abe3ac04` is an ancestor
of the cumulative branch with no additional main-only commits at review time.
Recheck live ancestry during consolidation; this is not permission to overwrite
later unrelated work. Exact new-head workflow evidence belongs in its PR checkpoint.

## Explicit compatibility limits (not hidden clearance paths)

- Old installed software cannot install its own recovery redesign merely because
  newer code exists. Deploy the authenticated application installer through its
  normal OS authorization. Bootstrap preserves private legacy evidence; it does
  not grant consent. A legacy baseline may require a further normal Restart.
- Restart establishes only an earlier process lifetime, not package health or
  completion. Detection covers the reviewed native sources, not every conceivable
  detached third-party installer. Fresh execution checks and native package locks
  remain mandatory, including after a warning is acknowledged.
- Corrupt/unreadable operational evidence cannot be acknowledged by guessing an
  identity. Source-specific diagnostics/support remain available; no universal
  self-service corruption repair or deletion override is promised. An owner UAT
  blocker must report the precise finding, not manufacture a pass.
- Ambiguous duplicate generations, unavailable historical sources and bounded
  lookup overflow remain visibly unknown/unavailable. They lack a selected-view
  deletion token rather than arbitrarily selecting a generation. No age/count
  purge occurs. A hidden history view or deleted report is not evidence removal;
  current findings and minimum decisions remain independent and protected.
- Per-account files follow the implemented native profile trust checks. Standard
  Windows profile inheritance is not a claim of protection against a local
  administrator; machine journals/receipts keep their separate protected ACLs.
- Browser fixtures cannot certify real UAC/polkit cancellation, native dialogs,
  a real restart or the owner's historical machine. Those belong to focused UAT,
  not another synthetic test requirement for the owner to manufacture.

## Finite next steps

1. Run targeted frontend tests/build and require the existing complete Build on
   this exact head, including all inherited native/trust/installed/recovery and
   signed-upgrade gates. End while long CI is pending; record head and run in PR.
2. On success, consolidate the complete verified cumulative stack, preserving any
   unrelated main changes. Confirm the effective diff and ancestry before choosing
   the squash/consolidation target; do not merge a partially functional increment.
   Require full Build success on the exact resulting combined `main` commit.
3. Inspect live tags/releases, choose an unused candidate version, and use the
   existing protected candidate workflow. Never overwrite v1.2.18 or another
   published candidate. Check for duplicate dispatches first; follow the separately
   authorized release-branch/candidate procedure and retain its evidence ledger.
4. Stop before protected signing approval and provide the owner the precise run
   URL/action. After owner approval and authenticated publication, supply the
   focused UAT sheet with exact candidate identity, hashes and install instructions.

No new product decision is required for these corrections. Signing, owner UAT,
stable promotion, fleet rollout and milestone closure are not completed by this
review. Windows interruption evidence and Mint v1.2.18 **35/0/0** remain untouched.
