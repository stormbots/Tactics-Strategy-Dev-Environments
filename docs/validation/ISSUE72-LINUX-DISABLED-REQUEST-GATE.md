# Minimum Linux request/deployment native gate (proposed, not executed)

This gate validates deployment and OS-authorized arrival at the **disabled**
fixed broker. It does not validate an enabled update, worker lifetime, receipt ACL
visibility, package hooks, protected close, installation or recovery. PR #73 stays
 draft and unmerged; the desktop and broker source gates remain false. No
capability receipt is created or repaired. Original protocol research remains
historical: W2h's delegated-authorization counterexample and W2m's cleanup failure
are not resolved by these local checks or by the proposed native gate.

## Reviewed wiring

The broker publishes a root-written, named-UID-read-only pending receipt and
per-user correlation pointer before spawning, then publishes accepted after
Popen succeeds. Accepted means launch initiated, not liveness/Ready/installation.
Failure after launch retains uncertainty and never kills or retries the worker.
Unresolved/current-boot checks prevent a second queued attempt; terminal pointer
replacement retains old run evidence and still requires all installation-core
admission/trust checks. At eight retained runs the broker stops without pruning.

The desktop's fixed Linux transport has no caller parameters. It invokes only
`/usr/bin/pkexec --disable-internal-agent /usr/local/libexec/skyview-app-update-request`,
with null input/error streams, a fixed environment, a 1,024-byte response bound
and 120-second UI deadline. A retained background owner reaps the child; it never
kills an uncertain independent attempt. Uncertain outcomes prohibit retries in
that GUI process. Successful stdout must match the protected accepted receipt.
The desktop source gate refuses before reaching this transport.

A no-argument read-only command resolves the original user's current protected
receipt; Schedule can reconnect to its progress. Pending/expired records remain
observations. Close and eligibility remain independently disabled. Busy startup
still refuses ordinary GUI admission; no GUI is admitted without S. Restricted
startup presentation and actual close/admission behavior remain native gates.

Bootstrap deploys only disabled broker/policy bytes, root-owned directories and
an inode-preserved request gate. It records hashes in app-only-deployment.json;
that file is **not** app-only-capabilities.json. Unknown/changed/incomplete prior
deployment stops without repair. Known upgrade bytes may be replaced; partial
publication stops and requires review. The remove hook removes only recorded,
unchanged broker/policy files, retaining requests, gates, capabilities and recovery
evidence. No hook starts an app-only worker. Existing maintenance configuration
and tools remain on the existing scheduled path. Native package-hook behavior
is unproven and is outside the proposed gate.

## Preconditions and exact authority requested

Use the spare Mint host only if fixed deployment paths are absent and no installed
SDE or self-update state exists; otherwise stop and select a disposable Mint
filesystem/environment. No VM/runner/media pipeline is required. The active
original desktop user must have a functioning existing polkit authentication agent.
Read-only preflight checks Mint release, uid, boot ID, pkexec/pkaction/Python
availability, path ownership/modes, free disk, and absence of SDE deployments,
transaction intents and existing action IDs. Missing tools stop; no package install.

A separately authorized operator may:

1. Deliver only the three hash-pinned sources below to a fresh root-owned private
   staging directory, checking hashes before executing anything. Create the missing
   fixed bundle directories `/usr/lib/Skyview Dev Setup/backend/linux/self-update`
   and sibling `polkit` as root:root 0755; copy bootstrap.py/app_request.py and the
   policy under those fixed names, root-owned and not group/other writable. Record
   every created inode/path in a root-private bounded journal. Refuse any existing
   source/target; do not overwrite installed SDE.
2. Run exactly `/usr/bin/python3 -I '/usr/lib/Skyview Dev Setup/backend/linux/self-update/bootstrap.py' --deploy-app-only-disabled`
   once as root. This provisions the fixed polkit action (privileged registration),
   broker, deployment record, root state directories and request.gate only. It does
   not query packages, create a service/task/timer or activate a worker/capability.
3. From the active original user's terminal, invoke the fixed pkexec command once
   and cancel authorization. Record exit status and verify no runs/current pointer
   or worker appeared. Cancellation exit codes are observations, not guessed proof.
4. Invoke the same command once and approve the OS prompt. Require exit **78** and
   bounded stderr JSON `{ "schemaVersion":1, "status":"disabled", "uid":<original uid> }`.
   Verify no run, request, current pointer, worker or capability was created and
   that the pause/maintenance state and disabled source bytes are unchanged.
5. Archive bounded evidence, then run the exact bootstrap
   `--remove-app-only-disabled` operation as root once. Verify only the matching
   recorded entry/policy were removed. Remove individually only the run-owned
   delivered source files and now-empty directories after inode/hash/owner checks;
   preserve the evidence journal and do not recursively remove any state tree.
   Unexpected residue is retained/reported, never relabeled successful cleanup.

