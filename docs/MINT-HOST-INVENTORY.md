# Spare Mint host inventory: disabled infrastructure only

This workflow registers its name on main so an organization administrator can
select it in a restricted runner group. It does not enable or deploy #72, merge
#73, register/start runners, provision guests or install application packages.

## Activation is a separate approval step

Leave these repository Actions variables absent during PR review and merge:

- MINT_RUNNER_ENABLED (must later equal exactly `true`)
- MINT_RUNNER_ACCESS_READY (must later equal exactly `verified`)
- MINT_RUNNER_APPROVED_SHA (must later equal the full reviewed main commit SHA)

Missing flags or mismatched SHA skip the sole job before scheduling. There are
no dispatch inputs, PR/push triggers or reusable-workflow entry points for the
inventory. It is manual-only and main-only. Later main commits disable it until
reviewed and approved explicitly. Do not set the variables during this PR.

Before setting ACCESS_READY, an organization administrator must verify:

1. Group `sde-mint-isolated` is not Default, uses Selected repositories containing
   only stormbots/Tactics-Strategy-Dev-Environments (explicit public-repo opt-in),
   and Selected workflows containing exactly:

   stormbots/Tactics-Strategy-Dev-Environments/.github/workflows/mint-host-inventory.yml@refs/heads/main

2. Main is protected against unreviewed/direct/force changes and deletion,
   including workflow code-owner review and no routine administrator bypass.
3. Environment `mint-host-access` already exists, has an independent required
   reviewer, prevents self-review, permits main only, has no secrets, and disables
   administrator bypass where supported. GitHub can create unprotected environments
   automatically: naming an environment in YAML does NOT establish these settings.
4. The exact SHA and live settings have been reviewed. Only then set ACCESS_READY,
   APPROVED_SHA, and ENABLED last. This is an administrator attestation; the job
   does not claim to inspect organization settings through its empty-permission
   token. A trusted administrator can alter policy; labels/flags are not a
   substitute for scheduler-side repository/workflow restrictions.

No runner should be registered until these controls are verified. Repository
admin permission alone did not let Codex inspect org runner groups: that API
returned 403. If any protection cannot be applied, stop without broadening access.

The group cannot be configured with this workflow until it exists on main.
Merge this separate infrastructure PR only after its checks/review pass and
merge authorization is given; keep #73 draft/unmerged. Then create/verify the
restricted group and approval environment. Registration, start, dispatch and
guest testing remain separately authorized later steps, not consequences of merge.

## Fixed inventory boundary

The job uses `org/sde-mint-isolated` and routing label `sde-mint-inventory`, runs
as a non-root dedicated account, has no GitHub token permissions, secrets,
checkout, third-party action or arbitrary command/ref input. Its fixed inline
Python only queries KVM_GET_API_VERSION (no VM created), checks Mint release,
and calls QEMU --version. It prints bounded facts with guestExecuted=false,
mediaAuthenticated=false, consolePrepared=false and productionReady=false.
The five-minute job timeout is not a guest-worker kill/cleanup mechanism. No
registration, VM boot, privileged change, media download, service, application
build, package operation, signing or release step is present.

The account needs existing KVM access; neither account creation nor dependency
installation happens here. The reviewed temporary-runner setup remains on #73's
branch for later approval; it is deliberately not imported into this PR.

## Focused CI and review evidence

mint-host-inventory-checks.yml runs static/unit policy checks and actionlint on
GitHub-hosted Ubuntu only. It cannot select the spare runner or its environment.
Tests parse inline Python without executing it, exercise missing/partial flags,
wrong events/repos/refs/SHAs, and assert a fixed read-only subprocess command.
They also verify installer CI is skipped only for exact infrastructure paths.

main's existing CI otherwise builds installers automatically, so the existing
scope classifier gains an exact seven-file infrastructure allowlist. PRs containing
any application/unknown path still require normal CI. A main push skips application
CI only when its complete before/after diff contains exclusively these exact
infrastructure files. Missing/malformed/deleted/mismatched push metadata or failed
diff cannot skip. Release refs and manual application dispatch are unchanged.
No application workflow steps/triggers or package policies were transplanted
from #73. This narrowly avoids installer preparation both for this PR and a
future authorized infrastructure-only merge.

No native runner enforcement, host execution, authentication or cleanup has been
validated by these static checks. Historical #72 research failures remain intact.

