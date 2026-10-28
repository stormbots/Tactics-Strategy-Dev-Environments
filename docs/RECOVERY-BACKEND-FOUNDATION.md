# Recovery backend foundation: engineering and native handoff

Branch: `codex/recovery-backend-foundation`, based on verified PR #113 head
`1f1e44918be9645069312a388601fdc7e1c2bc13`. The branch includes that unmerged
feasibility work and the approved plan; do not assume it is already on main.

## Completed in this bounded increment

- Production `coordination/src/recovery.rs`: fixed-root sanitized incident
  inspection, privileged preparation of public/private records, non-elevated
  intent submission to a pre-created slot, and private diagnostic verification.
- Private binding includes both journal content hash and native object generation.
  A new transaction with identical legacy PID/bytes must receive a new ID.
- Strict canonical UUID/schema parsing, duplicate/extra-field rejection, bounded
  reads, root-owned/administrator-owned storage, pinned handles, no-follow/reparse
  and single-link checks, and separate public/private/intent permission policies.
- Preparation reuses an unchanged incident and can reconstruct a missing public
  marker from its private binding. Binding is published before the public marker;
  partial, stale, or changed intent is never approval.
- Typed safety policy in `coordination/src/safety.rs`: trust, activity, package
  health, and protected acknowledgment are independent. Exhaustive combination
  testing enforces the approved blocking/warning table.
- Native Rust tests exercise the production storage functions on disposable
  protected fixtures, including an actual standard-user child on each platform.
  The Windows test uses `Invoke-RecoveryStorageStudentCI.ps1`, not the simulated
  storage helper from the initial permission-layout experiment.
- SHA-256 and UUID dependencies added to the coordinator; dependent lockfiles
  regenerated for the shared library. No package versions were changed in the
  updater/Tauri lockfiles; Cargo also normalized existing dependency edges.

## Deliberate boundary

This is a backend foundation, not the completed recovery feature or a candidate.
No normal startup, GUI action, installer/bootstrap, script, scheduler, or updater
currently calls these new storage/policy APIs. The current operation/installation
guards remain unchanged. A submitted intent does not remove, rename, or archive
`transaction.json`, does not create a protected acknowledged disposition, and
does not permit package changes. Tests explicitly require continued blocking.

The policy module does not collect evidence. In particular, an inactive SDE gate
is not proof of globally inactive package work. Native activity/health collection,
the current GUI inspection error handling, and enforcement adapters are still
part of the dependent implementation; this increment does not claim them fixed.

There is no production path override, arbitrary command/path payload, elevation
service, permission relaxation on existing protected files, or release change.
Owner Windows evidence and Mint v1.2.18 acceptance (35/0/0) remain untouched.

## Local verification

The coordinator compiles on Linux and cross-compiles/checks all targets/tests for
Windows GNU. Rust Clippy passes with warnings denied on both targets, and format
and diff checks pass. The new pure Rust payload and safety-policy tests pass.

The local UID is not root. Existing protected-fixture test helpers return early
without privileged execution; their ordinary Cargo test success is not native
permission evidence. Real Windows ACL tests, standard-user child execution,
privileged Linux fixtures, and PowerShell helper parsing/execution remain CI work.
The GNU target check is not a substitute for Windows MSVC/native execution.

## Exact native acceptance criteria

Use the latest PR head and existing Build Skyview Dev Setup workflow. No new
workflow dispatch or weaker fixture-only workflow is required.

1. `update-trust` Windows and Linux: `cargo test --locked` and static checks pass.
   Root-owned Linux invocation must have `SDE_REQUIRE_COORDINATION=1`; do not
   accept early-return non-root fixture results as the proof.
2. `recovery_real_standard_user_can_submit_through_production_storage` must
   actually execute under the native fixture context on both OSes. Its student
   process must not read/write private evidence or write the public marker, must
   submit through the actual API without elevation, and must emit
   `SDE_RECOVERY_PRODUCTION_STUDENT_SUBMISSION_OK` (asserted by the parent).
3. Require native tests for unchanged journal preservation, unchanged identity
   across reinitialization, active gate rejection, malformed/partial payloads,
   changed evidence and byte-identical replacement generations, and stale IDs.
4. Windows: overbroad intent rights/private-binding disclosure must be rejected.
   Linux: permission drift, symlink and FIFO intent paths must be rejected without
   following the link or blocking on IPC. Keep all existing coordination tests.
5. Retain the dedicated original Windows feasibility marker gate and all existing
   native build, trust, and signed-upgrade checks. Verify exact integrated source,
   not only the older #113 success. No check may be waived.

If a command fails, return its exact assertion/log excerpt to engineering.
Infrastructure/download failures belong to DevOps diagnosis, not silent retries
or a claim that the recovery contract passed. End if CI is pending; do not poll.

Do not merge, bump versions, dispatch candidate preparation, publish, approve
signing, resume automation, or request owner UAT for this partial increment.

## Remaining implementation

After production storage native validation, continue T1 legacy bootstrap/deployment
and crash consistency, T2 observation/enforcement adapters, T3 durable evidence
archives and protected acknowledged disposition, T4–T6 Windows/Linux/backend and
updater integration, T7 reports/history, and T8 UI/resumption. Then consolidate
and hand off full candidate validation and focused owner UAT under T9–T10.

Do not turn `verify_submission()` into cached execution permission. Reconciliation
must use the same lease as evidence preservation/new transaction and fresh safety
checks. The old blanket block is replaced only when that complete path is ready.
