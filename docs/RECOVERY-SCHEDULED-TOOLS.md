# Scheduled tool supervision: engineering handoff

Branch: `codex/recovery-scheduled-tools`, based on accepted #118 head
`fe0bee97a6d288e084feb7961ca95f04ea8da548` (Build `40881178483`). Stacks
still-unmerged #113–#118. A bounded part of T4, not full execution parity,
end-to-end Recovery UI, or a UAT/release candidate.

## Acceptance criteria and implementation

The existing authenticated maintenance worker's tool phase now uses the shared
Rust System mutation guard through `updater/src/tool_coordination.rs`. It does
not self-elevate, change a scheduler, accept caller paths/commands, or choose a new
baseline. Fixed trusted embedded supervisors and existing system environments
remain selected by the platform drivers.

- Acquire/recheck before the child copies or executes deployed applied scripts.
  Embedded immutable supervisor files may be materialized first; no deployed
  script content or package work is read/executed before the operation lease.
- Linux enters the existing `applied.py --leased` path. The flag alone grants
  nothing: `coord.check()` validates actual inherited session/operation descriptor
  identities before creating the applied snapshot. Windows's existing embedded
  wrapper validates its private token and held gate, then snapshots under the
  same Rust transaction. Nested wrappers do not clear the supervisor's journal.
- A new interruption without incident-specific consent, unknown/active work,
  incomplete health, or untrusted state defers with sanitized typed findings and
  exit 75. No interactive prompt, automatic acknowledgment, retry loop, package
  termination, lock deletion or journal reset. Existing next-invocation behavior
  remains; no automatic uncertain mutation retry.
- A valid incident intent/receipt permits only the existing evidence-preserving
  transition after independent fresh safety checks. Restart alone is not consent;
  consent alone cannot make an earlier unknown process lifetime inactive.
- Share the GUI's completion policy in `safety::known_backend_completion`: only
  successful controlled synchronous completion plus fresh native inactivity and
  no known incomplete state permits clearing its own new journal. Unknown health
  alone warns/allows. Failure/unknown outcome retains intent; Validation never
  acknowledges or completes a transaction.
- Both platform drivers stop before application discovery/staging/installation
  if tools defer or fail. Linux already stopped here; Windows now follows the
  same explicit `incomplete_outcome` contract. Application-update pause still
  affects only SDE installation, not tool maintenance. No signature, eligibility,
  installation identity or native package safeguard is changed.

No scheduler task/timer, baseline content/version, permission, deployed script
hash or application version changes. Standalone/manual outer script wrappers and
SDE application-installation recovery still use their prior conservative gates;
they require subsequent integration. Reports/history/acknowledgment UI and real
reboot/resumption remain later work. Do not claim full T4/T5 or release readiness.

## Tests and evidence

Local targeted results: coordinator harness 55 successful entries, with protected
fixtures returning early at UID 1000 (not native proof). The shared completion
table test runs locally. The updater compiled on Linux and its targeted
`tool_coordination::tests` outcome test passed. Coordinator Linux/Windows GNU and
updater Linux all-target Clippy with warnings denied passed, as did formatting,
eight backend/three permission contracts, Bash syntax and diff checks. Windows native
updater and Tauri execution remain CI responsibility; cross-compilation is not
native proof. No owner machine or actual package transaction was exercised locally.

Initial head `0f399e8` passed both trust jobs, general checks and the Linux native
Mint path in Build `40889137194`. Windows passed packaging/installed bootstrap
but failed at the first test-only fixture guard, before coordination-state access:
`GITHUB_ACTIONS` was absent in Task Scheduler's separate SYSTEM environment.
The harness had already set `SDE_NATIVE_UPGRADE_FIXTURE` explicitly there, but
omitted the non-secret CI indicator. The focused correction sets that one flag
inside the private SYSTEM worker, after its SID assertion and after the outer
disposable-CI guard has authorized creation. It does not copy runner credentials
or broadly inherit an environment. The Rust assertion, required test/markers,
production journals, nesting and gate behavior are unchanged. A source regression
requires the CI flag inside the child worker before native test execution while
retaining both guards. Nine backend contracts and diff checks pass locally;
PowerShell/SYSTEM execution and revised-head Mint/inherited validation remain CI
responsibility. No failed assertion was waived or replaced by old-head evidence.

