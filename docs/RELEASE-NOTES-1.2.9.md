# SDE 1.2.9 — Compact appearance controls testing candidate

Testing prerelease for Windows 11 x64 and Linux Mint Cinnamon 22.x amd64.
Includes merged PR #69 and the consolidated native UAT audit from PR #70.
Stable promotion, fleet rollout and application-update policy resume remain
unapproved. Published v1.2.8 and earlier assets/tags remain unchanged.

- Compact System/Light/Dark icon buttons beside the heading in wide layouts.
- Fixed-width minus/percentage/plus zoom at 90/100/115/130/150%, replacing the slider.
- Compact layouts use an Appearance settings icon opposite top-header branding.
  Its nonmodal panel keeps controls out of the heading row and scrolls in short windows.
- Accessible names, pressed/expanded states, theme tooltips, distinct selected/focus
  indicators, and one polite zoom announcement. Keyboard focus survives zoom limits
  and layout transitions; held-key repetition cannot reverse direction at a limit.
- Retains themes, preference persistence, actionable validation guidance, the Overview
  question and banner removal. Appearance changes preserve current work and logs.

Application/activated maintenance-engine identity is **1.2.9**. The managed-tool
baseline remains **1.2.1**. Installing the app alone does not apply a tool baseline,
install development tools, or resume application updates. Preserve existing policy
and project/editor data.

Native automation tests a 1.2.8 → 1.2.9 identity upgrade with unpublished fixtures
built from one reviewed source. It checks package identity, retained policy/data
and no automatic baseline/schedule provisioning. The 1.2.8 fixture is not a
replacement for the published v1.2.8 installer. Native desktop/webview, Narrator/Orca
and student-workstation acceptance remain pending; Mint desktop availability is blocked.

Download all five release assets together and authenticate with the trusted installed
pinned verifier before installation. Checksums alone are not signature authentication.
Minisign authentication does not imply Windows Authenticode or SmartScreen approval.

See [v1.2.9 installation and UAT](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/main/docs/UI-UAT-1.2.9.md)
and [the consolidated checklist](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/main/docs/UI-MILESTONE-UAT.md).
Keep #4/#5/#6 open until explicit acceptance. Publication is not stable promotion
or permission for fleet rollout.
