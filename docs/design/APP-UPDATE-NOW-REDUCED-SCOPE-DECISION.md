# #72 approved decision: fixed app-only update request

**Status:** Product/design direction approved by the owner on 2026-10-17.
**Issue:** https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/72
**Approval:** The owner approved the complete four-decision package in this
conversation: "I approve this design entirely."
**Authority:** This step records/publishes documentation only. Production code,
experiments, elevation, registration, package operations, build dispatch, release
preparation, stable promotion and rollout are not authorized by this decision.
Each implementation/execution phase below needs separate authorization.

## 1. Decision and relationship to earlier work

Replace the proposed bidirectional GUI/supervisor command protocol with **one
OS-authorized, fixed application-only update attempt**. The privileged worker owns
preparation, installation and recovery. Unelevated SDE reads protected progress
and cooperatively closes. There is no GUI privileged commit/cancel channel.

This is the active product direction for #72. It supersedes conflicting behavior
in the original issue acceptance criteria and revision-4 protocol, particularly
separate final-click commit authority and immediate cancellation. It does not
silently rewrite or satisfy those older criteria. The issue body/comments,
[original protocol](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/d260160/docs/design/APP-UPDATE-NOW-PROTOCOL.md),
[Phase 1 research ledger](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/d260160/docs/design/APP-UPDATE-NOW-PHASE1-VALIDATION.md), harnesses and evidence
remain historical context. Their dated statements and results retain their meaning.

The original Option A Schedule card / Option C preparation communication remain
the UI direction. This decision simplifies authority and lifecycle, not progress
communication. Approval of a design is not implementation or native validation.

## 2. Four approved product decisions

| Decision | Approved behavior |
| --- | --- |
| Upfront installation consent | OS authorization permits preparation and installation once every SDE session closes. Ordinary close or a GUI crash can satisfy closure; the later Close button is not another authorization. |
| No immediate cancellation | Remove Keep working, Later and Cancel actions after authorization. Keeping a window open prevents installation and eventually defers the attempt. Closing all windows before expiry may permit installation. |
| Deadlines | Fifteen minutes overall, beginning when the privileged bootstrap creates the authorized request; at most two minutes waiting for windows, beginning when admission closes. The earlier deadline wins. Suspend counts; reboot invalidates pre-install continuation. |
| Pause commitment boundary | Respect pause through the final validated policy check immediately before durable installation intent creation. A later pause applies to future attempts and does not cancel the committed attempt, even if the native installer has not yet started. |

These values are approved product defaults, not experimentally validated timings.
The final policy check, intent publication and native launch form a short local
sequence with no intervening network work or user interaction. If implementation
cannot maintain it, stop for design review. Failure/uncertainty during intent
publication or launch enters conservative recovery, not safe automatic retry.

The two-minute waiting period never extends the fifteen-minute overall period.
Use verified suspend-aware elapsed-time/boot semantics; clock uncertainty prevents
native launch. Actual OS authorization dialogs are outside the worker's fifteen-
minute period, which begins only at creation of the authorized request. No queued
request or reboot may revive or reset an expired authorization. Commitment must
occur within the pre-install deadlines; after commitment, expiration never kills
an installer or unlocks an uncertain transaction.

## 3. Consent and visible interaction

Before elevation:

> **Update SDE on this computer?**
> This prepares and installs the latest eligible SDE application update.
> Installation may begin once preparation succeeds and all SDE windows are closed,
> including if a window closes unexpectedly. After authorization, leave SDE open
> to defer this attempt. Development tools and maintenance settings will remain
> unchanged.

Actions: **Authorize update** and **Back**. Denial creates no installable request.

After admission is actually closed and preparation is complete:

> **Update ready**
> Close all SDE windows to install. Leave this window open to defer this attempt.
> New windows are temporarily blocked while the update waits.

Offer **Close SDE & install**, and show the remaining waiting period when reliable.
Do not provide Keep working, Later or Cancel buttons. Do not force-close existing
windows, terminate work or force reboot. A stale progress record never causes
automatic GUI closure. Ordinary closure/crash can permit installation under the
upfront consent. Another remaining session still prevents installation.

States: Checking, Authorizing, Preparing (Downloading/Verifying), Ready/waiting,
Deferred, Installing, Postchecking, Updated, Reboot required, Recovery required.
Checking is advisory. New launches during protected handoff/installation receive
an accessible restricted-startup notice without a main application session or
provisioning. No automatic elevated or original-user GUI relaunch is included.

## 4. Fixed action, shared core and platform privilege

Only a fixed official eligible stable SDE application update is authorized. The
GUI cannot choose executable/script paths, installer paths, URLs, privilege users
or arbitrary versions. Request correlation hints are not capabilities or authority.
One authorization creates at most one claimed attempt; reject/defer competitors,
not a queue. Claimed, expired or uncertain requests cannot be replayed by retries.

