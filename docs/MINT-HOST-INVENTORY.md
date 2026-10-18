# Spare Mint host inventory: disabled infrastructure only

## Current approval policy — sole maintainer

The owner authorizes the sole maintainer, rdpollard, to approve their own
mint-host-access runs. This standing policy supersedes earlier temporary
self-review-exception and restoration instructions in historical evidence below.
One-time administrator change: uncheck **Prevent self-review** for this repository's
mint-host-access environment and save protection rules. Leave it unchecked;
Codex must not request re-enabling it without a concrete, material reason.

Keep rdpollard as a required reviewer, administrator bypass disabled, and the
sole deployment branch rule main. Self-approval remains an explicit approval of
the exact queued job, source SHA and bounded operation; it does not authorize
runner registration/start, dispatch or native operations by itself. Retain the
selected-repository/exact-workflow runner-group restrictions, reviewed SHA/hash
bindings, first-attempt-only checks, disabled-by-default activation and fresh
single-job ephemeral runner requirements. No checkbox toggling is part of run
setup or closeout. After each authorized job, disable activation and verify
local credential cleanup and remote deregistration separately.

This policy change authorizes no activation or execution. Historical reports of
prevent_self_review=true remain accurate records of earlier observations, not
instructions for the current setup. Recheck live settings before an authorized
run; a user-reported change is distinct from independent API verification.

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
3. Environment `mint-host-access` already exists, has required reviewer
   rdpollard, allows self-approval, permits main only, has no secrets, and disables
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
and did not authorize future self-review at that time. The current standing
sole-maintainer policy above now supersedes that restriction.

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

Before dispatch, verify required approval by rdpollard with self-approval allowed.
Require explicit approval of the exact protected-environment job, disable
activation after the job, and verify deregistration again. No temporary
self-review exception or checkbox restoration is needed. Inspect for an
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
   for any runner registration/start or dispatch. Required environment approval
   permits sole-maintainer self-approval under the current policy. ENABLED
   remains reported false; #73 remains draft/unmerged. Application/native-package
   workflows, guest tests, build/signing/release work remain deferred.

Diagnostic result: local mocked checks Pass. Native media authentication: NotRun.
Native cleanup correctness/authentication safety: unproven. Whole-host cleanup:
NotRun. Production readiness: false. Historical #72 failures remain preserved.


## PR #76 review

Review found and fixed an untracked descriptor leak when `Workspace.create`
fails its initial `fstat`/ownership inspection. Rejection now closes the descriptor
once before propagating failure; a failed close explicitly reports cleanup
uncertainty. Mocked fault checks cover inspection failure, ownership rejection,
and close uncertainty. Actual application-workflow gate/output/dependency checks
were added so path classification alone is not treated as installer-skip proof.

The preparation policy job runs static/mocked checks only on hosted Ubuntu.
Separately, changing `tests/ci_scope.py` triggers the pre-existing Native UAT
fixture workflow: Windows filesystem/ACL checks and a hosted Mint-userland
container job, including its existing media preparation/dependency installation.
Those are not mocked-only checks and are not spare-host or guest-desktop proof.
No new native workflow or native operation is introduced by this PR. Application
installer jobs and release jobs are independently gated and were observed skipped.
The older fixture workflow's automatic native scope is unchanged; it must not be
confused with authorization to run the new preparation helpers.

No native helper activation, spare-host access, guest boot or application packaging
was performed in this review. Both #73 and #76 remain draft and unmerged.

## Explicit native-fixture dispatch boundary

PR #76 now supersedes the trigger-only assessment above. The legacy fixture
workflow keeps its existing PR/push path filters, but automatic events can reach
only `workflow-checks` (hosted Ubuntu checkout and actionlint). Both native jobs
require the canonical repository, `workflow_dispatch`, and the typed boolean
`run_native == true`; the required input defaults to false. They depend on a
successful static job. Missing/false input, PR/push events, workflow calls and
fork repositories cannot enable native jobs. No dispatch was performed.

This job boundary applies even when an infrastructure PR edits the native
workflow itself, so publishing the boundary does not launch the old media/package
steps. Manual native checks retain their existing Windows/Mint fixture semantics,
including Mint media acquisition, extraction, container dependencies and cleanup;
none are moved into the automatic job. They are not application installer builds,
spare-host validation, or guest-desktop tests. A future operator must separately
authorize those native operations before selecting the opt-in input. The manual
entry point becomes available on the default branch only after an authorized
merge; both current PRs remain unmerged.

The exact native-fixture workflow path is also included in infrastructure-only
main-push classification, preventing installer packaging after a future authorized
infrastructure-only merge. Unknown/application/signing-key paths still retain
application CI. The policy workflow watches and lints this gate file on PR/main,
and tests enumerate event/repository/boolean combinations, verify static-only
steps and successful-static dependencies, and inspect actual installer gates.
No self-hosted runner, environment activation or application workflow was changed.

Local validation: 55 checks passed (38 mocked helper, 9 scope, 8 policy), focused
actionlint and diff whitespace checks passed. This establishes local policy and
mocked coverage only; native preparation-helper authentication/cleanup/console
claims remain unvalidated. Historical fixture success and #72 findings remain
historical evidence, not proof of the new preparation helpers.

## Prepared manual media/console workflow (not activated)

The separately prepared `.github/workflows/mint-media-console-prep.yml` uses the
merged helpers through `tests/run_mint_media_console.py`. This section supersedes
the earlier proposal's “no caller/workflow” status only. Preparation does not
authorize publication/merge, runner registration/start, settings changes,
dispatch, media acquisition or guest execution. #73 remains draft/unmerged.

