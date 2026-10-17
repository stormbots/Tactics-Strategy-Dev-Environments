# #72: App-only update and close/install protocol

**Status:** review draft, revision 4 (B02 proposal based on W2h). Not implementation-ready; blockers B01–B06 remain. No implementation or build authorization.
**Design:** Option A inline Schedule card with Option C preparation progress.
**Issue:** https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/72
**Inspected implementation:** `ff2ff50c768663ef3dd22bd640859102d5978c34`.
This revision reviews the proposed protocol, not alleged defects in shipped v1.2.9.
Revision 4 is documentation-only; its Linux record adapter and next validation
gate are proposed and unexecuted. No application version changes.
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
3. No **manual** native installation starts without explicit CommitInstall and
   transaction-scoped administrator authorization. Both manual and scheduled
   installation require valid policy, compatible coordination, exclusive access
   and durable intent. Existing scheduled authorization does not require a GUI
   CommitInstall and is not disabled by this feature.
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
  Windows: UAC authorizes a fixed broker which starts the final snapshot worker as
  SYSTEM; administrator elevation alone is not SYSTEM identity. Linux: polkit
  starts the final root supervisor without a Windows-style identity hop.
- **Supervisor:** a one-shot process from that snapshot with bounded pre-install
  lifetime, but no forced native-installer termination deadline. It holds leases,
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

Local administrators/root and a compromised kernel are outside this privilege
boundary; they already control the installation. Same-user malware or a compromised
webview cannot be distinguished from that user's intent by a nonce or process path.
Security comes from explicit OS authorization of a fixed narrow action, authenticated
transport, strict command scope and signed packages, not from claiming that IPC
proves a physical button click. Bound resource use and tolerate denial of service
without privilege escalation. A process path/PID alone is never peer authentication.

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
- Before commit, complete each IPC frame within five seconds; a connect/Hello/Prepare
  exchange has a fixed 30-second overall bound. Acquire O only for an accepted
  Prepare request, not merely because a client connected. Limit control frames to
  ten per second, queue at most 32 controls and coalesce progress to one replaceable
  snapshot. A slow, flooding or silent client cannot keep O/A alive indefinitely.
- Network preparation: retain existing bounded download/retry/size policy. Do not
  invent a new unbounded wait or report false percentage while waiting on a retry.
- Ready: five minutes from readiness; show remaining time and explanation, then
  cancel immediate intent. Use a boot/incarnation-bound suspend-aware monotonic
  deadline where available; on resume or uncertain sleep/clock continuity, invalidate
  pre-install readiness. Ordinary suspend-excluding elapsed time alone cannot keep
  an administrative grant alive through an overnight sleep. Repeated requests,
  progress polls and reconnect attempts never extend the grant.
- CommitAccepted: 30 seconds to drain existing sessions. New starts are blocked;
  other windows are not killed. On timeout record Deferred and release pre-install
  locks; do not launch an installer or preserve a fake installation journal.
- Before admission closes: complete network eligibility refresh and expensive
  package/authentication checks while the GUI can explain progress. Eligibility must be at most ten seconds old when A is acquired and commit is
  accepted (inclusive boundary). If acquiring A crosses that limit, release A and
  refresh while the GUI remains open before accepting commit.
  If the selected version/digest changes, require a new reviewed preparation.
- Native installation: no kill deadline. Indeterminate progress, durable journal
  and existing recovery rules apply until a trustworthy outcome is established.

Ordinary close, Later, CancelPreparation or channel loss **before commit** cancels
preparation/immediate intent. Cache may be removed by safe existing cleanup; any
reuse requires a new request, authorization and revalidation.

CommitInstall is the explicit installation authorization boundary. Once accepted,
channel loss or GUI crash is not cancellation. The supervisor may proceed after
all session leases actually drain. It aborts before launch if the drain deadline
or a final policy/identity/eligibility/package check fails. The GUI closes only
after a matching authenticated, currently valid close grant as defined in section 6;
no valid close grant means it stays
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
3. Start the non-renewable drain deadline at the instant A closes. Publish
   CommitAccepted progress, keep A held, and enqueue acknowledgement without
   waiting for a client to read it. Receipt or socket writes cannot suspend the
   deadline indefinitely. Begin bounded session draining. The initiating GUI disables new operations and requests
   its normal close only after validating the close grant in section 6. The Busy mechanism must distinguish closing for this handoff
   from an active provisioning operation that correctly prevents close.
4. Obtain S exclusive without releasing O/A. Retry only this nonblocking acquisition
   within the session-drain bound; never upgrade the GUI's own shared S in place.
5. Repeat bounded local installed-identity, pause, staged-integrity and package-
   health checks. Admission closure starts a non-renewable 45-second deadline
   through the final pre-spawn decision, inclusive of session drain, checks and
   durable intent/receipt work. The drain must finish strictly before 30 seconds;
   the final launch decision must occur strictly before 45 seconds. No
   network fetch, credential prompt or unbounded package-manager wait is permitted
   here. Bind the eligibility snapshot to this attempt, Ready epoch and exact
   candidate. Its ten-second age limit applies at commit acceptance, not again
   after draining. This bounded continuation permits evidence age strictly below
   55 seconds at the final launch decision; it is not a renewable grant. A remote release may change
   immediately after the last check: record that check and do not promise an atomic
   GitHub-to-native-launch transaction. Never silently substitute another candidate.
