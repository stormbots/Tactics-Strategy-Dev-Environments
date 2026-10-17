# #72 Phase 2: coordination boundary

Status: implemented and locally reviewed; protected/native validation pending.
No Update Now command or UI is enabled by this change.

## Ownership and admission

`session()` checks durable intent, takes A shared, rechecks intent, takes S
shared, rechecks intent and releases A while retaining S. Every failure releases
its temporary leases. Missing admission storage fails closed. Package initialization
creates the additional protected empty gate without replacing existing gates or
removing intent. Linux and Windows initialization use the same gate list.

`prepare_app_only()` retains O through compatibility validation and preparation.
`Preparation::close_admission()` consumes that ownership and adds A exclusive.
`Admission::try_installation()` adds S exclusive without reacquiring O/A. On
contention/error it returns ownership to the caller. Pre-commit deferral drops
O/A; an Installation retains O/A/S through the shared core and postchecks.
These APIs do not implement polling, request authorization or deadline enforcement.
A future worker must bound its wait and must never use dropping leases as recovery
from uncertain native launch. Transaction Drop still preserves durable intent.

Existing GUI operations remain nonblocking O requests while holding S. Scheduled
installation retains its previous O/S acquisition behavior; the repeated startup
intent checks protect against journal publication in legacy acquisition schedules.
No new global S/O ordering rule is imposed.

## Compatibility and hooks

Scheduled compatibility still requires the existing V1 marker. Manual preparation
requires the stronger `SDE_COORDINATION_ADMISSION_V2` marker in deployed maintenance
entry/helper files when maintenance exists. Current V1 helpers therefore disable
manual preparation with NeedsRepair. This is an intentional fail-closed migration
boundary, not a claim that adding a marker alone establishes compatibility.
Do not relabel legacy scripts: review/migrate their startup and inherited-lease
paths first. No tool baseline, external launcher, schedule or policy is changed.
Absent maintenance remains supported by the coordination prerequisite.

This API is only a coordination prerequisite. Full enablement must additionally
validate protected bootstrap/request capabilities, installed GUI/launcher support,
record schema and package hooks. No version-only or marker-only feature enablement
is implemented. Existing/copied binaries bypassing this crate are unsupported.

Linux postinst and Windows NSIS hooks already invoke the early coordination-init
path, before GUI session acquisition. Initialization validates gate identity,
ownership/ACL and shape without taking another lease; it must not treat its
parent's journal as an unrelated interrupted startup. Runtime proof of hooks under
parent ownership remains required on each platform.

## Local review and evidence

Two local startup tests pass: exact I/A/I/S/I ordering, failures at each intent
boundary, both gate failures, and temporary-lease release. Nineteen existing
shared installation-core tests pass. Linux updater all-target clippy and Windows
GNU coordination all-target check/clippy pass; formatting and diff checks pass.
Windows MSVC compilation, Windows execution, native hooks and desktop UAT are not
covered by cross-compilation.

Two added protected-fixture tests cover preparation allowing startup, admission
blocking startup, Busy retaining O/A, consuming ownership into Installation,
initialization preserving live exclusion, intent surviving owner loss, safe
pre-commit deferral and missing-admission rejection. They have NOT been run as
root. Existing tests silently skip protected fixtures when unprivileged, so a
whole-suite unprivileged green result would not close this gate.

## Next stop gates

Run the coordination tests with SDE_REQUIRE_COORDINATION=1 against disposable
root-owned /var/lib/coordination-test-* fixtures, including cross-process tests.
Only fixture directories may be created/deleted; no installed updates, package
operations, tasks or services. Then prove Windows ACL/share semantics and both
platform package hooks under retained ownership before claiming Phase 2 native
completion. Missing compatibility must remain disabled until reviewed migration.
Phase 3 must integrate deadline/boot/pause validation at the actual shared-core
commit boundary after native preflight, not merely before calling the core.

User will perform desktop UAT on owned Mint and Windows 11 PCs. Application builds
and release preparation remain deferred. W2h remains a counterexample; W2m's
immediate cleanup failure remains Fail; W2n native N1/N2 remain NotRun. Diagnostic
completion, cleanup correctness and authentication safety remain separate.