The workflow is manual-only, takes no dispatch inputs, has contents-read-only
permissions, and shares the non-cancelling `spare-mint-host` concurrency group.
Its sole 25-minute job selects `org/sde-mint-isolated` with routing label
`sde-mint-prep`, and requires the `mint-host-access` approval environment.
Labels are not authorization. Before any separately authorized execution, an
administrator must replace the runner group's sole selected workflow with
`stormbots/Tactics-Strategy-Dev-Environments/.github/workflows/mint-media-console-prep.yml@refs/heads/main`,
retain selected-repository access only to this repository, verify public-repo
and branch protection settings, and verify the environment's main-only deployment
rule, required reviewer and administrator-bypass policy. No such settings were
changed by preparing this workflow. The old inventory allowlist is not sufficient
to execute the new workflow, and must not be broadened to all workflows.

Independent disabled-by-default gates (none configured in this preparation):

- `MINT_PREP_ENABLED` must be exactly `true`.
- `MINT_PREP_ACCESS_READY` must be exactly `verified`, after live control review.
- `MINT_PREP_APPROVED_SHA` must equal the reviewed main commit being dispatched.
- `MINT_PREP_HELPERS_SHA256` must be the independently reviewed source-bundle hash.

Unset values prevent scheduling. Inventory activation variables cannot activate
this job. The event/repository/ref/workflow-ref must be the fixed manual main
workflow, workflow SHA must equal source SHA, and run attempt must be 1. A rerun
is refused; an authorized retry requires a new reviewed dispatch/owned run.
The environment reviewer must inspect the exact queued commit and operation.
The required reviewer may approve their own run under the standing sole-maintainer
policy; PR approval settings do not waive required environment approval. Leave the
runner absent and all preparation flags unset/disabled until those gates pass.

The checkout is pinned to `github.sha`, does not persist credentials, and disables
submodules/LFS. The caller runs under `/usr/bin/python3 -I -B`, with no CLI args.
Before loading native ports it verifies the fixed Actions context and five
bounded regular non-symlink source snapshots (caller, core, native ports, local
launcher, public signing key), rejecting writable/untrusted ancestry and changing identities.
The bundle framing is `SHA256(b'mint-prep-bundle-v1\0' + each fixed path's ASCII
name + NUL + ASCII decimal byte length + NUL + raw bytes)`, in the `SOURCES` order
in the caller. It compiles only the approved helper snapshots, not a second
pathname import; preloaded helpers are rejected. Approval values must come from
independent review of the merged source, never from the running job blessing its
own files. The bundle hash is not a cryptographic signature or a defense against
malicious same-account/root code modifying the caller before it starts.

Mint host collection and the merged host/resource gates precede exclusive
workspace creation. The existing one-mirror signature/digest/ownership/size/
deadline/stop rules remain unchanged. A fresh UUID binds the private retained
workspace to the run. Neither QEMU nor a disk/package/service/runner executor is
called. The offline plan is data only; guest readiness remains unproven.

After durable helper report/ownership persistence, the caller reads back the
bounded run-bound ownership manifest and closes owned descriptors before emitting
one JSON export of at most 64 KiB. It includes source/bundle hashes, actual host
facts, Actions run/attempt IDs and fixed job name, report and manifest. No ISO/keyring/raw tool
output or artifact glob is exported. Sanitized failure output identifies the run
UUID once allocated and marks cleanup NotConfirmed. Partial workspaces remain
private for investigation; no recursive deletion, resume or mirror substitution.
Helper completion, successful workflow export, descriptor/process cleanup,
runner deregistration and whole-host restoration are separate outcomes.

Remaining native gates: real checkout permissions/tool ancestry, Mint/GPG/curl
compatibility and mirror access, actual signature/digest/owned filesystem behavior,
export/log retrieval and cancellation/owned-child cleanup are not validated by
mocks. GitHub timeout or forced interruption can leave uncertain state; filesystem
calls are not hard-real-time and no SIGKILL cleanup guarantee is claimed. Stop
and preserve uncertainty; do not automatically retry or start another runner.
Actual console/controller/guest tests require later authorization.

Automatic preparation CI adds only this exact workflow/caller/test to its watched
paths and installer-skip exception, and lints the new workflow. It runs the new
mocked driver/gate tests; native fixture jobs remain dispatch-gated. No production
or active inventory workflow changes are included.

Workflow preparation review evidence: **74 local checks passed** (38 existing
helper mocks, 19 caller/workflow checks, 8 policy checks, 9 scope checks), plus
focused actionlint and whitespace checks. The approved-snapshot loader was checked
with actual helper definitions while native open/ioctl/socket/process entry points
were denied; this is import/definition coverage, not native execution proof.
Fault cases cover wrong/missing context, reruns, source tampering/ownership and
bounds, helper preloading/partial-load restoration, host rejection, preparation
failure, ownership/export bounds, close uncertainty and sanitized error output.
No helper activation, media download, KVM access, GPG/curl process, QEMU process,
runner operation, workflow dispatch, application build/package/release or #73
merge was performed. Publication and a separate infrastructure PR remain a next
review step; the prepared workflow is not present on main yet.

### Local caller/workflow review follow-up

The local review found and fixed these caller issues before publication:

- TERM/INT previously had default process behavior and could bypass Python
  unwinding. The fixed main entry point now temporarily installs a first-request
  interruption guard, restores prior handlers on exit, and refuses success after
  any recorded interruption. Further TERM/INT requests return while the initial
  exception unwinds, rather than disrupting owned cleanup. Failure output retains
  an independent interruption flag even if a helper translates the exception.
  Handler installation/restoration failures stop; restoration uncertainty prevents
  success export. Tests invoke captured mock handlers, never send real signals or
  install handlers on the testing host.
- Source traversal could leak the newly opened next descriptor if closing its
  parent failed. Every opened descriptor is now tracked immediately, close is
  attempted once without retry, remaining descriptors are still attempted, and
  any ambiguous close produces SOURCE_CLEANUP_UNCERTAIN.
- Ownership export could accept a valid JSON prefix from a short read. It now
  bounds the recorded file size before reading, requires exactly that many bytes
  and unchanged size afterward, rechecks owned identity and requires a JSON object
  bound to the run. Size bounds reject before allocation/read.
- Error reporting could fail when a preloaded helper lacked a valid Stop class.
  The sanitizer now verifies exception-type identity before inspecting controlled
  reason codes and never substitutes arbitrary exception text for a reason.

The workflow's disabled activation, protected environment, exact workflow/main
source approvals, restricted runner group, no-input interface, no-rerun gate,
resource bounds and installer-skip rules remain unchanged. Source bundle approval
must be recomputed from the final reviewed/merged caller, not a previous candidate.
No approval variables or runner/group/environment settings were changed.

QA: **84 local mocked/static checks passed** (38 existing helper checks,
29 caller/workflow checks, 8 policy checks, 9 scope checks), focused actionlint and
whitespace checks passed. Added fault coverage includes parent/final descriptor
close failure, partial/changing manifests, malformed preloaded modules, handler
partial installation/restoration failure, repeated interruption during cleanup,
helper exception translation and suppressed-interruption false-success control.
The 74-check result above records the earlier candidate, not this revision.

Remaining proof gates are unchanged: no actual signals, child processes, KVM,
network/media, GPG, owned native filesystem run or GitHub cancellation was exercised.
SIGKILL, interpreter failure, cancellation grace periods and blocking filesystem
calls can still leave uncertain state. Graceful-unwind mock success establishes
neither actual process cleanup nor authentication safety. Reports, file retention,
runner deregistration and whole-host restoration remain separate outcomes; no
forced-interruption cleanup guarantee or production-readiness claim is made.
Publication and activation remain deferred, as do runner operations, workflow
dispatch, guest work, #73 merge, application builds, packages and releases.

### PR #77 security/stopping/CI review

Review found that the reused curl/GPG process environment dropped
`RUNNER_TRACKING_ID`. Because owned children start a new session, retaining the
runner's opaque job-tracking marker helps preserve GitHub's separate best-effort
orphan cleanup path if the caller is forcibly terminated. The fixed allowlist
now forwards that marker only when present, without logging it or adding it to
command arguments. It remains cleanup metadata, never an authentication or
runner-group authorization boundary. Proxy/CA settings are still preserved;
GitHub tokens, SSH agent settings and dynamic-loader injection variables are not
inherited. This changes only the test-infrastructure native port, not production
updater code. The caller bundle includes this port, so the final independently
approved bundle digest must include the fix.

QA: **86 local mocked/static checks passed** (39 helper checks, 30 caller/workflow
checks, 8 policy checks, 9 scope checks), focused actionlint and whitespace checks
passed. The two additional checks use a fully mocked child environment/process
and a synthetic handler invocation reaching the real owned-child cleanup logic;
no process is spawned and no signal is sent or installed. Both present and absent
tracking-marker cases preserve the limited environment. The synthetic termination
checks owned kill/wait/stdout/selector cleanup calls; they do not establish kernel
or GitHub cancellation behavior.

Dispatch controls, settings and workflow definitions are unchanged by this review.
The full PR remains confined to exact infrastructure paths; automatic validation
is static/mocked, with native fixture and installer/release jobs dispatch/scope
controlled. Remaining execution gates include live runner-group/environment
verification, fresh exact main SHA and bundle approval, ephemeral single-job
registration, explicit dispatch authorization and native media/cancellation/
filesystem/export validation. SIGKILL, missing tracking metadata, runner failure
or blocking calls can still leave uncertain state. Authentication safety, process
cleanup, runner deregistration and whole-host restoration remain distinct.
Both #73 and #77 remain draft/unmerged; activation, runner operation, dispatch,
downloads, guests, application builds, packages and releases remain deferred.

## SOURCE_OWNER checkout-creation fix (proposal; no host changes)

The stopped run 39099802574 at 05a8142 remains a failure. Owner-provided `id` and
`namei -l` evidence showed correct sde-runner UID 1001 ownership, but group-writable
`_work`, repository ancestors and `tests` (0775), plus caller file 0664. Root/home
ancestors and the dedicated account/session were not group-writable. SOURCE_OWNER
was therefore the intended rejection, before native helper loading, workspace
allocation or media work. No claim is made that source permissions were the only
remaining native gate. The failed checkout remains unchanged as evidence.

### Narrow remediation boundary

Prevent shared-write creation in a NEW session rather than chmod/chown the failed
checkout, accept shared groups, copy unverified mutable code into a trusted path,
or relax read_source. `tests/start_mint_preparation_runner.py` is a future LOCAL
listener launcher, never a workflow step or automatic CI command. It sets umask
0077 before executing the fixed trusted runner run.sh, so the listener, worker,
checkout action and git inherit the restrictive creation mask. Setting umask only
in the later preparation step is too late to protect checkout's ancestors.

