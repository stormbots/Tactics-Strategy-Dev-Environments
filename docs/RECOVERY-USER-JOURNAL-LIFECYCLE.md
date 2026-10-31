# Evidence-preserving user-journal lifecycle

Branch: `codex/recovery-user-journal-lifecycle`.
Accepted at `175004d8a189e8d2dd2ec0a934da6f553ce5c784` in full successful
[Build 41214719832](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41214719832):
Windows trust 100/100, root Linux 115/115 and inherited native gates passed.
The [proven-not-started increment](RECOVERY-NOT-STARTED-OUTCOMES.md) follows;
pending-CI language below records this task's original checkpoint.
Base: #130 at `0a678c08a590ded2df3ac3e2cbb2788cb5f09070`, accepted in
[Build 41210917994](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41210917994).
Windows trust passed 92/92, root-required Linux 107/107. Both native jobs,
report-history tests, general checks, actual Mint 22.3 and Windows SYSTEM signed
upgrades and all inherited recovery gates passed. The stack remains draft/unmerged.

## Bounded lifecycle acceptance criteria

1. Replace the GUI journal's blind initial overwrite with a per-account lifecycle
   store. Hold `recovery-state/user-operation.gate` across begin, stage updates,
   privileged helper/profile/validation work and finish. Unix uses nonblocking
   flock and CLOEXEC; Windows uses exclusive sharing on the fixed regular handle.
   Reject unsafe links/types/Unix permissions. This lock is not a machine lease
   or OS authorization and does not replace protected native coordination.
2. Existing unknown/unacknowledged, malformed, changed or unpreserved user evidence
   blocks a new journal. Require a matching generation-bound separate decision
   with verified preserved bytes; never manufacture acknowledgment at begin.
   A new operation gets a fresh UUID, private flushed staging record and native
   generation. Retained earlier source bytes/receipt remain in the decision store.
3. A user-only crash can leave a detached profile child after the machine journal
   has already completed. Therefore a decision and an unlocked user gate are not
   proof of inactivity. Capture a private per-run restart marker before the new
   journal; prepare a legacy baseline during acknowledgment/attempted transition
   without changing the journal. Before replacing an interrupted journal, require
   an independently confirmed later session, using the existing native Linux boot
   UUID / Windows SMSS plus OS-start-record comparison. No elapsed-time/PID-absence
   shortcut or caller skip flag. Native machine mutation still rechecks current
   package activity/health, authorization, evidence and package locks independently.
4. The native-only serialized `RestartMarker` exposes no boot-key accessor and is
   never returned in IPC, reports, logs or error text. It is per-user operational
   data, not protected machine authority. If a baseline was unavailable and later
   becomes readable, capture it then and require a subsequent Restart; never
   reinterpret that first capture as proof the old lifetime ended. Existing known
   baselines are not refreshed. Missing/invalid/mismatched/partial restart evidence
   stays blocking. Legacy first capture can require one further Restart.
5. Stage and finish recheck the current native generation and exact bytes. They
   cannot update/delete a foreign/recreated/replaced journal. The only normal
   finish branch requires controlled successful validation with actual collected
   checks, an inactive privileged SDE gate and no interrupted/unavailable/untrusted/
   repair-required protected status. Error, failure, cancellation and guard drop
   retain the current record; no timeout or background retry deletes it.
6. User acknowledgment acquires the same account lock before source capture,
   automatic report attempt and separate evidence/decision commit. It does not
   delete the source or grant a protected mutation permit. Read-only validation
   does not start/finish a user journal. Read-only inspection derives acknowledged
   state from the separate matching decision, never from PASS or a source rewrite.
7. Legacy `acknowledge_operation_incident` now refuses deletion. Remove the old
   frontend dismiss button and automatic Repair acknowledgment call rather than
   silently preserving the old deletion route. Successful Repair no longer claims
   that an earlier uncertain operation completed. Final one-action UX is a later
   integration; do not ship this partial interaction as an owner UAT candidate.
8. Native journal inspection adds explicit `backendActivity: active | inactive |
   unknown`. The old boolean remains conservative/blocking for unknown until the
   final frontend consumes the new field. This is an SDE operation-gate observation,
   not a claim about package activity or a user child's lifetime. Final admission
   must combine native safety and restart findings, not reuse the boolean as proof.

## Tests and limits

Seven substantive portable lifecycle tests plus one child-probe helper run in the
exact-source coordinator harness and native Tauri. They cover drop retention and
refused overwrite; acknowledged/preserved transition only after simulated prior
session; stage/finish rejecting changed generations; malformed/corrupt preservation
blocking; missing baseline never proving restart or dropping the decision; and
independent-process exclusion/release and hardlink rejection without target writes. Parent tests require the child helper to
actually run exactly once, not merely exit with zero tests. The normal helper
entry returns early unless invoked by its parent test. Native Windows and root
Linux remain authoritative. The simulated restart is not an actual reboot test.

Local lifecycle tests and context regression tests passed at UID 1000. Linux and
Windows-GNU coordinator clippy, 27 backend contracts, four command/module tests,
138 frontend tests, production frontend build, formatting and diff checks passed.
Native Tauri compilation, Windows sharing/move execution, native restart-source
availability and all inherited Windows/Mint 22.3 recovery/signed-upgrade gates
remain required CI. Local cross-compilation is not Windows runtime acceptance.

This account-owned lock coordinates new SDE instances; it is not a security
boundary against a malicious same-account editor or a legacy executable ignoring
the lock. Generation rechecks reject observed replacements; arbitrary external
writes are not an atomic cross-version compare-and-swap protocol. Protected
machine state, nesting and native package locks remain independently enforced.
Windows AppData ACL privacy and unelevated restart-source accessibility still
need explicit validation; no new service or acknowledgment elevation is introduced.

## Remaining integration / durable continuation

Final T8 must present user-only restart/unknown findings explicitly, read the new
tri-state rather than the legacy boolean, wire one evidence-preserving action,
keep machine/user identities separate, and implement safe history viewing/export/
selection deletion. This increment conservatively retains preflight-denied or
authorization-cancelled attempts too. Before release, distinguish proven not-started
outcomes from uncertain execution through a reviewed native outcome contract;
do not turn arbitrary exit codes into an automatic clearance or add mutation replay.
Keep the earlier decision when an actual invocation is cancelled and allow explicit
retry through ordinary confirmations/OS approval, as the approved plan requires.

No automatic crash/startup retry, prototype, partial-stack merge, signing, release,
publication or owner UAT. Completed-run notices authorize exact-head CI review and
the next bounded integration, not a status-only handoff. Leave source/run evidence
in the PR checkpoint if only long CI remains. Owner Windows interruption evidence
and Mint v1.2.18 Install/Validate 35/0/0 remain intact.
