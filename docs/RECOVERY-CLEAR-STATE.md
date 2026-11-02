# Recovery when no action is needed

## Acceptance criteria

- Show the owner's exact “There is nothing to recover from right now” heading,
  Overview explanation and optional support-report privacy reminder.
- Use the normal surface and border, not a warning color. The only button in
  this card is **Create support report**, disabled while busy.
- Keep Technical details, Open logs, acknowledgment/report-save warnings and
  existing incident/report history available outside the clear card.
- Use this presentation only for ready-for-native-recheck observations with
  inactive activity, trusted coordination, readable machine/account sources,
  no known incomplete packages, no acknowledgment action, no pending operation
  and no inspection error. Unknown package health alone remains nonblocking.
- Preserve the active recovery experience, explicit acknowledgment, normal
  operation confirmation and fresh privileged safety checks. This card neither
  certifies package health nor grants execution permission.

## Scope and validation

This is frontend presentation only. No protected journal, native coordination,
release asset, version or owner workstation state is changed. Windows interruption
evidence and Mint v1.2.18's 35/0/0 acceptance remain preserved.

Component tests cover the exact card/action, unknown health, negative safety
states, pending continuation, report-save warnings and busy controls. App tests
retain acknowledgment/confirmation/no-replay assertions. Browser coverage checks
the neutral card in Light/Dark at 640/1140px while retaining active-recovery
contrast, keyboard, accessibility and reflow checks. Authoritative browser and
cross-platform/native validation belong to the existing Build workflow; capture
exact-head evidence in the pull request before accepting this change.

Local validation: 200 frontend tests, the production TypeScript/Vite build,
35 backend contracts, four command-permission tests and whitespace checks passed.
Playwright discovered 109 cases; local browser executables are unavailable, so
discovery is not a browser execution or visual acceptance result. CI remains
required before merge, and a future replacement candidate needs owner UAT.
