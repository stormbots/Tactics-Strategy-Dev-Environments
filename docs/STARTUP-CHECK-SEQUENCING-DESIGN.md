# Startup check sequencing — follow-up design

Status: **design only; implementation not authorized**. Recorded November 12,
2026, following owner UAT of v1.2.23. Track in [#160](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/160).
The owner requested the design be committed to GitHub and explicitly requested
that implementation not start. This document does not authorize code/test changes,
CI execution, candidate builds, signing, publication or promotion.

## Baseline and observed problem

Reviewed source: `f6715a728bd6017ad6b6d8294cf2f1bf914da2ca`, the authenticated
v1.2.23 tag. Current [owner UAT #151](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/151)
remains open; this finding is not owner acceptance. Published assets and the
original Windows interruption/Mint v1.2.18 35/0/0 evidence must remain unchanged.

The owner reports that every ordinary launch on Mint 22.3 first presents
**Check not finished / Try checking again**, and that **Check again** clears it.
Startup should finish its bounded read-only check without that extra click when
no genuine blocker prevents collection. The screenshot also shows the generic
“This workstation could not be checked” message.

The code supports a specific self-contention hypothesis. Owner-device startup
logs have not yet confirmed the exit/status behind this particular occurrence.
Do not label the device diagnosis confirmed, imply its setup is broken or infer
that all startup failures have the same cause.

### Existing call paths

| Path at baseline | Relevant behavior |
| --- | --- |
| `installer/src/App.tsx` mount effects | Starts `inspect()` and `refreshRecovery()` independently, alongside maintenance/discovery initialization. |
| `bridge.ts::inspect` → native `main.rs::inspect_system` | Acquires the app Busy guard and runs the existing `Operation::Validate` implementation. |
| `recovery_summary.rs::inspect_recovery_state` | Performs native recovery observations independently of the validation Busy guard. |
| `coordination/src/observations.rs::inspect_at` | Takes `operations.gate` exclusively while collecting a read-only observation. |
| `linux/Validate-SkyviewStudentDev.sh` → `linux/lib/coordination.py` | Read-only validation also takes the operation gate exclusively and nonblockingly. Contention returns a deferred warning and exit 75 before checks/summary exist. |
| `model.ts` / `overviewDecision.ts` | No collected check rows can produce the generic initial error; absent/incomplete current verification produces Check not finished. This is correct about missing evidence, but not a useful normal startup experience. |
| Manual `App.tsx::start("validate")` | Awaits fresh Recovery inspection before submitting validation; this ordering differs from startup. |

A plausible ordering is: Recovery takes the gate → startup validator cannot take
it → no validation rows/summary → generic incomplete state. Manual Check again
then succeeds because its own safety read completes before validation starts.

Before implementation, capture sanitized initial Details/log evidence if naturally
available, or reproduce the ordering in disposable fixtures. Look for a deferred
warning/exit 75 before validation events; also distinguish missing resource,
launch/IPC, malformed output or genuine native activity failures. Do not request
private journals, induce an owner-device incident or treat error text alone as
native permission or proof of non-start.

## Goal and constraints

An ordinary supported, healthy launch completes **one** automatic read-only
validation with current results and no manual recheck. The app must not collide
with its own local safety/status reads. A real external blocker or collection
failure must still be reported honestly.

Preserve the authority boundaries in [ADR 0001](adr/0001-interruption-acknowledgment-boundary.md)
and [ADR 0002](adr/0002-lease-bound-recovery-transition.md): UI ordering is not
consent, a native lease, evidence retirement or execution eligibility. No native
lock mode, permission, journal, acknowledgment, package, tool-baseline, update
policy or installation behavior change is proposed. A free gate does not prove
that an earlier installer completed. Passing validation does not acknowledge an
interruption. Unknown/untrusted findings never become clear by UI scheduling.

## Proposed design

### 1. One request owner for the read-only setup sequence

Introduce a small private frontend coordinator for local inspections that can
contend with setup validation. Give each sequence the existing mount/request/
context-generation identity, with a synchronous admission guard for duplicate
callers. This coordinator serializes this window's requests; it cannot reserve
the machine gate or stop another process from becoming active.

Startup and explicit Check again should use common sequencing/result handling
with separate presentation adapters:

1. Enter one startup sequence and retain Checking state for its full lifetime.
2. Await fresh Recovery/safety inspection. Do not start validation concurrently.
3. If an authoritative current observation says an operation is active, retain
   its paused/wait guidance and defer validation. Do not poll, retry or wait for
   that operation to finish automatically.
4. Otherwise attempt one read-only validation through existing native commands
   and their safeguards. A safety blocker for **mutations** does not by itself
   forbid supported read-only diagnostics: preserve the current diagnostic rules
   for unknown activity, unavailable evidence and retained incidents.
5. Publish a result only if its request/context is still current. Release the UI
   sequence owner after actual completion, not after an arbitrary timeout.
6. Drain still-relevant queued read-only requests without launching another
   startup validation or replaying any pending operation.

Do not literally call the existing `start("validate")` from the checking effect:
its `busy` guard currently rejects `stage === "checking"`, and it carries explicit
navigation/task behavior. Extract/share the read-only sequencing primitive without
bypassing the guards on public operation actions. Existing `inspect_system` and
`run_operation(validate)` already share native `run(Validate)`; preserving those
IPC adapters is preferable to introducing a new native command.

A failed safety query is not a clean result. Retain its diagnostics and existing
mutation block; a separately permitted read-only validation cannot override it.
If validation subsequently defers because another process won the native gate,
preserve that outcome. At most one bounded fresh safety inspection may clarify
the current reason after deferral; it must not resubmit validation or become a
retry loop. Never infer safe cancellation or execution authority from exit 75.

### 2. Coordinate every relevant same-window reader

Audit the real call graph before editing code. Known additional contenders include
`inspectSelfUpdate`/`updater::observation::inspect`, whose coordination status query
briefly takes the operation gate, and incident/support/history reads when they
reach native coordination inspection. About/Recovery/Details navigation can
start these while the initial sequence is still pending.

Route confirmed gate-taking readers behind the same coordinator, or defer their
initial invocation until the local startup sequence settles. Coalesce only
identical non-mutating reads within the same current request context. Do not cache
or reuse a safety observation as authorization for later execution. Explicit
mutations still require original review and fresh native admission.

Do not serialize every API indiscriminately. The existing managed-tool metadata
reader explicitly does not use the global operation gate; its current stage/
snapshot-generation guard should remain. Application release discovery has its
own admission/rate-limit behavior. Gate-free network discovery and the separate
Schedule reader should not delay local readiness. Verify those classifications,
including any nested status calls, rather than guessing from a function name.

The coordinator must not recursively enqueue itself and deadlock when a compound
sequence invokes its own safety/validation adapters. Use one outer admission
owner and internal already-owned read helpers. No global UI/native mutex is held
while awaiting an unrelated network request.

### 3. Honest loading, failure and navigation

| Condition | Intended presentation / behavior |
| --- | --- |
| Startup sequence admitted or waiting on this window's own read-only query | Keep the existing Checking your setup / Finding your next step presentation; no transient Check not finished between phases and no invented percentage. |
| Safety/validation completes with full current required verification | Recompute the existing shared recommendation once. Ready still requires actual check rows, native collection time and a matching terminal summary. Optional updates remain optional. |
| Genuine active native work | Existing Changes are paused / wait guidance; do not claim that a check failed, kill work or automatically retry after it ends. |
| Unknown/untrusted evidence or retained incident | Existing precedence, diagnostic access and mutation restrictions; no forced onboarding, automatic acknowledgment or generic repair. |
| Actual failed/partial/unavailable collection | Preserve available findings, exit/protocol diagnostics and an explicit supported recheck. A zero exit, old success or elapsed delay is not verification. |
| Navigation while startup is pending | Keep a supported status cue; no late redirect, focus stealing, mutation or loss of diagnostic access. Queue a gate-taking diagnostic read when necessary, with an honest pending cue. |
| Duplicate effects/clicks | One owned sequence and at most one actual startup validator request. Busy/duplicate guards cover the entire sequence, including the transition after safety returns. |
| Unmount/reopen or newer request | Abandon unsubmitted obsolete work; ignore old results. Do not kill submitted native work, clear its guard early or replay intent on reopen. |

The default update-check option remains unchanged; startup must not turn on remote
managed-package checks merely to unify adapters. Do not invent collection times
in frontend code. Preserve focused-action binding, original native close guards,
source/generation-bound acknowledgment and all existing report/history warnings.

### 4. Scope of a later implementation

Expected affected areas, subject to the gate-use audit:

- App startup orchestration and the common explicit read-only check path.
- A private read-only request coordinator, plus relevant bridge/recovery/About/
  diagnostic consumers so that navigation cannot reintroduce self-contention.
- Production-App/browser tests and relevant existing native fixture coverage.

No backend semantics change is currently planned. If diagnosis requires broader
native cancellation, timeout, authorization or observation changes, report the
concrete evidence/scope before expanding the implementation. Do not relax locking
or create new privileged/native APIs to make a UI symptom disappear.

## Planned verification — not executed

| Layer | Required future proof |
| --- | --- |
| Deterministic production App | Hold safety unresolved; assert no validator call. Resolve it, hold validation unresolved, and assert continuous checking. Deliver a complete current report and assert one automatic transition with zero manual clicks. |
| Same-window contention | Delay gate-taking About/Recovery/support reads and navigate while startup runs. Assert non-overlap/coalescing as designed, retained diagnostic access and no duplicated validation or lost mutation guard. |
| Optional discovery | Hold/fail network metadata queries and confirm that local startup can complete. Unknown update availability is not zero updates or a readiness failure. |
| Genuine blocker/error matrix | Active external lease, unknown lifetime, unavailable/untrusted source, retained incident, deferred validation, invalid/missing summary, zero exit without checks, rejected invocation and genuine failed checks. Assert no automatic retry, false Ready or safety bypass; complete failed checks remain findings rather than a fabricated incomplete collection. |
| Lifecycle | Development duplicate effects and ordinary production launch, rapid Check again/secondary clicks, navigation, unmount before/after submission, newer request and reopen. Assert invocation counts, stale-result rejection, no focus/page theft and no canceled-native-work claim. |
| Real native boundaries | Disposable Linux and Windows fixtures exercise production inspection/validator entry points and the actual operation gate with controlled ordering. Show that self-serialization avoids contention while an independently held lease still defers/blocks. No owner faults or package-process killing. |
| Packaged follow-up | Repeated ordinary launches on the supported Mint desktop (proposed sample: ten idle launches), and Windows regression, finish without a manual click. Record exact package/source, launch/check counts, native logs/summary/time and current safety state. State whether real packaged Tauri IPC/UI interaction occurred; browser/native component passes are not that proof. |
| Regression/release | Keep all existing applicable browser, accessibility/theme/zoom, backend, native/trust/storage/acknowledgment, Windows feasibility/bootstrap/signed SYSTEM, actual Mint bootstrap/manual/scheduled-tool/signed upgrade and aggregate acceptance gates. New failures require diagnosis, not blind retries or relaxed assertions. |

Coverage emphasis: WF01, WF07, WF15–WF17, WF20–WF21 and WF25–WF30 in the
[existing UAT plan](OVERVIEW-NEXT-STEP-UAT-DRAFT.md). This design adds ordering
proof, not a replacement acceptance oracle. A missing packaged test facility is
an explicit evidence gap to resolve before claiming the packaged startup fix;
do not transfer difficult failure testing to owner laptops.

## Acceptance and follow-up handoff

Implementation may start only after a later explicit owner instruction. The future
implementation issue remains unassigned until that point. No code, tests, native
experiments or CI jobs have been started for this design.

Before implementation, confirm the reported startup failure's evidence or reproduce
it safely, and finish the gate-use classification. Reject a fix based only on a
fixed sleep, hidden error, cached Ready, changed native lock mode, swallowed Busy
or repeated automatic validation attempts. One clean automatic startup check is
the success criterion; a genuine external blocker remains an honest exception.

Keep collecting v1.2.23 UAT findings. Batch approved fixes into one consolidated
follow-up candidate. **v1.2.24 is tentative only**: no version/tag is reserved,
metadata changed or release dispatched here. Existing v1.2.23 acceptance is still
an owner decision; this plan does not accept, replace, rebuild or promote it.
A future candidate needs its own exact-head/final-main evidence, normal human
signing approval, independent asset authentication and focused owner UAT. Stable
promotion still requires separate authorization. No fleet/policy resumption.