6. Create/flush durable installation intent and the detailed private installation
   receipt **before** spawning the native installer. Both must be durable before
   any process that can mutate the installed app starts. Once intent is created,
   missing the launch-decision deadline must not clear that intent on a timer. Record a
   conservative recovery outcome if pre-spawn completion is uncertain.
   Perform the final pause read after durable intent/receipt work, immediately
   before spawn; then check the monotonic launch deadline, with no intervening
   network, credential prompt or blocking IPC. Expiry prohibits spawn. Finalize
   only if no launch is proven; otherwise retain recovery intent. This bounds the
   local decision, not OS scheduling or the duration of the spawn syscall.
   If paused, finalize this proven-not-launched transaction safely and do not spawn.
   A pause arriving after that final read can race the OS spawn; it is preserved
   but cannot be promised to preempt this launch. This matches the existing
   pause/launch contract; tests must cover both race orderings.
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

GUI/backend clients that own S shared may only **try** O nonblocking; they may
not wait for O or A exclusive. Existing shell/Python/PowerShell coordination
wrappers also take session/operation leases: include them in the ordering audit.
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

### Revision-4 review scope and W2h finding

Revision 4 changes only the B02 design and its validation gate. It is a proposed
specification, not a validated adapter, shipping feature or authorization to run
an experiment. The existing revision-3 transaction, timing, lock, journal and
close-grant rules remain in force. W1 results remain selected revision-3 model
evidence; they do not become revision-4 transport conformance evidence.

The [reviewed W2h diagnostic](../../tests/prototypes/manual-update-w2h/README.md)
shows a distinct holder writing through an explicitly inherited connected socket
while the original client remains alive. SO_PEERCRED still names the original
client and its retained pidfd remains live; the tested guard permits the holder's
request. Diagnostic success is CounterexampleDetected, not authentication safety.
The diagnostic omits the full production handshake/capability/authorization chain.
It disproves sufficiency of connection credentials plus liveness for the tested
sender requirement, not the full protocol or a released SDE implementation.

### Threat boundary and meaning of sender identity

| Actor / ability | Proposed boundary |
| --- | --- |
| Independent unprivileged process, including the same desktop UID | In scope: endpoint spoofing, replay, hostile records, and possession of a connected descriptor without execution inside the enrolled native bridge. Descriptor possession must not confer the enrolled process's sender identity. |
| Enrolled native bridge and protected supervisor | Trusted to execute their intended code. They own their IPC descriptors and private native-memory capability. Their identity and enrollment must originate in authenticated OS/privileged bootstrap context. |
| Same-UID memory reading, ptrace/code injection, or arbitrary execution inside an enrolled actor | A UID is not an isolation boundary. Protection against these abilities is not established by this IPC design. Either prove the required OS isolation or explicitly retain uncompromised native actors as the threat assumption. Do not advertise general same-user-malware resistance. |
| Compromised webview | Untrusted requests are constrained by the fixed native API and independent administrator authorization. IPC does not prove that an allowed request reflects a physical click. Native-memory secrets must remain inaccessible to JavaScript. |
| Malicious root/administrator, compromised kernel, or capabilities permitting credential impersonation in relevant namespaces | Outside this installation privilege boundary. Reject unsupported namespace/credential contexts; tests with zero capabilities cannot certify broader contexts. |

**Proposed requirement:** before treating a received command as authoritative,
the receiver must establish that the kernel attributes the complete command to
the enrolled peer process instance. Before accepting a pre-commit state-changing
request, the original GUI instance must also be live at validation. The GUI must
apply equivalent sender checks before trusting supervisor responses or close
authority. A connection PID, payload PID, descriptor, process path, nonce or
capability alone is insufficient evidence of the submitting process.

Here, sender means the process the kernel attributes to the data submission. It
does not mean the person, JavaScript component or causal origin that induced that
process to send. Initial executable checks and retained process handles do not
prove ongoing code integrity, prevent exec, or make validation and later action
atomic. Known credential/executable/namespace changes invalidate the attempt;
stronger exec-continuity or memory-isolation guarantees remain explicit proof
obligations, not implied properties of pidfds.

Authenticate every accepted command, including Hello and GetStatus, and every
accepted authoritative response. Invalid input must not enter mutation replay
slots, consume a logical action, create Ready, authorize close or trigger an
effect. Bounded transport decoding needed to extract credentials is not authority
to interpret the payload as an accepted command.

Once CommitInstall's effect is accepted, sender/transport loss does not revoke
that effect or make installation depend on GUI survival. Drop the failed channel
and continue the existing authoritative state machine, drain/launch deadlines,
lease and intent rules. Do not clear intent, restart, or cancel a committed native
child because later IPC fails. Before accepted commit, authentication failure
ends the attempt with only proven safe owned staging cleanup.

### Design alternatives and required review decision

| Alternative | Assessment |
| --- | --- |
| Linux record transport plus per-record kernel credentials | Preferred candidate below: a complete command and its sender evidence have one record boundary. Feasibility remains unproven. |
| Retain SOCK_STREAM with SO_PASSCRED/recvmsg | Possible alternative only with a reviewed proof that every byte of a complete envelope is attributed correctly across split/coalesced reads and mixed writers. Checking credentials on one fragment is insufficient. |
| Explicitly delegable channel/capability authority | Different security contract. It may constrain an administrator-authorized fixed action, but cannot promise original-process submission. Requires an explicit threat-model/specification decision; it is not an automatic fallback. |