Reuse existing discovery, pinned authentication, protected staging, native
package identity checks, pause policy, postchecks and recovery primitives. Recheck
eligibility/installed identity before commitment. Expensive network work precedes
the final policy/intent/launch sequence.

Add an explicit **app-only** entry point: current maintenance runs tools first and
cannot be triggered unchanged. Preserve tools, applied baseline, schedules,
maintenance enabled state, pause policy, user/project/editor data and unattended
maintenance behavior, including package-hook effects. A tool schedule is not a
prerequisite on an otherwise trusted supported application-only installation.

Refactor a **shared installation core** receiving an already-established validated
installation context. The manual worker must not hold leases and call an unchanged
routine that reacquires them. Scheduled/manual callers retain the same checks;
no second, less-checked installer path is acceptable.

Windows: preserve SYSTEM execution. Use a fixed UAC-authorized broker and protected
one-shot SYSTEM request/task mechanism. Do not weaken the identity check, grant
ordinary users general task authority, reuse/change the weekly task, accept
variable commands or automatically restart uncertain installation. Task security,
alternate-admin consent and execution settings remain native proof obligations.

Linux: fixed polkit authorization launches a root worker from a protected snapshot
with constrained arguments, validated ownership/paths and sanitized execution
context. Do not change/reuse the maintenance timer or depend on it being enabled.

Both: snapshot all required worker files outside the installation. The worker and
package supervision must survive GUI exit and application replacement. No GUI
runs elevated/root/SYSTEM. Bootstrap correlation/request security still needs
review; removal of custom command IPC does not remove the privilege boundary.

## 5. Corrected coordination and admission rules

O = existing operation exclusion; A = new admission gate; S = existing session
ownership (shared GUI / exclusive installation). I = protected durable installation
intent, a recovery barrier rather than a live lock.

| Participant | Rule |
| --- | --- |
| Installation worker | O -> A exclusive -> S exclusive. |
| GUI startup | Check I; acquire A shared; recheck I; acquire S shared; recheck I while holding S; release A, retain S. Reject safely and release leases on any failure. |
| Existing GUI operation | May request O while holding S. Contention fails promptly; no indefinite wait. |
| GUI closure | Requires neither O nor A. |

The worker order is **not** a blanket order for all participants: existing GUIs
already hold S before requesting O. A GUI cannot wait for O while the worker
waits for that GUI to release S. Preparation conflicts must defer, not create a
cycle. Package hooks must participate without reacquiring/rejecting their own
parent's locks or intent.

The worker acquires O with bounded contention handling, prepares while existing
windows retain S, then acquires A exclusive before announcing Ready. It obtains
S exclusive within the earlier remaining deadline. New participating sessions
cannot enter between admission closure and exclusive ownership. Existing windows
are not forced out. Failure before commitment safely defers only after proving
no native installation began. Close admission only for this bounded transition;
preparation does not permanently deny launches.

All supported scheduled/manual launch and package paths must have reviewed
compatibility. Startup's second intent check is a compatibility safeguard, not
proof that arbitrary legacy workers/executables are safe. Missing support disables
the feature rather than weakening exclusion. Existing maintenance's drop/reacquire
lease boundaries cannot simply be copied into a protected manual handoff.

## 6. Protected records, intent and recovery

The privileged bootstrap creates the request identity and protected lifecycle
record, including schema/capabilities, available trusted authorization context,
boot identity, deadlines, candidate digest after verification and terminal outcome.
Protected progress is bounded, atomically published, privileged-writable and
readable only to its intended audience. The GUI verifies location/ownership,
schema, bounds and request correlation. Secrets and executable commands are absent.

Progress cannot authorize installation, prove liveness or clear recovery. Missing
or stale progress is reported honestly. Before launch, progress failure prevents
misleading readiness and may defer. After native launch, reporting failure must
not terminate the installer or release ownership.

Reuse/extend the existing durable transaction contract. Intent is written before
native launch and survives process loss. Once publication starts, ambiguous
publication/launch status is recovery-required; lack of a successful API return
is not proof of safe non-installation. A known unstarted attempt may be deferred
only after that fact is established and its own state is safely finalized.

A dead worker/released lock/stale PID does not prove package children ended.
Preserve ownership and recovery evidence; never kill package processes, delete
package locks or clear uncertain intent merely to retry. Reboot invalidates
uncommitted requests; unresolved committed intent remains a startup/recovery
barrier. Windows power-loss ordering remains unproven: the existing directory-
sync implementation adds no Windows durability operation.

Success requires native completion and resource/application/activated-engine
postchecks. Reboot-required is distinct. Blocking intent clears only through a
reviewed durable terminal sequence after known package-child completion.

Keep independent: observation/progress completeness, installation outcome,
immediate resource cleanup, owned-process accounting, persistence and recovery
readiness, authentication safety, and production readiness. Eventual teardown
never repairs an earlier immediate-cleanup failure.

## 7. Compatibility and enablement

