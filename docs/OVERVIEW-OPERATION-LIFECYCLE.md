# Guided Overview operation lifecycle — #149

Base: accepted main `f15e72b17f6257d5b297b2935371a07f4d92942b` after
Build 42864697447 passed. #148 is closed; #149 connects existing native outcomes
and command boundaries to the guided card. No native or privileged behavior,
journal, capability, release metadata or offline-prototype changes.

## Outcome evidence

`operationLifecycle.ts` consumes the existing `Report.mutation_outcome`, validator
rows/summary/time, and actual reported error. It never derives non-start or
completion from a numeric exit code, error wording, elapsed time, UI storage or
absence of output.

| Existing evidence | Presentation |
| --- | --- |
| `not_started` | Native-confirmed non-start, explicit Back to Overview; no false incident or automatic approval retry. |
| `uncertain`, absent outcome, unexpected `not_requested` on a mutation, or rejected invocation | Unconfirmed outcome; changes may have occurred. Preserve error/recovery evidence, no cancellation/rollback/success claim. |
| `completed` but complete current frontend verification is unavailable | Completion and incomplete check are separate; offer read-only Check my setup. |
| `completed` with reported required failures | Retain findings and supported diagnostic review, never Ready or automatic Repair. |
| `completed` plus complete passing verification | Recompute the shared next step from fresh observations, including remaining optional updates and safety blockers. |
| Repair report repeats a prior failed finding | Explain that repair has not confirmed a resolution, retain uncertainty and diagnostics; no repair loop. |

Current native `main.rs::run` emits `completed` only after successful validation,
a collection time and its existing coordination/journal checks. This invariant
is unchanged. Incomplete-verification-after-reported-completion cases are defensive
frontend/transport contract fixtures, not claims that the current native producer
emits contradictory Reports. Actual native validation/launch failures without
completion proof stay uncertain. #150 must retain this producer invariant and
identify each evidence layer rather than manufacture a native completion flag.
No broader backend observation or success/cancellation definition was added.

Network/download details are retained verbatim from reported errors. The UI does
not guess a network cause from unknown text or assume a download failure means
nothing changed. It cannot promise repair, rollback or safe replay.

## Review and command boundaries

Install, Repair and Update now all enter explicit review through the same guarded
start path. Every confirmation performs fresh Recovery inspection and the original
native preflight/admission/privilege path. A private review fingerprint binds mode,
validation request context, update option, platform, tool/version/source findings
and visible native incident/acknowledgment identity. It is not sent as native
consent or used as an execution permit.

Equivalent fresh inspection timestamps do not invalidate review. Changed scope,
options, versions or incident evidence require a fresh review and confirmation;
preflight remounts and resets its uncertainty acknowledgment. A safety blocker
routes to current Recovery findings before submission. Successful acknowledgment
re-enters review only; it never reuses an approval or starts a mutation.

Optional tool discovery is invalidated by actual operation/validation context,
not every read-only safety inspection. This avoids clearing a reviewed tool
snapshot or repeatedly querying metadata during confirmation itself.

A synchronous in-flight guard spans inspection, dispatch and result collection.
Late stream lines are rejected after completion or when their run/request is
superseded. Reports remain request-bound. Navigating or cancelling while an
unsubmitted inspection is pending abandons that UI request, rather than later
submitting it or stealing focus. This does not cancel a running installer.
Acknowledgment completing after navigation retains its source-specific results
without redirecting or replaying a pending operation.

## Progress, navigation and reopen

Progress uses reported protocol events; the existing native final-validation
phase is shown as Checking the result. No percentage is generated from a timer.
A running task retains its supported status cue across navigation and its result
is available on return, without a duplicate operation or forced page switch.
No process-killing Stop control, rollback promise or automatic retry was added.

Unstarted reviews/results are memory-only. Reopen queries current validation and
Recovery again rather than restoring execution intent or old success. If native
observations say work is active/unknown, that finding is shown honestly. There is
no supported cross-window percentage/progress reconnection API; the UI uses the
existing native activity inspection and does not invent one. Native close guards,
source/generation-bound acknowledgment, automatic summary attempts, partial-source
warnings, histories and original evidence remain unchanged.

## Evidence ownership

Tests exercise pure result/review decisions and actual App dispatch boundaries:
raw cancellation codes/text versus native proof, incomplete/partial results,
explicit checking without reinstall, unchanged repair findings, changed review,
duplicate clicks, late output, navigation/cancel during inspection, navigation
while running, reopen and acknowledgment completing after navigation. Browser
fixtures exercise the production card in both themes at 390/1140px, preserve
accessibility/reflow/screenshots and distinguish synthetic Reports from native
execution. Existing native launch-outcome tests are run from their real source
through the coordination crate, without modifying them or inducing owner failures.

Exact test counts, source SHA and CI URLs are recorded in the PR/checkpoint. Full
existing Build/browser/native/trust/Windows SYSTEM/actual Mint 22.3 gates remain
required before acceptance. #150 owns complete WF01–WF31 integrated/native evidence;
these fixtures do not substitute for a packaged native UI pass. #151 still needs
human signing approval and exact authenticated-candidate owner UAT. Stable promotion
requires separate authorization. Historical Windows interruption evidence and Mint
v1.2.18 35/0/0 acceptance remain untouched.