Retain attempt capability, signed package authentication and OS consent under
all alternatives. Those checks can reject an FD-only holder lacking the secret,
but a transferable secret does not independently establish nondelegable process
identity. W2h does not evaluate the full capability protocol. No alternative is
accepted as production-ready by this draft.

### Common handshake and message rules

- Protocol major/minor negotiation; unknown major or required capability rejects
  the operation before staging/closing. Both sides declare their supported phase.
- The privileged side verifies the connecting GUI using OS peer identity and a
  process-instance identity (kernel PID plus creation identity/retained process
  handle, not PID alone), expected desktop user/session, and the trusted installed
  executable. Retain process identity through preparation. Initial connection
  identity and liveness do not authenticate each writer: require kernel-attributed
  sender evidence for each complete accepted command and recheck the original GUI
  instance at pre-commit state changes. Do not accept a passed descriptor as sender
  authority. Rendezvous arguments alone do not authenticate identity.
- The GUI authenticates the privileged endpoint before trusting status or closing.
  The supervisor also authenticates the GUI; a UUID/nonce is not a substitute for
  OS peer authentication. Reject remote and cross-session connection attempts.
- Bind the authenticated channel first to a supervisor-issued attempt UUID,
  process-instance identities and a fresh 256-bit challenge/capability. After
  preparation, bind a separate immutable Ready epoch to the selected version,
  manifest digest, installed-version expectation and supervisor incarnation.
  A Hello before discovery cannot already authenticate a nonexistent candidate. Capability is scoped to this one live connection and
  remains in native memory; never put it in command-line arguments, logs, public
  status, environment variables or JavaScript/localStorage.
- Envelope: four-byte unsigned network-order JSON byte length followed by exactly
  that many UTF-8 JSON bytes; maximum 16,384 bytes including the four-byte prefix
  (JSON payload at most 16,380 bytes). Reject zero-length JSON, length mismatch,
  unknown fields/tags, duplicate keys, invalid UTF-8, excessive nesting and
  out-of-range values before command execution. The Linux candidate sends exactly
  one envelope per record; this is a required profile change, not a compatible
  stream-only fallback. Windows framing/credential association remains a separate
  proof obligation. Logs/notes are not raw control messages; sanitize public text
  and use official validated links only.
- Keep **event sequence**, immutable **Ready epoch**, mutation **commandId** and
  read-only **queryId** separate. Event sequence orders authoritative state/progress;
  polling does not advance it or invalidate consent. Responses identify the attempt,
  supervisor incarnation, correlation ID, current state and event sequence.
- Client commands: Hello, PrepareLatestStable, CancelPreparation, CommitInstall,
  GetStatus. Server messages: HelloAccepted, Progress, Ready, CommitAccepted,
  Rejected, Terminal. No ResumePolicy, arbitrary Run, installer path or download URL.
- Mutation replay records retain the complete canonical payload and accepted effect
  for each logical action for the entire attempt. Reserve three fixed slots for
  PrepareLatestStable, CommitInstall and CancelPreparation; do not evict accepted
  records. Each action can be accepted at most once. A second commandId for an
  already accepted logical action returns AlreadyAccepted without a new effect or
  slot. Same-ID altered payload is a protocol violation. Invalid/rejected requests
  use bounded transient replies, not permanent replay entries. A new preparation
  after expiry/cancellation requires a new authenticated attempt and authorization.
- GetStatus uses queryId only, never occupies a mutation slot, never authorizes
  closing and never renews any deadline. Keep at most one outstanding status query
  per connection and one coalesced current-status reply, with no query history.
  Repeated queryIds simply read current state. Rate/queue/frame bounds still apply
  before processing queries or retries; floods cannot consume reserved mutation
  capacity. Distinct identifier namespaces prevent query/mutation ID collisions.
- CommitInstall includes Ready epoch, transaction/version/digest and expected
  installed identity, not the last progress event number. A matching retry preserves
  the historical accepted effect, but regenerates the response from current state;
  never replay cached close authority. Public status never authorizes control.
- CommitAccepted distinguishes historical `effectAccepted` from `closeAuthorized`.
  Close authority is true only while the original supervisor owns O/A, this exact
  commit is in session draining, no terminal decision exists and the non-renewable
  drain deadline remains live. Bind it to the original channel/process instance,
  attempt, incarnation, Ready epoch, candidate digest, commandId and current event
  sequence. Expired, Deferred, Canceled, Recovery and completed states always return
  false even when effectAccepted is true. Status and unsolicited progress cannot
  substitute for this correlated control response.
- The native GUI bridge accepts a close grant only for its outstanding commit or
  explicit same-command retry, authenticated live channel and matching bindings.
  Reject responses older than the highest observed event sequence or superseded
  by a terminal event. Validate the absolute drain deadline in the same boot-bound,
  suspend-aware host monotonic clock domain before requesting graceful close; fail
  closed on uncertain mapping, suspend or incarnation change. No wall-clock TTL
  or receipt-relative timeout may extend a delayed grant. Exact platform clock
  mapping remains a B02/B06 native proof obligation; no mapped clock, no close.
