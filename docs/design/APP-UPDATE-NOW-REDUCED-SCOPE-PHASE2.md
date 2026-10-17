# #72 Phase 2: coordination boundary

Status: implemented and locally reviewed; Linux protected process tests passed;
Windows runtime and installed package-hook validation pending.
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
pre-commit deferral and missing-admission rejection. They subsequently passed as root; see the dated validation sections below. Existing tests silently skip protected fixtures when unprivileged, so a
whole-suite unprivileged green result would not close this gate.

## Next stop gates

The Linux protected coordination fixture gate passed. Prove Windows ACL/share
semantics and both platform installed package hooks under retained ownership
before claiming complete native validation. Missing compatibility must remain disabled until reviewed migration.
Phase 3 must integrate deadline/boot/pause validation at the actual shared-core
commit boundary after native preflight, not merely before calling the core.

User will perform desktop UAT on owned Mint and Windows 11 PCs. Application builds
and release preparation remain deferred. W2h remains a counterexample; W2m's
immediate cleanup failure remains Fail; W2n native N1/N2 remain NotRun. Diagnostic
completion, cleanup correctness and authentication safety remain separate.

## Authorized protected Linux validation — 2026-10-17

The owner authorized root coordination tests using disposable fixtures only. The
non-root shell has no sudo, so the existing test executable was copied with its
local runtime libraries into a temporary Docker image (no downloads or application
builds). The container ran UID 0, network none, all capabilities dropped, read-only
root filesystem, bounded memory/PIDs and a private 16 MiB /var/lib tmpfs. No host
filesystem or Docker socket was mounted into it.

`SDE_REQUIRE_COORDINATION=1` prevented silent unprivileged fixture skipping. All
10 test entries passed, including six protected-fixture tests; process_probe is
a helper also invoked by the cross-process test, not an independent scenario.
The native kernel was Linux 6.18.44 x86_64, not a Mint desktop environment.
Fixture inventories were empty before and after. Container and temporary image
removal both succeeded. The binary digest, source commit, invocation and raw
output are recorded in evidence/ISSUE72-PHASE2-PROTECTED-LOCAL.{json,txt}.

This closes the previously unrun Linux protected-fixture gate only. It does not
validate installed package hooks, capability migration, Windows share/ACL runtime
behavior, desktop UAT, privileged bootstrap or request deadlines. No changes to
production code were needed during this run. The earlier statements that fixture
tests had not yet run describe the preceding local-review stage.

## Phase 2 review — 2026-10-17

Reviewed source and prior protected evidence; fixed these findings:

- Readiness queries previously released O before checking S and compatibility.
  They now retain O/S throughout, with a protected regression test.
- A missing entry point previously hid orphan helpers or dangling links. Only
  true absence of both files counts as no maintenance. Partial/untrusted state
  fails closed. Markers must be complete UTF-8 lines, not substring matches.
- Shared-core intent creation now forwards its explicit scope. Publishing
  app-only intent requires an Installation retaining admission ownership. A
  scheduled O/S-only owner cannot publish it; scheduled journal shape is unchanged.
- DEB and NSIS bootstrap code now reads a bounded protected schema-1 intent. Its
  app_only scope suppresses service drop-in/task action/maintenance-ACL migration;
  it never grants install authority or bypasses trust checks. Malformed, oversized
  or unsupported present intent fails rather than falling back to scheduled mode.
  Existing schema-1 records without scope retain scheduled behavior. Engine and
  protected application receipts still activate normally. No environment boolean
  chooses packaging scope.
- Windows lookup reuses the existing anchor-aware coordination checks, avoiding
  rejection of ordinary ProgramData creation grants. It pins a regular, singly
  linked record and bounds reads to 4097 bytes, rejects beyond 4096, uses strict
  UTF-8 and exact string/type validation. This has local syntax/parser coverage;
  native ACL/handle proof is still pending.
- The compatibility error no longer promises that today's baseline Repair can
  deploy the new V2 capability. Current V1 helpers remain deliberately ineligible
  for manual preparation; no scripts were relabeled or silently migrated.

A new protected test runs initialization in a separate process while the parent
retains O/A/S and scoped intent, verifies all three gates remain excluded and the
intent bytes unchanged, then completes and reopens normally. This executes the
coordination initializer, NOT the installed DEB/NSIS packaging hooks.

