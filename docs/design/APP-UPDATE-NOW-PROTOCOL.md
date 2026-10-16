# #72: App-only update and close/install protocol

**Status:** review draft, revision 1. No implementation or build authorization.
**Design:** Option A inline Schedule card with Option C preparation progress.
**Issue:** https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/72
**Inspected implementation:** `ff2ff50c768663ef3dd22bd640859102d5978c34`.
All proposed names, schemas and deadlines below are design decisions for review,
not claims about functionality shipped in v1.2.9. No release version is allocated.

## 1. Scope and current implementation

Provide an explicitly requested, administrator-authorized **SDE application-only**
update. Do not run tool maintenance, apply a tool baseline, change pause policy,
enable a schedule, force an application exit/reboot, or launch a GUI as root/SYSTEM.
The existing unattended updater remains operational and shares the same exclusion,
trust, installation, package-identity, postcheck and recovery primitives.

Relevant current source:

| Source | Existing behavior / consequence |
| --- | --- |
| `installer/src/DetailsPages.tsx` | Schedule reads historical status; Refresh does not request discovery or installation. |
| `installer/src-tauri/src/main.rs` | GUI acquires a session lease before webview startup; current Busy flag blocks window close during operations. Manual preparation/commit need distinct close behavior. |
| `installer/src-tauri/src/process.rs` | Elevation runs the application executable. Do not keep this executable running as the supervisor replacing its own installation. |
| `coordination/src/lib.rs`, `windows.rs` | Lifetime shared sessions; exclusive operations; installation acquires operations then exclusive sessions. Session acquisition currently does not implement admission or an interrupted-install startup check. |
| `updater/src/staging.rs`, `discovery.rs` | Official stable selection and protected authenticated staging can be shared. |
| `updater/src/windows_install.rs`, `linux_install.rs` | Maintenance runs tools first. Private installation routines acquire their own leases; refactor their boundary without bypassing their validations. |
| `windows/self-update/Bootstrap-SkyviewSelfUpdate.ps1`, `linux/self-update/bootstrap.py` | External engine generations and protected snapshots exist. Linux's schema-1 launcher is installed once; replacing bundled code does not automatically migrate that launcher. |

## 2. Safety invariants

1. A GUI request grants neither administrative privilege nor arbitrary execution.
2. Only fixed official release selection and pinned authentication determine the
   install candidate. A discovery result alone is not trusted installation input.
3. No native installation starts without explicit CommitInstall, successful
   administrator authorization, valid policy, compatible coordination, exclusive
   installation access and durable installation intent.
4. The supervisor owns preparation and installation outside the installed app
   directory. It does not depend on a webview, removable drive, user CWD, or GUI
   process remaining alive.
5. Every supported new GUI launch passes admission before obtaining a session.
6. Once a committed handoff blocks admission, no new participating GUI can enter
   between the initiating GUI's exit and exclusive-session acquisition.
7. An OS-owned lock is authority for live exclusion. A progress file is not a
   lock. A durable installation journal is authority to stop unsafe retry after
   an uncertain installation, not evidence that an installer is still alive.
8. Losing a process, receiving a timeout, or seeing an old PID never proves that
   native package children ended. Never kill them or clear unknown intent to retry.
9. Checked, prepared, committed, installed and successfully postchecked are
   different outcomes. Reports must never conflate them.
10. App updates preserve applied baseline, tools, project/editor data, schedule
    and pause policy. Administrator pause is respected with no one-time override.

## 3. Components and protected storage

- **GUI/native bridge:** unelevated; owns advisory discovery, a single authenticated
  channel, UI progress and graceful-close initiation. Raw IPC capabilities stay in
  native memory, not browser storage or JavaScript-readable receipts.
- **Elevated bootstrap:** fixed installed administrative entry point, validated
  ownership/ACL/path/package association; starts a trusted external engine snapshot.
  It must not reuse the long-running `skyview-dev-setup --privileged` GUI helper.
- **Supervisor:** a bounded one-shot process from that snapshot. It holds leases,
  handles requests, stages, supervises native installation and writes receipts.
  It remains alive independently after the GUI exits. No always-running service.
