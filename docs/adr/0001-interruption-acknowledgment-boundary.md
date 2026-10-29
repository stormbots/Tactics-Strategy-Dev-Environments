# ADR 0001: Prompt-free interruption acknowledgment boundary

Status: permission-layout feasibility accepted at `1f1e449`; production storage
foundation implemented, native production validation pending. Execution behavior
is unchanged. Implements the T1 checkpoint in
[the recovery plan](../INTERRUPTED-OPERATION-RECOVERY-PLAN.md).

## Context

The owner approved acknowledgment by any student without a separate elevation
prompt. Acknowledgment persists machine-wide, including for scheduled work.
Private transaction bytes, active-operation checks, and normal OS authorization
must remain protected. Administrator/sudo membership does not elevate a GUI.

The existing manual application installer already invokes privileged coordination
initialization: NSIS runs `--coordination-init`; the Debian post-install hook does
the same. Initialization can inspect a legacy record without deleting it. This
is distinct from the automatic updater, whose normal installation gate currently
rejects an interrupted record. We must test actual deployment separately; this
ADR does not claim that an old blocked automatic updater can install its own fix.

## Proposed contract

During an already-authorized installation/bootstrap, trusted code holding the
operation gate prepares three separate records under the fixed coordination root:

- `transaction.json`: original private evidence, unchanged.
- `recovery-incident.json`: protected, publicly readable snapshot containing
  `schema: 1` and a fresh opaque UUID `incidentId`. No token, raw journal hash,
  path, PID, package argument, or privileged command is published.
- `recovery-acknowledgment.json`: pre-created, administrator/root-owned fixed
  regular file. Users may read/write its bounded non-authoritative contents,
  but may not replace/delete it, change its ACL/owner, or create sibling files.

The private binding pairs the public UUID with a SHA-256 of the original journal
bytes and its native file-generation identity. A hash alone cannot distinguish
identical legacy bytes in two different transaction objects. On Unix the identity
includes device, inode, ctime/mtime with nanoseconds, and length; on Windows it
includes volume/file index, creation/write time, and length. It is not readable
by students. A privileged consumer must compare the
binding with the currently opened journal under its gate before recognizing the
intent. Matching a UUID alone is not sufficient. Never derive a public incident
ID from the Windows nesting token. A changed journal requires a new generation.

The acknowledgment payload has exactly two fields: `schema` (integer 1, not a
boolean or string) and `incidentId` (canonical lowercase UUID). Extra/duplicate
fields, oversized payloads, invalid encoding, and stale IDs are rejected. There
is no caller path, command, token, skip flag, or operation argument.

The mutable slot is an explicit exception to the read-only-file convention, not
a relaxation of the protected root, gates, public marker, private binding, or
journal. Unix uses a root-owned regular file mode 0666 beneath a non-writable
root; Windows uses a protected DACL granting Users read/write data only (no
DELETE, WRITE_DAC, WRITE_OWNER, or parent FILE_DELETE_CHILD). Native probes must
verify effective access from an actual unprivileged process, not just inspect
mode bits or an administrator token's permissions.

Any user can submit a matching acknowledgment because the owner selected that
policy. The file is deliberately not authenticated as a privileged instruction.
It cannot enable elevation, launch maintenance, override pause, or bypass trust,
activity, package-state, candidate/signature, or native package-manager checks.

## Required implementation before production use

The initial permission fixtures demonstrated a proposed layout, not production
functions. The production `sde_coordination::recovery` API now implements bounded
storage, incident binding, sanitized inspection, and intent submission; native
tests exercise these actual functions. No GUI, installer/bootstrap, scheduler, or
execution consumer calls the API yet. Before enabling it:

1. Validate ownership, ACLs, regular-file type, link count, no-follow/reparse
   semantics, fixed path, size, and handle identity in shared production code.
   Check snapshots/intent/binding under the relevant lease; do not trust data
   read before acquisition. A partially overwritten slot is invalid, not approval.
2. Define atomic publication and crash recovery for the binding, snapshot,
   acknowledged disposition, archive, and new transaction. Intent by itself is
   not the final durable acknowledgment. Reports remain separate and best-effort.
3. Reconcile valid intent into protected machine disposition during the next
   normally privileged operation, bootstrap, or scheduled invocation. Scheduling
   cannot infer safety from the intent. Preserve evidence before replacement.
4. Rotate snapshot/binding for every new interruption. Reject old intent even
   if an older public marker remains after a crash. Bound parsing and never
   interpret fields as executable input.
5. Cover root/SYSTEM versus GUI account transitions, mixed versions, manual
   installer deployment with a legacy transaction, normal privilege prompts,
   disk-full/partial-write failures, and restart. Do not claim these later
   lifecycle guarantees from a permission-layout probe alone.

If the native layout cannot meet these requirements, keep the existing guard
and return the failing assertion to engineering. Do not add a service, expose
private bytes, or substitute an extra acknowledgment elevation prompt silently.

## Evidence and scope

`tests/test_recovery_acknowledgment_contract.py` checks the proposed strict payload
and private binding. Its root-only Linux fixture drops to UID/GID 65534 for a
student submission and uses a synthetic journal under an isolated `/var/lib`
directory. `tests/Test-RecoveryAcknowledgmentFeasibilityCI.ps1` uses a disposable
standard Windows account and an isolated ProgramData fixture. Neither accesses
the real coordination root, changes production behavior, or launches packages.

Existing Build Skyview Dev Setup jobs run the probes; the CI workflow chat owns
their authoritative native results. Build run
[40779104989](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/40779104989)
passed at `1f1e44918be9645069312a388601fdc7e1c2bc13`. DevOps confirmed both Windows
permission markers (native job `123136019245`) and the Linux root fixture, with
all other applicable checks passing. This accepts the permission-layout gate,
not production lifecycle or UAT completion. See the
[backend foundation handoff](../RECOVERY-BACKEND-FOUNDATION.md) for subsequent work.
Existing Windows interruption evidence and Mint v1.2.18 UAT acceptance are unchanged.
