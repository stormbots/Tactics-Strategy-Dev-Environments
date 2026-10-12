# Self-update UAT candidates 1.2.2 and 1.2.3

These are **unaccepted prereleases**, built from the same reviewed commit with
different application version identities. Development-tool baseline versions do
not change. 1.2.2 is the test starting point; 1.2.3 is the upgrade target. Do not
promote 1.2.2 merely to make testing easier. Existing stable 1.2.1 stays unchanged.

Both versions include the implemented self-update trust, protected discovery and
staging, session/maintenance coordination, Windows/Mint native installation,
administrator pause/resume, separate application/engine/baseline status, and
retained-installer verification. New installations start paused; upgrading
preserves an existing policy. App installation does not apply a tool baseline,
create a new weekly schedule, or launch the GUI/reboot.

Each release must contain both native installers, SHA256SUMS.txt, signed
sde-update.json and sde-update.json.minisig. The protected workflow authenticates
both installers before publication. Minisign authentication is separate from
Windows Authenticode; no SmartScreen exemption is promised.

Use [the owner UAT procedure](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/main/docs/SELF-UPDATE-UAT.md). These packages support a real,
verified manual two-version upgrade while production remains paused. Production
discovery ignores them because they are prereleases. Native CI separately tests
the production installation components and deferral/failure contracts; it does
not replace Windows 11, booted Mint, or school-network acceptance.

Record findings with Codex. Acceptance and stable promotion remain pending your
explicit instructions. See [migration and rollout](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/blob/main/docs/SELF-UPDATE-ROLLOUT.md).
