# Student-focused Recovery page

Branch: `codex/student-recovery-page`, based on main `a72ae62`.
Scope: presentation, action visibility and tests only. No native recovery,
journal, acknowledgment, packaging or release behavior changes.

Accepted at `8879f9b607f60fdd2a99ac05bd40d8a583dff5a8` in
[Build 41278626292](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41278626292):
188 frontend/109 browser checks and every applicable native/trust/signed-upgrade
gate passed. Merged as main `75a7da2`; the historical correction below remains
the audit trail. Continue with [v1.2.21 preparation](RECOVERY-CANDIDATE-1.2.21.md);
published v1.2.20 assets remain unchanged.

## Acceptance criteria

- Lead with **Let’s get setup working again**, a short explanation and **What to
  do now**. Unknown activity gets save-work → normal Restart → open SDE/Check
  again instructions. Windows uses Start → Power → Restart; other systems use
  their normal power menu. Never suggest a restart while work is known active.
- Match other current states honestly: active work means wait; unavailable or
  untrusted records mean recheck/support, not a promise that restart repairs
  them; known incomplete packages get the existing reviewed repair guidance in
  Technical details only after inactivity. Unknown activity takes priority over
  package-repair instructions. A ready observation is still not execution authority.
- Give the relevant action the primary style. Check again is primary while
  blocked; eligible acknowledgment or an existing pending continuation may be
  primary instead. Blocked acknowledgment can still be recorded with a clear
  warning that changes stay paused. No implicit acknowledgment or operation.
- Show Run validation only after known inactive activity and trusted native
  coordination observations. This is a presentation filter, not a native permit;
  fresh backend checks still apply, including when entering through Validation.
- Say the computer acknowledgment is already present only when its current
  available source has an incident and matching submitted intent or recorded
  acknowledgment. Do not infer it from a prior report/outcome, unavailable source
  or another account incident. Keep submitted versus protected commitment precise
  in Technical details; no blanket claim that all incidents are acknowledged.
- Keep automatic report-save results and failures visible. Move incident/report
  reference IDs, observation time, known/unknown package/activity/trust fields,
  precise acknowledgment state, original platform guidance and Open logs behind
  **Technical details**. Do not fabricate completion, timestamps or package health.
- Collapse **Earlier recovery events** and **Saved reports** by default. Shorten
  their introductions/empty states; distinguish computer/account records and
  missing reports from cleared incidents. Retain uncertainty, generation-bound
  deletion, explicit confirmation, paging, export, focus and retention behavior.
  Avoid empty list markup. No new automatic upload or refresh polling.
- Replace Recovery’s Cancel with **Back to Overview**; it still forgets the
  pending request and does not replay work. Keep support optional and accessible,
  with the privacy reminder to review a report before sharing.

The existing native guidance catalog remains available in the expanded details;
the simple introduction is not an alternative safety policy or a universal fix.
Existing per-source evidence and minimum operational records are untouched.

## Verification

Local results:

- 188 frontend tests passed, including 13 new Recovery component cases covering
  submitted/missing/unavailable/different-source consent, separate account consent,
  active/unknown/incomplete activity, platform-specific steps, automatic-summary
  explanation, warning visibility, continuation/cancellation and busy controls.
- Existing App tests still verify no consent from Validation, one-action source
  acknowledgment, report failure, duplicate/stale/partial results, fresh checks
  after confirmation and cancellation without replay. Only changed text/disclosure
  expectations were updated; safety assertions were retained.
- Production TypeScript/Vite build, 35 backend contracts, four command-permission
  checks and whitespace review passed. Playwright discovery found 109 cases.
- Local browser executables are known absent; browser discovery is not browser
  execution or a visual/contrast pass. Existing CI must run the full suite,
  including updated expandable history/export/deletion flows and four synthetic
  submitted-Windows-interruption cases in Light/Dark at 640/1140px. They require
  collapsed defaults, one primary Check again, keyboard access to Technical
  details, no unavailable validation/continuation, axe/reflow and screenshots.

## Handoff

### Initial CI correction

Head `dcb6e96e7201cb73319bc007a79af0066f77b40a` failed
[Build 41275567651](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41275567651)
in browser accessibility checks: four Light/Dark 640/1140px cases found poor
contrast on hovered Check again (1.19:1 Light, 1.28:1 Dark; required 4.5:1).
The later, more-specific `.result-actions button` rule overrode the primary
button foreground with the link color while hover used a primary background.
The other 105 browser cases and both native/trust jobs passed, but the full
initial head is not accepted.

A Recovery-scoped primary rule now restores the existing theme's primary text,
normal/hover background and border tokens, matching the preflight hierarchy.
It affects all primary Recovery actions, not native behavior or unrelated cards.
Browser regressions now check actual computed normal/focus/hover styles in both
themes and widths, plus the original full axe audit while hovered. No contrast
assertion, threshold or required CI gate was disabled. Complete replacement-head
CI remains required before integration or a future candidate.

Use the exact PR head and its Build URL in the tracker checkpoint. Require full
applicable browser/native/trust and inherited recovery/signed-upgrade checks;
stop while CI is pending, with no continuous polling. No native tests or owner
workstation mutations ran locally for this presentation-only change.

After CI acceptance, integrate through the existing verified-source process.
The existing v1.2.20 release/candidate and its assets are not rewritten by this
change. Any later candidate requires an unused version, its own exact-source
validation, the existing signing approval gate and focused owner UAT. Do not
resume an older signing/publication run to ship different source.

Windows original interruption evidence, existing release/UAT state and Mint
v1.2.18 Install/Validate **35/0/0** remain preserved. No release publication,
signing, automatic repair, journal clearing, fleet rollout or milestone closure.