- Close authority describes state at response generation and expires at the drain
  deadline. A supervisor can crash between bridge validation and actual GUI exit;
  IPC cannot make those operations atomic. A late detected EOF cancels a pending
  close where possible. Do not claim guaranteed installation or automatic reopening:
  a crash can leave the GUI closed without an update. Native mutation still needs
  O/A/S and durable intent, and uncertain intent still requires recovery.
- Publish protected progress after acquiring A before sending CommitAccepted.
  Lost responses use same-channel retry without another effect or deadline renewal.
  After commit, execution no longer depends on the connection or invoking GUI.
- All IPC reads/writes are bounded/asynchronous relative to the supervisor's state
  machine. Before commit, transport failure cancels safely. After commit, discard
  the channel and continue from authoritative state; a full pipe cannot prevent
  timeout, lock release, native launch, postchecks or terminal receipt persistence.

### Windows proposed profile

The existing worker's `system()` check requires LocalSystem. A UAC-elevated
administrator process must not call that path directly or silently weaken it.

Proposed bridge: after explicit UAC consent, a fixed installed administrator broker
creates a private bounded request and registers/starts a dedicated **one-shot,
on-demand SYSTEM task** for this request. Its executable is the fixed protected
manual bootstrap, with only a strictly validated request UUID; task configuration
contains no GUI-supplied script, path, URL, user or command. It has no recurring
trigger and must not alter/reuse the weekly tool-maintenance task. Do not grant
ordinary users task-run/edit/registration rights. Prove task-folder/definition ACLs,
account-mode behavior and restart policy before accepting this bridge (B01).

The SYSTEM bootstrap validates the administrator-owned request, scope, live original
GUI identity and expiry, then starts the final protected snapshot supervisor. The
supervisor—not an intermediate process—creates and owns the authenticated endpoint.
Only one transaction can claim the request; a scheduler retry must reject a claimed
request even if a previous attempt crashed. Disable automatic task restarts; never
resume a committed/native-uncertain transaction as a new preparation. Cleanup may
remove only this terminal request's task/metadata after the supervisor and all
package children are known finished. Leaving a disabled inert task after failure
is safer than deleting or restarting an uncertain live transaction.

The supervisor creates a local-only, single-instance named pipe with a fresh
validated rendezvous ID. Use FILE_FLAG_FIRST_PIPE_INSTANCE and reject remote
clients. The final endpoint owner/server identity must be SYSTEM, not merely any
administrator process; use an explicit
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
Also prove that an unprivileged GUI cannot impersonate the SYSTEM server with a
restricted token, alternate object owner or extra pipe instance. If the required
native queries cannot be made under the intended DACL, revise the Windows IPC design and review it before implementation continues; do not weaken
server authentication or rely on a public nonce. A squatted endpoint must cause
bootstrap failure while SDE stays open, never a connection to the squatter.

#### Windows requirements still unresolved after W2h

Linux SCM_CREDENTIALS provides no Windows proof. The current named-pipe owner,
DACL, impersonation/token and GetNamedPipeClientProcessId/server-process checks
are proposed connection/enrollment controls. Their ability to identify the writer
of every complete command across inherited/duplicated handles is not established.
Do not infer per-message process identity from their names or a retained live GUI.

B02 Windows remains blocked until a reviewed native mechanism demonstrates:

- Complete-command sender association and both directions of authentication under
  inherited/duplicated handles, token/impersonation changes and partial/message
  boundaries. The default guarantee may not silently become delegable authority.
- Original SID, logon/session and process-instance binding through same-user and
  alternate-administrator UAC without substituting the elevated account or broker
  for the enrolled desktop bridge or final SYSTEM supervisor.
- Necessary query/read/write rights under the exact DACL, impersonation reversion
  before privileged work, denial on failed queries, and no unauthorized creation,
  squatting or replacement of an extra server instance.
- Preservation of native-only capabilities, command/replay bounds, sender failure
  before commit, post-commit independence and the full current close-grant checks.

If an equivalent guarantee is infeasible, propose a separate documented security
contract or transport/broker revision and review it before Windows implementation.
The Linux candidate is neither a Windows solution nor permission to weaken the
common requirement. No Windows experiment or elevation is authorized by revision 4.

### Linux proposed record profile: linux-record-v1

**Status:** review candidate; native semantics and deployment support are not yet
validated. `linux-record-v1` is a symbolic transport-profile name, not an app or
release version. Both endpoints must explicitly support this required profile.
Reject unsupported profile/version before preparation or close. There is no
silent downgrade to the connection-credential/liveness-only guard or a legacy
stream adapter. How installer-carried capabilities advertise support remains B04;
do not extend the signed schema-1 manifest to negotiate it.

Use an AF_UNIX SOCK_SEQPACKET connection at a root-owned pathname beneath the
fixed protected `/run` namespace. Only root creates/removes the per-attempt
namespace and socket; grant the initiating desktop UID narrowly scoped connect
rights. No production endpoint under `/tmp`, home or removable media. Validate
protected ancestors, ownership, ACLs, socket type and run/attempt association;
reject links, squatting, foreign namespaces and replacement. Test-only private
roots do not validate this production namespace policy.

#### Enrollment and first exchange

1. The fixed privileged bootstrap must establish the original GUI's process
   instance, desktop identity/session and relevant namespace context from trusted
   OS evidence. The native bridge must obtain the expected final supervisor
   instance through an authenticated bootstrap handoff. Caller arguments,
   HOME/USER/PKEXEC_UID-style strings, a public status file, or the first packet's
   claimed PID cannot create enrollment. The exact privileged enrollment/handoff
   mechanism remains B02-unproven and needs its own later validation.