This packet authorizes nothing by itself. Execution requires explicit user approval
of these operations and a source commit pin. No runner registration/dispatch is
needed. Environment approval/self-approval policy is unchanged if a later workflow
is separately proposed; no temporary self-review toggling is required.

## Source pins

Verify with `sha256sum` against these independently calculated content hashes:

| Source | SHA-256 |
| --- | --- |
| linux/self-update/app_request.py | 122bef3156eb03e258c1693af3eb177e082a0c84db9fe2d927ed8b039d581b10 |
| linux/self-update/bootstrap.py | bc5971d271e3f0712c02cd3ba12ca26d73f47f5ab30ea26e24f539d72ac9c667 |
| linux/polkit/org.skyviewrobotics.sde.app-update.policy | 50900fa7d3f8f92c8646c8ae821b6ed6ac9356639abed17c9091b7ee17b25187 |

The eventual execution approval must pin the commit containing this packet and
verify these bytes again. A mismatch stops; never update a hash to fit host bytes.

## Bounds, evidence and stopping rules

One deployment, two explicit authorization prompts (one cancelled, one approved),
one removal; 15-minute total operator budget, each prompt at most 120 seconds,
16 KiB per observation, 1 MiB total journal/evidence, no media or installer bytes.
A timeout stops further attempts; no pkexec/broker/worker kill or automatic retry.
Record command/exit, timestamps/boot, original/effective identity, root ownership,
hashes/modes/inodes before/after, action listing, source-gate false, zero worker
and run creation, and exact cleanup inventory. Do not record credentials.

Stop on any unsupported prerequisite, unexpected prompt/result, ownership/link/
hash drift, created request/worker/capability, changed maintenance state, deadline
or evidence bound, partial deployment or uncertain cleanup. Preserve evidence;
do not tune permissions, enable gates, repair records or substitute mechanisms.

Report three separate outcomes: **diagnostic completion**, **cleanup correctness**,
and **authentication safety**. Even all expected observations establish only this
disabled OS-authorized entry boundary, not end-to-end authentication safety.

## Remaining gates before feature enablement/testing build

Next prove actual named-UID ACL visibility and denial to another existing UID with
root-owned bounded synthetic records and the real Rust reader (not a Python
substitute). Then prove independent worker ownership, O/A/S transitions, timeout,
pause, crash/reopen and compatibility using package-free fixtures where possible.
Real package hooks/install/recovery and Windows privileged launch require separate
native authorization and evidence. No native-validation markers may be fabricated.
Only after the relevant platform gates pass may enabling source/capability changes,
protected close behavior, installer testing builds and desktop UAT be proposed.
Optional runner/VM infrastructure remains paused.

## Local review evidence

Local checks for this change: 140 UI tests; 17 ordinary desktop Rust tests;
61 updater library tests passed with one POSIX-ACL native test intentionally ignored;
10 broker mocks/temp-fixture tests; 12 package-hook mocks/temp-fixture tests;
7 backend permission-contract checks; 10 CI-boundary and 9 CI-scope checks.
Rustfmt, Clippy with warnings denied (both crates/all targets), TypeScript,
affected-file Prettier, hook shellcheck, actionlint and diff whitespace checks pass.
The updater's local HTTP test initially could not bind under the sandbox; rerunning
with network permission passed. No production updater, pkexec, root operation,
package action, ignored ACL test or native guest experiment ran. Windows compilation
for the changed source must be assessed separately by automatic CI, not inferred
from these Linux checks. Launch transport local coverage checks its fixed command;
it does not yet simulate every child/output/deadline failure schedule. Those
coverage limits are retained, not a claim that the transport is ready to enable.

## Execution outcome and superseding next-session plan

The original clean-host prerequisite failed on the spare Mint host because SDE
and updater/coordination state were already present. A narrower two-file-only
broker/policy attempt was performed under user authorization, without bootstrap.
The action registered, but pkexec returned 127 without any GUI prompt. Neither
cancellation nor approved broker entry was validated. Agent process-name and
journal diagnostics did not establish the cause. User-pasted cleanup output
confirms removal of both temporary files after recorded ownership/inode/mode/hash
checks; sources and root journal were retained. Whole-host cleanup is not claimed.

See the [bounded evidence](../design/evidence/ISSUE72-SPARE-MINT-DISABLED-BROKER.json)
and [consolidated Linux-first plan](ISSUE72-LINUX-CONSOLIDATED-NATIVE-PLAN.md).
This packet remains historical and must not be replayed blindly on the installed
host. Authentication safety and the native ACL/package/worker gates remain open.