- **Coordination:** existing protected coordination root; add an admission gate
  and capability receipt. Preserve existing session/operation gate objects.
- **Manual-update state:** separate protected subtree under the existing self-update
  root, not user profiles or the application installation. Private transaction
  records/staging/logs are administrator-only; a bounded, sanitized public status
  projection is administrator-writable and ordinary-user-readable.

Only the privileged host creates transaction UUIDs and trusted snapshot paths.
Rendezvous IDs supplied before elevation are strictly validated hints, not authority
to choose a path, user, executable, release or action. No request grants file access
outside fixed validated roots. Reject symlinks, reparse points, hard links, unsafe
ancestors and untrusted ownership/ACLs using the existing platform contracts.

A supervisor snapshots its complete required generation before it can commit.
It verifies snapshot provenance and protocol capabilities. Updating the installed
app or active engine cannot redirect the running transaction to new mutable code.

## 4. States, deadlines and user consent

| State | Owner / UI | Allowed next transition |
| --- | --- | --- |
| Checking | Unelevated advisory check; real check time | Current, Available, Unavailable |
| Available | Installed/candidate versions, official notes, Update now | Authorization |
| Authorization | OS UAC/polkit, no credentials inside SDE | Preparing or canceled/denied |
| Preparing | Privileged supervisor; Downloading then Verifying | Ready, Failed, Canceled |
| Ready | Target/digest fixed; Close SDE & install, Later | CommitAccepted or Canceled/Expired |
| CommitAccepted | Admission closed; Closing SDE / waiting for other windows | Installing or Deferred/Paused/Failed before native launch |
| Installing | Durable intent and exclusive installation ownership | Postchecking or RecoveryRequired |
| Postchecking | App/resources/engine and native outcome checks | Updated, RebootRequired, RecoveryRequired |

Proposed initial bounds (internal policy constants, not webview parameters):

- Administrator authorization: governed by OS cancellation; do not hold operation
  or admission locks while awaiting the credential prompt.
- Channel setup after successful bootstrap: 30 seconds; otherwise shut down safely.
- Network preparation: retain existing bounded download/retry/size policy. Do not
  invent a new unbounded wait or report false percentage while waiting on a retry.
- Ready: five minutes from readiness on a monotonic clock; show remaining time and
  explanation, then cancel immediate intent. Repeated requests do not extend it.
- CommitAccepted: 30 seconds to drain existing sessions. New starts are blocked;
  other windows are not killed. On timeout record Deferred and release pre-install
  locks; do not launch an installer or preserve a fake installation journal.
- Native installation: no kill deadline. Indeterminate progress, durable journal
  and existing recovery rules apply until a trustworthy outcome is established.

Ordinary close, Later, CancelPreparation or channel loss **before commit** cancels
preparation/immediate intent. Cache may be removed by safe existing cleanup; any
reuse requires a new request, authorization and revalidation.

CommitInstall is the explicit installation authorization boundary. Once accepted,
channel loss or GUI crash is not cancellation. The supervisor may proceed after
all session leases actually drain. It aborts before launch if the drain deadline
or a final policy/identity/eligibility/package check fails. The GUI closes only
after a matching authenticated acknowledgement; no acknowledgement means it stays
open and shows uncertain handoff status until reconciled or timed out.

The server processes CommitInstall and CancelPreparation in one serialized state
machine. Whichever valid transition is accepted first wins. After commit, Cancel
returns TooLate; it never kills package processes. A normal GUI close must never
be interpreted as CommitInstall.

## 5. Lock objects, order and ownership

| Gate | Who holds it | Lifetime |
| --- | --- | --- |
| Admission A (new) | Shared briefly by GUI startup; exclusive by committed updater | GUI startup-to-session acquisition, or committed handoff through postchecks |
| Operations O (existing) | Exclusive privileged operation/scheduled maintenance/manual supervisor | Full operation; manual supervisor holds it through protected preparation, Ready and installation |
| Sessions S (existing) | Shared by each running GUI; exclusive installer | GUI lifetime or exclusive native installation/postchecks |

