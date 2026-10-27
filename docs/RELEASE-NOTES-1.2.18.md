# SDE 1.2.18 — Safe Operations, Recovery and Support

Adds guided checks before Install and Update, durable interruption detection with
fresh validation before recovery, and a local HTML support report with an exact
redacted preview. Diagnostic logs remain optional and off by default.

The existing Overview status card now explains maintenance concerns in yellow
while retaining the prominent Ready! heading and red readiness failures.

This is the consolidated milestone 3 testing candidate. Use
[the compact Windows/Mint UAT sheet](SAFE-OPERATIONS-UAT.md). Codex owns automated
exceptional-state verification and findings. Native desktop acceptance is pending.
Stable promotion and fleet rollout require separate owner decisions.

Only 1.2.18 is published. The same-source 1.2.17 package is an unpublished upgrade
fixture; existing published releases remain immutable. Application installation
enables SDE updates as in 1.2.17; the tool baseline and student projects/settings
remain separate.
