# Native Recovery observation and admission contract

Branch: `codex/recovery-state-contract`. Bounded T8 prerequisite; native CI pending.
Base #132: `e2aa71eede4ceea878e70292ffd01af59759ce75`, accepted in
[Build 41218520518](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41218520518).

## Acceptance criteria

- The fixed, input-free `inspect_recovery_state` command returns separate machine
  and account incident findings, activity/restart/health observations, source
  availability, acknowledgment capabilities and request readiness. No frontend
  field grants an execution permit.
- Inspection does not provision missing account storage, create a restart
  baseline, acknowledge an incident, write a report or clear/replace a journal.
  Missing/unreadable source evidence is not represented as a clean bill of health.
- Machine student intent is distinct from the protected acknowledgment receipt.
  A submitted matching intent may admit an otherwise-safe request to the normal
  native recheck, where the privileged consumer must validate and commit it.
  The response still reports `needs_acknowledgment` until protected commitment.
- Active activity, unknown lifetime, unavailable trust or positively incomplete
  package health cannot become ready through acknowledgment. Unknown package
  health alone retains the approved warning behavior once activity is inactive.
- Acknowledging a user incident requires the opaque view token returned for its
  exact native file generation, not just a copied incident UUID. Replacement with
  identical bytes is stale. Verification precedes baseline/report/decision writes;
  the normal acknowledgment account lock is still acquired first.
- Real standard-user native CI must read the sanitized public snapshot and obtain
  stable restart provenance without elevation. Existing private-storage denial
  assertions and every inherited native/trust/signed-upgrade gate remain required.

## Implementation boundaries

The protected coordinator reads the public incident, bounded fixed intent slot and
public disposition under its existing operation lease. Malformed student-writable
intent is not consent; unsafe permissions/type/ownership still fail. Inspection
does not read private bindings or retire transactions. Machine snapshots before
and after the safety observation must have matching incident identities; a changed
frame becomes unavailable. This is not an atomic execution snapshot: every actual
change still takes leases and rechecks current protected evidence and native state.

Account observation probes only an existing trusted gate and existing restart
record. A free gate is not proof that an earlier child finished; an interrupted
account incident still needs independent later-restart evidence. An absent gate is
unknown, and a legacy incident's restart baseline is prepared only by the existing
acknowledgment path, never by Check Again.

The in-memory view registry retains one opaque nonce bound to the native file
generation. Unchanged refreshes reuse it, replacements rotate it, and application
restart invalidates old tokens. Native generations and boot keys are neither IPC
inputs nor report fields. The nonce is not persistent consent or a machine permit.
Account evidence preservation and exact-generation rechecks remain mandatory.

## Validation and remaining integration

Local portable tests: nine observation/view-policy tests, eleven user-journal
tests including no-creation/held-gate and identical-file-replacement checks, plus
existing user-acknowledgment tests. Linux and Windows-GNU coordinator clippy,
29 backend contracts and four command-permission tests pass. Local unprivileged
root-required fixtures return early; their passing harness count is not native
acceptance. GTK/WebKit Tauri and native Windows execution are delegated to CI.

New required CI coverage includes the root public-intent observation test and the
existing real standard-user production-storage probe, now also asserting public
snapshot readability and stable native restart provenance. Failure of a standard
account's restart query must be diagnosed, not waived or replaced with a mentor
or acknowledgment-elevation requirement. No private restart key is printed.

The frontend has no callers of the new contract yet. Next: integrate existing
Recovery/Overview UI, one-action automatic summary and acknowledgment, stale-view
Check Again, explicit continuation through ordinary preflight/confirmation, and
history/export. Complete malformed/unavailable-source self-service guidance and
retained-history review before consolidation. No auto replay, background polling,
new Overview status card, automatic repair or arbitrary evidence deletion.
Real reboot/UAC/polkit interaction remains focused owner UAT after native gates.

All test sources are disposable fixtures. Owner Windows interruption evidence and
Mint v1.2.18 Install/Validate 35/0/0 remain untouched. No partial-stack merge,
signing, publication, release preparation or UAT is authorized by this checkpoint.