All gate objects are fixed protected zero-length files, administrator-created,
non-replaceable by standard users. Unix uses read-only file descriptors and flock;
Windows uses the validated handle/share-mode design already in coordination.
Lock authority is handle-owned and non-inheritable by unrelated children. Standard
users' ability to hold read leases grants no privileged command authority; hostile
same-machine clients can cause deferral, not unsafe replacement.

### GUI startup

1. Validate coordination root, gate objects and supported capabilities.
2. Try A shared, nonblocking. If busy, show a small accessible native update-in-
   progress notice; do not construct the main webview or acquire S.
3. While holding A, check for trusted unresolved installation intent. An unresolved
   journal yields a native recovery notice instead of a normal GUI session. The
   GUI does not edit private journals or adjudicate package health.
4. Acquire S shared, nonblocking. **Recheck trusted unresolved installation intent
   after S acquisition**, while still holding A. This second check covers an old
   scheduled worker that respects O/S but not A: it could create intent and crash
   between the first check and this session acquisition. On detection, release S/A
   and show recovery guidance. While S is held, conforming installers cannot create
   new installation intent. Then release A and retain S for the GUI lifetime. Never
   hold A while requesting O or running a privileged child.

### Preparation

1. Complete elevation and authenticated channel setup, then try O exclusive.
2. If O is busy/interrupted/untrusted, report the specific safe state; do not wait
   while holding other gates or interrupt another operation.
3. Hold O during protected staging and Ready. This intentionally blocks conflicting
   provisioning and scheduled maintenance temporarily, but navigation remains
   available. The card explains this. Active work is not terminated to begin prep.
4. Do not take A exclusive during download/Ready. Checking/preparation must not
   prevent ordinary GUI launches or hold the session-exclusive gate.

This initial design chooses a short operation reservation over a second pinning/
staging-retention protocol. If that restriction proves unacceptable in UAT, a later
revision may introduce independently pinned preparation, with its own concurrency
and cleanup proof. Do not silently change lease scope during implementation.

### Commit and installation

Canonical updater order is **O exclusive → A exclusive → S exclusive**.

1. The owner of O validates the authenticated CommitInstall against its Ready
   transaction and target digest; rechecks pause, eligibility and current identity.
2. Try A exclusive. A racing GUI either completes its A-shared-to-S-shared entry
   first and becomes an existing session, or fails admission after A closes.
   Do not wait indefinitely for A or acknowledge commitment without owning it.
3. Publish CommitAccepted progress, keep A held, send acknowledgement, and begin
   bounded session draining. The initiating GUI disables new operations and requests
   its normal close. The Busy mechanism must distinguish closing for this handoff
   from an active provisioning operation that correctly prevents close.
4. Obtain S exclusive without releasing O/A. Retry only this nonblocking acquisition
   within the session-drain bound; never upgrade the GUI's own shared S in place.
5. Repeat installed identity, pause, eligible-release, authenticated staging and
   package-health checks. If the candidate changed since the user reviewed it,
   do not substitute a different version silently; end this request and recheck.
6. Create/flush durable installation intent and the detailed private installation
   receipt **before** spawning the native installer. Both must be durable before
   any process that can mutate the installed app starts.
7. Invoke the existing native installation/postcheck path with the owned lease
   bundle. Refactor its boundary so it does not reacquire O/S. Only a typed,
   validated installation lease bundle permits native mutation.
8. Keep O/A/S through installer completion, resource/engine verification and final
   receipt persistence. Clear the installation journal only under existing proven-
   completion rules, then release S/A/O. Reopening is a user action, unelevated.

New scheduled installation follows the same O→A→S order, using nonblocking
acquisition and deferral rather than waiting for GUIs. Legacy supported scheduled
clients use O→S; they cannot overlap a manual transaction that owns O. They do not
participate in the new manual handshake or inherit its authority.

No participant that owns S shared may wait for O or A exclusive. GUI operation
requests remain nonblocking, with no lock upgrade. These rules avoid the cycle
GUI(A/S waits O) ↔ updater(O waits A/S).

## 6. Authenticated IPC: protocol and platform profile

