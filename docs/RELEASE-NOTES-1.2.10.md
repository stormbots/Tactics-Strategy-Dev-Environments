# SDE 1.2.10 — UI milestone acceptance candidate

Testing prerelease for Windows 11 x64 and Linux Mint Cinnamon 22.x amd64.

- Adds an opaque white background to all packaged application icon sizes for
  visibility on dark taskbars. Preserves the supplied logo artwork and shared
  in-app logo.
- Retains the accepted v1.2.9 themes, five-step zoom buttons, compact Appearance
  settings and actionable validation guidance.
- Reconciles historical UAT records and provides a focused milestone results sheet.

The application/activated maintenance engine is 1.2.10; the development-tool
baseline remains separate at 1.2.1. Application installation does not provision
tools or change the existing application-update pause policy.

The native 1.2.9 -> 1.2.10 probe uses unpublished fixtures built from the same
reviewed source. It does not replace the published v1.2.9 assets or prove a
historical-binary desktop upgrade. Owner UAT exercises the actual installed
workstation upgrade, taskbar visibility and native UI behavior.

Download all five assets together and authenticate with the trusted installed
pinned verifier before installation. See the
[installation and focused UAT sheet](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/main/docs/UI-UAT-1.2.10.md).
Candidate publication is separate from owner acceptance and stable promotion.

Issues #4/#5/#6/#63 and the milestone remain open for owner acceptance. Stable
promotion, fleet rollout and application-update policy resume are separate decisions.