Build `40894284658` at `fa1ed25` then reached the Windows contract but correctly
deferred with `activity: active`, `activityReason: package_active` and
`decision: block_active`, including after simulated restart provenance and intent.
The failure at the final exit-0 assertion was not evidence of missing consent or
coordination state. The fixture ran after real package provisioning without first
establishing native inactivity. Existing logs do not identify the matching process;
an idle MSI service or a still-finishing installer must not be assumed safe or
excluded from production inspection on this evidence. The later PowerShell packaged
NEXT invocation is after the failed native executable and was not reached in this
run; its assertions remain required, not independently proven failed or passed.

The focused fixture correction uses the same read-only native collector before
creating its synthetic journal. It waits at most 15 minutes for observed inactivity,
fails immediately for unknown activity or known incomplete package health, and
fails closed at its deadline. It never retries a mutation, kills a package process,
clears a journal, or changes production process classification. Production mutation
begin/run still independently recheck; unexpected later activity still fails the
unchanged exit-0 assertion. The outer SYSTEM observation deadline is 30 minutes to
allow this setup budget plus the actual upgrades; expiration never kills packages.
Fixture-only diagnostics log package process names/PIDs/parent PIDs before native
execution, not command lines or private journal contents. If activity never becomes
inactive, return this evidence for diagnosis rather than weakening the gate.

Targeted local validation of this correction: ten backend contracts; two updater
tool-coordination tests, including active-to-inactive, active timeout, unknown and
incomplete fixture outcomes; updater Linux all-target Clippy with warnings denied;
Rust formatting and diff checks. Native SYSTEM/Mint proof remains pending on the
new exact head. Owner Windows interruption evidence and Mint v1.2.18 35/0/0 remain
untouched; no release or UAT action is authorized by these fixture results.

The existing signed SYSTEM/Mint native fixture functions now call a test-only
contract using a private synthetic legacy journal on the disposable runner. It
verifies deferral with current-session uncertainty, still defers after intent
alone, and simulates previous-session provenance. Clearing only that fixture's
intent then proves restart evidence still needs consent. A resubmitted intent
allows a harmless fixed `true`/`cmd exit 0` child; original bytes/object and private
receipt remain archived and the new known-completed journal is cleared.
This is not an actual reboot or a production/test override flag.

Both existing native harnesses now require the exact marker
`SDE_RECOVERY_SCHEDULED_TOOL_CONTRACT_OK`, in addition to all original signed
upgrade and end-to-end markers. No successful test skip can replace this proof.
The same fixtures' existing NEXT packaged-worker invocations still run applied
maintenance while SDE installation is paused/ineligible: Linux through the actual
Mint launcher and Windows through its committed worker and temporary deterministic
no-package baseline (restored afterward). Keep their held-gate, applied snapshot,
baseline/user/settings and pause assertions intact.

## DevOps handoff

Validate the exact pushed head with existing Build Skyview Dev Setup; no duplicate
dispatch, waiver, older-head substitution or continuous polling. Require:

- Coordinator completion-policy table, all production storage/durable replay,
  bootstrap, mutation/nesting and root-required/native suites.
- Updater `failed_or_deferred_tools_never_authorize_application_work`, trust and
  signature/staging suites; native Tauri completion/stream/error tests still pass
  after sharing the policy predicate.
- `SDE_RECOVERY_SCHEDULED_TOOL_CONTRACT_OK` in BOTH signed native paths, plus real
  packaged next-invocation tool execution and original end-to-end/signed markers.
- Original feasibility and installed-bootstrap markers, including Linux inside
  actual Mint 22.3, native builds and all general/trust checks.

Return exact SHA, run/job URLs, counts and failure-specific assertions. Do not
merge partial work, sign, publish, prepare a candidate, resume automation or ask
for UAT. Preserve owner Windows evidence and Mint v1.2.18 35/0/0 acceptance.
After this gate, return to engineering for remaining direct-script and application
installation adapters, then report/history/Recovery UI and consolidated validation.