The initial expanded run failed because the new test closed the child's stdout
before the child harness finished reporting. Five later entries failed from the
poisoned fixture mutex. The test now captures child output through completion.
Both the failed output and the final passing evidence are preserved under
`evidence/ISSUE72-PHASE2-REVIEW-*`. The initial failure is not represented as six
independent product failures or erased by eventual cleanup.

Final QA: 14 root coordination entries pass (nine protected fixtures and one
helper entry); fixtures empty before/after and temporary container/image removed.
Forty updater library tests pass, including nineteen shared-core tests; four
native/protected tests are filtered. Python local checks pass: seven mocked hook,
three runtime and nine schedule tests; four unrelated protected schedule cases
remain skipped. PowerShell 7.6.7 on Linux parses the Windows hook and passes fifteen
scope cases. Formatting, Linux/Windows-GNU clippy, Python compilation and shell
syntax pass. Details and source commit are in `evidence/ISSUE72-PHASE2-REVIEW.json`.

### Remaining native gates and safe continuation

| Gate | Required proof / stop condition |
| --- | --- |
| Windows coordination and hooks | Run development tests under real Windows, including PowerShell 5.1, standard-user admission, protected ACL/share checks and initialization while O/A/S/I are held. Stop on hook conflict or unsupported parent ownership. GNU cross-compilation and Linux PowerShell are insufficient. |
| Installed package behavior | In disposable native upgrade tests, verify actual DEB/NSIS hooks preserve tool baseline, timer/task configuration, enabled state and pause policy, while activating the expected engine and retaining intent on failure. Stop on schedule/tool mutation or premature intent removal. No package operation was executed in this review. |
| Compatibility deployment | Establish protected bootstrap/startup/launcher/schema/package-hook capabilities for both current and candidate packages; validate external entry points. V2 marker checks here are only a prerequisite. Do not enable on old hooks or relabel V1 helpers without migration review and native proof. |
| Worker integration | Phase 3 must supply fixed authorization/request claiming, supervisor lifetime, suspend-aware deadlines/boot checks, final commit validation after preflight, and recovery handling. Stop if any authority or ownership guarantee cannot be established. |
| Desktop UAT | Owner uses owned Mint and Windows 11 PCs after a separately authorized test build; no UAT is due from the owner at this code-only stage. |

Engineering can proceed with Phase 3's bounded worker implementation once
separately scoped; native gates above remain required before feature enablement.
No new product decision is needed for these corrections. No PR, application build,
release, stable promotion or rollout was initiated.

## PR #73 review corrections

Windows now seals a flushed transaction writer into a read-only handle that
permits hook readers while excluding writes/deletion. Do not flush that reader
at completion: Windows FlushFileBuffers requires write access and the immutable
record was already flushed at publication. A Windows fixture verifies reader
access and denied write/delete before terminal closure.

Older deployed Windows workers still hold their original no-sharing journal
handles. Package hooks therefore must not read `transaction.json` to choose scope.
The manual transaction also publishes a separate protected, bounded
`installation-scope.json` hint, closes its writer and syncs before begin returns.
Only then can shared-core native launch occur. Scheduled transactions never
create this hint. Its absence retains legacy scheduled packaging behavior without
trying to read an older worker's locked journal. A present hint must have exactly
the supported app-only scope/kind/schema; malformed or unknown content fails closed.
This is preservation metadata, not installation or recovery authority.

Both journal and scope hint are startup/preparation recovery barriers. Drop or
failed publication leaves evidence; initialization never removes it. Known terminal
completion removes/syncs the hint FIRST, while the journal still blocks legacy
workers, then closes/removes/syncs the journal. Hint cleanup failure retains the
journal. Owned recovery must account for both records; absence of a PID or elapsed
deadline never authorizes clearing either. Windows power-loss ordering remains a
native stop gate; no durability proof is claimed by this code.

The review also fixed CI's stale exact dependency-list assertion, fail-fast
Windows Rust validation (later lint success must not hide test failure), and
Windows capability fixture ownership (runner-personal-SID files correctly fail the
production trust check). Bounded failure annotations make diagnostics available
without requiring raw-log storage access. Original historical evidence is retained;
subsequent exact-head native CI results are recorded in the PR review.