Use a local duplex connection owned by the native bridge, not webview stdout,
removable/user-writable request files, arbitrary ports, or a public control receipt.
It is one connection for one authorization attempt. The final supervisor creates
the endpoint after snapshot startup; do not authenticate a bootstrap then transfer
the connected endpoint to a different process identity. No automatic reconnection or
replay after disconnect; a new attempt uses a new rendezvous and authorization.

### Common handshake and message rules

- Protocol major/minor negotiation; unknown major or required capability rejects
  the operation before staging/closing. Both sides declare their supported phase.
- The privileged side verifies the connecting GUI using OS peer identity and a
  process-instance identity (kernel PID plus creation identity/retained process
  handle, not PID alone), expected desktop user/session, and the trusted installed
  executable. Rendezvous arguments alone do not authenticate any of these.
- The GUI authenticates the privileged endpoint before trusting status or closing.
  The supervisor also authenticates the GUI; a UUID/nonce is not a substitute for
  OS peer authentication. Reject remote and cross-session connection attempts.
- Bind the channel to a supervisor-issued transaction UUID, process-instance
  identities, a fresh 256-bit challenge/capability and the reviewed candidate
  version/manifest digest. Capability is scoped to this one live connection and
  remains in native memory; never put it in command-line arguments, logs, public
  status, environment variables or JavaScript/localStorage.
- Length-prefixed UTF-8 JSON, maximum 16 KiB per message; strict tagged types,
  bounded strings and integers, unknown fields rejected. Logs/notes are not raw
  control messages; sanitize public text and use official validated links only.
- Monotonic sequence numbers and command IDs; every state-changing response names
  the transaction, accepted command, authoritative state and sequence. Repeated
  command IDs return the same result; conflicting reuse is rejected.
- Client commands: Hello, PrepareLatestStable, CancelPreparation, CommitInstall,
  GetStatus. Server messages: HelloAccepted, Progress, Ready, CommitAccepted,
  Rejected, Terminal. No ResumePolicy, arbitrary Run, installer path or download URL.
- CommitInstall includes the Ready transaction/version/digest and last known state
  sequence; stale/foreign commitments fail. Public status never authorizes control.
- CommitAccepted is sent only after admission is locked and protected progress
  published. A lost response is resolved by an idempotent retry on the same live
  channel; retry does not extend deadlines. After commit, the supervisor no longer
  depends on the connection or invoking GUI for continued execution.

### Windows proposed profile

The fixed privileged bootstrap starts the final snapshot supervisor. That
supervisor creates a local-only, single-instance named pipe with a fresh validated
rendezvous ID; it owns the authenticated endpoint for the whole connection. Use FILE_FLAG_FIRST_PIPE_INSTANCE and reject
remote clients. Endpoint owner is SYSTEM or Builtin Administrators; use an explicit
protected DACL. Grant the original desktop client only the precise connect/read/
write/read-control rights needed, **not** generic write rights that also grant
FILE_CREATE_PIPE_INSTANCE, nor WRITE_DAC/WRITE_OWNER. No user-created fallback pipe.

Derive the expected original client's SID, logon/session ID and process instance
from validated kernel process identity, not the elevated alternate administrator's
profile or caller-supplied SID. Authenticate the pipe client using impersonation/
token inspection and GetNamedPipeClientProcessId, then revert impersonation before
privileged work. Validate the client executable and retained process identity.
The native bridge checks the pipe object's owner/DACL and server process identity
using the kernel pipe APIs; failure to query/validate is a denial, not an allowance.

**Phase-1 proof requirement:** validate this rights/identity exchange with a
standard student user, same-user UAC elevation and alternate-administrator UAC.
If the required native queries cannot be made under the intended DACL, revise the
Windows IPC design and review it before implementation continues; do not weaken
server authentication or rely on a public nonce. A squatted endpoint must cause
bootstrap failure while SDE stays open, never a connection to the squatter.

### Linux proposed profile

