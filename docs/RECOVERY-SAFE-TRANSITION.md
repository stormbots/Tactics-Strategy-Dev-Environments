# Safe recovery transition: engineering handoff

Branch: `codex/recovery-safe-transition`, based on accepted PR #115 head
`046d56bd4f5f723e1d21eadbbc95674c558016ac` (Build `40800652705`). This stacked
branch includes still-unmerged #113–#115. It is not a complete feature or UAT
candidate. See [ADR 0002](adr/0002-lease-bound-recovery-transition.md).

## Acceptance criteria and implementation

- Separate fresh native package activity, package health and earlier-process
  lifetime evidence. Missing/failed activity checks block; unknown health alone
  does not. Read-only diagnostics are bounded and return sanitized reason codes.
- Capture incident-specific restart provenance without refreshing it after a
  restart. Require kernel boot UUID change on Linux, and both primary SMSS
  identity and OS-start event change on Windows. A restart does not acknowledge.
- Validate consent and original generation under the same operation/session
  leases as safety checks and new-transaction creation. Recheck after acknowledgment
  persistence. No UI-provided permit or production caller-supplied facts.
- Preserve original object and immutable evidence/receipt; never overwrite a
  retirement destination. New work receives distinct intent; dropping the guard
  retains unknown outcome. Explicit completion verifies its own ID/token.
- Supervise a trusted child using existing nesting protocol. Do not kill package
  children or clear intent on exit. Recheck immediately before launch.
- Keep existing execution APIs and all ordinary consumers unchanged. No production
  recovery path is enabled by this increment; isolated tests exercise the API.

Files: `coordination/src/inspection*`, `observations.rs`, `mutation.rs`,
`mutation_tests.rs`, `recovery/restart.rs`, and shared recovery lease helpers.
No workflow check, package fixture, production journal, release asset, owner UAT
result, version or scheduling policy is changed.

## Targeted local validation

Rust library harness: 47 successful entries; root-required fixtures return early
at local UID 1000, not native proof. Linux and Windows GNU test-target Clippy and
format/diff checks are required before push; cross-compilation is not MSVC proof.

An additional explicit local read-only native probe correctly failed closed:
the managed environment maps host dpkg/apt lock owners to UID 65534, not root.
No permission was relaxed or lock modified. Its activity result is unknown. This
container cannot establish native platform acceptance; required CI must demonstrate
the actual supported host sources. This failure is retained, not called a pass.

## Required DevOps validation

Inspect the existing Build Skyview Dev Setup workflow on the exact pushed head;
do not dispatch duplicates, poll long jobs or substitute older native evidence.
Require all applicable general, trust, native, feasibility and signed-upgrade checks.
Require Windows native coordinator execution and the Linux root invocation with
`SDE_REQUIRE_COORDINATION=1`. Specifically inspect:

- `native_restart_provenance_and_package_activity_are_available_on_required_runners`:
  actual package activity must not be unknown; restart provenance must be readable,
  canonical and stable across independent reads. Return numeric diagnostic codes
  on failure. Do not waive unavailable Windows SMSS/event sources.
- `mutation_*`: same/missing restart evidence blocks; restart without consent
  blocks; active/unknown activity and incomplete health never retire the journal;
  recheck catches activity after persistence; unknown health permits only when
  inactivity is established. Original bytes remain intact.
- Retirement destination collision cannot overwrite either file. A fresh intent
  follows retirement and remains on guard drop. Installation respects GUI sessions;
  explicit completion cannot remove a changed transaction.
- `mutation_supervised_child_inherits_coordination_but_exit_never_clears_intent`:
  actual child sees busy gate, Unix inherited descriptor identities with parent
  CLOEXEC unchanged, or the correct private Windows token. Child exit alone leaves
  intent. No package process is launched or killed.
- Existing real standard-user storage probe now also proves it cannot reach the
  privileged begin path before private access fails. Prompt-free intent submission
  still succeeds. Keep all durable acknowledgment crash/replay tests and both
  Windows feasibility markers passing.

Synthetic restart changes test decision logic, not an actual host reboot. Actual
restart/resumption and deployed platform adapters remain later integration/UAT
acceptance. Existing consumers are deliberately not using this API yet.

Return exact head, workflow/job URLs, native command counts, and failure-specific
assertions. No merge, signing, publication, automation resumption, UAT request or
owner workstation action. Preserve Windows interruption evidence and Mint's
v1.2.18 35/0/0 pass. After native acceptance, return to engineering for normally
privileged bootstrap/execution adapters, updater parity, reports/history and UI.
