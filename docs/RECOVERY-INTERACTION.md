# Recovery interaction and ordinary-review continuation

Branch: `codex/recovery-interaction`. Bounded T8 implementation accepted at
`d954c6d768c8c70dae50ca7835babf00cc4171e9` in
[Build 41226670429](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41226670429).
All 149 frontend tests and 89 browser checks passed, with Windows trust 119/119,
root Linux 133/133, native Tauri Windows 92/92 and Linux 89/89. Both signed-upgrade
paths, actual Mint 22.3 and all inherited recovery gates passed. Real dialogs,
restart and complete history/export remain separate acceptance work below.
Base #133 `de57ae045214052623788a7e8c4ca365bf7e0023` accepted in
[Build 41222693951](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41222693951).

## Acceptance criteria

- Recovery uses the input-free native observation, not the legacy boolean gate.
  Show machine/account incident identities separately, recorded operation/stage/
  times where available, current activity/health/trust and self-service guidance.
  Submitted machine intent explicitly remains distinct from a protected receipt.
  Unknown/unavailable is never displayed as absence or readiness.
- One acknowledgment action calls each eligible native source controller, which
  automatically attempts its own local summary before submission/recording.
  No report preview, save dialog or separate report action is required. Show saved
  report references and storage warnings; storage failure alone may be nonblocking,
  but evidence-preservation failure and unconfirmed submission stop continuation.
- Pass the displayed account view nonce. Stale views are not silently rebound and
  retried; require Check Again and another explicit acknowledgment. Preserve a
  successful first source's report/result if the second source fails. Synchronous
  in-flight guarding prevents duplicate click submissions before React rerenders.
- A pending Install/Update returns to ordinary preflight/review after successful
  acknowledgment and safe fresh findings, never reusing earlier confirmation.
  Repair returns to its ordinary operation review/button. Unknown/active activity
  and native blockers prevent continuation. Every change, including one confirmed
  after review, refreshes findings and remains subject to native execution guards.
- Check Again is read-only and never launches or acknowledges. Cancel forgets the
  pending request. Requests live only in React memory: restart cannot replay them.
  Read-only Validation remains available for diagnosis and never grants consent.
- Recovery remains accessible for diagnosis and future history. Reuse the existing
  first Overview card for colored attention/reason, not an additional status card.
  Once consent admits normal recheck, remove the incident-attention reason; current
  package-health, validation and maintenance warnings remain independently visible.

## Remaining preflight integration found during implementation

The old Install/Update preview and final unprivileged preflight called legacy
`operation()`, rejecting every retained transaction even when matching intent had
already been submitted. That would keep acknowledged users blocked before the
accepted privileged consumer could revalidate it.

The new exact-source `recovery_preflight` observer collects public state before and
after native safety inspection. Changed/unavailable source identity blocks. A safe
native `needs_acknowledgment` decision plus matching submitted intent yields a
**warning**, not a pass or permission. Known/unknown activity, untrusted/unavailable
coordination and incomplete package health still block. Unknown health alone warns.
The user retains ordinary preflight uncertainty confirmation; no journal is changed
or receipt committed by preflight. Account preservation/restart is enforced by the
existing account journal transition, and protected mutation rechecks/commits under
its own gates after normal OS authorization. Privileged helper behavior is not
relaxed. The admission-policy test exercises every blocking policy and no-intent or
changed-frame rejection; native CI runs its exact source on Windows and Linux.

## Validation and scope limits

Local: 149 frontend unit/component tests passed, including successful Validation
without acknowledgment, simultaneous sources and report failure, double click,
stale/partial failure, unconfirmed submission, unknown activity, Cancel/no replay,
changed findings after confirmation and unavailable-state accessibility. Production
TypeScript/Vite build passed. Exact-source admission-policy test passed; coordinator
Linux and Windows-GNU clippy with warnings denied, 30 backend contracts, four
command-permission checks and whitespace checks passed.

Local browser execution was blocked first by sandbox localhost binding and then,
after permitted network access, by missing Playwright browser executables. No
browser/contrast/reflow pass or screenshot review is claimed locally. The existing
Build workflow installs Chromium/WebKit; its full browser gate must pass, including
four new Recovery light/dark 640/1140px axe/reflow cases. Native installed bootstrap,
standard-user proof, Windows SYSTEM and actual Mint 22.3 signed-upgrade gates all
remain mandatory. Real UAC/polkit/reboot behavior remains owner UAT later.

This is not the full milestone or UAT candidate. Next after exact-head acceptance:
retained history/report view/export/deletion, report-independent minimum incident
history completeness and unavailable/malformed-evidence self-service review, then
consolidated execution/UX acceptance and focused UAT preparation. The current UI
shows report IDs, not a completed sharing/export workflow. Operational evidence
and decisions never depend on those report views remaining present.

Only disposable test data was used. Owner Windows interrupted-operation evidence
and Mint v1.2.18 Install/Validate 35/0/0 remain untouched. No partial-stack merge,
release/signing/publication, automation resumption or owner UAT was performed.
