# #72 Phase 1: protocol feasibility validation plan

**Status:** W1 executed locally (L1); the separately authorized W2a/W2b/W2c unprivileged
Linux lock subsets were executed (narrow L2 evidence). Remaining W2/W3 and
production integration remain unauthorized. No workflow/application build was dispatched.
See [W1 results](../../tests/prototypes/manual-update/EVIDENCE.md).
**Baseline:** [protocol revision 2](APP-UPDATE-NOW-PROTOCOL.md), commit
`7a9c3de3aee6f2bab22e9c91f6acaf0d934f7005`.
**Issue:** https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/72
**Owner:** Codex owns harnesses, engineering review and evidence; the owner performs
later desktop UAT. This plan requests no workstation action from the owner now.

## 1. Purpose, boundaries and evidence levels

Determine whether B01–B06 have a feasible safe implementation, identify necessary
protocol revisions, and bound a later prototype. Do not implement the Schedule
feature, invoke an installed updater, modify fleet state, allocate a version or
create a candidate/release/signature. Do not create/change workflows, open a PR
that triggers builds, or dispatch anything under the current authorization.

The experiment list below remains the validation target. Selected L1 portions
were exercised by the authorized W1 harness; see its per-fault ledger rather than
marking entire experiments complete. Native tests, fixture packaging, W2/W3 and
CI dispatch still require separately granted scope. Those permissions are not inferred from
this planning request or from the already approved v1.2.9 rollout.

Evidence levels must remain distinct:

| Level | What it can establish | What it cannot establish |
| --- | --- | --- |
| L0 source/design review | Explicit invariants, API candidates, legacy contracts and gaps | Executable correctness or OS behavior |
| L1 local model/surrogate | State-machine properties and deterministic race/fault outcomes in a bounded model | Real pipe/token/ACL/flock/share-mode semantics, UAC, package installation or power-loss durability |
| L2 disposable native primitive tests | OS identity, IPC, locks, task/service lifetime and filesystem behavior exercised | Full SDE replacement, actual legacy package-hook migration, real desktop/screen-reader acceptance |
| L3 later integrated native upgrade/UAT | Actual installer, bootstrap, activated engine, retained policy/data and desktop behavior | An absolute proof for untested OS/account/storage configurations |

A blocker may be **Design feasible; integration proof pending** after Phase 1.
Do not mark B01–B06 resolved from surrogate success. Protocol review readiness,
permission to implement, and acceptance of a shipping feature are separate gates.

## 2. Narrow prototype proposal

Propose a separate test-only crate/harness beneath `tests/prototypes/manual-update/`
with no production imports that invoke fixed real SDE paths. No production source,
Tauri command/capability, updater CLI, installer hook or workflow changes. Suggested
actors are: GUI lease holder, supervisor, IPC peer, fake native child and legacy
O/S-only actor. An orchestrator controls named event barriers and synthetic clocks.

All paths, lock objects, requests, receipts and capability fixtures belong to a
fresh test root. The nonprivileged orchestrator cannot inject arbitrary executable
paths into a root worker: root-side helpers have a fixed sentinel action and fixed
registered test-root policy. Test configuration flexibility is not a proposed
production privilege API. Use a distinct PROTOTYPE identifier and no release keys.

The fake native child can only write a predeclared sentinel in that root, wait at
barriers and exit with a chosen fixture code. It never launches NSIS/APT/DPKG,
Chocolatey, SDE, project tools, a downloaded executable or another user command.
Old-worker actors reproduce reviewed O/S semantics against test objects; they are
not evidence that an old released installer actually upgraded successfully.

### Proposed authorization units