The launcher requires the dedicated non-sudo account, a fixed new session below
its passwd home (`mint-prep-runner-private-session`), mode-0700 session and empty
mode-0700 `_work-private`, root/current-user-owned non-writable ancestry without
symlinks, no inherited default ACL on session/work root, an owned non-writable
regular executable run.sh, and bounded private .runner configuration selecting
`workFolder: _work-private`, `ephemeral: true`, `agentName: sde-mint-prep-once`, and
`gitHubUrl: https://github.com/stormbots`. The config is not an authorization
boundary: group restrictions, exact approved workflow/SHA, protected environment,
and one-run approval remain mandatory. It never reads registration credentials.
Configuration field names were checked against actions/runner v2.338.0's
Runner.Common/ConfigurationStore.cs; native serialization remains a proof gate.

It exposes no arguments, registration, download, install, chmod, chown, ACL repair,
recursive traversal/deletion or generic shell action. Wrong modes, default ACLs,
symlinks, a reused work root, changed configuration, wrong account or unexpected
runner settings stop instead of silently fixing state. ACL inspection uses the
Python standard library; unsupported/denied inspection stops without installing
utilities. Settings reads are bounded, reject duplicate JSON fields/change/short
reads, and close once; uncertain close cannot pass. A failed preflight/exec restores
the launcher's earlier umask. Successful exec carries 0077 into the listener.

### Future preparation sequence — NOT authorized by this PR

1. After separate review/merge and a new execution authorization, independently
   bind the new main SHA, source bundle and this local launcher's exact file hash.
   The caller's bundle now includes FIVE fixed source files, adding the launcher
   before the public key in SOURCES. The old packet/hash/run is not reusable.
2. Revalidate the approved runner archive and prepare a fresh dedicated session
   named mint-prep-runner-private-session with umask 0077 and exclusive 0700
   creation. Create an empty `_work-private` there with mode 0700. If either
   already exists, stop; do not overwrite/reuse/remove it. Do not touch the old
   mint-prep-runner-session/_work or its failed checkout.
3. Register one ephemeral runner using the reviewed interactive token prompt
   (never token in argv/history/chat), same restricted group and sde-mint-prep
   label, with `--work _work-private`, in that fresh session under umask 0077.
   Verify the actual private configuration/schema and group while offline.
4. Deliver the approved launcher as a separately SHA-256-verified private regular
   file; do not depend on a checkout that has not happened yet or fetch mutable
   branch code at listener startup. The future start invocation is isolated
   `/usr/bin/python3 -I -B <verified-local-launcher>` with no arguments. Approve
   the exact waiting environment job using sole-maintainer self-approval before
   invoking it; do not toggle Prevent self-review. Do not bypass this launcher
   with direct run.sh or set a weaker umask for registration/listener startup.
5. Observe actual creation modes and strict source-guard results in the newly
   authorized bounded run. A runner/action resetting umask, unexpected ACL,
   serialization mismatch or any other native difference stops; never apply a
   recursive permission repair or weaken the source check as fallback.

No host command in this sequence was executed. Native inheritance through the
actual runner/worker/checkout, actual ACL/settings behavior and media/authentication
remain unvalidated. This is a proposed setup correction with fail-closed checks,
not a successful native rerun. Default ACL inheritance is explicitly rejected
because ACL-based creation can differ from the ordinary umask model.

### Local regression and CI review

97 mocked/static checks pass (39 existing helper, 30 caller/workflow, 11 new
launcher/permission checks, 8 policy, 9 scope), plus focused actionlint and whitespace
checks. Mocked launch tests observe 0077 at the exec boundary, model ordinary file
0600/directory0700 creation, verify earlier mask restoration on failure and assert
no exec for unsafe context. Inspection tests cover wrong owners, symlinks,
permissive modes, default ACLs, reused workspaces, registration drift, bounded/
short/duplicate settings and uncertain descriptor closure. The original source
reader still rejects the observed 0775 and 0664 modes without chmod.

Only the exact two new launcher/test paths join the existing infrastructure scope
exception and automatic mocked/static policy coverage. Native preparation, native
fixture and application/release workflow gates are unchanged. A mixed application,
key or unknown path retains application CI. Keep this infrastructure PR unmerged,
activation disabled, and runner operations, dispatch, media, guests, #73 merge,
application builds/packages/releases deferred. No source-guard permission rule was
relaxed and no spare-host permission was changed.

### PR #78 permission/security review follow-up

The review preserved the strict source-ownership policy and found three launcher
startup gaps, fixed before any native use:

1. Inherited BASH_ENV/ENV, shell option/function exports, NODE_OPTIONS and dynamic
   loader hooks could influence the script/worker environment before checkout.
   The launcher now uses execve with those hooks removed while retaining ordinary
   runner context and configured proxy/CA settings. This is launch-time filtering,
   not attestation or modification of a persisted runner .env file. Future runner
   configuration still requires a trusted clean shell, verified archive and fresh
   private session; malicious same-account/root changes are outside this boundary.
2. An unexpected FIFO or terminal at .runner could block or acquire terminal state
   before fstat rejected it. Opening now includes O_NONBLOCK and O_NOCTTY as well as
   O_NOFOLLOW/CLOEXEC; only a bounded owned private regular file can be read.
3. Failure while restoring the earlier umask could bypass structured failure
   reporting. Restoration is now attempted before the failure record is emitted,
   and any uncertainty is reported as UMASK_RESTORE_UNCERTAIN without exposing
   native exception text or retrying. Successful exec still never returns and
   retains the restrictive mask. An unexpected exec return fails explicitly.

