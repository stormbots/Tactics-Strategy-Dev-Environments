# Linux manual system supervision: engineering handoff

Branch: `codex/recovery-linux-manual-supervision`, based on accepted #119 head
`c3328f2c79d3093e92e1c8c8fbf3b56e77f093f1`. The recovery stack remains unmerged.
This is another bounded part of T4, not full cross-platform parity or owner UAT.

## Acceptance criteria and boundary

Linux Install/system Repair and Update shell entry points use the shared native
System mutation policy when they do not already have real nested leases. The
original student workflow still requests sudo and does per-user configuration
and validation afterward. The installed app dispatches `--supervise-linux-system`
before starting the GUI. It never elevates itself or submits acknowledgment.

- Before private-state access, require effective UID 0. Sudo/admin group membership
  alone does not qualify. No new frontend command, permission or elevation route.
- Accept only an absolute, root-owned protected regular script (one hard link,
  no symlink, no group/other writes, protected ancestor directories) named
  `Install-SkyviewStudentDev.sh`, `Update-SkyviewStudentDev.sh`, or the deployed
  `skyview-student-dev-update`. Install requires `--system-only` and optionally a
  validated target account; updates accept no additional options. Arguments are
  passed as data, never shell command strings. The root caller cannot select an
  interpreter or arbitrary command through this interface.
- Run fixed `/bin/bash` with the same sanitized system environment as the GUI
  helper, under `mutation::Scope::System`. Fresh safety and generation-specific
  durable intent are reconciled under the lease. Never infer consent from sudo,
  Validation, CLI invocation, elapsed time, or native package-process absence.
- The existing shell nested path still executes Python's real descriptor checker.
  A pair of environment values is not a permit. GUI and scheduled callers keep
  their own Rust supervisor and do not recursively acquire a new operation gate.
- Only controlled success plus fresh inactivity and no known incomplete health
  clears this supervisor's own new journal. Nonzero/signal exits and unknown
  completion retain it; original evidence and durable receipts remain protected.
  No package timeout, termination, lock deletion or automatic retry.
- Missing/incompatible installed native support stops the operation; no fallback
  to Python's legacy system journal writer. The shell first uses the existing
  non-GUI `--coordination-init` mode and requires the new capability response.
  Old apps return no capability and stop there, never receive the unknown new
  supervisor flag and never accidentally open a root GUI. Initialization may
  prepare an incident under its gate; it never acknowledges or retires one.
  The capability string is compatibility metadata, not an execution permit.
  Scripts in user-writable downloads or
  checkouts must be installed into a protected location first. This is not an
  elevation feature for source checkouts. Old/mixed app versions fail closed.

Windows outer PowerShell invocation remains a subsequent increment. The old
Python `run system` interface is retained as a conservative legacy interface;
supported shell mutation entry points no longer select it. Read-only/session
wrappers and baseline provisioning content are unchanged. Application installation
recovery, diagnosis/guidance, reports/history and final Recovery UI remain later
tasks. No final user-facing acknowledgment action is enabled by this work.

## Verification and native gate

Targeted library tests cover invocation grammar, unelevated rejection, protected
script trust, real existing Python nesting and held gates, successful completion,
nonzero/signal retention, uncertain postchecks, acknowledged-generation evidence
preservation, and a synthetic supervisor crash. The crash test kills only its own
Rust test process; its harmless shell child exits naturally and retains its gate
until then. Protected tests return early outside root; those local entries are
not native proof. Existing coordinator policy/storage/replay tests remain required.

The existing Linux native job additionally requires
`SDE_RECOVERY_LINUX_MANUAL_SUPERVISOR_OK`, once on the installed host and again
inside actual Mint 22.3 before the signed-upgrade fixture. The fixture invokes the
installed release app through a root-owned, no-package shell script and the real
shell wrapper. It proves actual FD nesting, operation contention, known completion,
non-root rejection, extra-option rejection, forged-descriptor rejection, target
account argument retention, and unchanged original bytes/inode on deferral.
It simulates previous-boot provenance only in its synthetic metadata, verifies
that this alone cannot release the journal, then submits an explicit intent to
the existing slot. Successful re-execution must retain both original evidence
bytes and the original object's inode, plus a private receipt, and clear only
the new known-completed journal. This is not actual reboot/UAT proof. The fixture
neither replaces packaged backend files nor provisions development tools.
Cleanup is limited to its successfully verified synthetic history, under the
operation gate, with no active journal removed; failures preserve CI evidence.

Keep all existing native/bootstrap/scheduled-tool, trust, feasibility and signed
upgrade gates. Do not accept an older head, missing marker, or local protected-test
early return as evidence. CI owns full native proof and packaging; engineering
stops after pushing and recording the initial Build run, without polling.