| Wave | Proposed work, only after authorization | Explicit exclusions |
| --- | --- | --- |
| W1: local model | Implement state/consent model, bounded framing parser, fake transport, synthetic filesystem/crash recorder, deterministic scheduler and checks. Compile/run only this isolated harness in temporary paths. | No elevation, scheduled tasks/services, real IPC endpoint creation, package fixtures, SDE changes or CI/workflow dispatch. |
| W2: native primitives | Add fixed-action Windows SYSTEM broker and Linux supervisor/IPC/lock adapters, solely on disposable native test hosts. Run sentinel experiments after separate native-test authorization. | No weekly task/timer changes, fleet hosts, installed updater, actual application upgrade or production GUI. |
| W3: disposable fixture integration | If separately authorized, create minimal non-SDE NSIS/DEB fixtures and test bootstrap context/capability extraction against temporary state; perform controlled VM resets/storage tests. | No published SDE packages or signing keys, no application version changes, no production package database/data outside disposable host. No implicit CI dispatch. |

**W1 only was subsequently authorized and implemented locally.** Its findings
require review before expanding scope; no privilege-specific code was added. W2/W3 require
review of their exact host/privilege/cleanup scope; they are not included in W1.
Do not generalize a successful prototype straight into a privileged production API.

## 3. Environment and safety envelope for later native experiments

- Windows Server 2022 CI can supply disposable SYSTEM/task/ACL/process evidence;
  actual Windows 11 desktop sessions are required for genuine same-user and
  alternate-administrator UAC. A pre-elevated runner is not a UAC test.
- Mint 22.x userland/container can exercise some UID/socket/filesystem primitives;
  booted Mint Cinnamon with system systemd/logind/polkit is required for logout,
  desktop authentication, suspend/resume and service lifecycle evidence. Debian
  local tests and Mint containers cannot certify those behaviors.
- No disposable desktop VMs are currently available. Record desktop-only cases
  **Blocked**, not Pass. Codex should use existing permitted native automation for
  engineering tests only after authorization; do not ask the owner to provision VMs
  merely to repeat existing CI. Do not use the owner's working laptop as a default
  crash/power-loss/task-broker laboratory.
- Every privileged test uses a host/account-bound test enrollment and random run
  UUID in a separate protected namespace; reject production SDE roots, arbitrary
  caller paths, pre-existing test data, links or unknown ownership. Snapshot first.
- Dedicated test users contain no student data. Capture permission metadata and
  before/after inventory. Do not export credentials, tokens, private capabilities,
  request secrets, personal profiles or full protected logs.
- Cleanup is run-owned, idempotent and refuses unknown/changed paths. Inert failed
  test tasks/units may remain until reviewed rather than killing an uncertain child.
  Disposal/snapshot reset is the final recovery, never blanket lock deletion.
- Test sentinels may be deliberately terminated on disposable hosts. That permission
  does not extend to production installers, package managers or maintenance.

## 4. B01 — Windows UAC-to-SYSTEM broker

**Question:** Can a fixed, one-shot administrative broker start exactly one bounded
SYSTEM request without exposing a reusable standard-user privileged task?

### Experiments

- **E01 (L0/L1):** enumerate exact task folder/name, command, allowed UUID syntax,
  request fields, claim/expiry states and task/request cleanup rules. Model duplicate
  Run calls and crash between claim and worker start. Reject arbitrary action/path/
  user/argument substitution and return inert terminal state for a claimed request.
- **E02 (L2 Windows):** UAC-authorized test broker registers an on-demand task whose
  only action is the fixed installed test bootstrap/sentinel. Record broker and
  worker token identities. Run standard-user attempts to read secrets, execute,
  edit, replace, duplicate or register in that namespace. Test same-user and
  alternate-admin consent separately from pre-elevated runner behavior.
- **E03 (L2 Windows):** capture all task settings: no recurring triggers or automatic
  restart, no default execution deadline that can kill an accepted installation,
  and no battery/idle/session transition policy that terminates the fake child.
  Exercise battery/session/disconnect transitions where the host supports them.
  Expired or already-claimed requests never start a new attempt after a scheduler
  delay/retry. Verify no dependency on the weekly SDE task.

