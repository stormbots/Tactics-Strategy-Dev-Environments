# #72 disposable Mint validation: review and approval packet

Status: driver prepared and reviewed with **mocked local checks only**. Native
execution is not authorized by this document. PR #73 remains draft/unmerged.
No application, package, signing or release workflow has been dispatched.

Basis: [published proposal](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/73#issuecomment-6235900434).
Production source remains `a2a518684a77a5fc86287144f932c1510f1971e8`.
The new files live only under `tests/mint_validation`, its mocked test module,
and documentation. They do not enable Update Now or modify production code.

## Components and actual coverage

- `host_preflight.py`: read-only Ubuntu 24.04 x86-64 host assessment: accessible
  KVM API 12, protected QEMU/SSH/GPG binaries, two CPUs, 6 GiB available RAM and
  36 GiB free disk. No QEMU execution, VM creation, package command or download.
  It also authenticates supplied Cinnamon media using an isolated GnuPG home,
  private metadata copies, pinned signing fingerprint and explicit ISO digest.
  It never treats the Xfce checksum as a Cinnamon checksum. Host/disposable,
  loopback-console and no-host-mount acknowledgements are declarations, not
  hardware, isolation or disposability attestation. Actual guest boot must use
  private immutable media and revalidate the digest; the preflight does not boot it.
- `driver.py`: explicit plan/prepare, desktop enrollment, fixed authorized request,
  protected capture and ownership-checked root-fixture cleanup. It has no generic
  executor, installer, downloader, maintenance registration or valid capability
  receipt. The control entry points require `--execute`, private root staging,
  an approval record, matching VM/boot and exact source artifact hashes. GUI
  authorization and ACL probes are unelevated, with fixed paths/arguments.
- `sentinel.py`: root test-only script substituted into a separate fixture engine.
  It writes a bounded probe, waits at a 30-second release barrier, then publishes
  a released receipt. No subprocess/network/package executor. Root observation
  uses retained pidfds and external FD inventory, not self-enumeration that could
  confuse a transient observation FD with an inherited FD.

The real production worker is deliberately stopped at invalid `{}` capabilities:
claim + protected Deferred progress, without installed identity, discovery,
staging, tools, admission or native installation. That path does not validate a
positive installation handoff. The sentinel validates broker/surrogate lifetime,
not actual Tauri cgroups, replacement or installer children. A new session alone
never establishes cgroup independence.

## Approval requested, once an appropriate host is available

Authorize these operations **only inside one verified disposable Mint 22.3
Cinnamon QEMU/KVM VM** and its owned host artifacts:

1. Provision a 2-vCPU, 4-GiB guest with a 30-GiB ext4 disk from authenticated media;
   provide an actual Cinnamon login, polkit agent and loopback-only console/SSH.
   Create fresh `sde-student`, `sde-other`, `sde-mentor` accounts; only mentor has
   sudo membership. Install missing OS/test development components. Generate
   guest credentials privately; never put passwords in argv, artifacts or logs.
2. Stage exactly five reviewed artifacts and `approval.json` as root in
   `/run/sde-mint-validation-<runId>` (directory 0700, approval 0600): `driver.py`,
   `sentinel.py`, `app_request.py`, the fixed policy file and `sde-update-trust`.
   The verifier is an ordinary release-profile **development tool** build of the
   pinned updater source, <=64 MiB; no Tauri/application installer build.
3. Temporarily install the fixed broker at
   `/usr/local/libexec/skyview-app-update-request` (0755), policy at
   `/usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy` (0644),
   readonly helper at `/opt/sde-phase3-validation`, and synthetic protected
   receipts/snapshots under `/var/lib/skyview-robotics/self-update`. All root-owned.
   The only capabilities receipt permitted is `{}`. No coordination tree,
   maintenance entry point, schedule, baseline or SDE package changes.
4. Run the exact owned-file ACL control and cases below through the real OS
   authorization boundary. Inspect bounded logind/PolicyKit service attribution,
   sanitized polkit audit facts, ownership, ACLs, processes/cgroups/FDs. The lifecycle controller
   signals only an enrolled, positively identified GUI surrogate via its retained
   pidfd in the abrupt case; it never kills a production worker or installer. The bounded read-only probe runner may terminate its own read-only test command group.
5. Export bounded sanitized evidence; clean only sealed, manifest-owned fixture
   objects, then discard the entire VM, guest accounts, staging/evidence and host
   disk/key artifacts. Do not delete or reset a failed/uncertain fixture to retry.

Development components and investigating host access were already authorized.
This packet does not request new design decisions or access to the owner's PCs.
It does not authorize SDE package operations, service/task registration, native
W2/W3 research, application builds, signing, releases, stable promotion or rollout.

## Prerequisites that remain unestablished

No actual host preflight, ISO authentication, VM or native test ran in this step.
A suitable KVM host and console remain to be established; current managed access
had no attached VM host. The Python preflight is not a VM provisioner, console
backend or GitHub workflow. No new workflow or dispatch path was created. If a
validation-only hosted-runner workflow is chosen, it needs separate review and
registration on the default branch before it can be manually dispatched; do not
silently dispatch a build/native-package workflow or merge #73 to obtain a host.
Do not substitute TCG, Docker, chroot, Xvfb or a student laptop.

Native logind subject mapping and distro polkit audit formatting remain feasibility gates. If attribution is unavailable, stop and report that validation limitation; it is not proof that the product is unsafe. Do not replace it with fake session variables or silently claim a native pass.

The actual Cinnamon ISO digest must be authenticated and frozen by Codex before
constructing approval.json. Media/VM/account/boot facts and built artifact hashes
are engineering values to fill from observations, not questions for the owner.
An execution approval may be conditional on all those prerequisites passing.

## Reviewed sequence (commands are for a future authorized VM, not run here)

1. On the intended disposable host, supply the official checksum list, detached
   signature, Cinnamon ISO, repository signing key and authenticated digest. Run
   the read-only preflight via `PYTHONPATH=tests python3 -m
   mint_validation.host_preflight --execute-read-only --workspace <private-work>
   --disposable-host-ack --loopback-console-ack --no-host-mounts-ack --media
   <private-media> --signing-key <repo-key> --pin <verified-Cinnamon-SHA256>`.
   A prerequisite failure is a stop, not permission to weaken the check.
2. Boot/provision the approved VM and accounts. Run the exact owned-file ACL Rust
   control by its full name as described in the Phase 3 document; no broad
   `--ignored` selection. Unsupported ACLs stop before the guest cases. No
   world/shared-group permission fallback. Record actual OS/tool versions.
3. Create the private root staging bundle and approval record with schema 1;
   `purpose: mint-phase3-negative-and-sentinel-only`; canonical run/VM/boot UUIDs;
   `productionCommit` above; all five `artifactSha256` entries (`broker`, `policy`,
   `verifier`, `sentinel`, `driver`); actual three `uids`; authenticated media
   SHA-256; `expiresBootMs` no later than 30 minutes from creation; exact actions
   `[root-fixtures, temporary-polkit, desktop-authorization,
   owned-sentinel-signals, owned-cleanup]`. Root control must start before expiry;
   this is not a real-time bound on blocking filesystem operations. Boot mismatch
   prevents resumption. No credentials or fake native-validation attestation.
4. Fresh VM/approval/fixture for each case. Execute root control using
   `/usr/bin/python3 -I /run/sde-mint-validation-<runId>/driver.py prepare
   --execute --approval <stage>/approval.json --kind production` (or `sentinel`
   only for the two lifecycle cases). It aborts on SDE/fixture collisions or an
   ambiguous package database. It journals pending mutation before each object
   creation; a crash/pending entry requires preserving evidence and discarding VM.
5. In the actual student desktop, launch this **exact argument order**:

   ```text
   /usr/bin/python3 -I /opt/sde-phase3-validation/driver.py desktop-request --execute --case approved
   ```

   The helper first writes a private, unprivileged Ready hint and waits. Root
   executes `arm-desktop --execute --approval <stage>/approval.json --case
   approved`. It enrolls the actual process instance, source command, kernel UID,
   logind session and PolicyKit bus owner before creating the root-owned go barrier.
   Unprivileged receipts are hints, not authentication/installation authority.
   The owner/authorized console controller then performs the actual agent dialog;
   no password is passed to the driver. Console automation/access remains a host
   prerequisite, not something mocked results establish.
6. After helper completion, root runs `capture --execute --approval ... --case
   approved`. This waits boundedly for the real worker, requires the exact schema, public progress CLI,
   UID/boot/request/claim, Deferred error/sequence, no candidate/native phase,
   correct kernel ACL and intended/other UID access, and rejected claim replay
   without changed progress. It binds audit attribution to the actual PolicyKit
   bus owner's PID/UID (root or system polkitd), expected action and pkexec subject.
   Raw journal messages never enter exported evidence. No package-execution absence
   claim rests only on missing log output: the pinned, invalid-capability source
   boundary is part of this narrowly scoped evidence.
7. Repeat fresh fixtures for `denied`, `bad-args`, `inactive`; use the other account
   and a real inactive logind session for `inactive`. No fake XDG variables. A
   missing/changed provider, missing expected authentication audit or unsupported
   log format stops. Some inactive denials emit no authentication event: report
   `action: NotObserved` and the attribution limit, rather than inventing proof.
   No new request is permitted for rejected cases.
8. Fresh sentinel fixtures for `normal` and `abrupt`, with the same desktop/root
   sequence and `--kind sentinel`. Capture retains GUI and sentinel pidfds, checks
   root/same-instance/session/PGID/FDs at the barrier, releases normal GUI or signals
   only the enrolled GUI in abrupt mode, checks sentinel survival/cgroup evidence,
   releases sentinel and requires an explicit released receipt plus process exit.
   Missing receipt/natural timeout is a failure, not successful release. Actual
   application/desktop-scope teardown and authentication-agent restart are not
   automated in this driver; they remain distinct native coverage gaps. Never
   claim the GUI surrogate represents those scopes.
9. Export `case-evidence.json` and, if present, `failure.json` without secrets. After successful cleanup, also export `ownership.json` for its explicitly scoped cleanup result.
   Root `cleanup --execute --approval ...` is permitted only after successful
   capture sealed the manifest. It holds the broker request gate, checks scope,
   all identities and complete child sets before any deletion, and removes owned
   entries in reverse order without recursive rm. `cleanup: Pass` means only
   **manifest-owned root fixtures**. Accounts, staging and VM destruction have
   separate completion evidence. On any uncertainty, do not attempt cleanup or
   retry; export what is safe and discard the VM.

## Bounds and outcomes

Production 15-minute/2-minute deadlines, eight retained attempts, 32 progress
publications and 4096-byte progress bounds stay unchanged. The fixture uses one
request per fresh case. Sentinel 30-second, GUI 90-second and read-only probe
5-second limits are explicitly test-only. Probe output <=8192 bytes while reading;
read-only probes may be terminated as owned test processes. No production worker
or installer uses that termination path. Replay completion uncertainty is never
resolved by killing a worker. Directory inventories cap at 256 names; FD inventory
at 32 entries. One exported case <=64 KiB, at most six cases (<1 MiB); no raw
stdout/password/journal export. Evidence failure prevents sealing/continuation.

A pending lifecycle state (`Arming`/`Capturing`), previous failure, unknown staging
file or identity discrepancy prevents resuming. Failure evidence is best effort
when storage itself fails; do not label failed persistence or unknown cleanup as
Pass. Keep diagnostic completion, manifest cleanup, whole-VM cleanup,
authentication safety and production readiness separate.

The managed-filesystem ACL EOPNOTSUPP failure remains preserved. W2h remains a
counterexample; W2i–W2l limited; W2m immediate cleanup Fail; W2n N1/N2 NotRun.
These driver mocks neither repair nor replace those results. Positive app-only
installation, actual GUI cgroups/replacement, package children, suspend/reboot,
durability, migration/hooks and Windows remain unvalidated. Production readiness
is false and feature enablement remains blocked.