2. Retain OS process-instance handles/pidfds and validated creation identities for
   enrolled peers. Define UID/GID policy from trusted kernel credential sets, not
   directory ownership or self-reported credentials. Default SCM_CREDENTIALS uses
   real UID/GID; explicit credentials can use permitted real/effective/saved IDs.
   The supported profile must pin the intended non-transitioning credential sets
   and PID/user namespace interpretation. Thread/PID semantics, namespace changes
   and exec are later proof obligations; a numeric PID alone is never enrollment.
3. Enable SO_PASSCRED before receiving any application data on both endpoints.
   Configure the listener and accepted endpoint as required; verify actual option
   state and accepted-socket behavior instead of assuming inheritance. Prequeued
   data without valid credentials must fail, not acquire authority retroactively.
   All reads use recvmsg with bounded payload/control buffers; ordinary read/recv
   must not discard ancillary evidence on this channel.
4. The first Hello is a bounded credential-bearing record. Verify kernel sender
   identity against pre-established enrollment before accepting negotiation fields.
   Hello carries no installation authority or secret that an unauthenticated peer
   may obtain. After validating the client, the supervisor returns HelloAccepted;
   the bridge validates that record's kernel-attributed sender against the enrolled
   root supervisor before accepting its attempt/incarnation/capability. Discovery
   and Ready candidate binding follow the existing sequence. No circular trust in
   a first packet's self-declared identity is permitted.

SO_PEERCRED remains a connection snapshot and is not per-record authority.
Its availability on the candidate socket type is not assumed. It may be recorded
as additional diagnostic evidence but cannot replace mandatory per-record
credentials or the authenticated enrollment mechanism. A candidate implementation
must not depend on undocumented SOCK_SEQPACKET query behavior.

#### Complete-record validation

One successful sendmsg submits exactly one complete common envelope in one
record. On a short send, fail the channel; do not concatenate later sends into an
apparently authenticated command. On EAGAIN, retain only bounded pending output
and retry the whole unsent record under the existing deadline/queue rules.
Receive one record at a time; never combine fragments/records or credential sets.

For every record, before payload dispatch:

- Require exactly one well-formed SOL_SOCKET/SCM_CREDENTIALS item of the expected
  native ucred size. Require its PID/UID/GID to match the enrolled peer policy;
  check the retained process instance/liveness where required. A live original
  process does not excuse a record attributed to another process. Apply the same
  rule to server replies, including progress and CommitAccepted.
- Reject MSG_TRUNC or MSG_CTRUNC, absent/duplicate/ambiguous credentials, unknown
  ancillary types, unsupported identity/namespace context, zero-length records,
  envelope length mismatch, multiple envelopes in a record, malformed JSON and
  unsupported versions/capabilities. Do not recover by reading a suffix, using a
  previous packet's credentials or trusting a payload identity claim.
- This protocol accepts no SCM_RIGHTS or other descriptor-transfer messages.
  Receive with MSG_CMSG_CLOEXEC where supported so unexpected installed FDs cannot
  leak through exec before rejection. Inventory and close every actually delivered
  descriptor even on rejection/truncation, and close no descriptor named only in
  untrusted payload bytes. Bounded ancillary storage and verified no-leak cleanup
  are adapter proof obligations; unsupported safe handling blocks the adapter.
- Credential success does not authorize an effect. Validate the existing attempt
  capability, phase, immutable Ready binding, candidate/installed identity,
  command/query namespace, replay rules, administrator authorization and policy
  before any accepted state transition. Validate close authority separately in
  the native bridge; public status and progress remain unable to grant close.