**Pass:** only the fixed worker runs as LocalSystem; GUI identity stays the original
unelevated user; unauthorized task/request operations fail; one request produces at
most one committed sentinel; runtime/energy/session settings cannot terminate a
post-commit child; cleanup touches only proven terminal run-owned objects.

**Fail:** administrator-only fallback, standard-user task-run/edit authority,
variable command execution, duplicate commit, secret exposure, or automatic retry
of a committed/uncertain request. Any fail stops the Windows broker approach.

**Evidence:** exact XML/security descriptors and request schema with secrets
redacted; kernel identities/process creation data; denied-access results; task
setting/transition trace; task/namespace inventory before and after. Genuine UAC
is still required to clear the desktop portion of B01.

## 5. B02 — Authenticated IPC and bounded control

**Question:** Can both peers authenticate the intended process instance and retain
safe authority under alternate accounts, endpoint races and hostile traffic?

### Experiments

- **E04 (L1):** strict frame parsing with length limit, duplicate JSON keys, depth,
  integer bounds, unknown tags/fields/version, partial frames and disconnect at
  every byte boundary. Model event sequence independently from immutable Ready
  epoch. Replay command IDs with identical versus altered payloads and cross-
  transaction capabilities. Test all Cancel/Commit orderings.
- **E05 (L2 Windows):** prove the exact named-pipe access mask, SYSTEM owner/DACL,
  FIRST_PIPE_INSTANCE/local-only behavior, client impersonation/token reversion,
  and kernel client/server process checks. Try same SID different logon/session,
  alternate-admin credentials, wrong SID/PID/image, server spoofing, extra pipe
  instance, pre-squatted name and descriptor alteration. Query denial must reject
  rather than silently skip server authentication.
- **E06 (L2 Linux):** root-owned socket path/ACL and SO_PEERCRED with separate
  unprivileged users and process instances. Attempt endpoint replacement, inherited/
  passed FD reuse, PID reuse, process exit/exec, namespace/session mismatch and
  private-root traversal. Verify the original desktop UID comes from authenticated
  peer context, not untrusted environment or request identity strings.
- **E07 (L1 then L2):** silent peer, slow partial frame, flooding and a peer that never
  reads. Exercise the five-second frame, thirty-second handshake, control-rate and
  queue bounds. Fill the outbound pipe after commit. The supervisor must still
  evaluate deadlines, release safe pre-install locks, run postchecks and persist
  terminal state without waiting for the reader.

**Pass:** intended peers work in each supported account mode; spoofed/foreign peers
cannot obtain control or cause GUI close; valid Ready consent survives harmless
progress; replay/conflicting commands do not repeat effects; memory/queues stay
within declared limits; blocked IPC never stalls the supervisor state machine.

**Fail:** a PID/path/nonce alone authenticates a peer; endpoint ownership can be
spoofed; alternate-admin binding changes the target user; malformed traffic changes
state; replay repeats an effect; or backpressure retains locks indefinitely.

**Evidence:** concrete masks/ACLs/OS API outcomes, peer/process-instance matrix,
redacted frame corpus/results, command-effect counts, queue/resource high-water
marks and ordered progress/deadline traces. Do not record private capabilities.

## 6. B03 — Independent supervisor and child lifetime

**Question:** Can the accepted transaction survive normal GUI/session teardown
without the OS killing package children or treating parent death as completion?

### Experiments

- **E08 (L1):** crash GUI, broker and supervisor independently at every state. Before
  accepted commit, confirm no sentinel starts. After accepted commit, close the GUI
  and transport; confirm the supervisor proceeds only after existing sessions drain.
- **E09 (L2 Windows):** SYSTEM task worker outlives GUI/terminal close, desktop logoff
  and elevated broker exit. Retain a fake native child after supervisor loss and
  demonstrate that the durable journal blocks normal startup/retry. Inspect task
  timeout/battery/session and process-job settings instead of assuming detachment.
