# Privileged GUI helper supervision: engineering handoff

Branch: `codex/recovery-helper-supervision`, based on accepted #117 head
`46667078290536380583d6e6f0671f7c07845742` (Build `40831671161`). This draft
stacks still-unmerged #113–#117. It is a bounded part of T4, not full platform
execution parity or a UAT/release candidate.

## Acceptance criteria and implementation

- The installed release GUI's existing privileged helper continues to accept
  only Install/Repair/Update plus its validated run ID and existing preflight
  uncertainty choice. No arbitrary frontend path/command, extra elevation,
  acknowledgment override or new IPC capability is introduced.
- Preserve installed-resource trust checks, fixed script selection, normal
  elevation, sanitized system environment, independent preflight and redacted
  line streaming. The frontend preflight remains conservative until final UI
  integration; its uncertainty flag is not machine acknowledgment or authority.
- After the privileged helper's preflight, acquire the shared Rust System
  mutation guard. It independently enforces trust, activity, package state,
  exact incident binding and durable consent. The helper-only preflight omits
  the obsolete blanket coordination row, not platform/package/disk checks;
  authoritative coordination is mandatory immediately before launch.
- The guard injects the existing Windows private nesting token or Linux real
  inherited lease descriptors. Existing nested script coordination validates
  them and reuses the supervisor rather than creating/clearing another journal.
  `run_supervised` is a trusted synchronous Rust adapter, not a serialized permit
  or general privileged service. It cannot accept UI-supplied safety facts.
- Keep raw `ExitStatus` through streaming, including signals, and retain the
  same redaction before display/logging. No timeout, forced package termination
  or automatic retry is added. A runner error keeps unknown intent; a second
  launch through the same guard is rejected.
- Only a normally completed, successful fixed synchronous backend plus a fresh
  independent native inactivity check and no known incomplete package state
  permits explicit completion of that guard's own journal. A zero exit alone or
  passing Validation never completes it. Unknown package health alone does not
  become a permanent gate. Active/unknown activity, known incomplete health,
  nonzero/signal/spawn/wait failure retain intent and report recovery guidance.

The selected backends already wait for their controlled package commands. This
completion contract depends on retaining that property; detached/unknown work
must not be newly certified by a caller. The wrapper's native exit and postchecks
are separate from later user-profile configuration and Validation. Original
acknowledged incident evidence remains protected in its archive.

## Boundaries and remaining work

Only the installed privileged GUI helper uses the new adapter in this increment.
Direct/manual script entry points, applied/scheduled maintenance and SDE updater
installation still use their old conservative outer gates. They must be migrated
before claiming policy parity. Nested reuse from the new helper is covered here;
standalone outer-wrapper recovery is not. No script permission/hash, scheduling
policy, package baseline or version is changed.

The GUI's old interrupted-state navigation/preflight remains in place until
report/history and final acknowledgment/resumption integration. Therefore this
is not a user-visible end-to-end Continue feature. No machine-consent button or
report save behavior is added. Do not merge/release this stack as a final design.
Full installed release-helper/UAT operations and real reboot/resumption remain
later consolidation acceptance, not inferred from isolated nesting fixtures.

## Targeted local verification

- Coordinator harness: 54 successful entries. Protected fixture cases return
  early at local UID 1000 and are NOT native proof.
- Coordinator Linux and Windows GNU all-target Clippy pass with warnings denied.
- Three command-permission/source-boundary contracts pass. No new frontend grant.
- Changed-file Rust formatting and diff checks pass.
- Full Tauri test compilation is unavailable locally: offline dependency lookup
  lacks `adler2`, and GTK/WebKit development packages are absent. The new helper
  streaming/completion tests must compile/run in existing native CI. No claim of
  application test success is made from coordinator-only results.

Initial head `1446f6e` failed the existing actionable-spawn-error assertion on
both native targets in Build `40838067271`. The supervision refactor had replaced
the specific startup error with a generic completion message. The focused fix
adds phase-specific context at the actual spawn/wait boundary, retains the I/O
error kind and underlying OS text, and lets the string wrapper preserve that
message. The regression now also checks no output on failed spawn and typed
`NotFound`. No native exit status, guard, completion policy or CI gate changed.
The new completion-policy and streaming/redaction tests, coordinator and trust
checks passed on the old head; they are historical evidence only. Revised-head
native application tests, Linux installed-bootstrap/actual Mint marker and all
signed-upgrade checks must complete before acceptance.

## Required DevOps evidence

Validate the exact pushed head in the existing Build workflow; no duplicate
dispatch or continuous polling. Require all applicable existing checks, including
the #117 installed bootstrap markers on Windows/Linux and actual Mint, original
feasibility markers, trust/native builds and signed SYSTEM/Mint upgrades.

Require native Windows and root Linux coordinator suites with
`SDE_REQUIRE_COORDINATION=1`. Specifically:

- `mutation_runner_preserves_existing_platform_nesting_and_does_not_clear_on_exit`
  runs the real Python coordination check on Linux or the real PowerShell
  `Invoke-SkyviewCoordinated -Mutation` wrapper on Windows, using an isolated
  synthetic root. Require `SDE_RECOVERY_EXISTING_LINUX_NESTING_OK` or
  `SDE_RECOVERY_EXISTING_WINDOWS_NESTING_OK` as asserted by the test. The callback
  must observe successful real child completion, unchanged journal bytes and a
  still-held gate. A second runner attempt must not reach inspection/launch.
- `mutation_runner_failure_keeps_unknown_intent_and_active_check_precedes_callback`
  proves runner errors retain intent; a fresh active check prevents the callback
  entirely and aborts only its own never-started new attempt.
- Existing production-storage, durable acknowledgment, bootstrap, mutation and
  stale-generation tests remain required.

The existing native application **Rust tests** step must compile and execute
`process::tests::helper_completion_requires_controlled_success_and_fresh_native_inactivity`
and `process::tests::streamed_runner_preserves_exit_status_and_existing_redaction`
on both supported native targets. The latter runs only a synthetic test child,
requires its real exit 7 and stderr marker, and rejects its synthetic secret from
the redacted stream. `stream_child_probe` alone with no fixture environment is
not proof. Keep all preflight/permission tests passing.

Return exact head, run/job URLs, command counts and failing assertions. No merge,
signing, publication, automation resumption or UAT. Preserve Windows interruption
evidence and Mint v1.2.18 35/0/0 acceptance. After this native gate, return to
engineering for remaining direct/scheduled/updater adapters and report/history/UI.
