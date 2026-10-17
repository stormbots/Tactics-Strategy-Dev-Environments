# #72 B02 revision-4 review and proposed record-credential gate

**Status:** planning only; not executed or authorized to execute. This document
proposes the next isolated gate, provisionally W2i, after review of
[protocol revision 4](APP-UPDATE-NOW-PROTOCOL.md#6-authenticated-ipc-protocol-and-platform-profile).
No production code, experimental adapter, elevation, registration, package,
workflow/build dispatch, version allocation or release preparation is included.
B01–B06 remain open. No owner workstation/VM action is requested.

## 1. Why this gate is needed

[Reviewed W2h](../../tests/prototypes/manual-update-w2h/README.md) establishes a
counterexample to the sufficiency of connection credentials plus retained-client
liveness for original-process message submission. Its diagnostic succeeds while
its authentication-safety result is CounterexampleDetected. It does not exercise
the full capability, privileged enrollment or installation protocol.

The next question is whether a Linux record and its kernel-delivered sender
credentials can be bound to an enrolled process strongly enough to reject that
same independent holder. This is a proposed native primitive experiment, not a
claim that SO_PASSCRED or SOCK_SEQPACKET is already validated for SDE.

## 2. Gate A: specification review before any implementation

A reviewer must explicitly accept or revise these decisions first:

| Decision | Proposed criterion |
| --- | --- |
| Security property | The kernel attributes each complete accepted command to the enrolled peer. Process liveness, attempt capability, OS authorization and state checks remain separate required conditions. |
| Threat assumptions | Independent unprivileged writers, including an FD-only same-UID holder, are in scope. Trusted native actors, memory isolation limits, code injection/exec and privileged credential-forgery capabilities are explicitly bounded as in revision 4. No physical-click guarantee. |
| Linux candidate | AF_UNIX SOCK_SEQPACKET, one complete common envelope per record, mandatory recvmsg/SCM_CREDENTIALS evidence with SO_PASSCRED enabled and verified before any application send is permitted; MSG_CMSG_CLOEXEC is mandatory. No connection-PID-only fallback. |
| Wire contract | Four-byte network-order JSON length, at most 16,384 record bytes including prefix, exactly one envelope, strict schema and bounded ancillary handling. Required profile negotiation; no silent stream downgrade or schema-1 manifest extension. |
| Enrollment | Expected identities come from a trusted fixture for this primitive gate. Production original-GUI and final-supervisor bootstrap enrollment remains a separate unresolved B02 obligation. A packet's claimed PID cannot create trust. |
| Windows | Named-pipe complete-command writer identity, duplicated handles, account modes and exact access rights remain unresolved. Linux success cannot close those obligations. |
| Transaction continuity | Authentication does not replace explicit administrator authorization, pinned candidate/Ready/attempt bindings, replay controls or current close authority. After accepted commit, channel/GUI loss cannot revoke installation authority or erase intent. |

If sender attribution is weakened to delegable channel authority, return to
specification review with an explicit changed threat contract. Do not label that
change a passing result for the current requirement. Gate A acceptance is not
permission to execute Gate B; a separate instruction is required.

## 3. Gate B: proposed smallest unprivileged native experiment

### Environment and boundaries

- Existing managed disposable Linux runtime; Python standard library or another
  separately reviewed minimal adapter with no dependency installation. No desktop,
  VM, container, service manager, polkit or root account is required for this gate.
- Unprivileged UID, zero effective capabilities, AF_UNIX SOCK_SEQPACKET,
  SO_PASSCRED, sendmsg/recvmsg and SCM_CREDENTIALS, readable process creation and
  real/effective/saved credential metadata, MSG_CMSG_CLOEXEC, pidfds and
  owned-child reaping.
  Record effective/permitted/inheritable/ambient capability sets and namespace
  identities from OS observations; controlled actors must not change credentials,
  namespaces or capabilities during a case. No privileged credential-forgery
  capability may be effective at submission. This is not cross-UID/root coverage.
- Private fresh 0700 prototype root and 0600 socket; all actors and fixtures belong
  to the run. No production SDE path, downloaded code, package manager, command
  executor, intent, real CommitInstall or GUI-close operation.
- Independent server, enrolled client and holder. Trusted separate controls enroll
  process instances and establish barriers; they never tell the receiver to allow
  an action. The kernel-credential endpoint is independently created by the actors,
  not a parent-created socketpair with inherited connection credentials.
- The original client must stay alive before and after evaluation. These are
  barrier-controlled observations, not a proof of atomic liveness-to-action or
  continuous executable integrity in production. Use retained
  pidfds and independent creation/parentage observations. Explicit FD inheritance
  establishes the holder's connected endpoint. If temporary child-subreaper state
  is needed for failure cleanup, record and restore it.
- Single-threaded actors and unchanged PID/user namespaces only for this first
  gate. Record namespace identities and credential sets; unsupported contexts are
  Blocked. This does not certify real GUI thread semantics or namespace transitions.
- Use named readiness/send/evaluation/cleanup barriers, with an explicitly test-only
  five-second per-operation diagnostic watchdog. No timed sleeps or aggregate
  stress success establish ordering. I3's rejection needs the actual sendmsg errno
  and an independently queryable receiver action count; a receive timeout is not
  credential-forgery evidence. These bounds validate no production 30/45-second
  handoff deadline and authorize no process kill outside owned test actors.
- Preflight option/support checks, including listener/accepted endpoint settings,
  are part of a later authorized run, not activities performed by this plan.
  Missing primitives are Blocked. No socket-type or missing-credential fallback.
  Enable and verify SO_PASSCRED on the listener before connect and on receiving
  endpoints before releasing a peer-send barrier. Verify accepted-socket settings.
  Never rely on enabling the option only after data is queued.

### Three core native schedules

Use the same valid bounded dummy request shape in all applicable cases. Bind
fields to each case's test attempt and original PID, then hold those fields fixed
when the holder submits within that case. Do not reject the holder merely
because it lacks a dummy secret or has a malformed payload: isolate kernel sender
attribution. Only an in-memory fixed-action counter may change. Each case has a
fresh connection, enrolled instances and counters starting at zero; handshake and
read-only evidence queries never increment the action counter. Within I2/I3, the
holder uses the connection established by that case's original client. Trust is
enrolled out of band before the first application record; Hello confirms it and
never enrolls identities learned from the received packet.

| Case | Barrier-controlled operation | Required observation and action count |
| --- | --- | --- |
| I1 Intended sender | Initial credential-bearing exchange confirms pre-enrolled instances. The original client submits one complete record with explicit valid SCM_CREDENTIALS naming itself and its unchanged real UID/GID, providing the positive control for I3. | Receiver observes original-client PID/UID/GID for the complete request; retained instance live; exactly one permitted test action and a credential-validated fixed reply. |
| I2 Live-client holder | After that case's original-client connection is established, the client explicitly passes its connected endpoint to a distinct holder and stays alive. Holder sends the same request without explicit credentials, testing kernel-generated credentials; original client sends no action request. | Connection metadata may still name the original client, but per-record credentials identify the holder. Receiver rejects for sender mismatch, with one attempted request and zero permitted actions. Original client/holder liveness and matching endpoint identities are independently observed before/after. |
| I3 Explicit credential forgery attempt | Holder uses sendmsg with SCM_CREDENTIALS claiming the live original client's PID, from the same zero-capability account/context. Use I1's valid ancillary layout and unchanged UID/GID; only the claimed PID differs from the submitting holder's own PID. | Expected kernel rejection is EPERM; record the actual syscall result/errno. No forged accepted record and zero permitted actions. Any other behavior stops for review. Another errno is not proof of the intended credential check; accepted forged authority is a counterexample. Never synthesize EPERM or infer it solely from a timeout. |

SO_PEERCRED may be collected for contrast if supported on this socket type; it is
not a required security input or a substitute for record credentials. Its absence
does not waive any mandatory sender check. No unsafe mutation/omitted-guard native
control is needed: preserved W2h already supplies the reviewed counterexample.

### Companion local validation, not additional native coverage

Before considering Gate B complete, exercise the proposed record validator using
explicitly labeled synthetic metadata: missing/duplicate credentials, payload or
ancillary truncation flags, inconsistent lengths, empty/multiple envelopes,
unknown control types, unexpected descriptor attachments and malformed JSON.
Every rejection must yield zero actions and bounded cleanup of delivered test
FDs. These checks must not be reported as native hostile-traffic evidence. Native
ancillary-FD leak/truncation, saturation, namespace, exec/thread, reverse-server
and cross-UID/root schedules require separate scoped proposals after this gate.
In particular, fabricated ancillary arrays do not prove the adapter can enumerate
and close descriptors actually installed by recvmsg, including partial delivery
on MSG_CTRUNC. Native checks of that behavior and bounded rejection of malformed
records remain prerequisites to adapter acceptance, not optional hardening.

## 4. Evidence and acceptance criteria

Record source/fixture hashes; OS/kernel/Python and namespace/account context;
actual socket options/type; both initial credential directions; kernel records
associated with each received envelope; expected/actual process instances and
retained pidfds; FD flags and fstat identities; sender/non-sender counters;
ordered barriers; requested forged credentials and real syscall errno; receiver
rejection reasons; effect counts; all failures; process reaping; filesystem/handle
cleanup; and restoration. Never log real transaction capabilities or privileged
secrets. Fixed dummy test fields are not production capabilities.

**Primitive feasibility pass** requires I1 = 1 action, I2 = 0, I3 = 0, with complete
kernel and ownership evidence, bounded local rejection tests, no unexpected
infrastructure failure and complete cleanup/restoration. No message may inherit
credentials from an earlier record or another process. A count alone, parent
allow/deny command, payload PID, mock kernel record or an absent syscall result
cannot establish a native pass.

Report independently:

- Experiment completion and evidence integrity.
- Sender-binding outcomes at this narrow native scope, including every rejected
  and accepted request.
- Authentication/production readiness: still **unproven**, even if I1–I3 pass.
  The healthy reply checks only an intended server; rejection of a delegated or
  impersonating response writer remains untested. Local malformed-input tests
  cannot substitute for native ancillary/descriptor and hostile-record coverage.
  Protected enrollment, root namespace, full capability protocol, Windows and
  remaining B01–B06 requirements do not become validated.

If any unexpected delegated authorization occurs, preserve it as a security
counterexample and stop. Completing a diagnostic that finds a counterexample
must never be reported as authentication success. An unexpected safe rejection
also needs investigation; do not fabricate a feasibility pass or replace the
candidate mechanism during the run.

## 5. Stopping and cleanup rules

Stop dependent cases on failed healthy control, delegated/forged authorization,
unexpected missing or ambiguous record credentials in a core native schedule,
partial/incorrect credential association, unsupported option behavior, unknown ownership or namespace, timing watchdog,
identity replacement, resource bound violation, incomplete reaping or failed
restoration. Classify unavailable prerequisites Blocked; unexpected outcomes
once a case starts are Fail/CounterexampleDetected with precise evidence.
Expected I2 sender rejection, I3 EPERM and synthetic malformed-input rejection
are required negative outcomes and do not trigger this stop rule. A diagnostic
may complete with an intact counterexample report while the security property
fails; report diagnostic completion, property outcome and cleanup independently.

Only registered run-owned process handles may be signaled, plus a still-unreaped
direct Popen child if pidfd setup failed. Reap a known holder even if signaling
races with its exit; validate returned wait identity/status. Never signal an
unknown adopted actor. Close delivered test descriptors and all owned transport
handles. Refuse deletion of unknown/replaced paths or roots with uncertain
process ownership; preserve their reported locations for review. Restore any
runner-local process setting and record remaining children. No lock deletion,
package recovery, task/service removal or host reset belongs to this gate.

## 6. Required disposition afterward

Engineering review must decide whether the evidence supports this primitive at
its stated scope and what the next unresolved obligation is. Even a clean Gate B
result does not authorize production implementation, elevate privileges, register
services/tasks, run remaining W2/W3, change versions or dispatch builds/releases.
The Windows sender mechanism, privileged enrollment/namespace proof and integrated
close/installation behavior remain separately gated.

## 7. Documentation review disposition

Revision-4 review corrections (documentation only; no new native evidence):

| Finding | Disposition / remaining obligation |
| --- | --- |
| Enabling credentials only before receive leaves queue/readiness ambiguity | Require option verification before sends; fixture barriers isolate the primitive. Production readiness/enrollment ordering still needs proof. |
| First exchange could be read as enrolling a self-declared peer | Confirm trusted pre-enrollment only, in both directions. |
| Forgery rejection without a valid explicit-credentials control is inconclusive | I1 explicitly supplies valid own credentials; I2 exercises automatic credentials; I3 changes the submitting-process claim. Actual EPERM and zero effects are both required. |
| Optional CLOEXEC and synthetic FD tests could overstate safety | Require atomic close-on-exec receive support; native ancillary/truncation/FD cleanup remains a later mandatory adapter gate. |
| Case counters and expected rejection stopping rules were ambiguous | Fresh per-case counters; expected negative outcomes distinguished from faults and counterexamples. |
| Narrow primitive success could be mistaken for mutual authentication | Preserve separate diagnostic/property/readiness results. Reverse hostile-writer checks, protected enrollment, GUI/thread/exec/namespace semantics, compatibility migration, Windows and full transaction integration remain open. |

The record candidate is feasible enough to propose for isolated validation, not
proven feasible on supported desktops. Specification review does not waive those
obligations or authorize any implementation/experiment. Preserve W2h unchanged as
a diagnostic success that demonstrates an authentication counterexample.