References:
- https://docs.github.com/en/enterprise-cloud@latest/actions/how-tos/manage-runners/self-hosted-runners/manage-access
- https://docs.github.com/en/rest/actions/self-hosted-runner-groups

## Spare Mint inventory closeout: observed evidence

The inventory session completed on October 17, 2026, at 9:46 p.m.
America/New_York. The host remains a spare physical machine; a disposable Mint
**guest** has not yet been created or validated. The earlier hosted-Ubuntu
inventory's unavailable KVM result is a different environment, not a contradictory
result or a failure repaired by this session.

| Item | Evidence and scope |
| --- | --- |
| Approved source | main commit `28fb4d058e0e3ec363a1b03d715d56342f457795` |
| Successful run | [39085486766](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39085486766), workflow_dispatch, completed/success; no rerun |
| Successful job | `117551015842`, inventory, success; October 17, 9:45:56–9:46:00 p.m. America/New_York |
| Actual execution identity | GitHub job API: runner `sde-mint-spare-once`, runner ID 195, group `sde-mint-isolated`, group ID 3 |
| Job boundary | Setup, fixed read-only inventory, completion all succeeded. Reviewed source rejects root, requires KVM API 12, checks Mint 22.3, and invokes QEMU --version. No checkout, guest creation, native installer or application/package build |
| Raw stdout limitation | Actions log download endpoint returned Forbidden. Job success/source contract is verified; exact emitted JSON was not independently retrieved. Do not invent a captured report or QEMU version from missing logs |
| Host versions/resources | User separately reported Mint 22.3 Cinnamon, Intel i5-7500T/4 CPUs, about 15 GiB RAM/199 GiB disk free, KVM API 12, QEMU 8.2.2. These are user terminal observations, not extra fields measured by this four-second inventory |
| Local runner teardown | User terminal: job Succeeded; Removed .credentials; Removed .runner; runner listener exit 0; Exiting runner. This proves reported local teardown, not erasure of all host artifacts |
| Remote deregistration | User checked the group page and confirmed the runner is no longer listed. Organization runner APIs return 403 to this integration; remote removal is administrator-observed, not independently API-attested |
| Activation disabled | User confirmed MINT_RUNNER_ENABLED=false. Variables API returns 403; this is user-attested, not independently read back |
| Extra dispatch | [39087384990](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39087384990) existed in waiting state, attributed to rdpollard. Codex cancelled it before execution; API now says completed/cancelled. Its cause was not established. Exactly one inventory job executed; two dispatch records exist |
| Approval restoration | Environment API now reports prevent_self_review=true, required reviewer rdpollard, can_admins_bypass=false; branch-policy API reports the sole rule main/type branch |
| PR/release state | #73 remains OPEN/draft at 22c724dfdb28a923dda6b0ed9c2b14e66957941b. No guest, application build/package/release workflow was dispatched during this session |

### Single-reviewer exception and its closure

The API dispatch was attributed to rdpollard, who was also the only required
reviewer. Prevent-self-review therefore blocked the initial approval. The owner
explicitly authorized a temporary one-run exception for this fixed inventory.
Codex's environment-update request returned 403; the owner changed the checkbox
and approved the waiting run. No administrator-bypass setting was enabled.
The owner has now restored prevent-self-review and Codex verified restoration
through the environment API. Do not describe this run as independently reviewed:
it used an expressly approved single-operator exception. That exception has ended
and does not authorize self-review for any future run.

No runner is to be restarted/re-registered and no workflow is to be dispatched
under the closed inventory authorization. The remaining runner directory,
downloaded archive, logs, dedicated account and kvm group membership were **not**
deleted. No service was installed by the reviewed instructions. Full host cleanup
or retirement of that account remains a separate scoped operation if needed.

Diagnostic inventory: **Pass**. Intended local teardown: **reported Pass**.
Remote runner deregistration: **administrator-confirmed**. Whole-host cleanup:
**NotRun**. Media authentication, working guest console, GUI/cgroup handoff,
privileged updater authentication and guest tests: **NotRun/unproven**. Production
readiness remains false. Preserve W2h's counterexample, W2i–W2l limited results,
W2m's immediate cleanup failure, W2n N1/N2 NotRun and the managed-filesystem ACL
EOPNOTSUPP result; this inventory neither resolves nor supersedes them.

## Next bounded phase: media authentication and offline console preparation