QA: **102 mocked/static tests passed** (39 helper, 30 caller/workflow, 16 launcher/
permission, 8 policy, 9 scope), focused actionlint and whitespace checks passed.
New cases cover hook filtering with proxy/CA preservation, nonblocking special-file
rejection, mask restoration uncertainty, unexpected exec return, every disallowed
privileged group and effective-UID mismatch. All OS/process/mask operations in
these launcher tests are mocked. Workflow definitions and activation gates are
unchanged. Both infrastructure-only installer skipping and mixed app/key controls
remain checked, and the original source-reader function remains unchanged.

No actual umask inheritance, native runner/script/environment/settings/ACL behavior,
permission modification, startup, cancellation, authentication or cleanup is proven
by these checks. A future approved native run must still stop if a stored runner
environment or runner/action code changes creation policy. The failed checkout is
retained unchanged; no normalization or retry is authorized. The new launcher bytes
require a fresh independently approved file and five-file bundle hash after any
separately authorized merge. Keep #78 and #73 draft/unmerged; activation, runners,
dispatch, downloads, guests, application builds/packages/releases remain deferred.

## Fixed checkout-only validation added to PR #78

This addition prepares the next permission diagnostic only; no native execution
is authorized or performed. The earlier SOURCE_OWNER run remains a stopped
failure. #78 and #73 remain draft/unmerged, and the failed host checkout is
untouched. This diagnostic precedes any proposed media retry.

`.github/workflows/mint-checkout-validation.yml` has only workflow_dispatch, no
inputs, contents-read permissions, the existing non-cancelling spare-mint-host
concurrency group, protected mint-host-access environment, restricted
org/sde-mint-isolated group and routing label sde-mint-prep. Its observe job has a
10-minute limit and an identical pinned checkout step/configuration to the media
workflow; sparse checkout or different Git options are not substituted for the
permission-creation behavior under examination. Normal Actions/repository fetches
would occur in a future authorized run, but no ISO, package or development-tool
installation is included. Automatic events cannot schedule this observer.

New independent activation candidates, all left unset/disabled now:

- MINT_CHECKOUT_ENABLED=true and MINT_CHECKOUT_ACCESS_READY=verified.
- MINT_CHECKOUT_APPROVED_SHA equal to the separately reviewed final main SHA.
- MINT_CHECKOUT_BUNDLE_SHA256 equal to an independently calculated six-file bundle.

The event/repo/ref/workflow-ref must match this exact manual main workflow, source
and workflow SHA must match approval, and attempt must be 1. MINT_PREP_* values
cannot activate it. The observer rechecks the gates and accepts no arguments.
The existing media workflow and source guard are unchanged. A later authorized
execution must replace the group's sole selected workflow with
stormbots/Tactics-Strategy-Dev-Environments/.github/workflows/mint-checkout-validation.yml@refs/heads/main,
not add broad/all-workflow access. Selected repository, required-reviewer,
main-only and no-bypass controls, with sole-maintainer self-approval allowed,
must be verified independently. No controls or settings were changed here.

`tests/observe_mint_checkout.py` is standalone standard-library code. It neither
imports nor executes repository helper modules. It reads/hashes their bounded
source bytes as inert data, with root/current-user-owned non-writable ancestors,
no symlink/special-file substitution, identity/change checks and descriptor
closure. New private-session/checkout directories additionally must be owned by
the dedicated account with mode 0700 and no default ACL; source files must have
no group/other permissions. It reports fixed-path metadata before rejecting a
bad component, avoiding the earlier unlocalized SOURCE_OWNER diagnostic. These
are stricter diagnostic checks, not a relaxation of the preparation source guard.

The observer requires the dedicated non-privileged account on Linux x86_64 and
bounded root-owned Mint RELEASE=22.3 metadata. It reads only Umask from the fixed
/proc/self/status path (never changes umask or exports raw proc data), requires
0077, and verifies the expected private-session/_work-private repository location.
It records bounded UID/account/groups, actual path modes/owners/inode identities,
default-ACL presence, source sizes/hashes, Actions run/attempt/job name and SHA.
It creates no workspace/file/manifest and prints one sanitized JSON record <=64
KiB. File snapshots <=128 KiB each, host metadata <=8 KiB, proc status <=16 KiB,
path inventory <=32 and an observer budget of 30 seconds bound checked stages.
Blocking filesystem/account operations are not claimed hard-real-time; the
independent ten-minute workflow limit remains necessary. Cancellation or missing
export is unknown/failure, not permission-validation Pass or cleanup proof.

Bundle contract is deliberately independent of media preparation:
SHA256(b'mint-checkout-bundle-v1\0' + each ASCII path + NUL + decimal byte length +
NUL + exact bytes), in this fixed order:

1. tests/observe_mint_checkout.py
2. tests/run_mint_media_console.py
3. tests/mint_media_console.py
4. tests/mint_media_native.py
5. tests/start_mint_preparation_runner.py
6. tests/fixtures/linuxmint-iso-signing.asc

The media caller retains its separate five-file mint-prep-bundle-v1 contract.
Neither an old source approval nor one bundle hash substitutes for the other.
Approval must be calculated after any authorized merge, from final source bytes,
not self-approved by the running job. Local verified launcher delivery, new
private session/empty work root, fresh one-job registration, approved queued run,
manual listener start and deregistration remain separate authorization gates.
No existing registration, worktree or stopped run may be reused automatically.