Local results: coordinator harness 64 successful entries, including nine manual
test entries, with root-required cases returning early at UID 1000 (not native
proof). Invocation grammar and unelevated rejection executed locally. Coordinator
Linux all-target and Windows GNU all-target Clippy with warnings denied passed;
the Windows check is compilation/lint only, not native execution. Eleven backend
contracts, eighteen CI-scope/workflow tests, three permission-wiring tests, and
three Linux runtime tests passed. Python compilation, Bash syntax, the complete
Linux checksum manifest, coordinator Rust formatting and diff checks passed.
Packaged Tauri execution, ShellCheck/actionlint and protected/root/native proofs
remain delegated to the existing workflows; no local native pass is claimed.

### Fixture correction after initial native validation

Build `40946730414`, attempt 2, at `347b59e96c8b855b7e8a82c2c5760947c2a153c3`
failed in native Linux job `123727450657` before the manual-supervisor marker.
The fixture put its root-owned script under `/opt/sde-manual-ci-*`; the app
correctly returned `untrusted_entry_point` (exit 76). The native gate validates
every ancestor, not merely the private temporary directory and script. GitHub's
[runner image configuration](https://github.com/actions/runner-images/blob/main/images/ubuntu/scripts/build/configure-system.sh)
explicitly makes `/opt` mode 0777. A private root-owned child does not repair a
writable ancestor. The failed log did not capture individual ancestor metadata.

The fixture now uses `/var/lib`, matching the already-passing protected coordinator
fixtures, and independently checks each ancestor and both synthetic scripts with
`lstat` before native invocation. A mismatch fails with UID, mode, type and (for
files) link count, rather than silently changing host permissions. It never
chmods/chowns `/opt`, relaxes the production gate, changes coordination storage,
skips the marker, or substitutes a checkout binary. Metadata unit regressions
cover a private leaf under a writable/non-root/symlinked ancestor and unsafe
file mode, owner, symlink and hard-link counts. These are test setup checks,
not native trust evidence.

Focused local validation of the correction: thirteen backend contracts, Python
compilation and diff checks passed. Production Rust, shell wrapper, checksums,
workflows and all journal/gate/nesting behavior are unchanged. Actual installed
host and Mint 22.3 markers, Mint signed upgrade and every inherited Windows/Linux
gate must pass on the revised exact head; they remain pending, not waived.

### Consent-required deferral classification

Build `40978768354` at `9767b5dd720fcfdb3448ae72bc36cad6808a1bff` reached
the restart-without-consent assertion in the installed Linux verifier. The
application returned typed `Coordination(Interrupted)`, not success. Once fresh
safety/restart observations allow checking consent, `record_locked` returns no
receipt for an absent/invalid intent and `mutation::begin_at` correctly blocks
with `Interrupted`. The manual adapter classified that result as exit 76, while
its supported consent-required deferral protocol and verifier require exit 75.

The scoped fix adds only `Interrupted` to the manual adapter's deferral mapping.
It does not change the shared mutation decision, receipt validation, retirement,
journal, nesting, or gate behavior. The installed verifier's exit-75/no-child
assertion and both required host/Mint markers remain unchanged. A deterministic
local regression first reproduced `Interrupted: 76 != 75`, then passed after
the mapping correction. It also keeps unavailable/untrusted/repair-required,
invalid invocation and uncertain completion classified as exit 76. The root-only
manual lifecycle regression now explicitly checks no consent after simulated
restart: exit 75, no child, unchanged original bytes/inode and no archive; then
valid consent permits the existing evidence-preserving transition. Root-required
execution remains CI responsibility, not a local pass claim.

Focused local validation: ten manual Rust test entries passed (protected cases
return early at UID 1000), Linux all-target Clippy with warnings denied, Rust
formatting and diff checks passed. Native Linux host, actual Mint 22.3 and every
inherited Windows/Linux gate remain required on the new exact head.

The same failed Build's Windows native job encountered HTTP 503 fetching
`powershell-core` 7.6.9 from the Chocolatey community feed in the existing real
Node migration fixture. That is separately evidenced infrastructure failure;
no Windows application change or retry was made for it. DevOps must reassess
the feed on the corrected head and still require the full signed SYSTEM upgrade,
not infer success from the skipped step. No release or UAT action occurred;
owner Windows evidence and Mint v1.2.18 35/0/0 remain preserved.

## DevOps prompt

Validate the new PR's exact head in its existing Build Skyview Dev Setup run.
Require Linux root `manual_*` tests, installed manual-supervisor marker on both
host and actual Mint 22.3, and every inherited Windows/Linux coordinator, trust,
feasibility, bootstrap, scheduled-tool, native-build and signed-upgrade gate.
Return SHA, run/job URLs, completed/pending checks and exact failure assertions.
No merge, signing, publication, release preparation, automation resumption or UAT.
Owner Windows interruption evidence and Mint v1.2.18 35/0/0 stay untouched.
