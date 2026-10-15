# SDE 1.2.8 — Accessibility and UI Usability testing candidate

Testing prerelease for Windows 11 x64 and Linux Mint Cinnamon 22.x amd64.
Stable promotion, fleet rollout and application-update policy resume remain
unapproved. Existing published installers/tags are unchanged.

- System, Light and Dark themes, saved between sessions and responsive to system
  appearance when System is selected (#4).
- Whole-UI zoom at 90%, 100%, 115%, 130% and 150%, saved between sessions (#5).
- Actionable validation failures: impact, next safe step, expandable original
  diagnostics, and explicit Review Repair/Update choices before starting work (#6).
  Unknown failures retain mentor guidance. Command failures ending in “not found”
  are no longer mistaken for known missing-tool reports.
- Overview asks “Are you ready to build?”; the status card supplies readiness.
  Retains the decorative banner removal and Windows Logs migration from v1.2.7.

Application/activated maintenance-engine identity is **1.2.8**. The managed-tool
baseline remains **1.2.1**. App installation alone does not apply that baseline,
install development tools or enable/resume application updates. Existing policy
and project/editor data must be preserved.

Native automation tests a 1.2.7 → 1.2.8 identity upgrade using unpublished fixtures
from the reviewed source, including package identities, retained policy and data,
and no automatic baseline/schedule provisioning. Those 1.2.7 fixtures are not
replacements for the published v1.2.7 assets. Desktop/webview rendering, assistive
technology and real student-workstation operation acceptance remain UAT work.

Download all five assets together and authenticate with the installed pinned
verifier before installation. SHA256SUMS alone is not signature authentication.
Minisign authentication does not imply Windows Authenticode/SmartScreen approval.

See [v1.2.8 installation and UAT](UI-UAT-1.2.8.md) and
[the consolidated milestone checklist](UI-MILESTONE-UAT.md). Keep #4/#5/#6 open
until their native acceptance is recorded. Publication of this prerelease does
not authorize stable promotion or fleet rollout.