Pass requires all source/identity/private-mode/ACL/mask/hash/context checks and
complete bounded export. Failure retains bounded offending metadata where
available and stops without repair, fallback or automatic retry. Every outcome
marks media authentication NotRun, guestExecuted=false, productionReady=false,
cleanupCorrectness=NotValidated and no whole-host cleanup claim. No GPG/curl,
KVM/ioctl, socket/network client, subprocess, package, disk creation, console,
guest, updater or build/release operation exists in this observer. Successful
permission observation would not authorize the media phase or establish its
cryptographic safety, process cleanup or usable console behavior.

Local review/QA: **118 mocked/static checks passed** (102 prior checks plus 16
observer/workflow cases), focused actionlint and whitespace checks passed. Cases
cover disabled/default/wrong approvals/events/refs/attempt/location/account,
mask/release/digest mismatch, original shared modes, symlinks/default ACL, short/
changed sources, close uncertainty, deadline, proc bounds, argument rejection,
failure sanitization/export size and six-file tamper sensitivity. Static checks
verify the identical pinned checkout and only observer command, no repository
imports or native execution ports. Only the three exact new workflow/observer/test
paths join automatic mocked policy coverage and installer-skip scope. Actual native
runner inheritance, filesystem/ACL/account behavior, log retrieval and closeout
remain unvalidated. Activation, runners, dispatch, downloads, guests, #73 merge,
application builds/packages/releases remain deferred.


### Checkout observer review follow-up

The observer now reports defaultAcl=null when no ACL query was completed, rather
than claiming absence on ancestors outside the private session. It retains the
failing directory's bounded mode/owner/identity metadata before querying ACLs,
and validates directory type/ownership/mode before that query. An ACL-query
error still stops with sanitized failure; it does not authorize a fallback or
source read. A checked private directory reports true/false as observed.
The fixed proc Umask parser now accepts horizontal whitespace only, rejecting a
malformed value on a different line.

Local QA: **121 mocked/static checks passed**, including added cases for failed
ACL-query evidence, unchecked ACL reporting, ancestry changes, the 32-directory
inventory limit, mid-read deadline closure without retry, and multiline Umask
rejection. No observer, listener, checkout action or host preparation was executed.
Approval gates and workflow commands are unchanged; group/reviewer/settings must
still be verified before separately authorized execution. These local results do
not validate native inheritance, ACL support, deregistration, cleanup correctness
or authentication safety. The stopped media preparation result remains unchanged.

## Checkout-only native evidence and next media proposal

### Completed checkout diagnostic (not media authentication)

Run [39132131036](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39132131036),
job 117689277573, executed observe once on source/workflow SHA
c8e0134a3de8f36981a83bea1546b5b9a9daf1d6, attempt 1. GitHub API confirmed success
and explicit environment approval by rdpollard under standing self-approval.
The owner supplied the observer JSON because integration log retrieval was denied.
It reports pass=true, reason=CHECKOUT_VALIDATED and bundle SHA-256
27689dc72c1b72d30a031ed1bbd807130c0a21ec4ae5bce54df3b718ba66f445.

Observed Mint 22.3 account sde-runner UID 1001, groups kvm/sde-runner/users,
effective umask 0077. All six fixed source files were owned by UID 1001 with
mode 0600 and expected sizes/hashes. The session, _work-private, repository
ancestors, tests and fixtures directories were UID 1001/mode 0700 with
no default ACLs. Root/home were root-owned 0755; the account home was UID
1001/mode 0750. ACL=null on those outer ancestors means unchecked, not absent.
This validates permission creation through this actual runner/worker/checkout
schedule; it does not prove every possible filesystem or runner configuration.
The earlier SOURCE_OWNER media failure is preserved as a separate stopped run.

Closeout evidence is deliberately separated:
- Owner terminal showed runner 2.338.0, observe succeeded, local .credentials
  and .runner removed, listener exit 0. This is terminal evidence, not a complete
  process/descriptor inventory or whole-host cleanup proof.
- Owner confirmed MINT_CHECKOUT_ENABLED=false. Variable API readback is unavailable
  to the integration; this is owner-attested, not independently verified.
- Remote sde-mint-prep-once remained listed after local exit. Owner manually
  removed it and confirmed absence. Do not claim automatic deregistration passed.
- JSON explicitly reports cleanupCorrectness=NotValidated,
  mediaAuthentication=NotRun, guestExecuted=false, productionReady=false and
  wholeHostCleanupPerformed=false. Permission diagnostic completion, cleanup
  correctness and authentication safety remain distinct.

No ISO, guest, package, application build or release operation was part of this
run. The private checkout and earlier failed media checkout remain retained.
PR #73 remains draft/unmerged. No follow-on execution is authorized.

### Proposed next bounded phase — preparation only

Reuse the existing fixed media workflow/caller and the validated private-launcher
permission approach; do not weaken source checks or apply chmod/chown repairs.
Permit a future separately authorized single media-authentication/offline-plan
job only after the following setup gate is resolved and controls reverified.

**Fresh-session blocker:** mint-prep-runner-private-session now exists and contains
this evidence. The launcher rejects nonempty _work-private; neither old session
may be reused or silently deleted. Proposed smallest preparation is a separately
reviewed local archive procedure with mocked-only coverage: verify dedicated
account, no active listener/job, absent registration files, expected ownership,
non-symlink ancestry and retained evidence identity; verify a collision-free
run-bound sibling destination; move the whole completed session without overwrite
or recursive modification/deletion; retain a source/destination identity record.
Unexpected identities, inability to establish quiescence, destination collision
or rename uncertainty stop without retry/fallback. Same-UID/root mutation remains
outside this procedure's trust boundary. Actual archival and fresh-session
creation require separate explicit authorization; neither happened here.