- **E10 (L2 booted Mint):** compare direct detached root supervision with a dedicated
  transient **system** service started by the fixed polkit-authorized broker. Neither
  may depend on the weekly maintenance unit or create a permanent daemon. Inspect
  logind/user-session cgroups, logout and stop behavior. In particular, a transient
  unit's default cgroup-kill/restart/timeout settings must not kill a package child
  after supervisor failure. Choose/document a service type, process ownership,
  child-survival and eventual reaping strategy from evidence, not `setsid` alone.

**Pass:** ordinary GUI/terminal/session closure does not abort accepted work; root/
SYSTEM remains the only installer authority; supervisor loss leaves the child
uninterrupted and durable uncertain intent intact; no automatic duplicate restart.
Before commit, disconnect cancels safely and releases only proven pre-install state.

**Fail:** terminal/logoff/user-slice cleanup kills the accepted child, a task/service
stop policy kills the native process tree, the GUI hosts the supervisor, or process
absence is used to clear intent. Redesign lifetime handling before integration.

**Evidence:** process tree plus stable creation identities, job/cgroup/unit config,
ordered close/logoff/kill events, fake-child sentinel lifecycle and journal/startup
results. Container or Server evidence cannot certify desktop logoff behavior.

## 7. B04 — Package-hook migration and target capabilities

**Question:** Can additive bootstrap distinguish its own live installation from
unrelated uncertain work, including legacy parents that lack a new bootstrap token?

### Experiments

- **E11 (L0/L1):** enumerate actual old/new hook and coordination contracts at source
  revisions 1.2.5, 1.2.9 and the proposed feature. Inspect `--coordination-init`,
  Windows share-mode metadata probes and Linux fixed schema-1 launcher. Model
  new/legacy parent, manual/direct installer and unrelated interrupted journal.
  Reject any rule based only on a flag, environment string, journal presence or
  an unauthenticated ancestor PID. Record an explicit supported migration rule or
  leave legacy-hook authentication unresolved; do not fabricate a proof.
- **E12 (L2 then separately authorized L3):** run a minimal fixed hook surrogate
  with parent O/A/S and journal held. It validates existing objects and creates
  additive test objects without reacquiring parent locks. Try a forged hook-context
  call, orphaned parent and mismatched transaction. Confirm no journal/gate reset,
  no live snapshot cleanup, and no child-versus-parent wait cycle. Later miniature
  NSIS/DEB fixtures must exercise genuine native hook invocation; actual supported
  old SDE-to-feature upgrades remain a later integration requirement.
- **E13 (L1, then separately authorized fixture packaging):** define versioned
  capability fields in DEB control metadata and Windows NSIS/PE resources, inside
  bytes authenticated by the existing manifest. Test bounded inspection after
  authentication without executing target code. Missing/unknown/downgraded claims
  reject the target. Compare declared versus installed actual capabilities.
  Reusing strict schema-1 metadata must not introduce unknown signed-manifest fields.
- **E14 (L1/L2):** crash at every additive-file/activation-receipt boundary. Capture
  gate identity before/after, including old leases. Test compatible rollback,
  unsupported rollback/uninstall and an active unrelated journal. Capability
  readiness is not published early; active coordination objects are never replaced.

**Pass:** an authenticated own hook can complete without recursive locks, while a
forged/unrelated hook cannot obtain the exception; all old gate identities and
leases survive; target capabilities are inspectable within signed-installer trust;
partial activation is unavailable, not ready; schema-1 verifier interoperability
is preserved. Explicitly list every old version/source and invocation mode covered.

**Fail:** every own upgrade rejects its parent journal, a plain flag grants bypass,
old leases are detached by gate replacement, capability is inferred from semver,
uninstalled target code runs for discovery, or old fleet verifiers reject the new
manifest format. Do not use broad Repair as a hidden migration shortcut.