Use a root-owned Unix-domain socket beneath a fixed protected `/run` directory.
Only root can create/remove the per-request directory/socket name; grant connect
rights to the initiating desktop UID via a narrow ACL. No socket under `/tmp`, the
user's home or removable media. The client verifies root-owned protected ancestors,
socket metadata and SO_PEERCRED identifying the server as root. The server checks
SO_PEERCRED against the expected GUI UID/PID and process creation identity and
validates the installed executable. Reject foreign peers/namespaces and PID reuse.

Polkit authenticates the fixed bootstrap action; it does not authorize arbitrary
paths or commands. Use OS peer credentials as the authority for the original GUI
user, not HOME/USER or an unverified PKEXEC_UID-style environment variable. The
root supervisor must survive closing the GUI and terminal; prove one-shot process
lifetime/reaping on Mint without requiring the weekly service or a permanent daemon.

The challenge is correlation, not home-grown cryptography. Use maintained OS/crypto
primitives; no new signing keys, custom signatures or network authentication scheme.

## 7. Status, cancellation and crash boundaries

Public manual status contains schema/protocol, transaction ID, source=manual,
phase/outcome, public app versions, real bytes/total when known, event sequence,
check/ready/completion times, safe action and validated relative log reference.
Never expose credentials, capability, private staging paths, full process tokens,
student data or raw native logs. Private records additionally bind candidate
manifest digest, snapshot generation, command history, native intent and recovery.

Write receipts atomically with platform-appropriate durability. Readers validate
ownership/path/schema/bounds; malformed or stale data is Unavailable, never Updated.
A last automatic attempt remains separate. Progress events are truthful but are
not proof of lock ownership; native receipts/postchecks decide installation success.

| Boundary / event | Required behavior |
| --- | --- |
| GUI/connection lost before commit | Cancel preparation, confirm no native intent was created, clean only owned safe staging and release O. No automatic install on GUI exit. |
| Ready expires or Later wins | Same pre-install cancellation. No permanent denial of startup from a retained progress record. |
| Commit accepted but acknowledgement lost | O/A remain held; no silent cancellation. Idempotent same-channel query/retry. If GUI stays alive, session-drain deadline eventually defers safely. |
| GUI crashes after explicit accepted commit | Its S lease releases. Supervisor may install once all sessions drain; prior commit remains consent. |
| Supervisor dies before durable installation intent | OS-owned locks release. No native mutation is allowed to have started. New startup may show canceled/failed preparation but does not block solely on stale progress. |
| Durable intent exists, no proven completion | Block normal startup/retry with recovery guidance. Distinguish live Busy from interrupted intent; no unconditional age-based cleanup. |
| Supervisor dies while native child continues | Journal survives even if locks release. Do not launch main GUI or another updater, kill the child, clear intent, or infer completion from parent death. |
| Proven completion plus failed postcheck | Retain required recovery evidence; never label Updated or automatically retry the same transaction. |
| Pause or candidate changes before native launch | Stop without installation and record Paused/StaleCandidate. No policy override or unreviewed version substitution. |
| Pause changes after native launch | Allow native installer to finish; preserve the new pause policy for subsequent work. |
| Native result indicates reboot | Report RebootRequired distinctly; never force reboot or pretend ordinary postcheck success. |

Before clearing interrupted intent, a privileged recovery path must establish
package/installer child quiescence, inspect installed resources/identity and native
package health, and reconcile the durable transaction. PID absence alone is
insufficient. This draft deliberately does not invent automatic recovery where the
existing mentor contract requires assessment.

A normal launch during live admission closure uses a small accessible native
notice, without entering the main application. An unresolved-install recovery
notice likewise does not create a full GUI session. No polling loop repeatedly
restarts the main GUI or steals focus. The user explicitly reopens after success.

## 8. Compatibility and packaging migration

Use an explicit protected capability receipt (proposed schema 1 with
coordinationProtocol=2, admissionGate=1, manualUpdateProtocol=1 and engine/build
association). Version numbers alone do not prove capabilities. Exact schema and
signed-engine association require Phase-1 review.

- App packaging/bootstrap installs the new gate, bootstrap, IPC policy and engine
  capability atomically in the sense of **complete files then final activation
  receipt**. It never claims the whole multi-file change is one atomic write.