Enable only after validating capabilities for app-only bootstrap, participating
startup, worker/coordination, protected record schemas and package hooks. Version
strings alone are insufficient. Updating bundled code does not automatically
migrate installed external launchers. A prerequisite upgrade must establish these
capabilities; capability deployment mechanism and native migration remain gates.

Retain existing legacy-maintenance compatibility restrictions. Do not silently
apply a tool baseline or provision/repair tools to enable manual updates. Missing
or inconsistent support disables Update now with an actionable explanation.
Rollback/uninstall must preserve compatibility or explicitly disable the feature.
Do not promise admission protection for unsupported copied/legacy executables.

## 8. Historical gates and deferred custom-protocol work

| Historical work | Disposition |
| --- | --- |
| B01 privileged launch | Remains, narrowed to fixed request authorization/claiming. |
| B02 original-process authorship of commit/cancel, close grants and acknowledgement freshness | Removed from this feature's critical path; those commands do not exist here. Narrow bootstrap authorization, correlation and protected progress integrity remain. |
| B03 independent supervisor/package-child lifetime | Remains. |
| B04 package/bootstrap/startup compatibility | Remains. |
| B05 durable intent/result/recovery | Remains. |
| B06 coordination/interleavings | Remains with fewer GUI-command states. |
| Bidirectional progress/control, custom Linux record-credential adapter and Windows counterpart, additional W2/W3 custom-protocol diagnostics | Deferred. Reopen only if an actual implementation introduces the corresponding dependency, with separate authorization. |
| W2n observer/N1 driver/native N1/N2 | Research infrastructure retained; no additional review/implementation/native execution authorized here. |

B01-B06 are not declared closed by adopting this architecture. W2h remains an
authentication counterexample. W2i-W2l retain limited results. W2m M2 remains Fail
for immediate cleanup; zero actions and eventual teardown do not repair it.
W2n native N1/N2 remain NotRun. Authentication safety remains Unproven; production
readiness false. Do not reinterpret this evidence as shipped-updater defects or
safe outcomes. The local N1-driver commit `585add9` is not part of this documentation
publication and remains separate/unpublished at the time of this record.

## 9. Bounded implementation plan and stop gates

Approval settles product direction only. Each phase requires separate scope.
A failure stops the relevant path and prompts reassessment; it does not authorize
another experiment series automatically.

| Phase | Deliverable | Explicit stop gate |
| --- | --- | --- |
| 1. Shared app-only core | Common validated installation boundary, explicit app-only dispatch and focused automated coverage. | Tools run, checks diverge or leases must be reacquired. |
| 2. Coordination and compatibility | Admission/startup checks, compatible lease ownership, capability gating and recovery handling. | A supported launch bypasses admission, a deadlock is possible, hooks conflict or uncertain intent can clear. |
| 3. First platform integration | Fixed authorized launch, request claiming, independent worker and protected progress; review before native execution. | Privilege, ownership, exclusion, deadline/clock mapping or request claiming cannot be established. |
| 4. Disposable native validation | One complete app-only upgrade and essential concurrency/failure cases. | Unauthorized execution, duplicate installation, unsafe reopening, unknown children or lost recovery evidence. |
| 5. Schedule integration and native UAT | Consent/progress/Close/restricted-startup/results and accessibility. | Behavior contradicts consent or accessibility/native acceptance fails. |
| 6. Second platform | Same common contract with platform-specific proof. | Any corresponding gate fails; first-platform evidence never certifies another platform. |

Select the first native platform by available disposable access. Give Windows
privilege feasibility early attention; without a suitable environment report its
proof unavailable rather than substituting Linux/mocks. Do not invent a schedule
or completion date before that environment is established.

Minimum focused coverage: denial; pause; current/offline/download/authentication
failure; app-only scope; duplicate/manual-scheduled contention; multiple windows
and users; ordinary close/crash; repeated rapid reopen; both deadlines/suspend;
worker failure around intent and native launch; known/unknown package children;
legacy capabilities/hooks; reboot/interruption; failed postcheck; reboot-required;
and complete native upgrade. Desktop UAT covers keyboard/focus/announcements,
contrast, theme/zoom, progress and restricted startup. Local checks, native process
checks and desktop acceptance are distinct evidence levels.

## 10. Remaining decisions and authorization

The four product choices in section 2 are approved, not pending. Remaining items
are engineering/native gates: exact platform bootstrap/task/polkit schema/security,
suspend-aware clock mapping, lease API/core boundary, capability migration and
package hooks, child supervision, and durable terminal ordering. Resolve those
within the bounded phases; do not treat approval as proof.

Next proposed phase: separately authorize Phase 1's shared app-only core and
focused checks with strict limits on executing real updates. Native environments,
privilege work, package operations, PR/workflow effects and release work need
explicit scope before they occur. This record allocates no version, changes no
fleet policy, and authorizes no change to published release assets.