**Evidence:** old/new contract matrix with source hashes, hook authorization rule,
barrier trace, gate file identity/permissions, fixture declarations/parser results,
activation interruption matrix and old-verifier compatibility results. Surrogates
cannot clear the actual-legacy-upgrade portion of B04.

## 8. B05 — Durable intent, terminal ordering and restricted startup

**Question:** Does every observable crash boundary preserve either a proven safe
pre-install state or a recoverable uncertain installation, without false success?

### Experiments

- **E15 (L1):** journal/receipt model with injection before/after each create, write,
  flush, replacement, directory/namespace persistence and acknowledgement. Enforce
  intent before mutation; complete receipt/status before journal removal; journal
  removal before final lock release. A public Updated snapshot plus unresolved
  intent must still yield recovery guidance, not ordinary success/startup.
- **E16 (L2):** reproduce write ordering on disposable Windows NTFS and Mint-supported
  native filesystem. Abruptly kill only test actors; restart the harness and inspect
  files/identity/locks. Process-kill survival is not power-loss durability evidence.
- **E17 (later disposable VM/storage authorization):** controlled reset/power-loss
  tests at publication boundaries. Verify documented Windows file replacement/
  flush semantics and Unix file plus parent-directory fsync behavior. No forced
  reboot or reset on the owner's working computer. If environment cannot support
  this, retain the power-loss portion as Blocked with the precise claim unproven.
- **E18 (L1/L2):** journal remains while fake native child survives supervisor loss,
  child ends nonzero/unknown, or postcheck fails. Test native restricted-startup
  notice without obtaining a normal session lease. Recovery may proceed only with
  authenticated privileged inspection of actual child quiescence/package state;
  test-only sentinel quiescence is not proof of real APT/NSIS recovery correctness.

**Pass:** no native mutation without durable intent; no normal Updated/startup from
uncertain state; proven pre-install cancellation leaves no permanent admission
block; malformed/unsupported receipts fail safely; a private journal/PID disappearing
alone cannot authorize clearing uncertain native intent. No timer unlocks a live or
unknown transaction. Later real package recovery stays a separate acceptance gate.

**Fail:** power loss can expose an apparently completed but unreconciled transaction,
public status overrides the journal, stale Ready is treated as authorization, or
age/parent death/receipt absence is interpreted as native completion.

**Evidence:** storage/platform/version, exact persistence API sequence, crash-point
inventory, recovered receipt/journal bytes with secrets excluded, startup decision
and quiescence proof. Mark each claim L1/L2/L3; no fabricated power-loss result.

## 9. B06 — Coordination/state-machine proof and timing

**Question:** Are all reachable interleavings safe, with a bounded pre-install
handoff under stated fairness/OS assumptions, while retaining old-client exclusion?

### Experiments

- **E19 (L1):** deterministic state explorer for one supervisor, initiating GUI,
  second participating GUI, legacy O/S-only actor, scheduler, transport and crash
  events. Model A/O/S ownership, immutable Ready epoch, commit/cancel serialization,
  durable intent and bootstrap hook. Explore every enabled transition within a
  documented finite bound and report state count/coverage/counterexamples. A
  finite model is not a universal proof of arbitrary processes or OS fairness.
- **E20 (L1 then L2):** event barriers around all gate attempts, acknowledgement,
  GUI close, post-S journal check, intent creation, spawn, postcheck and release.
  Force both orderings for each pairwise conflicting transition. Include old
  workers writing intent between startup's first and post-S checks, a legacy GUI
  holding S, repeated launches and GUI/backend wrappers taking S then trying O.
  Never use successful timed sleeps as race-freedom evidence.