Afterward, a newly created fixed-name 0700 session/empty work root, verified
runner archive and local launcher hash, token-safe ephemeral registration,
offline group-membership verification, exact SHA/bundle approvals and one
protected dispatch would be needed. Do not turn this proposal into host commands
until the archive/setup procedure has been reviewed. Keep the failed media-run
session untouched as well.

Control changes proposed only: replace the group's sole selected workflow with
stormbots/Tactics-Strategy-Dev-Environments/.github/workflows/mint-media-console-prep.yml@refs/heads/main;
retain only this selected repository, explicit public-repository access, required
rdpollard approval with self-approval allowed, main-only environment and no admin
bypass. Keep checkout/inventory activation off. Future MINT_PREP_ENABLED=true
is set last, only after MINT_PREP_ACCESS_READY=verified, approved final main SHA
and independent MINT_PREP_HELPERS_SHA256 are bound. No settings changed here.

At c8e0134 the five-file mint-prep-bundle-v1 digest is
1eaf77cd1379b60d191bfadeda74066cab598daf2e91acf1e6a33dbcacab4c7c;
launcher SHA-256 remains
d6fcdbc5bf8edd3f583206292eb8f4fcbf8fa95b503f2201707399d6b85d736b.
These are proposal references, not activation approval. Recalculate from the
final approved main commit after any documentation/implementation merge; do not
reuse the consumed checkout or failed media authorization.

Future native scope: fixed mirrors.kernel.org/linuxmint/stable/22.3 checksum,
detached signature and linuxmint-22.3-cinnamon-64bit.iso acquisition; fixed
pinned signing key fingerprint 27DEB15644C6B3CF3BD7D291300F846BA25BAE09;
isolated GPG verification, ISO SHA-256 readback, private UUID-bound workspace,
bounded report/ownership manifest and offline console-plan data only. Existing
host gates include Mint 22.3/x86_64, dedicated nonprivileged account, KVM API 12,
trusted tools, >=6 GiB available memory and >=40 GiB available disk. No tool
installation or alternate mirror is an automatic fallback.

Limits: workflow/helper budget 25 minutes, checksum fetch 60 seconds/signature
60 seconds/ISO 900 seconds (also bounded by overall deadline); checksums <=64 KiB,
signature <=8 KiB, ISO <=6 GiB, workspace <=8 GiB and stdout export <=64 KiB.
Existing same-origin/same-path bounded redirects only; no mirror substitution.
Quiescence/host/settings/signature/digest/resource/deadline/ownership failure,
interruption, missing export, extra dispatch or unexpected process stops without
resume or automatic retry. Retain bounded owned partial evidence, not recursive
cleanup. An expired forced workflow cannot itself prove process cleanup.

Pass requires the pinned signature and digest verification, completed bounded
readback/export and run-bound report/ownership evidence. An offline plan must
retain diskCreated=false, qemuStarted=false, consoleValidatedNatively=false and
launchAuthorized=false. No guest image creation, VM boot, console socket launch,
package operations, elevation, service/task registration, updater execution,
application build, release or #73 merge is included. Media success would not
validate a usable console, guest behavior or Update Now production readiness.
Closeout separately disables media activation and verifies local runner exit,
remote removal (manual if necessary), owned process/descriptor results and
retained workspace status; no whole-host restoration claim is inferred.

### Reviewed archival/setup procedure — no execution authorized

Review of the recorded evidence supports the observed checkout permission Pass,
not media verification or automatic deregistration. The next media proposal
retains the fixed source/transport/validator limits; its five-file bundle is
separate from the six-file observer bundle. Successful checkout does not waive
rechecking host tools, available resources, KVM, controls or signature validity.
Manual remote runner removal is an observed closeout requirement, not an assumed
automatic success. The old media authorization remains consumed.

Prepared `tests/mint_session_archive_plan.py` is a pure plan validator with an
injected observer, no host inspector, mutation executor, imports or CLI. It does
not scan this environment or the spare host. Its eight mocked/static tests
exercise acceptance/rejection rules; they do not validate native rename, ACL,
process enumeration, persistence, race handling or recovery. The observations
are not authenticated by this model. A plan returns executionAuthorized=false.
No runner setup or media operation is embedded in it.

Fixed paths (no caller-supplied destinations):
- Source: /home/sde-runner/mint-prep-runner-private-session
- Archive: /home/sde-runner/mint-prep-runner-private-session-checkout-39132131036
- Older failed session, never moved/traversed/modified:
  /home/sde-runner/mint-prep-runner-session
- Fresh work root after archival: source/_work-private

Future procedure, requiring separate authorization and a reviewed native executor:

1. Keep all activation disabled. Verify the remote registration is absent and no
   approved/unapproved job is queued or active. Under the dedicated account,
   establish no other account processes or active runner/service exist (excluding
   only the identified inspector/controller); unknown or inaccessible observations
   stop. Scan process/registration state completely and stably within 30 seconds.
   A prior terminal exit alone is insufficient. No process is killed by this
   procedure. Same-UID/root interference remains outside the trust boundary;
   quiescence observations are not a permanent kernel-enforced freeze.
