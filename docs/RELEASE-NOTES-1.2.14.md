# SDE 1.2.14 — Trustworthy Update Discovery and Preview, Part 1

Testing candidate. Owner desktop UAT and stable promotion are pending.

Supersedes the unaccepted 1.2.13 candidate. Fixes the Linux sidebar stopping
above the window bottom at 130% zoom by anchoring it to both viewport edges.
The fixed sidebar keeps its scrollable footer in short windows. Adds desktop
sidebar coverage at all five zoom levels in Chromium and WebKit.

- Local workstation readiness appears independently of network update checks. Slow or unavailable sources do not mean the environment failed validation.
- SDE checks official stable releases on launch and About, with platform-specific browser downloads, release notes, version-specific dismissal and non-blocking failure explanations. It never installs through the notification path.
- Managed-tool Update opens a read-only preview with installed/available versions, per-source unknown/partial results, the Node 24.x/Python 3.14.x policy, and configuration/extension refresh scope.
- Update preflight checks free-space budgets, package activity/state, coordination, detectable restart conditions and representative required source connectivity. Known blockers prevent changes; warnings/unavailable checks require review. Conditions and native locks are rechecked before changes.
- Windows PowerShell availability compares the actual executable with Chocolatey's package record and available version. Metadata drift is identified rather than advertised as an equal/older update.
- Public introductory downloads track the current official stable release; historical release and recovery links remain fixed.

Application/activated engine candidate identity: 1.2.14. Managed-tool baseline:
1.2.1. App installation preserves the applied baseline, student data/settings,
schedule and existing application-update pause policy. The Update tools action
remains a separate explicit operation. Part 2 and manual Update Now are excluded.

See [Part 1 UAT](UPDATE-DISCOVERY-PART1-UAT.md) for verification, installation,
acceptance and known evidence limits. Published assets are immutable. Stable
promotion preserves the exact accepted tag and all five signed candidate assets;
fleet rollout and update-policy resume require their separate decisions.