Status: reviewable proposal only. No helper/workflow implementation, media
acquisition, disk creation, runner registration/start or dispatch occurs in this
documentation step. Actual desktop installation/boot and updater validation need
later explicit authorization. Keep #73 draft and unmerged.

### P1: authenticate one Cinnamon ISO on the spare host

Prepare a fixed-purpose helper and its mocked tests before authorizing native
execution. Adapt host preflight explicitly for the actual **Mint 22.3 host**;
the historical Ubuntu-only preflight would reject it and must not be passed by
relabeling the host. The media verifier can reuse its signature/digest contract
without importing production updater code or pretending the host is Ubuntu.

Future execution, only after a separate review/authorization:

- Run as the dedicated non-sudo account in a new mode-0700 directory under
  `$HOME/mint-validation/<run UUID>`. No personal home traversal, shared writable
  directories, sudo, service registration, package manager or remote shell input.
- Recheck owned path ancestry, Mint release, architecture, trusted fixed tool
  paths, KVM API 12, at least 6 GiB available RAM and 40 GiB free disk. Record the
  host OS as Mint, separately from the intended Mint guest. Unsupported facts
  stop without permission fallbacks or dependency installation.
- Retrieve only the official Mint 22.3 signed checksum list, detached signature,
  and `linuxmint-22.3-cinnamon-64bit.iso` from one reviewed fixed HTTPS mirror:
  `https://mirrors.kernel.org/linuxmint/stable/22.3/`. Verify a bounded redirect
  chain stays on the reviewed HTTPS host; no user URL, unsigned alternate or
  quiet mirror substitution. Actual spare-host connectivity is unproven. The
  Codex workspace's earlier mirror 403 remains a separate access limitation.
- Use the reviewed repository key `tests/fixtures/linuxmint-iso-signing.asc`,
  bound by reviewed source SHA and file hash. Require primary fingerprint
  `27DEB15644C6B3CF3BD7D291300F846BA25BAE09`, successful detached-signature
  validation in a fresh private keyring, disabled automatic key retrieval,
  exactly one canonical Cinnamon checksum entry and no unexpected signature.
  Reject signature errors and revoked/expired keys. The pinned fingerprint is
  the trust anchor; do not modify ambient ownertrust merely to silence warnings.
- Freeze the digest from authenticated metadata, then stream-hash the complete
  regular ISO and require equality. Never substitute the Xfce pin. Stop before
  any extraction/boot on signature/digest/edition/size mismatch. Do not invent a
  Cinnamon pin now: it has not been authenticated or downloaded in this step.
- Maximum key/checksum files 64 KiB each, signature 8 KiB, ISO 6 GiB; one transfer
  at a time; 20-second connection, 60-second metadata and 15-minute ISO deadline,
  at most one attempt each. Stop on a partial transfer; quarantine its owned
  partial file instead of treating it as media. No resume/retry/mirror tuning
  in this first bounded run. Reserve at most 8 GiB actual storage in its owned
  workspace and check size while receiving, not only after download.
- Seal complete media read-only within the private workspace. Record byte size,
  actual SHA-256, key/metadata/signature hashes, accepted signing identity, source
  URL, tool versions, and verifier/source hashes. Revalidate immutable identity
  and bytes before a separately authorized future boot. A read-only mode alone
  is not tamper-proof against the owning account.

Pass means one cryptographically authenticated Cinnamon ISO and bounded durable
verification evidence. A downloaded file, successful HTTP response or a website
checksum alone is not a pass. Failure stops P2; preserve bounded reasons and
ownership evidence. No broad deletion of an uncertain workspace.

### P2: offline console launch plan, without starting QEMU

After P1 passes, prepare only a validated manifest/argument plan. No QEMU process,
VM disk, user account, polkit policy or guest credentials are created in this
phase. A future launch must revalidate the plan and receive separate permission.

- Guest plan: Mint 22.3 Cinnamon, KVM only, 2 vCPUs, 4 GiB RAM, 30-GiB virtual
  disk on ext4 when installed, standard QEMU identity plus a new run-bound UUID.
  Host resources remain independent; no TCG/container/chroot substitution.
- Console/control plan: VNC and optional QMP **Unix-domain sockets only**, below
  the run-owned mode-0700 directory, accessible only to the dedicated account.
  Validate QEMU Unix-socket path-length bounds before producing a plan. No
  public/loopback TCP listener, SPICE clipboard, USB/host-device passthrough,
  host filesystem share, network monitor, generic shell or reusable password.
  The launch plan has no guest NIC; network enablement is a later decision.