- Do not rename, replace, truncate, chmod broadly or delete existing gate files.
  Keep their object identity so existing leases continue excluding work.
- Initialize admission with the same protected ownership/ACL rules as other gates;
  standard users can take read leases but cannot replace or write the object.
- Do not create/delete admission during each request. Publish capability readiness
  last, only after all required paths, policies and permissions are validated.
- A partial/mismatched migration disables manual Update now with mentor guidance.
  Do not silently fall back to admission-free startup if a committed handoff might
  exist. A feature-capable GUI may expose read-only status only when package and
  coordination safety can be established; otherwise use the native recovery notice.
  Existing automatic maintenance remains usable only where its original contracts
  still validate. Never claim handoff protection without the admission capability.
- Preserve existing transaction schema/recovery compatibility and leave unknown
  or active journals intact. Migration during uncertain package work is rejected.
- Respect the Linux fixed schema-1 launcher: prefer a separate versioned manual
  bootstrap rather than assuming package replacement upgrades that launcher.
  On Windows also install a dedicated fixed protected manual bootstrap, preserving
  task principal/triggers/action and existing engine-generation rules.
- Do not change applied-baseline scripts just to add this app feature. Existing
  incompatible pre-coordination maintenance still requires the established mentor
  migration; never treat app-only update as permission to apply a baseline Repair.
- Feature-capable installed GUI entry points participate in admission. The initial
  feature release itself reaches older installations through their existing signed
  automatic/manual app-install path, not through a button they do not yet have.
- A legacy copied GUI or nonparticipating client may still obtain an old shared S
  lease and delay a handoff. Existing S exclusion remains mandatory: defer safely,
  never force installation or claim admission controls unsupported legacy binaries.
  New supported launches from the current installation must be fully protected.
- Old scheduled workers that respect O/S remain serialized by O. No capability
  upgrade permits abandoning those gates or ignoring their package children.

No version/tag allocation, installer rebuild, signing, policy resume, schedule
change or fleet deployment follows from accepting this specification.

## 9. Fault and acceptance matrix

Every row needs automated state/coordination coverage. Platform-sensitive rows
also require actual Windows and Mint process/ACL/socket/installer evidence. Fake
IPC/browser simulations are labeled separately; desktop and screen-reader UAT
remain explicit acceptance work, not inferred from container/Server CI.

