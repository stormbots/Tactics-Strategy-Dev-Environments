# Guided Overview integration — #148

Base: final accepted main `7a3b16065cfdad0178b558cc4dd86c5a3019ae9d`.
#147 is closed with full exact-main Build/native/trust evidence recorded on the
issue. #148 integrates that decision into the real App, not the offline demo.

## Production behavior

- Overview always opens first and keeps the existing bounded read-only startup
  inspections. Missing/delayed safety evidence produces a specific Overview
  explanation instead of an automatic Recovery redirect. Current blockers still
  prevent mutating shortcuts and fresh native checks remain mandatory.
- The slim status and one next-step card use the shared decision. Install, Repair,
  Validate and Update tabs and the permanent Install default are removed. Setup,
  repair and update review/progress occupy the same card; successful current
  validation recomputes the next step rather than stacking a second success card.
- Ready-with-updates retains Ready!, the exact approved Install updates wording
  and one Review updates primary. Editor/workspace access moves to Other actions.
  App-update notices/discovery remain separate and use existing policy behavior.
- Other actions, Details and Development tools start collapsed. Findings, update
  uncertainty, validation times, logs, support and Validation/Recovery/Schedule
  routes remain accessible. Known maintenance failures retain their log route.
  Missing maintenance/update observations do not fabricate recovery incidents.
- Reviews explain the actual full setup/repair scope, current findings and normal
  administrator approval. The existing preflight/update components and original
  start/native dispatch path remain. No selective repair, new permission,
  automatic replay, process cancellation or policy changes.
- In-flight guards prevent competing starts; navigation retains a running-task
  cue. Query results are request/context-bound and invalidated before a new
  operation. A background update finding cannot silently replace the action of
  a focused button: its label/ID stays bound until blur or explicit re-review.
- The accepted Recovery clear card and acknowledgment/report/history components
  are unchanged. Acknowledgment still returns through ordinary review; stale
  native findings are checked again before execution.

Native and privileged code, journals, release metadata and the offline prototype
are unchanged. Only synthetic browser Reports receive explicit synthetic check
collection times; native timestamps still come from actual validator output.

## Validation layers

App tests retain the existing recovery, source-bound acknowledgment, report-save
failure, no-replay, safe confirmation and read-only diagnostic assertions, updated
for explicit Recovery navigation and the new disclosure layout. New integration
coverage checks exact update copy, one primary, editor alternatives, blockers on
Overview and delayed discovery while the editor action is focused.

Browser tests exercise production components with explicitly synthetic modules,
not native journals or owner machines. `overview.spec.ts` covers checking,
unavailable/incomplete validation, setup, supported repair, unsupported findings,
Ready, optional updates, active/unknown/untrusted safety, incidents and native
incomplete state in Light/Dark at 390/1140px. Each scenario has a screenshot,
accessibility audit and reflow/diagnostic-route assertions. Existing browser tests
retain all themes, supported zoom levels, review/cancel, progress/log, Recovery,
history, Schedule, About and privacy-route checks with the new controls.

Screenshots are emitted to `installer/test-results/guided-*.png` and retained by
Build's existing ui-verification artifact, alongside existing browser evidence.
Local browser runs use installed `/usr/bin/chromium` with a temporary local config;
Playwright's download domain was denied by the managed network policy. CI retains
its original Chromium/WebKit configuration. No assertion or gate was disabled.

Local validation: 235 frontend tests passed, with all 36 App tests rerun after
the final presentation fixes; TypeScript/Vite build, 35 backend contracts and
four command-permission tests passed. The final broad Chromium run passed 106
of 107 cases; its reduced-motion case exposed a missing progress spinner. After
restoring it, that case passed on a targeted rerun (107 scenarios covered). The
state suite produced 52 screenshots. Exact CI links are recorded in the PR and
issue checkpoint.
Local screenshots are synthetic component evidence, not packaged end-to-end or
installed owner acceptance. Do not close #148 until the PR is reviewed and its
required CI evidence is passing; do not close #150/#151 from UI tests.

## Remaining dependent work

#149 owns explicit operation-result distinctions (known not started versus
uncertain launch, partial outcomes and verification failure), fuller reviewed
scope binding and fresh reconstruction after reopen. The UI currently retains
native error details and recomputes supported next actions without automatic
mutation retries. It does not claim all lifecycle acceptance is complete.

#150 owns the complete WF01–WF31 coverage ledger, production dispatch/native race
fixtures and final platform integration evidence. #151 owns the authenticated
candidate, normal human signing approval and exact-candidate owner UAT. Every
existing Windows feasibility/bootstrap, coordinator/trust, signed SYSTEM and
actual Mint 22.3 bootstrap/manual/scheduled-tool and signed-upgrade gate remains.
Release promotion requires separate authorization. Original Windows interruption
evidence and historical Mint v1.2.18 35/0/0 acceptance remain untouched.