- The intended controller runs as that same account in a future approved runner
  job and talks only to this owned console/control socket. It must bind process
  identity and UUID, constrain commands and bound/redact evidence. This is a
  proposed controller boundary, **not a controller implemented or proven today**.
  A real Cinnamon login/polkit agent and safe mentor-password entry cannot be
  asserted from an offline plan or replaced with fake session variables.
- Validate paths, no symlink replacement, collision refusal, exact allowed argv,
  no arbitrary config includes/extra QEMU args, media identity binding and a
  future owned-process cleanup plan. If a secure controller or host-display
  approach cannot be established, stop before boot; do not expose VNC publicly
  or borrow ryan's desktop credentials/authority as a convenience fallback.

P2 pass means a reviewed offline manifest with no execution effects. A usable
console remains **NotRun** until separately authorized launch/controller checks.
Ownership cleanup for preparatory files is separate from runner deregistration
and future guest/process cleanup.

### Workflow and approval gates before any future execution

Implement/review helpers and local mocked checks first, using no real network,
GPG process, QEMU, runner or guest in those tests. Then a separate infrastructure
PR can propose a clearly named fixed-purpose `mint-media-console-prep.yml`.
It must not quietly expand the historical inventory workflow into a downloader
or VM launcher. No dispatch input may select commands, URLs, refs or extra args.

Only after its separate review/merge authorization may the administrator replace
the group's sole selected workflow with that exact new workflow at main, verify
the reviewed SHA and approval environment, and authorize a fresh ephemeral
registration/start plus one dispatch. Do not broaden the group to all workflows.
Leave ENABLED=false until those gates pass; main changes invalidate the old
approved SHA. Evidence must name the actual executed source SHA, account/group,
run/job ID and all report-source limitations.

The single-reviewer limitation must be handled **before** dispatch: either an
independent permitted reviewer is available, or the owner explicitly approves a
new narrowly scoped, temporary self-review exception. The past exception is not
reusable consent. Require owner confirmation of the protected environment's
approval, restore prevent-self-review immediately after approval, disable
activation after the job, and verify deregistration again. Inspect for an
unexpected second dispatch; cancel any unapproved waiting duplicate before
runner startup. No automatic workflow rerun or re-registration on failure.

Proposed whole-job limit: 25 minutes, including at most four bounded metadata/key
inputs and one ISO transfer. Export only a sanitized report <=64 KiB plus an
explicit ownership manifest; no passwords/tokens, keyring private state, raw
runner diagnostics, browser session data or ISO artifacts. Mirror/signature,
storage/time bounds, changed ownership, controller ambiguity, unexpected network
or package/guest activity, or failed evidence persistence are stopping conditions.

Current authorization ends with this preparation. It does not cover implementing
or executing that workflow, creating a VM, guest package operations, updater
fixtures, installed SDE changes, application builds/signing/releases or #73 merge.

## Isolated helper implementation and local review

The preparation-only proposal above now has isolated helper code; no executable
entry point or workflow has been added. These modules are test infrastructure,
not production updater code:

- `tests/mint_media_console.py`: Mint-specific host gates, approved source/helper
  bindings, pinned public-key hash, bounded transfer orchestration, strict GPG
  status validation, exact Cinnamon selection, sealed-file read-back hashing,
  stopped-run evidence and an offline console manifest. It does not launch QEMU.
- `tests/mint_media_native.py`: explicitly constructed future native ports for
  secure run-owned files, read-only host collection, fixed curl/GPG subprocesses
  and bounded process/descriptor handling. Imports do not perform I/O. There is
  no CLI, default activation, generic shell, package/runner executor or QEMU
  launch method. Only curl and GPG are in the process allowlist.
- `tests/test_mint_media_console.py`: in-memory orchestration tests and mocked
  native adapters. Synthetic ISO bytes, detached-signature placeholders and GPG
  status records are explicitly fixtures, not real authentication evidence.

A future reviewed caller must collect actual host facts before workspace creation,
validate the reviewed source SHA and helper hash against trusted approval values,
supply the reviewed key bytes, and construct the ports explicitly. The helper
compares those bindings; it does not independently establish Git provenance from
arbitrary caller-supplied strings. Use Workspace as a context manager and propagate
all close/cleanup exceptions. No such native caller is shipped in this step.

Review fixes made before completion:

- curl's first option disables ambient curlrc; redirects are handled explicitly,
  never followed by curl. HTTPS/proxy/CA settings are preserved without logging
  credentials. Fixed-origin/path redirects are limited to three; HTTP failures,
  oversized/ambiguous headers, body-length mismatch and unexpected encoding stop.
- Private GPG snapshots and a fresh keyring avoid interpreting a different
  downloaded metadata pathname after signature verification. No ambient options,
  auto key retrieval or autostart; the signer must match the pinned primary
  fingerprint. Unknown ownertrust is not replaced with manufactured trust.
- File identity/owner/mode/link checks, exclusive creation and collision refusal
  precede writes. Transfer bounds are enforced before writing; received bytes
  and sealed-file read-back hashes must both match. Final ISO publication never
  overwrites an existing pathname. Failures retain unpromoted partial files.
- Root directory identity excludes the link-count change caused by creating its
  own GPG child directory; inode/device/owner/mode replacement still stops.
  Directory inventories are bounded while iterating, not after an unbounded list.
- Selector-initialization failure still reaps the owned tool child. Deadlines,
  output overflow and uncertain process cleanup close the pipe/selector and
  attempt cleanup of that child only. There is no installer/guest kill path.
- Context-manager close attempts all tracked descriptors once, reports uncertain
  closure and never retries a possibly reused descriptor number. Manifest-write
  failure or failed failure-evidence persistence cannot return preparation Pass.
- Console paths are canonical and argument-safe, sockets fit the Unix length
  bound, and disk/socket collisions stop. The generated fixed argv has no NIC,
  public socket, shared filesystem, SPICE or arbitrary extra configuration.
  It is a proposal requiring fresh validation and authorization before any launch.

Local QA: **36 mocked helper checks + 9 CI-scope checks + 3 existing inventory
policy checks passed**. Python syntax/AST and staged whitespace checks passed.
Mock coverage includes healthy orchestration, source/key/platform/privileged-group
rejection, signer/expiry/duplicate metadata rejection, redirect limits, partial
and corrupt transfers, deadlines/size bounds, disk read-back corruption,
ownership replacement, socket injection/collision, fsync/manifest failure,
selector failure, descriptor/process cleanup uncertainty and Mint host collection
with all file/KVM operations mocked. No real download, GPG/curl process, ioctl,
owned-native-filesystem experiment, QEMU process or spare-host action was run.

Remaining gates and limits:

1. Native mirror/TLS/proxy behavior, actual Mint GPG status/keyring filenames,
   signed Cinnamon digest, host tool ancestry/dependencies, ext4/fsync/link
   behavior and real child cleanup are unvalidated. Stop on unsupported behavior;
   these mocks do not establish cryptographic or kernel correctness.
2. Isolation assumes the dedicated account and reviewed helper/caller are trusted.
   This is not a defense against malicious same-UID processes or a compromised
   root host. chmod/read-back/identity checks are not immutable hardware attestation.
3. Deadlines bound owned tool processes and checked stages; blocking filesystem
   calls cannot be claimed hard-real-time. A future workflow needs the independent
   25-minute bound and must treat interruption as an uncertain, non-resumable run.
   GPG keyring growth is monitored/audited (1 MiB, fixed known public key), not
   enforced by a filesystem quota. No kernel-level storage-reservation claim.
4. No secure console controller, guest installation, real login/polkit interaction
   or guest cleanup has been implemented. The offline plan is not console proof.
5. Infrastructure integration adds only the three exact helper/test paths to the
   existing CI scope exception. Hosted Ubuntu automatically runs static policy
   checks and mocked helper tests; it never invokes the native ports. Both PR and
   main-push path filters include these files. The signing-key fixture also
   triggers these checks, but remains outside the installer-skip exception.
   Unknown paths and mixed application changes retain application CI. The fixed
   spare-host inventory workflow and its activation gates are unchanged. This
   infrastructure PR must remain unmerged pending review; it authorizes no native
   media or host operation.
6. The next implementation-integration step must preserve fresh explicit approval
   for any runner registration/start, dispatch or self-review exception. ENABLED
   remains reported false; #73 remains draft/unmerged. Application/native-package
   workflows, guest tests, build/signing/release work remain deferred.

Diagnostic result: local mocked checks Pass. Native media authentication: NotRun.
Native cleanup correctness/authentication safety: unproven. Whole-host cleanup:
NotRun. Production readiness: false. Historical #72 failures remain preserved.
