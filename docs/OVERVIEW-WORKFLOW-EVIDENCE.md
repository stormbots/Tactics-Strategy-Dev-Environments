# Guided Overview workflow evidence — #150

Status: **#150 automated/native audit accepted; candidate/owner acceptance pending**.
All 31 rows began Not run. Results below identify each tested boundary and limit.
No signed candidate, owner observation, publication or promotion is implied.

## Source and execution record

- Planning baseline: `d7cd425f56a992a233804132eeadd2918fe25cd3`.
- Integrated source S: `6e251b771c13b40ae5c62c76703ff47084e33db1`.
  #147–#149 are closed; implementation PRs #152, #155 and #156, with supporting
  CI-policy/contract corrections #153/#154.
- Exact PR head H: `fcf7139ba7e434c8f1855f43d701a1abfc88d6ae`,
  [Build 42905897948](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42905897948), all applicable jobs passed.
- Exact-main S: [Build 42914368941](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42914368941),
  all applicable jobs passed; release correctly skipped. Required `checks` and
  `acceptance` were confirmed on H before protected merge. No bypass/retry used.
- New combined-browser evidence C: `workflow-combinations.spec.ts`, added on
  `codex/150-workflow-evidence` from S. Local system-Chromium: **4 passed**, 100 combined state/theme/width/zoom
  observations and 20 screenshots. The existing 32 state/zoom/accessibility
  regression cases and production build also passed locally. Exact audit head
  `5a7c4a6ed030c3be97635f8c0b3e49ab490000cc`, PR #157,
  [Build 42922753860](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42922753860)
  passed all applicable jobs, including 124 browser cases. Merged audit source L
  `84a5ce3f24f5381a2651408853c8d051c9b4be28` has final-main
  [Build 42949291295](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42949291295)
  passed all applicable jobs.