| ID | Injection / scenario | Required invariant and visible result |
| --- | --- | --- |
| F01 | Current/offline/malformed release response | Correct Current versus Unavailable; no elevation or mutation. |
| F02 | Draft/prerelease/older/platform-incompatible candidate | Never offered for install; no string-order comparison error. |
| F03 | Paused before prepare, during Ready, before launch | No install or implicit resume; clear pause explanation. |
| F04 | UAC/polkit denied or canceled | GUI stays open; no protected staging/commit left active. |
| F05 | Same-user versus alternate-admin elevation | Correct original GUI peer binding; no root/admin profile substitution or GUI relaunch. |
| F06 | Wrong UID/SID/session, PID reuse, foreign executable | Reject channel/command without changing policy or package state. |
| F07 | Pipe/socket squatting or linked directory/receipt | Fail closed; GUI never accepts spoofed supervisor status or close instruction. |
| F08 | Oversized/unknown/version-mismatched/truncated IPC | Bounded rejection and safe cleanup; no parser-controlled paths or execution. |
| F09 | Replayed capability, reused conflicting command ID, stale Commit | Reject; exactly one state transition/native launch. |
| F10 | Signature/hash/size/package-identity mismatch | No Ready or install; GUI remains usable with accurate failure. |
| F11 | Candidate becomes ineligible, changes version, or installed version advances | Revalidate; no downgrade or silent replacement of reviewed target. |
| F12 | Existing Validate/provisioning/maintenance owns O | Preparation reports Busy without interruption; no new conflicting work. |
| F13 | Preparation owns O; another GUI starts provisioning | Other operation defers; navigation/focus/log history preserved. |
| F14 | Two manual requests or manual/scheduled race | One owner; other request reports Busy. No duplicate staging/install. |
| F15 | Later, ready timeout, ordinary close before commit | No installer; O released; stale progress cannot deny startup. |
| F16 | Cancel versus Commit concurrently | Server serialization decides one winner; no ambiguous cancel after native launch. |
| F17 | Reopen before A closes | Entrant becomes existing S holder; wait/drain or bounded defer. No unsafe install. |
| F18 | Reopen after A closes, before ACK, after ACK, during GUI exit | New supported main GUI never starts or obtains S; update notice; no cancellation. |
| F19 | Reopen while acquiring S, installing, postchecking, releasing | Continuous exclusion until durable terminal state; no replacement race. |
| F20 | Other GUI stays open; initiating window refuses close | Bounded Deferred, no force-close; release pre-install reservation safely. |
| F21 | Commit acknowledgement lost / duplicate commit | GUI closes only on authenticated matching ACK; idempotent replay; no deadline extension. |
| F22 | GUI crash before versus after accepted commit | Before: cancel. After: independent supervisor can proceed only after session drain. |
| F23 | Supervisor killed at every state before durable intent | No installer ever started; OS leases release; normal startup not permanently denied. |
| F24 | Power loss or helper killed between durable intent and spawn | Conservative interrupted recovery; no automatic journal deletion or retry. |
| F25 | Helper dies with native children still running | Retained journal prevents normal startup/retry despite released OS locks. |
| F26 | Native nonzero/unknown completion/postcheck failure | Preserve evidence/recovery; never report Updated or fabricate rollback. |
| F27 | Native success / reboot-indicated outcome | Verify resources/version/engine; distinguish Updated from RebootRequired. |
| F28 | Legacy S holder or old scheduled O/S worker, including intent written between startup checks | Safe deferral/exclusion; post-S journal recheck prevents normal startup after an old worker crashes; no false claim of legacy admission support. |
| F29 | Missing gate, partial capability migration, wrong permissions, active journal | Manual feature unavailable; existing data/locks/policy untouched. |
| F30 | App-only install with no tool schedule | Works when trusted app bootstrap/capabilities exist; no tool provisioning/schedule creation. |
| F31 | Full manual upgrade | Tools, baseline, schedule, pause and project/editor data preserved; real version/engine and receipts agree. |
| F32 | Stale/unknown/tampered public status or disconnect | No false success/close authority; safe status unavailable; authoritative journal respected. |
| F33 | Light/dark/high contrast, all zooms, minimum window, keyboard/reader | Stable targets/focus, real accessible progress, no byte-by-byte speech spam or clipping. |
| F34 | Reboot after completion versus uncertain installation | Completed receipt remains usable; uncertain state retains recovery restriction; no stale Ready grant. |
| F35 | USB/terminal/GUI removed after accepted handoff | Installed snapshot and supervisor continue independently; no dependency on original launcher files. |

Cross-process tests must place barriers at each acquisition/release/receipt/spawn
boundary and deliberately schedule both race orderings. Do not use successful
sleep-based demonstrations as proof of race freedom. Native acceptance must cover
standard desktop accounts and genuine privilege transitions on both platforms.

## 10. Review and implementation gates

1. Review invariants, lock order, Windows pipe authentication feasibility, original-
   user identity binding, Linux supervisor lifetime and migration compatibility.
   Resolve these before implementing the UI or claiming the protocol is proven.
2. Once separately authorized, implement and fault-test coordination/IPC primitives
   first; review them before exposing an installation command to the webview.
3. Implement app-only orchestration and refactor native installation to consume
   owned leases, retaining existing authentication/postcheck/recovery checks.
4. Add the inline accessible progress card, distinct manual receipts and close
   acknowledgement behavior; run full regression and native process/privilege QA.
5. Only with later authorization prepare a fresh immutable test candidate, perform
   desktop UAT, and separately decide release/promotion/rollout.

Open review decisions: confirm the five-minute Ready / thirty-second drain bounds;
prove Windows rights for both UAC account modes; choose the concrete bounded IPC
framing library; confirm platform durability and restricted-startup recovery UX.
These are review/implementation gates, not permission to relax the invariants.