- **E21 (L1 then L2):** verify fixed 30-second session drain, 45-second total pre-intent
  window, five-minute Ready, ten-second eligibility freshness, IPC deadlines and
  suspend/resume invalidation under synthetic clocks then native platform clocks.
  Include 11–30-second legitimate session drains: under revision 2's current strict
  freshness wording these may safely defer even before the drain allowance ends.
  This is historical revision-2 behavior. Revision 3 resolves D01: freshness at
  accepted commit, with a separate 45-second final-launch-decision deadline.
  Align W1 and test exact boundaries before claiming revision-3 coverage; do not silently relax freshness
  or perform network I/O after admission closes. Kernel-uninterruptible I/O is not
  promised a hard wall-clock termination; uncertain intent is never erased to meet
  an advertised time limit.
- **E22 (L1/L2):** execute all F01–F48 at the evidence level actually supported.
  Map each row to an experiment and result, including failures, Blocked and Not run.
  Test documented last-pause-read versus spawn orderings without claiming atomic
  GitHub eligibility or that a concurrent pause always preempts a launch.

**Safety pass:** no uncommitted native start; no simultaneous installer/GUI session
for participating clients; no duplicate effect; no lock upgrade/reentrant wait;
unknown durable intent blocks normal startup/retry; legacy holders cause safe
bounded deferral rather than unsafe replacement.

**Liveness pass:** with fair scheduling, functioning kernel/storage, responsive
bounded local probes and no continuing legacy blocker, the accepted handoff reaches
installation or an explicit pre-install terminal outcome within the specified
logical bounds. A hostile lease holder may cause deferral; it cannot be forced
out or turned into authorization. Native installation itself has no kill deadline.

**Fail:** any counterexample, unspecified transition, deadline extended by polling,
lock leaked through a normal cancellation, progress invalidating consent, or an
unsupported legacy process being treated as admission-aware. Fix the protocol/model
and rerun affected schedules; do not average failures out with successful stress runs.

**Evidence:** state diagram/transition table, invariants and fairness assumptions,
exploration configuration/counts, reproducible counterexample or barrier trace,
resource/lock inventory, time-source behavior and F01–F48 coverage ledger.

## 10. Traceability to protocol fault cases

Every case is mapped; this is a planned coverage map, not a completed test report.

| Experiments | Protocol cases |
| --- | --- |
| E01–E03 Windows broker | F04, F05, F14, F36, F37 |
| E04–E07 IPC | F06–F09, F16, F21, F32, F38, F39, F48 |
| E08–E10 supervisor lifetime | F15, F20, F22–F25, F35, F43 |
| E11–E14 migration/capabilities | F10, F11, F28–F31, F34, F40–F42, F47 |
| E15–E18 durability/recovery | F19, F23–F27, F32, F34, F46 |
| E19–E22 model/race/timing and result accounting | F01–F48; F01–F03/F12/F13/F17/F18/F33/F44/F45 have dedicated model/state accounting here |

F33's production layout, actual desktop keyboard/screen-reader and progress UI
acceptance cannot be proven by the Phase-1 state model. Mark those portions Deferred
to integration/UAT. Likewise real package upgrades, power loss, reboot-required
handling and package-child recovery cannot become Pass from fake sentinels.

## 11. Evidence package and decision ledger

Each later run records: source commit/tree and fixture hashes; experiment/F-case;
platform/kernel/filesystem/desktop and account mode; harness/prototype version;
privilege/enrollment scope; event/barrier sequence; state/lock owner identities;
expected/observed behavior; result and evidence level; cleanup/restoration result.
Preserve failure traces and failed attempts as well as successes. Use monotonic
relative times plus wall-clock correlation and boot identity; redact secrets.

Use these result values: Pass, Fail, Blocked, Not run, Deferred-to-integration.
A blocker ledger separately says Unproven, Redesign required, Design feasible /
integration proof pending, or Resolved at the named evidence scope. No blanket
“all blockers cleared” if only W1 or Server/container tests ran.