- Final integrated source F: `8e3c4463a475ed9fc7f89c88669fb12c129cf618`,
  [Build 42959957444](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42959957444),
  all applicable checks, Windows/Mint native, both trust and acceptance passed;
  release correctly skipped. #150 closed after reviewing the actual markers.
  Native-fixture PR #158 exact head `694b9bfc12534ea7aff5d8e0eb9d79fd89f907a0`,
  [Build 42951512266](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42951512266),
  also passed. The [acceptance record](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/150#issuecomment-6787445934)
  and [row reconciliation](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/150#issuecomment-6787128032)
  identify the evidence review and reuse limits.
- Candidate/version/assets/digests/signature/owner accounts: **Not run / not assigned**.
  Source baseline S is not a release-candidate identity.

Existing results at S may be reused only for unchanged code/tests and their stated
layer. C passed its own exact audit head and final-main runs. Subsequent application changes
require affected tests plus normal exact-head and final-main CI, never inference
from this baseline. Actions artifacts expire; job links and the assertions below
identify the retained evidence without publishing private logs or journal bytes.

## Evidence key and platform/account context

Codex owns A/N evidence. Owner alone owns O acceptance. In the table, A Pass and
N Pass describe the cited boundary only. **Partial** means the workflow still has
a missing integrated/native observation. Every O row is Not run on an identified
signed candidate; a safe naturally available owner journey is not fault injection.
The prototype supplies no execution evidence.

| Key | Exact source, execution and responsible layer | Actual result and limit |
| --- | --- | --- |
| A | S, [checks job](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42914368941/job/130172957100); production React with synthetic bridge observations, Chromium; WebKit only sidebar/self-update-setting | Pass: 262 unit tests, 120 browser cases, production build and contract checks. Browser fixtures do not invoke native commands or display real OS approval. |
| D | A: `installer/src/overviewDecision.test.ts`, `operationLifecycle.test.ts`, `App.test.tsx` | Pass: current-complete validation, all native blocker precedence, request identity, actual App dispatch, failure/review/reopen/duplicate guards. Pure decision coverage is not browser or native execution. |
| B | A: `installer/browser-tests/overview.spec.ts`, `operation-lifecycle.spec.ts`, `validation-guidance.spec.ts`, `update-discovery.spec.ts` | Pass: actual frontend renders/dispatches, synthetic observations, light/dark 390/1140px; screenshots and axe/reflow. |
| X | A: `zoom.spec.ts`, `accessibility.spec.ts`, appearance/sidebar/theme tests | Pass: supported 90/100/115/130/150% zoom, keyboard, labels, contrast, reflow, progress and completion. Installed assistive-technology observations still O. |
| R | A: recovery/incident/history/view-deletion browser tests and App/recovery unit tests | Pass: retained reports, source-specific results, privacy, optional sharing/export/deletion confirmations and no operation side effects at the frontend boundary. |
| W | S, [Windows native job](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42914368941/job/130175234751), disposable Windows Server 2022, elevated runner plus actual standard-user/SYSTEM probes | Pass: native app tests 106/0, installed bootstrap/manual boundaries, signed SYSTEM upgrade and standard-user status. Server 2022 is not owner Windows 11 desktop UAT. |
| M | S, [Linux native job](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42914368941/job/130175234460), Ubuntu build host plus actual Mint 22.3 userland from official media, root and unprivileged probes | Pass: app tests 104/0, installed bootstrap/manual/read-only validation on host and Mint, root signed APT upgrade. Mint container is not a rebooted Cinnamon desktop. |
| T | S, [Ubuntu trust job](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42914368941/job/130175234520) and [Windows trust job](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42914368941/job/130175234582), required coordination/storage contexts incl root/standard-user probes | Pass: fresh admission, real child supervision, source/generation binding, protected storage, durable acknowledgment, signatures/tampering, staging and cleanup. See named tests below. |
| U | W/M: `updater/src/windows_install.rs::signed_upgrade_under_system`, `linux_install.rs::signed_upgrade_on_native_mint` | Pass: actual package upgrades with fixture signing keys, synthetic 1.2.2/1.2.3 payload identities, trust rejection/deferral/failure retention, project/settings sentinels. Not a historical released-binary or final human-approved candidate-pair pass. |

### Named native assertions and markers

These executed at S; references are production tests, not a new equivalent model.

- Launch: `installer/src-tauri/src/launch_outcome.rs` tests require complete
  Polkit capture and no helper entry, or Windows OS cancellation without a
  process handle. `process.rs::authorization_capture_disambiguates_real_helper_exit_and_incomplete_output`
  executes real helper processes. This does not exercise the graphical UAC dialog.
- Completion: `process.rs::helper_completion_requires_controlled_success_and_fresh_native_inactivity`
  and `coordination/src/safety.rs::known_backend_completion_requires_success_inactivity_and_no_known_damage`.
  `main.rs::run` reports `completed` only with successful complete validation,
  collection time and its journal/native checks. Defensive completed/failed
  frontend Reports are not an emitted native state. Unproven failures stay uncertain.
- Admission/races in `coordination/src/mutation_tests.rs`:
  `mutation_run_rechecks_current_native_activity_and_aborts_before_any_child_is_started`,
  `mutation_rechecks_after_acknowledgment_persistence_before_retiring_the_original`,
  `mutation_runner_failure_keeps_unknown_intent_and_active_check_precedes_callback`,
  `mutation_preparation_transfers_installation_leases_without_a_gap`.
- Retention: `mutation_retains_original_object_and_receipt_then_creates_distinct_new_intent_under_the_lease`,
  `mutation_finish_known_cannot_remove_a_different_transaction`,
  `durable_acknowledgment_old_receipt_cannot_acknowledge_a_replacement_generation`
  in coordination tests. Public intent and UI review never mint execution authority.
- Restart: `inspection::tests::native_restart_provenance_and_package_activity_are_available_on_required_runners`
  reads native sources. Restart-comparison fixtures require both Windows signals;
  actual reboot/reconnect of a running UI was **not observed** in these jobs.
- Summary/consent: `recovery_acknowledgment.rs` tests one report before submission,
  saved-report warning versus unconfirmed consent, separate failures and no retry.
  `recovery_reports.rs`, `recovery_user.rs`, `history_views.rs` test production
  storage, hardlink/ACL rejection, retained evidence and source/generation identity.
- W includes `SDE_RECOVERY_WINDOWS_STANDARD_USER_INTENT_OK`,
  `SDE_RECOVERY_WINDOWS_PRIVILEGED_CONSUMER_OK`, installed bootstrap,
  `SDE_RECOVERY_WINDOWS_MANUAL_MAINTENANCE_OK`,
  `SDE_RECOVERY_WINDOWS_MANUAL_INSTALL_REPAIR_OK`, `SKYVIEW_SYSTEM_SETUP_OK`,
  `SDE_E2E_NATIVE_WINDOWS_OK`, `SDE_SIGNED_SYSTEM_UPGRADE_OK`,
  `SDE_STANDARD_USER_STATUS_OK`. Workflows require the corresponding markers.
- M includes `SDE_RECOVERY_LINUX_INSTALLED_BOOTSTRAP_OK`,
  `SDE_RECOVERY_LINUX_READONLY_VALIDATION_OK`,
  `SDE_RECOVERY_LINUX_MANUAL_SUPERVISOR_OK`, `SDE_E2E_NATIVE_MINT_OK`,
  `SDE_NATIVE_MINT_UPGRADE_OK`, `SDE_MINT_HISTORY_HOOKS_OK`.
  W/M include `SDE_RECOVERY_APPLICATION_INSTALL_CONTRACT_OK` and
  `SDE_RECOVERY_SCHEDULED_TOOL_CONTRACT_OK`.
- U compares project/settings bytes before and after the successful upgrade.
  Failure payloads deliberately exit 23 / fail postinst and must leave interrupted
  state blocking retry. Those expected errors are passing safety assertions.
  Installed manual supervisor fixtures use synthetic no-package children: they
  prove real nesting/privilege/admission, not full tool provisioning or user-profile
  preservation across Install/Repair.

## WF01–WF31 ledger

Every row records its original S evidence and A/N contexts above. Unchanged
code/tests are additionally covered by F's full final-main run; C has its own
exact-head/final-main evidence. N2 below supplies the new G1/G2 observations at F,
without treating separate browser/native layers as a packaged desktop pass. Expected
behavior comes from the unchanged [UAT matrix](OVERVIEW-NEXT-STEP-UAT-DRAFT.md#5-workflow-coverage-matrix).
Actual result records only assertions exercised. O remains Not run for **all**
owner-designated rows; exact installed candidate/platform/account is still absent.

| Workflow / expected result | A fixture and actual result | N fixture and actual result | Remaining observation / disposition |
| --- | --- | --- | --- |
| WF01 — read-only bounded startup, no redundant validation | D startup pending/retry/App tests; B checking/unavailable. Pass: no mutation and no fake incident. | W/M installed read-only validator and IPC permission tests; T absent-account inspection. Pass at boundary. | O natural startup Not run. |
| WF02 — existing tools ready without account history | D `existing tools are ready without account history or package-health proof`; B ready. Pass. | T `recovery_absent_account_state_does_not_require_creating_a_gate`; W/M real validation. Pass at respective boundaries. | No new-account fully provisioned packaged UI observation. Keep layer limit. |
| WF03 — review/back, one install, real verification before Ready | D Back/duplicate/verification; B install progress/result. Pass. | W/M manual admission/native completion Pass; N2 real system/profile preservation Pass. Full installed GUI journey Not observed. | N2 real system/profile sentinels Pass; installed UI journey remains O / Not run. |
| WF04 — partial setup preserves projects/settings with honest scope | D/B preflight full-scope review. Pass frontend. | N2 real Windows system Install and Windows/Mint profile sentinels Pass; U app-upgrade proof stays separate. | N2 supplies actual shared profile proof; do not reuse upgrade sentinels as full Install/Repair UI proof. |
| WF05 — ready/editor/workspace without setup | D single optional action/editor destination; B ready; existing destination contracts. Pass. | W/M native allowlisted destination/permission contracts. Boundary Pass. | O actual editor/workspace launch Not run. |
| WF06 — installer success alone never Ready | D partial/summary mismatch/uncertain mutation tests; B incomplete. Pass. | W/M protocol and helper completion checks; T known-success policy. Pass. | Contradictory completed Reports remain defensive frontend cases. |
| WF07 — failed/delayed collection is incomplete, fresh results win | D App retry and generation tests; B unavailable/incomplete. Pass. | W/M validator nonzero/summary and safe-failure contracts. Pass boundary. | No artificial native completion time invented. |
| WF08 — explicit repair, full scope, cancel and preservation | D repair review/unresolved tests; B guidance. Pass. | W/M installed manual Install/Repair wrappers/nesting Pass; N2 shared profile preservation Pass. | No full native repair/GUI pass inferred from app upgrade; shared profile and admission proofs are separate. |
| WF09 — unresolved repair has diagnostics, no repair loop | D `retains an unresolved repair and download diagnostics without an automatic repair loop`; lifecycle decisions. Pass. | T runner failure retains intent; W/M actual nonzero child tests. Boundary Pass. | Current native completion requires passing verification; the unresolved-finding dispatch fixture remains honestly uncertain. No contradictory completed native Report is invented. |
| WF10 — unsupported finding/incomplete package is not generic Repair | D validation guidance; B attention/native-incomplete. Pass. | T known damage/admission denials; U failed package blocks retry. Pass. | C combined browser blocker proof passed on the exact audit head; L and F final-main passed. |
| WF11 — exact optional-update copy, cancel, editor alternatives | D exact-copy/single-action; B updates/preview. Pass. | W/M preflight/native managed-update contract. Boundary Pass. | O naturally available updates Not run. |
| WF12 — reviewed update scope, normal authorization, fresh remaining state | D changed fingerprint/verified outcome recomputation; B changed options/update preview. Pass. | W/M manual supervisor and update/preflight contracts Pass; N2 failure/retention boundary Pass with controlled payload. | No whole tool update GUI pass or public-feed outage inferred; distinguish N2 from U app upgrades. |
| WF13 — declined/partial update is uncertain, no automatic replay | D operationLifecycle native flags and error handling; B uncertain result/review cancel. Pass. | W/M launch proof/nonzero helper and T retention Pass; N2 actual before/after-change failure Pass. | N2 retains uncertainty/partial bytes, with no automatic retry or safe-cancellation promise. |
| WF14 — unknown tool discovery separate from app updates | D update discovery/guidance; B update-discovery/self-update-setting. Pass. | T updater observation/policy tests. Pass boundary. | No new update default or pause/resume authority. |
| WF15 — active operation blocks mutations, diagnostics remain | D safety combination; B active. Pass. C all zoom/combined checks Pass on the audit head. | T real cross-process gates/current-activity-before-child; W/M nesting. Pass. | No process-killing/restart instruction added. |
| WF16 — unknown lifetime remains uncertain; restart not repair | D/B unknown/recovery guidance. Pass. | T required native provenance reads/comparisons and unknown-state admission Pass; actual reboot Not observed. | G3 applicability/limit reconciled above; owner only naturally present state. |
| WF17 — unavailable/untrusted records fail closed, diagnostics accessible | D App unavailable/source-specific guidance; B untrusted. Pass. | T real storage links/ACL/native denials. Pass. | C cross-zoom diagnostics Pass on the audit head. |
| WF18 — acknowledgment preserves original source evidence, no execution | D two-source App/recovery tests; R incident/report behavior. Pass. | T real standard-user intent, privileged consumers, durable generation binding; W/M feasibility. Pass. | O natural incident only; no owner fault manufacture. |
| WF19 — summary save versus consent failure/partial success | D App partial/unconfirmed/no replay; R reports. Pass. | T native acknowledgment controller and production store failure tests. Pass. | Saved report reference is not a mutation permit. |
| WF20 — changed evidence caught at confirmation and execution | D fresh confirmation/changed scope/options; B rereview. Pass. | T no-gap lease transfer, fresh safety after persistence and before child. Pass. | C retains combined reasons; no stale UI permit. |
| WF21 — safety priority over pass/missing/update combinations | D six-blocker combined matrix. Pass; B individual states Pass; C combined browser matrix Pass on the audit head. | T `all_policy_combinations_keep_safety_independent_of_acknowledgment`, real child denial. Pass boundary. | C passed on the audit head; retain the separate L final-main gate. |
| WF22 — unknown package health/history is not an invented incident | D maintenance/unknown-health; B recovery clear. Pass. | T `recovery_unknown_health_alone_warns_and_snapshot_never_leaks_private_binding` and absent account/source tests. Pass. | O clear state Not run. Historical clear-state acceptance separate. |
| WF23 — Back/Cancel no work; only native proof establishes non-start | D cancel pending inspection/unmount/native-only outcomes; B cancel/reopen. Pass. | W/M process capture/Windows handle outcome policy; journals retained for uncertainty. Pass native proof boundary. | Actual graphical deny dialog Not observed, not an automated dialog pass. |
| WF24 — network before/after changes preserves uncertainty/evidence | D transport/download diagnostics, no retry; B uncertain result. Pass frontend. | N2 real HTTP failure before/after synthetic mutation and journal/retry denial Pass; U package failure proof separate. | Controlled native network boundary proved by N2; public package-feed outage / installed UI failure not induced. |
| WF25 — navigation/rapid clicks keep one real operation and progress | D duplicate/nav/actual-phase/late-stream; B operation-lifecycle and zoom active-log. Pass. | T actual cross-process leases and detached supervisor/child lifetime. Pass boundary. | O normal navigation Not run. |
| WF26 — reopen forgets intent, reconstructs fresh, no saved success | D unstarted/active reopen; B reload. Pass. | T durable evidence, required provenance comparisons and real supervisor crash Pass; rebooted UI Not observed. | G3 applicability/limit reconciled above; no invented reconnect percentage or replay. |
| WF27 — out-of-order observations cannot overwrite or repurpose focus | D request/epoch/late-stream and focused editor action; B scenarios. Pass. | T source/generation views and stale token rejection. Pass. | O keyboard/focus observation Not run. |
| WF28 — secondary/diagnostic routes preserve scope and shared guards | D App busy/shared dispatch; B/R navigation/details; C combinations Pass on the audit head. | W/M allowlisted IPC, T native admission. Pass boundary. | O route walkthrough Not run. |
| WF29 — reports/history/optional sharing distinct from operational evidence | R report privacy/cancel/history deletion; App retained receipt. Pass. | T protected report/history/user store tests, no journal deletion. Pass. | O safe report/history walkthrough Not run. |
| WF30 — keyboard/focus/themes/zoom/reflow/announcements | X/B/R: axe and keyboard/layout tests Pass, C combined every-zoom audit Pass on the audit head. | No native desktop screen-reader interaction asserted. | O installed keyboard/assistive technology Not run. |
| WF31 — installed candidate identity/upgrade/preservation/policy | B About/Schedule/launch routes Pass, no actual release identity claim. | U real fixture signed upgrade/sentinels/policy Pass; final candidate pair Not run. | #151 candidate identity/signature/owner installation; historical binaries not substituted. |

## Native fixture follow-up — N2 at accepted F

Branch `codex/150-native-outcome-fixtures` was based on L. Both exact PR head
and final-main F passed, with actual markers reviewed. New source-specific proof:

| Context at F | Final-main evidence / actual result |
| --- | --- |
| Windows Server 2022, real system Install and standard-user profile | [Native job 130325396073](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42959957444/job/130325396073): system/profile preservation markers and original signed SYSTEM marker Pass |
| Ubuntu host plus actual Mint 22.3 root/unprivileged profile contexts | [Native job 130325395852](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42959957444/job/130325395852): profile preservation in both contexts; before/after HTTP failure markers in Mint; original signed upgrade Pass |
| Windows native guard/transport | [Trust job 130325395843](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42959957444/job/130325395843): named before/after failure-retention test Pass |
| Ubuntu required root native guard/transport | [Trust job 130325395815](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42959957444/job/130325395815): named before/after failure-retention test Pass |

- G1 Windows: `tests/Test-Node24MigrationCI.ps1` now places synthetic project
  and editor-setting sentinels before its existing real system Install. It checks
  exact hashes afterward (`SDE_SYSTEM_PRESERVATION_WINDOWS_OK`). The normal
  Users workspace ACL is applied only when creating the disposable data root;
  no coordinator ACL or existing data is relaxed.
- `tests/Test-ProfilePreservationCI.ps1` runs byte-identical copies of the real
  profile/repository/coordination scripts twice under a real fresh standard-user
  token. Projects, JSONC settings and Git identity must survive, while disclosed
  Git/Explorer defaults are applied (`SDE_PROFILE_PRESERVATION_WINDOWS_OK`).
- G1 Linux: `tests/verify_profile_preservation_native.py` runs a byte-identical
  installed `Configure-SkyviewUser.sh` plus its real Git/jq/coordination code as
  UID 65534 with a synthetic home. It checks user precedence during baseline
  merge, the exact first backup, two invocations, JSONC preservation, project
  bytes, retained Git identity and disclosed defaults. The installed manual
  harness calls it on both Ubuntu and actual Mint
  (`SDE_PROFILE_PRESERVATION_LINUX_OK`).
- Profile fixtures use controlled empty extension lists and no remote clone.
  Linux CLI presence is a failing placeholder that must never be invoked. These
  tests cover the actual shared profile phase used by Install/Repair, not editor
  downloads, all development-package installations or installed GUI interaction.
  Existing native wrapper/scope tests and real package/upgrade gates remain
  separate. New profile helpers refuse a retained journal or unexpected repository
  policy rather than clearing/replacing them. No owner account is touched.
- G2: `coordination/src/mutation_tests.rs` starts an actual loopback HTTP server
  and actual child process. Before-change case returns HTTP 503 immediately;
  after-change case serves a synthetic tool payload, writes a real file, then
  returns 503. The production mutation guard must retain the same journal object
  and bytes, reject duplicate submission and block a fresh attempt even after
  its kernel gate becomes free. It never calls `finish_known` on those failures.
  Expected marker: `SDE_NATIVE_DOWNLOAD_FAILURE_RETAINED_OK` for **both** cases.
- The portable transport test passes locally with real HTTP and child exit 23.
  It does not exercise the privileged guard. Required root/Windows coordination
  CI executes the guard test; the existing Mint native job additionally builds
  and runs that exact test binary inside Mint with `SDE_REQUIRE_COORDINATION=1`,
  requiring both markers. Fresh safety facts are controlled fixture inputs;
  the gate/journal/child/filesystem/transport are real. This is a native failure
  boundary test, not an induced public Chocolatey/APT outage or a packaged GUI
  operation. Those evidence layers must stay distinct.
- G3 applicability review is complete: WF16/WF26 require independent native
  provenance and fresh reconstruction, and restrict deliberate restart/failure
  exercise to disposable fixtures. They do not add an OS-reboot automation
  mechanism to this UI milestone. Required real native source reads/stability,
  both-signal Windows comparisons, same-boot unknown-state denial, real child
  supervision/crash retention and App/browser reopen tests passed. ADR 0002 and
  the inherited integration review explicitly distinguish those proofs from an
  actual reboot. Real OS reboot plus desktop reconnect remains **Not observed**;
  it is not relabeled as a pass. No native assertion/gate is waived, no missing
  signal or free lock grants execution, and owner UAT uses naturally available
  states without manufacturing an interruption.

## Defect found by this audit

C reproduced horizontal overflow for the native-untrusted status at 390px and
150% zoom in both themes: the status flex child retained its minimum content
width. The narrow scoped CSS fix allows that child to shrink and its long status
text to wrap; it does not hide overflow or remove evidence. C now passes all
100 combined state/theme/width/zoom observations locally, including the original
failure, and emits 20 screenshots. Existing state/zoom/accessibility regression
and authoritative CI are recorded in the PR/checkpoint. No native behavior changed.

## Reconciled coverage boundaries and remaining owner observations

Automated/native acceptance is limited to these proved boundaries. Every O
observation remains Not run for the exact authenticated #151 candidate.

| Gap | Required Codex work / safe context | Current status |
| --- | --- | --- |
| G1 — tool/profile mutation preservation | Disposable Windows and actual Mint fixture must exercise the applicable real Install/Repair/user-configuration boundary with project/settings sentinels and disclosed normal configuration changes. Existing installed manual tests use synthetic children; upgrade sentinels cover a different operation. Record exact command/account/pre/post evidence. | N2 Pass at exact head and final-main F; real Windows Install/profile plus actual Mint shared profile phase. Full installed GUI/tool-provisioning journey is not inferred. |
| G2 — actual managed-tool partial/network outcome | Native fixture injects controlled download failure before and after a permitted synthetic change through the relevant production runner/guard. Assert retained journal, no false completion and denied unsafe retry. Retain actual error/receipt proof; do not weaken package/native checks or equate app upgrade with tool update. | N2 Pass at exact head and final-main F on Windows, required root Ubuntu and actual Mint; controlled payload/safety inputs remain explicit. |
| G3 — restart/reopen provenance | Trace whether the workflow specifically requires actual reboot evidence beyond native source reads, strict comparison fixtures and supervisor-crash probes. If required, run a disposable supported restart fixture and retain independent provenance; never ask owner to manufacture interruption. | Applicability reconciled above; required native/reopen boundaries Pass. Actual rebooted desktop remains Not observed, not an added or waived CI gate. |
| C — combined browser accessibility | New `workflow-combinations.spec.ts`: missing essential + available update + each native blocker, two themes, 390/1140px, every supported zoom; one primary, no mutation shortcuts, retained diagnostics and zero operations. | Local 4/4 Pass; exact audit-head Build 42922753860 Pass (124 total browser cases); L and F final-main passed. |

No candidate preparation while unresolved unsafe authorization, false Ready,
data loss, replay, duplicates, inaccessible diagnostics or an unbounded loop is
known. Missing evidence is not automatically a code defect or approval request:
complete safe fixtures first and record residual limitations explicitly.

## Preserved gates and next handoff

The native follow-up only adds fixture execution to `build-dev-setup.yml`; it
does not remove or weaken any existing job/marker/condition. Keep `checks`, Windows/Mint
native, both update-trust platforms and `acceptance`, all required feasibility,
bootstrap/manual/scheduled-tool/storage/retention markers and signed-upgrade tests.
Do not relax unknown-path CI classification for this document or new tests.
Retain useful existing runs; no blind retries or continuous polling.

#150 is closed on exact-head and final-main F evidence. #151 now prepares
one identified candidate: `prepare-self-update-uat.yml` builds an unpublished
same-source 1.2.22 baseline and a 1.2.23 candidate. Only 1.2.23 may publish;
existing v1.2.22 assets/tags remain unchanged. Candidate-preparation source must
pass its own exact-head and final-main gates plus the native pair workflow;
this F audit is not a replacement for those new runs. Human signing approval
is mandatory; no self-approval through tools. Then independently verify pinned-key
signature and both payload hashes, provide the focused owner checklist and stop
for exact-candidate UAT. Stable promotion needs separate authorization.
Original Windows interruption evidence and historical Mint v1.2.18 35/0/0 remain
unchanged and are not acceptance of the guided Overview candidate.