2. Pin root/home/source directories through descriptor-relative no-follow opens.
   Validate root-owned non-writable root/home ancestors, UID1001 home0750 and
   source0700, no inherited default ACL on creation ancestors, expected account
   groups and no elevation. Require source device66306/inode12088154 from the
   retained observer evidence; a changed identity stops for review, not automatic
   adoption. Bound fixed metadata reads; never enumerate checkout contents
   recursively or read credential contents. Check registration names are absent.
   Record the older failed session's directory identity without traversing it.
3. Verify archive destination absent, same filesystem, and native atomic
   no-replace rename supported. A separate existence test followed by ordinary
   rename/mv is NOT sufficient: it could overwrite an intervening destination.
   Do not copy, merge, remove or recursively chmod/chown either tree. Unsupported
   no-replace semantics stop rather than substituting another mechanism.
4. Prepare an exclusive owner-only, no-follow bounded phase journal alongside
   the session, outside the moved tree. Its fixed run-bound name must be absent;
   collision stops. Persist approved run/source/destination identities and
   preconditions before mutation; cap journal/report at 16KiB each and overall
   metadata/transition work at 30 seconds. Recheck gates, identities and absence
   immediately before the native no-replace rename. Use a pinned home descriptor
   and same-parent names; flush the parent after rename.
5. Read back archive identity and verify it equals the original session identity;
   source must now be absent and older failed-session identity unchanged. Persist
   the archived phase. The entire checkout/listener diagnostic evidence remains
   in the archive with its original ownership/modes; do not restart it there.
6. Exclusively create the fresh source0700 and empty _work-private0700 under
   umask0077. Pin/read back each newly created directory, owner/mode/identity and
   default-ACL absence. Flush directories/parent and persist final identities and
   completion phase. Do not populate/download/configure a runner in this step.
   Fresh session identity must differ from archived identity. Verify the archived
   and older session directory identities are unchanged.
7. On any interruption, uncertain syscall/close/fsync/journal outcome or failed
   postcondition: stop, report the last known phase, retain all state. No rollback,
   retry, deletion, alternate destination or automatic recovery. A lost export is
   unknown, not Pass. Separate read-only reconciliation must inspect source,
   destination and journal after uncertainty; never replay operations blindly.
   Cancellation must not be represented as restoration or cleanup success.

Allowed normal outcomes: (a) preflight rejection with no mutations; (b) archive
verified and fresh empty private directories durably recorded. Failure after
rename may leave only the archive, or archive plus a partially created new
session; both require reconciliation and are not healthy setup. No previous
session contents may be modified. Fixed-path directory identity checks establish
metadata preservation, not a new cryptographic inventory of every retained byte.

Before any future native implementation/execution, review the actual no-replace
rename binding, bounded inspector/journal, stop propagation and descriptor
cleanup. Their OS behavior remains unimplemented/unvalidated here. This is a
bounded local procedure/model, not authorization to extend into guest testing or
a general session maintenance tool. Application/updater code, existing launcher,
media transport/validator and approval gates are unchanged. Only exact planner/
test paths join automatic mocked checks and infrastructure-only scope.

Local procedure/model review: 129 mocked/static checks passed, focused actionlint
and git diff --check passed. No host inspector/executor or native archival test
was invoked. Native atomicity, process quiescence and durable recovery remain
explicit proof obligations, separate from permission diagnostic success.

### Archival model review corrections

The model now requires journalAbsent=true for the fixed sibling journal
/home/sde-runner/mint-session-archive-39132131036.json, in addition to archive
absence. Device/inode numbers are exact positive unsigned-64-bit integers, not
booleans/coerced strings; source and legacy identities must differ. This bounds
exported numeric fields and rejects observations that alias both evidence trees.
The plan explicitly returns operationsAreExecutable=false, the fixed journal
name, 16KiB record limit and 30-second transition budget. Its operation list is a
high-level description, not a complete syscall sequence: the ordered prose
procedure's preflight, revalidation, durable journal, fsync and stop gates remain
mandatory. No native executor may simply iterate the listed operations.

The model deliberately requires fresh default-ACL observations on root/home/home
creation ancestors; the checkout report's null values are not evidence of ACL
absence there. Legacy evidence contents are never scanned or modified by the
procedure. Inspector exceptions propagate without retry; a future controller
must sanitize/report them as stopped, not Pass or authorization. Oversized or
malformed native input needs bounds before decoding in that future inspector;
this pure in-memory model neither acquires nor serializes host evidence.

Review QA: **132 mocked/static checks passed**, including eleven planner tests
with missing/unknown gates, journal collision, bounded/non-coerced IDs, aliased
sessions, malformed observations, exact schema/account/group contracts and
inspector failure. Static checks forbid imports, generic execution calls and CLI
entrypoints in the model. Focused workflow lint/whitespace and exact full-branch
infrastructure-scope checks passed; mixed application/key changes still require
application CI. This review changes no host, launcher, media validator/transport,
activation setting or production code. Atomic no-replace rename, process-state
inspection, persistence/interruption handling and native recovery are still
unimplemented/unvalidated, not inferred from model acceptance.

Final merge-readiness review: **134 mocked/static checks passed**, including
explicit rejection of unknown/coerced ACL absence on every creation ancestor and
bounded serialized plan output with maximum accepted identity values. Unexported
extra observation fields are not echoed. The retained legacy directory's unchecked
ACL is not substituted for a creation-ancestor ACL check. No additional model
implementation defects were found; focused workflow lint and whitespace passed.
Merge readiness applies only to documentation/pure planning and mocked CI, not
native archival, quiescence verification, persistent recovery or execution approval.