| Decision / gate | Required disposition before proceeding |
| --- | --- |
| D01 Timing compatibility | Resolved in protocol revision 3: age ≤10 seconds at accepted commit; drain <30 seconds; final launch decision <45 seconds after A. Selected revised W1 local checks now pass; native timing evidence remains pending. |
| D02 Windows SYSTEM mechanism | Accept the narrowly scoped one-shot task only after E01–E03/E05 prove fixed action, access rights and account modes; otherwise redesign. |
| D03 Linux lifetime mechanism | Choose direct root versus transient system-service supervision from E10; explicitly control cgroup/restart/kill behavior without a permanent daemon. |
| D04 Legacy hook authorization | Specify and prove a new-parent and supported-old-parent binding. If infeasible, define a supported initial migration route instead of weakening the exception. |
| D05 Capability representation | Freeze exact authenticated installer fields, bounds/parser and old-verifier compatibility only after E13. No signed schema-1 format extension by accident. |
| D06 Durability / recovery limits | Record exactly which crash/power-loss and real-child reconciliation guarantees are proven and which remain blocked/integration work. |

Stop the current wave on privilege escape, unauthenticated peer control, a duplicate
committed effect, unsafe startup during uncertain native work, or gate/journal
replacement. Preserve evidence and redesign before executing dependent experiments.
Product-level application integration remains unauthorized even after a successful
wave; review evidence and scope the next instruction separately.

## 12. W1 authorization used (historical)

“Implement only W1 of #72's Phase 1 plan: an isolated local protocol/state-machine,
framing and deterministic fault harness using temporary test roots and fake native
children. Run local harness checks and report counterexamples/coverage. Do not
modify production code or workflows, elevate, register tasks/services, run installed
SDE/package managers, create package fixtures, dispatch CI/builds, or prepare releases.”

The owner subsequently authorized W1. The linked evidence records what actually
ran; this historical instruction does not authorize W2/W3 or integration.

## Revision-3 follow-up

See [W1 protocol review](APP-UPDATE-NOW-W1-REVIEW.md) for resolved timing, close-grant and query-cache rules. The pinned baseline and recorded W1 results above remain revision-2 evidence. W2/W3, production implementation and build dispatch remain deferred.

Selected revision-3 W1 checks were subsequently authorized and executed: [44-test local record](../../tests/prototypes/manual-update/EVIDENCE.md#revision-3-alignment-execution). This does not clear the native blockers or advance to W2/W3.


## Separately authorized W2a execution

The [W2a record](../../tests/prototypes/manual-update-w2a/README.md) documents five
passing unprivileged Linux lock checks, 49 barrier events, unchanged lock-file
identities, actor exit and temporary-root removal. This is only the E20/B06
cross-process O/A/S subset on the recorded Debian/Linux/tmpfs environment. It does
not clear B06, replace W1 evidence, validate Mint/Windows desktops or authorize any
remaining W2/W3 work. No elevation, registration, production implementation,
package operation, workflow/build dispatch or release work occurred.


## Separately authorized W2b execution

The [W2b record](../../tests/prototypes/manual-update-w2b/README.md) records descriptor
exclusion versus explicit inheritance with a surviving sentinel, stable process
ownership, unchanged lock identities and cleanup. Both Linux cases pass; four
focused mocked safety checks also pass. A development preflight Blocked result
is preserved. This is a narrow process/descriptor subset relevant to B03/B06,
not journal, real-installer, privileged-service or desktop proof. All six blockers
remain open and all other W2/W3, elevation, registration, production implementation,
package operations and workflow/build/release work remain deferred.


## Separately authorized W2c execution

The [W2c record](../../tests/prototypes/manual-update-w2c/README.md) documents healthy
admission, rejection on unresolved intent after supervisor loss while a sentinel
survives with released O/A/S, and continued rejection after sentinel exit. The
single native schedule passes; five focused fixture checks also pass. Fixture
publication calls, inode/content preservation, process ownership, decisions,
exits and teardown are recorded. This is only a Linux test-surrogate subset of
E18/B05/B06, not production startup/recovery or power-loss durability. All six
blockers and all other W2/W3, elevation, registration, production implementation,
package operations and workflow/build/release deferrals remain unchanged.