The Linux manual documents SO_PASSCRED/SCM_CREDENTIALS and kernel checking of
explicit credentials, including privileges that can permit identity substitution.
This draft is an API candidate, not native proof of those properties on the target
platform. See [unix(7)](https://man7.org/linux/man-pages/man7/unix.7.html).

#### Failure, resource and transaction behavior

Before accepted commit, sender/profile/record-authentication failure invalidates
the attempt: no new Prepare/Commit effect, no close grant and no automatic reconnect.
Retain historical accepted-effect/replay records; terminal failure does not make
an already accepted command repeatable.
Release only proven pre-install reservations and owned safe staging; keep the GUI
open with a bounded explanation. Preserve uncertain intent and recovery rules.
After accepted commit, discard the channel on failure and continue installation
from protected state; never make native work depend on the reader or original GUI.

Record and control buffer sizes, pending output and ancillary-FD inventory are
bounded before parsing. Existing rate limits, one outstanding query, coalesced
progress and mutation reservations remain unchanged. Blocking send/receive or a
full record queue cannot extend Ready/drain/launch deadlines or stall supervision.
The native GUI exposes sanitized progress to the webview, not credentials,
capabilities, raw IPC records or new arbitrary privileged commands.

The [next isolated B02 gate](APP-UPDATE-NOW-B02-RECORD-VALIDATION.md) proposes only
unprivileged primitive validation after specification review and separate execution
authorization. A passing gate would not clear protected enrollment/namespace,
Windows, desktop, capability integration or the remaining B01–B06 obligations.

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
| Pause observed at a required check, or candidate differs at the fresh eligibility check | Stop without installation and record Paused/StaleCandidate. A concurrent pause after the last read is not guaranteed to win the spawn race; preserve it for subsequent attempts. No silent version substitution. |
| Pause changes after native launch | Allow native installer to finish; preserve the new pause policy for subsequent work. |
| Native result indicates reboot | Report RebootRequired distinctly; never force reboot or pretend ordinary postcheck success. |

Before clearing interrupted intent, a privileged recovery path must establish
package/installer child quiescence, inspect installed resources/identity and native
package health, and reconcile the durable transaction. PID absence alone is
insufficient. This draft deliberately does not invent automatic recovery where the
existing mentor contract requires assessment.

Publishing Updated has a strict order: finish native work and postchecks; persist
the detailed complete receipt and final safe status; then clear the compatibility
installation journal, then release S/A/O. Crashes between receipt publication and
journal removal remain conservatively recovery-required; the UI cannot label them
ordinary Updated from the public status alone. Lock/journal state takes precedence.
Durability includes file flush, atomic replacement and parent/namespace persistence
where supported; Windows power-loss guarantees need native proof (B05). Logical deadlines are
not a promise that an uninterruptible kernel/storage operation can always be
terminated on time. Never unlock a transaction with uncertain intent just to
meet a user-facing timeout; report the appropriate recovery state once it can
be safely established.

App-only does not mean zero operating-system dependency changes: APT may resolve
required SDE runtime libraries under the existing no-remove policy. No managed-tool
update/provisioning, distribution upgrade, baseline change or weakened package
authentication is allowed. Record app dependency changes without claiming that
every system package necessarily remains byte-identical.

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
  or active journals intact. Reject an **unrelated/uncertain** installation; do not
  blanket-reject the active journal belonging to the installer's own supervised
  package hook. See the bootstrap exception and proof gate below.
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

### Package-hook and mixed-generation exception (review gate B04)

NSIS postinstall and DEB postinst invoke `--coordination-init` and bootstrap **while
the supervising installer owns the installation locks and journal**. They must not
enter normal GUI startup, acquire A/O/S as a new independent participant, wait on
their own parent, clear its journal, or reset an existing gate. Otherwise the
protocol deadlocks or rejects every legitimate upgrade.

During an authenticated package-hook invocation, additive initialization of the
new admission gate/manual bootstrap and validation of existing objects is allowed
without reacquiring the parent's leases. Existing metadata probes must remain
usable with the Windows sharing modes held by the supervisor. Publish capability
activation only after all required files/policies validate; native postchecks must
verify the same activated generation. Never garbage-collect a live snapshot.

This exception cannot be selected by a plain flag, environment variable, journal
existence or root-owned record alone. It needs a platform-authenticated native
installer/package-hook invocation and binding to the **current live supervising
installation**, not arbitrary ancestor PID strings. The new manual parent can
provide an explicit scoped bootstrap context, but old workers do not provide that
new token. A separate legacy-upgrade verification rule must be specified and proven
for each supported old parent/package hook, or an explicit supported migration
path must be documented. Do not invent a permissive fallback. This remains a
blocking compatibility decision; the draft does not claim the legacy proof exists.

The candidate package must preserve the coordination protocol required by the
running snapshot; publishing it as stable must carry forward that compatibility.
Capability checks in the installed version alone cannot prove the target package
keeps gate identities/schema/ordering. Define required target capability evidence
and validate it under the existing signed-package trust model before manual
installation can be declared supported. A signed package is authentic, but its
signature alone is not a new protocol-capability declaration.

Do not add fields to the current strict schema-1 signed `sde-update.json`: older
fleet verifiers reject unknown fields/schemas. The proposed representation is a
bounded capability declaration **inside the authenticated installer bytes**: DEB
custom control fields and Windows NSIS/PE version-resource fields for coordination
protocol, manual protocol and bootstrap capability. Exact names/parser limits and
NSIS resource feasibility require B04 proof before adoption. Authenticate the full
installer first, then inspect these declarations before commit; after installation,
compare declarations against actual protected files and activated capabilities.
Do not execute an uninstalled target helper to query its capabilities. A missing,
malformed, incompatible or uninspectable declaration is UnsupportedTarget, not
permission to guess from the version or downgrade to an older release. Preserve
schema-1 trust interoperability and test existing 1.2.5+ verifiers against the new
candidate format in the later authorized packaging phase. Rollback/uninstall
must not remove active gates or bypass unresolved journals; only compatible
recovery packages or a mentor-confirmed quiescent recovery path are supported.

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
| F03 | Pause observed before prepare, during Ready, or at final policy read | No install or implicit resume; clear pause explanation. Test after-read race separately in F44. |
| F04 | UAC/polkit denied or canceled | GUI stays open; no protected staging/commit left active. |
| F05 | Same-user versus alternate-admin elevation | Correct original GUI peer binding; no root/admin profile substitution or GUI relaunch. |
| F06 | Wrong UID/SID/session, PID reuse, foreign executable, live-client delegated writer | Reject channel/command without changing policy or package state. |
| F07 | Pipe/socket squatting or linked directory/receipt | Fail closed; GUI never accepts spoofed supervisor status or close instruction. |
| F08 | Oversized/unknown/version-mismatched/truncated IPC, missing/ambiguous record credentials or unexpected descriptor attachments | Bounded rejection and safe cleanup; no parser-controlled paths or execution. |
| F09 | Replayed capability, conflicting command ID or stale Ready epoch | Reject; one transition/native launch. Benign event-sequence advancement does not invalidate valid consent. |
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
| F21 | Commit acknowledgement lost / duplicate commit | Historical acceptance is separate from current close grant; reject expired/delayed/terminal replies; idempotent effect, no deadline extension. Include supervisor crash after client validation. |
| F22 | GUI crash before versus after accepted commit | Before: cancel. After: independent supervisor can proceed only after session drain. |
| F23 | Supervisor killed at every state before durable intent | No installer ever started; OS leases release; normal startup not permanently denied. |
| F24 | Power loss or helper killed between durable intent and spawn | Conservative interrupted recovery; no automatic journal deletion or retry. |
| F25 | Helper dies with native children still running | Retained journal prevents normal startup/retry despite released OS locks. |
| F26 | Native nonzero/unknown completion/postcheck failure | Preserve evidence/recovery; never report Updated or fabricate rollback. |
| F27 | Native success / reboot-indicated outcome | Verify resources/version/engine; distinguish Updated from RebootRequired. |
| F28 | Legacy S holder or old scheduled O/S worker, including intent written between startup checks | Safe deferral/exclusion; post-S journal recheck prevents normal startup after an old worker crashes; no false claim of legacy admission support. |
| F29 | Missing gate, partial capability migration, wrong permissions, unrelated/uncertain journal | Manual feature unavailable; existing data/locks/policy untouched. The installer's own authenticated hook is tested separately in F40. |
| F30 | App-only install with no tool schedule | Works when trusted app bootstrap/capabilities exist; no tool provisioning/schedule creation. |
| F31 | Full manual upgrade | Tools, baseline, schedule, pause and project/editor data preserved; real version/engine and receipts agree. |
| F32 | Stale/unknown/tampered public status or disconnect | No false success/close authority; safe status unavailable; authoritative journal respected. |
| F33 | Light/dark/high contrast, all zooms, minimum window, keyboard/reader | Stable targets/focus, real accessible progress, no byte-by-byte speech spam or clipping. |
| F34 | Reboot after completion versus uncertain installation | Completed receipt remains usable; uncertain state retains recovery restriction; no stale Ready grant. |
| F35 | USB/terminal/GUI removed after accepted handoff | Installed snapshot and supervisor continue independently; no dependency on original launcher files. |

| F36 | Administrator UAC broker attempts direct native installation without SYSTEM hop | Reject identity; no weakening of system() or fallback to administrator install. |
| F37 | SYSTEM task request swapped, duplicated, expired, automatically retried or user-edited | Narrow fixed action only; claimed request cannot run twice; no post-crash automatic install. |
| F38 | Slow partial IPC frame, flooding, blocked server write or dead reader | Bounded memory and deadlines; before commit cancel; after commit proceed/defer independently without lock leak. |
| F39 | Ready valid while a progress heartbeat increments event sequence | Valid Ready epoch still commits; stale epoch or changed payload does not. |
| F40 | Legitimate new/legacy NSIS or DEB hook runs with parent O/A/S and journal held | No recursive-lock deadlock/self-rejection; no journal/gate replacement; authenticated hook context required. |
| F41 | An unrelated privileged caller copies a hook flag/env/journal reference | Does not gain the package-hook exception or clear/alter an active transaction. |
| F42 | Target package drops/downgrades admission capability, rollback/uninstall races | Reject unsupported target/migration; current gate identities and uncertain state survive. |
| F43 | Suspend/resume, reboot or clock discontinuity while Ready | Invalidate pre-install grant; no stale authorization extended by suspend or reconnect. |
| F44 | Pause change before versus after final local read, and GitHub withdrawal after refresh | Before read: stop. After read: documented race, no claimed global atomicity; retained policy applies next time. |
| F45 | Eligibility age crosses ten seconds during drain; DNS stalls or package lock remains busy | Accepted snapshot survives bounded drain; no network after A. Drain <30 seconds and final launch decision <45 seconds; expired or uncertain intent is handled conservatively. |
| F46 | Crash at each final receipt/status/journal-clear/lock-release boundary | No ordinary Updated while journal unresolved; no app mutation without durable intent. |
| F47 | APT installs required runtime dependencies | Allowed bounded app-dependency scope; no remove/distribution/managed-tool or baseline operation. |
| F48 | Standalone root namespace/user-session mismatch, IPC endpoint survives supervisor turnover | Fail authentication; no endpoint transfer, inherited authority or automatic reconnect. |

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

## 11. Revision-2 review findings and remaining blockers

These findings concern omissions/contradictions in revision 1, not a completed
implementation review. “Revised” means the written rule is corrected; it does not
mean platform feasibility, race freedom or security has been experimentally proven.

| Finding | Severity | Revision / disposition |
| --- | --- | --- |
| R01: UAC administrator treated as adequate Windows worker identity | Critical | Preserve SYSTEM contract; specify dedicated one-shot SYSTEM broker. B01 remains blocking. |
| R02: Package hooks would reject/wait on their own parent journal/locks | Critical | Define narrowly authenticated package-hook exception, additive migration, and legacy proof requirement. B04 remains blocking. |
| R03: IPC backpressure could freeze commit/expiry while holding locks | High | Bounded framing/queues and nonblocking supervisor; post-commit independence. Native proof under B02/B03. |
| R04: Progress sequence conflated with readiness consent | High | Immutable Ready epoch distinct from event sequence; payload-bound idempotence. |
| R05: Network refresh after closing GUI allowed unbounded perceived outage | High | Refresh before A; bounded local-only launch-decision window and commit freshness rule; no global GitHub atomicity claim. |
| R06: Suspend could indefinitely extend readiness grant | High | Boot/incarnation binding; suspend-aware expiry or invalidate on resume. |
| R07: Existing pause API cannot atomically preempt native spawn | High | Explicit final-read boundary and both race outcomes; no stronger promise than existing contract. |
| R08: Generic Commit requirement accidentally applied to automatic updates | Medium | Scope explicit GUI Commit to manual mode; preserve scheduled authorization. |
| R09: Target-package compatibility and cleanup after successful receipts unspecified | High | Require target capability evidence; define final write/journal-clear order and conservative crash outcomes. B04/B05 remain blocking. |
| R10: App-only wording implied no runtime dependency changes | Medium | Permit required app runtime dependencies within existing native no-remove policy, excluding tool/baseline upgrades. |
| R11: New capability fields could break strict schema-1 fleet verifiers | High | Keep signed manifest schema unchanged; propose inspectable declarations inside signed-installer bytes. Representation/parser feasibility remains B04. |
| R12: A live enrolled process can delegate its connected socket without changing connection credentials | High | W2h detects the tested guard accepting holder data. Require complete-command kernel sender attribution; proposed Linux record profile needs native proof, Windows remains unresolved. |

| Blocker | Evidence needed to clear it | Owner / current state |
| --- | --- | --- |
| B01 Windows SYSTEM launch broker | Reviewed fixed-action task/request/ACL/restart/cleanup design and native proof under standard-user, same-user and alternate-admin UAC. No dependency on provisioned weekly task. | Codex; design proposed, no prototype/validation authorized or performed. |
| B02 Mutual IPC authentication | Trusted original-peer enrollment; kernel-attributed complete-command sender proof; Linux protected namespace and proposed per-record credentials; Windows DACL/identity/writer association under handle delegation; replay and bounded-I/O evidence. | Codex; W2h counterexample to connection-identity-plus-liveness sufficiency. Revision-4 Linux redesign proposed, not validated; Windows mechanism unresolved. B02 remains open. |
| B03 Independent supervisor lifetime | Windows task and Linux root process survive GUI/terminal/logoff transitions appropriately; retained journal protects orphan package children; Linux one-shot supervision/cgroup ownership chosen and proven. | Codex; mechanism must be finalized, no daemon assumption. |
| B04 Package-hook and target/migration compatibility | New and legacy-parent hook authentication rule; no reentrant locks; supported old-source upgrade matrix; trusted target capability evidence; rollback/uninstall/gate-identity behavior. | Codex; legacy hook proof and proposed installer-carried capability representation unproven. |
| B05 Durability and restricted recovery startup | Windows/Unix ordered receipt/journal durability including reboot/power loss, native child-quiescence reconciliation and user-readable recovery notice without acquiring a normal GUI session. | Codex; no automatic uncertain-state clearance authorized. |
| B06 Coordination/state-machine proof | Model or deterministic interleaving review for A/O/S and legacy wrappers, all fault boundaries, bounded admission/drain behavior, validated suspended-state handling. Then native cross-process and desktop acceptance. | Codex owns engineering evidence; owner handles later desktop UAT. Revision-2 W1 L1 evidence exists; revision-3 alignment and native proof remain pending. |

Product defaults for review: five-minute Ready, thirty-second drain, forty-five-
second admission-to-final-launch-decision bound, ten-second eligibility freshness
at accepted commit. These revision-3 timing rules supersede the revision-2
admission-to-intent and spawn-age interpretation. Confirm
these against platform behavior before freezing them. A timeout may abandon a
proven pre-install transaction; it never erases uncertain native intent. Selecting
a bounded framing library or native broker API does not by itself clear B01–B06.

**Exit criterion:** resolve or explicitly redesign each blocker with recorded
evidence before calling the protocol implementation-ready. Further design work
is permitted by the review request; prototype/production code, automated workflow
dispatch and candidate builds still need a later instruction.


## 12. Phase 1 validation plan

The [Phase 1 plan](APP-UPDATE-NOW-PHASE1-VALIDATION.md) specifies 22 isolated
experiments for B01–B06, evidence levels, pass/fail rules and a W1-only local
prototype proposal. The plan itself does not execute experiments; the separately authorized W1
execution is recorded below. Native
privilege, package, power-loss and desktop proof remain separately scoped gates.


### W1 execution evidence

The subsequently authorized [W1 harness and findings](../../tests/prototypes/manual-update/EVIDENCE.md)
provide L1-only model evidence. See its explicit scope and fault ledger; all six
blockers remain open. Freshness/drain timing, historical ACK validity and query
cache accounting are resolved normatively by revision 3; see the
[W1 review and alignment requirements](APP-UPDATE-NOW-W1-REVIEW.md). Original reports remain a revision-2 baseline. The subsequently authorized
[revision-3 local alignment](../../tests/prototypes/manual-update/EVIDENCE.md#revision-3-alignment-execution)
checks selected timing/close/cache rules in isolation; it is not full protocol conformance. No native proof,
production implementation or workflow/build dispatch follows from this result.
