# W2f implementation and evidence review

Reviewed the isolated harness and commit `cc06f25` evidence. Only W2f files and
the W2f execution record in the Phase 1 plan were revised. No other experiment,
production code, elevation, registration, package operation or workflow ran.

## Findings fixed

1. **Parent suppression masked endpoint enforcement.** Original negative cases
   sent `allow=False` to both peers. Kernel rejection was observed, but zero
   actions could follow from that command alone. The reviewed runner sends the
   same exchange command in every case. The unexpected client actually sends a
   request claiming the intended client PID, while the unexpected server sends
   an acknowledgment claiming the intended server PID. The rejecting endpoint
   records and discards the probe. The intended control still completes exactly
   one action/acknowledgment. The attempted request count in the wrong-client
   case is now one; this is expected and distinct from an authorized action.
2. **The evidence oracle checked too little.** Matching acceptance bits/reasons
   and selected counts did not prove the recorded kernel PID belonged to the
   actual owned actor or that a creation/liveness check had occurred. The new
   oracle cross-checks both directions, actual versus enrolled process records,
   same UID/GID, unprivileged direct-child ownership, successful creation samples
   and live pidfds, root/socket permissions, probe contents and byte counts,
   strict action/request/trust counters, and ordered verification/barrier/action
   timestamps. Contradictory recorded evidence is rejected in regression checks.
3. **Partial startup could escape teardown.** A child started before pidfd_open
   failure was skipped by the original `hasattr(pidfd)` cleanup condition.
   Startup now records the Popen handle before opening the pidfd and teardown
   reaps a child even if pidfd setup fails. Normal signaling uses registered
   pidfds. A narrowly scoped fallback can kill the runner's still-unreaped direct
   Popen child; it does not signal an arbitrary process found by PID. A peer
   exiting between poll and pidfd signaling is still reaped. Remaining direct
   children are reported on failure as well as success.
4. **Root identity was not checked during removal.** The original runner checked
   entries but could remove a different empty directory at the same root path.
   The root's original no-follow device/inode/owner/mode/type is now compared
   before cleanup, alongside entry identities. Unknown entries, replaced roots
   or sockets, and uncertain process cleanup preserve the root and fail the run.
5. **Malformed enrollment was not uniformly fail-closed.** Missing fields were
   caught, but non-dictionary/incorrectly typed fields could escape as TypeError
   or compare equal as booleans. Enrollment now requires the exact numeric
   process-instance schema, with positive PID/start ticks, before peer lookup.
   Data-channel frames also use bounded socket operations directly, avoiding
   mixing timeout-mode socket FDs with pipe-oriented byte reads.

## Verification and evidence

- `evidence/linux-run-reviewed.json`: three passing native Linux schedules,
  both verification directions and all attack-probe/action counters recorded.
  All eight owned actors exit zero with empty stderr, are reaped without forced
  termination, and all three private roots/four socket entries are removed.
  No children remain. UID/EUID/GID 1000; effective capabilities zero.
- `evidence/local-checks-reviewed.txt`: 18 passing focused checks. Credential
  error and lifecycle/cleanup failures in these checks are synthetic, not native
  fault-injection coverage. The oracle check deliberately corrupts recorded
  native snapshots; replaying those fixtures is not another native execution.
- Reviewed native evidence hashes both W2f Python files and the unchanged W2b
  definition-only support module. The original evidence remains unchanged and
  bound to its original source commit. The sandbox-denied initial run remains
  recorded; local Unix-socket permission, not OS elevation, was used for passing
  native runs. Review development runs had no failures.

## Remaining coverage gaps

All B01–B06 blockers remain open. Trusted parent enrollment is not production
IPC bootstrap. Private same-UID test sockets do not establish protected namespace,
ACL/DACL, root or cross-UID authorization. The fake server uses a distinct socket
path; endpoint replacement races are not exercised. Fixed well-formed spoofed
frames do not test arbitrary hostile framing, floods or malformed JSON.

SO_PEERCRED is a connection credential snapshot. Process creation samples and
pidfd liveness are checked during verification only; trusted lifetime barriers
keep enrolled peers alive until exchange completes. There is no claim about
PID reuse attacks, exec/credential changes, FD passing/inheritance, continuous
message origin, or production original-GUI binding. Directory cleanup checks
are not atomic protection against a malicious concurrent namespace racer.
Windows named pipes and native desktop/application integration remain untested.
