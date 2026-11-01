# Unavailable-source diagnosis and shareable support findings

Branch `codex/recovery-unavailable-diagnostics`; bounded completeness increment,
accepted at `bc778cda49287c9f8e07aaac9ac6eb322c27540f` in
[Build 41252483028](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41252483028).
All 172 frontend/101 browser, root Linux 151/151, Windows trust 136/136 and native
Tauri Windows 106/106 / Linux 104/104 passed, with both signed upgrades and all
inherited gates. Continue with the [final integration review](RECOVERY-INTEGRATION-REVIEW.md).
Base #137 `f1e4941b07b248d7ec39e87afcb5511b48797c14`
passed Build 41247275524, including the repaired root-owned test isolation.

## Finding and acceptance criteria

The generic support report previously had no structured recovery findings. If an
account journal was malformed/unreadable, the UI's aggregate unknown-trust message
could misleadingly suggest protected machine coordination was the problem; a
report with no readable account context also said no interruption was recorded.

- When machine trust is available/trusted but the account source is unavailable,
  show account-specific guidance. Preserve files, Check Again, collect/share the
  diagnostic report if desired; explain that restart does not repair malformed
  evidence and reinstalling application files does not clear the account journal.
- Support collection must succeed without parsing/copying malformed journal bytes.
  Distinguish absent, recorded and unavailable machine/account sources, and matching
  account decision observed/not observed/unavailable/not applicable. Missing clock
  or application-data location is unavailable, not fabricated observation data.
- Share only whitelisted native categories/time: machine activity/reason, package
  health, trust, restart **classification**, machine safety decision and source
  availability. No raw source, path, generation, binding, restart key or OS error
  text. Machine findings are explicitly not aggregate account-process clearance.
- Keep detailed logs off by default and explicitly optional. Reports remain local
  and user-shared; no upload. Unknown extra provider fields are not copied into
  snapshots, and HTML escapes diagnostic values. No absent-context completion claim.
- Support collection runs in a blocking worker, not on the UI thread. No inspection
  creates minimum state, acknowledges an incident, repairs evidence, alters journal
  behavior or authorizes mutation. Native preservation/activity/health/trust guards
  remain unchanged; this is useful diagnosis, not a corrupt-state bypass.

## Validation and remaining limits

Two portable native tests exercise actual bounded account-source reads, malformed
bytes remaining unchanged, no storage creation, absent-versus-unavailable categories,
missing clock/location and serialization without private data. Frontend tests cover
source-specific guidance, whitelisted support snapshots, no false absence claim and
escaped diagnostic text. Native exact-source Linux/Windows-GNU lint, backend and
permission contracts are required; CI remains authoritative for native Tauri,
root/standard-user and signed SYSTEM/actual Mint 22.3 paths. Local browser binaries
are absent; existing full browser support-report/recovery checks remain required.

This does not complete every recovery edge case. Ambiguous/overflowed historical
view deletion remains conservatively unavailable, malformed evidence is retained
and cannot become consent merely because a report was generated, and a report is
not proof that the earlier process ended. Finish the integrated execution/UX and
remaining edge-case audit before consolidating and preparing focused owner UAT.

Owner Windows interruption evidence and Mint v1.2.18 Install/Validate 35/0/0 remain
untouched. Only disposable files were used for tests. No partial-stack merge,
signing, release/publication, automation or owner UAT was performed.
