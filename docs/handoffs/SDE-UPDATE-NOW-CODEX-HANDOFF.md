# SDE Update Now — Codex handoff

## Start here

Continue issue #72's **approved reduced-scope, Linux-first Update Now feature**.
The owner wants the shortest defensible path to a Linux testing build and desktop
UAT, not another infrastructure/research project. Read this handoff, inspect the
current branch/PR, and make routine engineering decisions autonomously. Ask only
for missing product decisions or specific privileged/build/package authorization.

**This is a handoff, not permission to execute its proposed native steps.**
Application code currently keeps Update Now and protected close disabled. Do not
reinterpret passing local/CI checks as native authentication or installation proof.

Snapshot: application implementation commit
`8350cba954882366288976b92228241264524884`. This handoff may be committed afterward;
verify current HEAD instead of resetting to the snapshot or discarding newer work.

## Repository, branch and PR

- Repository: https://github.com/stormbots/Tactics-Strategy-Dev-Environments
- Issue: https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/72
- PR: https://github.com/stormbots/Tactics-Strategy-Dev-Environments/pull/73
- PR branch: `feat/issue72-app-only-pr`.
- PR #73 is **draft, open and unmerged**. Keep it that way.
- Last application commit: `8350cba` — gated close/admission/receipt follow-up.
- Previous application commit: `dc078e37c06270ba711e4d7abe307805833d9a82`
  — disabled broker/receipt/deployment wiring; source pin for the spare-host attempt.
- Earlier slice: `8824e6a` — verified read-only discovery and protected progress.
- Current local worktree, if this environment persists:
  `/workspace/Tactics-Strategy-Dev-Environments/work/issue72-app-only-pr`.
- Origin was verified as
  `https://github.com/stormbots/Tactics-Strategy-Dev-Environments.git`.

Read `AGENTS.md`, `docs/agents/domain.md` and
`docs/agents/issue-tracker.md`. Repository instructions require the `gh` CLI for
issue/PR operations. Read glossary/ADRs if present; they were absent earlier.
No subagents are requested. Keep edits focused on the existing feature branch;
do not create another infrastructure PR for routine feature work.

## Owner preferences and authorization boundaries

The owner is largely deferring to Codex for engineering and tooling decisions.
They are short on time and frustrated by repeated small approvals and optional
infrastructure detours. Handle routine decisions, reuse passing evidence, report
concrete blockers and consolidate required native work into a bounded session.
Suggested prompts should be fenced `text` blocks for copy/paste.

Authorized ongoing work:

- Complete/review Linux integration behind disabled gates and run appropriate
  automated/local QA; publish reviewed work to the existing draft PR.
- Record the stopped native attempt and cleanup; prepare a consolidated native
  validation plan and exact future execution packet.
- Development components/tooling are allowed. Investigating practical disposable
  access is allowed when actually necessary, but optional runner/VM/media work is
  now **paused**. Do not resume it as a default prerequisite.

Still deferred / requires separate specific authorization:

- Production update enablement, activation/capability receipt provisioning.
- Additional privileged native operations, polkit deployment/registration,
  package operations, or another native attempt after the stopped attempt.
- Application/installer-build dispatch; do not dispatch just because CI is green.
- PR #73 merge, release preparation/signing/publication, stable promotion or rollout.
- Windows implementation/native proof is deferred in favor of Linux-first delivery.

The owner authorized a bounded disabled-broker native attempt. That attempt stopped
on an unexpected authorization failure and its temporary files were removed.
**Do not replay it or treat its permission as an unlimited native-testing grant.**
The owner explicitly said elevation, registration and package deferrals are not
permanent refusals: prepare the exact needed operations and ask when truly needed.

The owner will do desktop UAT on their own Linux Mint and Windows 11 PCs. The
spare Mint machine below is separate from the UAT PC.

GitHub sole-maintainer approval is intentional: **Prevent self-review remains
unchecked for `mint-host-access`**. Required environment approval and other access
controls remain. Do not ask the owner to toggle self-review back on without a
specific strong reason. Other robotics groups share the stormbots organization;
avoid organization-wide policy changes or effects on other repositories.

## Approved product/architecture direction

The feature lives in Schedule's **SDE Application Updates** section. The owner
liked a compact Update Now interaction plus proactive preparation progress.

Use the existing protected updater and shared installation core, with one fixed
OS-authorized app-only request and read-only protected progress. Do not revive the
historical custom authenticated GUI/worker command protocol.

Approved behavior:

- Explicit upfront installation consent before OS authorization. It covers normal
  GUI close and crashes: either can allow installation once preparation is ready.
- No immediate cancellation after approval. `Keep working` was removed as an action.
- Keeping any admitted SDE window open retains its shared session lease and blocks
  installation until the request defers/expires.
- Overall pre-commit lifetime: **15 minutes**; Ready window: **2 minutes**, bounded
  by the overall deadline. Linux uses boot identity plus `CLOCK_BOOTTIME`, including
  suspend. Expiry is not proof of cancellation after commitment.
- Admin pause is checked until the final policy check before durable installation
  commitment. An already committed installation is allowed to finish.
- Installation remains app-only: no development-tool maintenance or timer changes.
- Close/reopen protection comes from admission, locks and durable intent, not a GUI
  process PID, progress poll, or the user keeping the app closed voluntarily.
- Uncertain intent/recovery is never silently cleared. Reopening never submits
  another request or grants installation permission.

Lock vocabulary: O = operation/preparation ownership; A = admission closure;
S = sessions (GUI shared, installer exclusive); I = durable installation intent.
The worker retains its leases through the shared core. Do not drop/reacquire
leases to cross a component boundary. Existing scheduled maintenance behavior,
release trust, signed recovery and native package identity checks must survive.

## What is implemented now

### Shared installation/coordination foundations

- Phases 1/2 established a shared installation core, app-only scope, startup and
  admission checks, ownership transitions, pause/intent ordering and compatibility
  gates. App-only never invokes tool maintenance.
- Existing scheduled maintenance stays on its existing behavior/path.
- Linux worker is independent of GUI lifetime and uses protected request snapshots,
  one-shot claims, O/A/S, signed discovery/staging/recovery, deadlines, postchecks and
  durable recovery barriers.

### Discovery, receipts and progress

- Schedule can perform a manual **read-only** official stable release check.
  Exact manifest bytes authenticate with the existing pinned Minisign key;
  tag/version/platform name/size are bound. No installer is downloaded by this check.
- Notification discovery has a separate bounded HTTP budget; existing scheduled
  discovery retains its budget. Single-flight/cooldown prevent request flooding.
- The fixed broker prepares a root-written receipt: pending before detached spawn,
  accepted after `Popen` succeeds. **Accepted means launch initiated, not liveness,
  readiness, completion, or installation authority.** Failure retains uncertainty;
  it never kills/retries a possibly independent worker.
- A protected per-user pointer supports no-argument receipt lookup and Schedule
  reconnection. Identity/current boot/canonical UUID and file ownership are checked.
  Root-written records use named-UID read ACLs, not shared-group access.
- At most eight run snapshots are retained; capacity stops without pruning unknown
  evidence. A new pointer may replace only a resolved terminal one; old run evidence
  remains. Unknown/pending/recovery state blocks new attempts.
- UI observations validate identities, candidate continuity, state/sequence/time,
  stale/cached snapshots and bounded serial polling. No URL/local-storage correlation.
- Unknown/timed-out receipt lookup blocks new consent, including with mocked future
  eligibility. Ambiguous submission permits **one read-only recovery lookup**, not
  another authorization attempt. Errors do not expose raw privilege details or claim
  cancellation.

### Prepared launch/close paths — still disabled

- Desktop request source gate: `EXECUTION_ENABLED = false` in `app_update.rs`.
- Broker source gate: `EXECUTION_ENABLED = False` in `app_request.py`.
- Desktop close source gate: `CLOSE_ENABLED = false` in `app_update.rs`.
- UI eligibility remains false and Close SDE & install remains disabled.
- Behind the request gate: fixed `/usr/bin/pkexec --disable-internal-agent
  /usr/local/libexec/skyview-app-update-request`, no caller-supplied command/path/
  candidate. Fixed environment, 1,024-byte response bound, 120-second UI deadline,
  retained child owner/reaper, no kill/retry after uncertainty. Stdout alone cannot
  confirm acceptance; it must match the protected accepted receipt.
- Prepared request/close handlers share existing GUI operation exclusion.
- Behind the close gate: fresh independent receipt/Ready/deadline/candidate/
  capability/recovery checks; potentially slow file hashing is followed by another
  protected read and time check. The process exit request retains operation
  exclusion; S is **never manually released/reacquired**. The root worker alone
  decides whether to install. This is not a custom close grant.
- Ready reports refresh no faster than every five seconds while O/A are retained
  and S is busy. At most 23 additional reports fit the unchanged 32-publication
  budget. Reports do not extend either deadline.
- Startup admission failure still shows a native notice rather than starting a
  normal webview without S. If readable, the current receipt is mentioned without
  claiming liveness. A richer restricted-startup webview is deferred; native
  dialog/actual exit behavior is unproven.

### Deployment/capability boundaries

- Bootstrap has exact disabled-only deployment/removal operations and package hooks
  for the fixed broker/polkit policy, trusted directories and inode-preserved gate.
- Deployment records exact hashes in `app-only-deployment.json`; this is **not**
  `app-only-capabilities.json` and never asserts native validation.
- Unknown/changed/incomplete deployments stop rather than repair/overwrite.
  Removal checks known bytes and retains runs, gates and recovery evidence.
- No bootstrap/hook creates a native-validation capability receipt.
- Real capabilities require exact deployed-file hashes, external maintenance-file
  coverage when present, and an allowlist of exact validated candidate package
  digests. Candidate/hook compatibility must not be faked to get past a gate.
- Pure tests now cover missing/changed/substituted capability files, external-file
  mismatch, unvalidated candidates and close failures. Native capability provisioning
  and migration/renewal still need a concrete reviewed path backed by native proof.

## Code map

| Area | Files |
| --- | --- |
| Shared core | `updater/src/install_core.rs` |
| Linux native install and trust | `updater/src/linux_install.rs`, `updater/src/host.rs` |
| Linux requests, capabilities, receipts, progress, close checks | `updater/src/linux_request.rs`, exports in `updater/src/lib.rs` |
| Fixed broker / deployment | `linux/self-update/app_request.py`, `linux/self-update/bootstrap.py` |
| Polkit policy | `linux/polkit/org.skyviewrobotics.sde.app-update.policy` |
| Package hooks | `installer/src-tauri/hooks/postinst`, `installer/src-tauri/hooks/prerm`, `installer/src-tauri/tauri.conf.json` |
| Coordination | `coordination/src/lib.rs`, Linux Python coordination adapters |
| Backend | `installer/src-tauri/src/app_update.rs`, `app_update_launch.rs`, handlers/startup in `main.rs` |
| Tauri command permissions | `installer/src-tauri/build.rs`, `installer/src-tauri/capabilities/main.json` |
| GUI | `installer/src/AppUpdateControl.tsx`, `AppUpdateProgress.tsx`, `AppReleaseCheck.tsx`, `appUpdate.ts`, `bridge.ts`, `DetailsPages.tsx` |
| Signed notification discovery | `updater/src/notification.rs`, `updater/src/discovery.rs` |

Synchronize command handler names, build permissions and capability entries; run
`tests/backend_contracts.py` if touching this surface. Do not grant generic shell
or filesystem permissions to solve a fixed-operation integration problem.

## Spare Mint host: actual state and stopped native attempt

Host: `ryan-ThinkCentre-M910q`, Linux Mint **22.3 Cinnamon**, local active X11
session, `ryan` UID **1000**, sudo. i5-7500T, 4 CPUs, 15 GiB RAM, roughly 200 GiB
free. Firmware virtualization was enabled; `/dev/kvm` works, KVM API 12, QEMU 8.2.2.
These facts do not require resuming VM work. `sde-runner` is UID 1001 from earlier
runner work; verify it still exists before using it as a second test UID.

The minimal preflight unexpectedly found existing:

- `/usr/bin/skyview-dev-setup`
- `/usr/lib/Skyview Dev Setup`
- `/var/lib/skyview-robotics/self-update`
- `/var/lib/skyview-robotics-coordination`

Therefore the original **clean-host bootstrap deployment packet was stopped**.
Do not uninstall SDE to force it to pass, or overwrite existing installed state.

A narrowed test temporarily installed **only two previously absent files**:

1. `/usr/local/libexec/skyview-app-update-request` (0755)
2. `/usr/share/polkit-1/actions/org.skyviewrobotics.sde.app-update.policy` (0644)

Pinned source commit: `dc078e37c06270ba711e4d7abe307805833d9a82`.

| Source | SHA-256 |
| --- | --- |
| `linux/self-update/app_request.py` | `122bef3156eb03e258c1693af3eb177e082a0c84db9fe2d927ed8b039d581b10` |
| `linux/polkit/org.skyviewrobotics.sde.app-update.policy` | `50900fa7d3f8f92c8646c8ae821b6ed6ac9356639abed17c9091b7ee17b25187` |

No bootstrap, worker, package or existing updater-state operation was requested.
`pkaction` confirmed the fixed action/exec annotation, active `auth_admin`, inactive
and any `no`. The first intended cancellation attempt ran:

```bash
/usr/bin/pkexec --disable-internal-agent \
  /usr/local/libexec/skyview-app-update-request
```

It returned **127** with `Not authorized`. The user confirmed **no graphical prompt
appeared**. Do not label this a successful cancellation. No approved attempt ran.
A `ps`/grep search found no matching desktop authentication-agent process; the
`polkit.service` journal query returned no entries. This is consistent with a
missing agent but **does not establish the cause**. Do not invent an agent repair.

The user then ran the supplied ownership/hash/inode/mode-checked cleanup and
reported successful removal of both temporary files. Root journal and downloaded
sources remain:

- `/var/tmp/sde-disabled-broker-zFfx0ifQ` — root-private plan and created-file records.
- `/tmp/sde-disabled-broker.zFfx0ifQ` — downloaded verified sources (may disappear
  after reboot/tmp cleanup; check instead of assuming it remains).

Evidence is user-pasted terminal output, not direct Codex observation. Cleanup is
verified **for the two temporary files**, not whole-host cleanup. Diagnostic outcome
is stopped/blocked; authentication safety, cancellation, approved entry, worker,
ACL and native package correctness remain unproven. No update was authorized or
confirmed by this attempt. Do not launch more agents/retry/deploy under an assumed
standing test permission after the explicit stop.

Machine-readable record:
`docs/design/evidence/ISSUE72-SPARE-MINT-DISABLED-BROKER.json`.

## Validation achieved

At application commit `8350cba`:

- **142 UI tests** passed.
- **18 ordinary Linux desktop Rust tests** passed.
- **64 updater library tests** passed; **one native POSIX-ACL test intentionally
  ignored**. Do not run it or any package-changing ignored tests by accident.
- Three affected real Chromium Schedule/accessibility/keyboard/reflow cases passed.
- Broker mocks 10; package-hook mocks 12; backend permission contracts 7;
  CI-boundary checks 10; CI-scope checks 9 passed.
- Both crates: Rustfmt and all-target Clippy with warnings denied passed.
- TypeScript, affected-file Prettier, actionlint and whitespace checks passed.
- Automatic CI passed, including Linux and Windows desktop compilation/tests,
  trust/coordination checks and browser accessibility.

CI: https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39179855136

Automatic mocked/static infrastructure checks also passed. Installer `native`,
release and native Mint/Windows fixture jobs were skipped. No workflow dispatch
was used. Windows compilation is **not** Windows UAC/package/desktop validation.
No new native host, package, GUI-exit or ignored ACL test ran during this follow-up.
A Rust local HTTP test needs sandbox permission for localhost binding; an earlier
sandbox binding refusal was environmental and passed with network permission.

In this existing workspace, development tools may be restored with:

```bash
source /workspace/.sde-tools/env.sh
export PATH=/opt/codex/cua_node/bin:$PATH
```

Cached Cargo/npm deps and development sysroot live under `/workspace/.sde-tools`.
Do not assume these paths exist in a new environment. Read the managed-cloud runtime
skill/network policy when applicable; keep credentials out of chat and logs.

Useful checks (inspect existing CI for exact supported invocations):

```bash
python3 tests/backend_contracts.py
python3 -m unittest discover -s tests -p test_app_only_request.py
python3 -m unittest discover -s tests -p test_app_update_package_hooks.py
python3 -m unittest discover -s tests -p test_ci_boundaries.py
python3 -m unittest discover -s tests -p test_ci_scope.py
cargo fmt --manifest-path updater/Cargo.toml --check
cargo fmt --manifest-path installer/src-tauri/Cargo.toml --check
cargo clippy --manifest-path updater/Cargo.toml --locked --offline --all-targets -- -D warnings
cargo clippy --manifest-path installer/src-tauri/Cargo.toml --locked --offline --all-targets -- -D warnings
```

Run npm tests/TypeScript and affected browser cases when changing the UI. Do not
blindly use `--ignored`, native-package opt-ins, installed-update scripts or
privileged fixture paths. Reuse existing green evidence for untouched areas.

## Read these documents before planning more work

All paths below are in the repository; use the feature branch/current HEAD.

1. `docs/design/APP-UPDATE-NOW-REDUCED-SCOPE-DECISION.md` — approved product choices,
   corrected lock rules, shared core, durable intent and phased stop gates.
2. `docs/design/APP-UPDATE-NOW-SCHEDULE-INTEGRATION.md` — current UI/backend state;
   later follow-up sections supersede earlier statements that paths are unwired.
3. `docs/validation/ISSUE72-LINUX-CONSOLIDATED-NATIVE-PLAN.md` — next-session plan,
   missing artifact/driver prerequisites and exact classes of privileged operations.
4. `docs/design/evidence/ISSUE72-SPARE-MINT-DISABLED-BROKER.json` — stopped attempt.
5. `docs/validation/ISSUE72-LINUX-DISABLED-REQUEST-GATE.md` — original packet plus
   outcome; historical, **not safe to replay blindly on the installed spare host**.
6. `docs/design/APP-UPDATE-NOW-REDUCED-SCOPE-PHASE1.md`, `...PHASE2.md`,
   `...PHASE3.md` — foundations and prior native/local evidence limits.

The original issue/protocol research remains historical. W1/W2a–W2n consumed
considerable effort before scope reduction. Preserve **W2h's delegated socket
message-authorship counterexample**, **W2m's immediate cleanup failure**, the
limited nature of W2i–W2l and the unexecuted observer/native gates. A previous managed
filesystem ACL probe failed with EOPNOTSUPP (95). None of these is closed by mocks
or adoption of the reduced architecture. Do not resume them unless implementation
actually depends on the corresponding custom protocol.

Earlier CI accidentally selected two Windows package-changing tests on disposable
GitHub runners. That history is preserved in PR #73; tests are now default-ignored,
manual-opt-in and script-guarded. Never erase that evidence or say package operations
never occurred anywhere in the project's history. New automatic CI must stay
separate from installer packaging, native package operations and releases.

## Prioritized next steps for Codex

### 1. Reestablish state and assess the shortest remaining route

Read the named docs/current PR and inspect HEAD/worktree. Confirm gates remain
false, PR #73 draft/unmerged and CI boundaries intact. Do not ask the owner to repeat
completed checks or wait for another permission to do normal engineering/review.
Do not restart the infrastructure chain or repeat the stopped native attempt.

### 2. Resolve native-session prerequisites through bounded preparation

Prepare the exact next native driver/artifact plan before requesting more host
work. Two concrete blockers are open:

- **Graphical OS authorization:** diagnose the existing Mint session/agent/action
  mapping with a targeted read-only check. Identify the actual existing packaged
  agent executable/autostart/session state; do not guess a package path or assume
  the process search proved absence. If an existing agent must be started, present
  that precise non-root operation and cleanup/ownership expectations for approval.
  No sudo fallback for production GUI requests; no package installation, settings
  repair or service changes by assumption.
- **Compatible artifacts and trust:** pin an installed testing baseline, candidate
  package version/hash/signature and exact package-hook compatibility. The product
  worker only discovers authenticated **official stable** releases, and capabilities
  bind exact candidate bytes. An arbitrary locally built/prerelease package is not
  an eligible production candidate. Do not fake capabilities, alter the production
  key/feed/version rules, or publish stable merely to manufacture a test candidate.

Decide the smallest engineering route: existing native package-fixture driver
through the shared core, plus an explicitly isolated/reviewed test-only signed-
discovery fixture if real worker end-to-end testing cannot use a compatible stable
candidate. Shared-core package proof and public stable-worker discovery proof are
separate; one cannot silently stand in for the other. Fixture implementation/source
scope may be prepared/reviewed locally; native execution remains separately gated.

Pin exact build/workflow inputs without dispatching. If packaging is now necessary,
explain the concrete Linux artifact job and ask for the specific build authorization
only after the reviewable setup exists. Do not invent a release version or sign/
publish a prerelease as an implied consequence of testing-build permission.

### 3. Finish any genuine enabling prerequisites behind disabled gates

Review remaining capability provisioning/migration/renewal and eligibility/close UI
integration for the separately authorized testing build. Existing capability
validation is not a provisioner. Do not create a receipt asserting native proof
before that proof exists. Keep unknown legacy hooks, recovery state and candidate
bytes fail-closed. Native dialog behavior, actual exit and full restricted-startup
UX remain unproven; richer restricted GUI work should not delay core proof unless
required by the approved acceptance criteria.

The last implementation added substantial gated checks; review/reuse them rather
than adding another protocol. Fix concrete defects, run affected checks once,
publish to PR #73 and monitor automatic CI. Do not merge it.

### 4. Present one consolidated native authorization packet

Use the existing spare **installed** Mint baseline with explicit preservation and
recovery scope; do not replay the clean-host packet. Fill source/artifact hashes,
exact commands, ownership journal, evidence/resource/deadline bounds, expected
outcomes and cleanup. Request only necessary root/polkit/fixture/package operations.

The planned session should cover, in order and stopping on first unexpected result:

1. Working OS prompt: one cancellation and one approved disabled entry with original
   UID; no request/worker on denial, expected disabled exit 78 on approval.
2. Same-user receipt visibility, denial to another existing UID and no unprivileged
   write; real kernel ACL evidence, not a permissive fallback.
3. Independent worker/lease ownership, O/A/S admission, multiple windows/users,
   duplicate/manual-scheduled contention, ordinary close/crash and rapid reopen.
4. Pre-commit pause/deadlines/suspend and interruption/recovery, using explicitly
   labeled package-free fixtures where possible. Fixtures never clear real intent.
5. One controlled app-only native upgrade of pinned compatible artifacts, actual
   package hooks/postchecks, known children and unchanged tools/schedule/pause.
6. Final feature/testing-build desktop UAT with Schedule consent/preparation/Ready/
   Close/reopen, keyboard/focus/status behavior, after separate build/enablement
   authorization and the relevant safety gates.
7. Closeout: disable test activation, preserve uncertain intent, remove only owned
   fixtures/deployments, retain evidence. Report diagnostic completion, cleanup,
   native safety evidence and desktop acceptance independently.

The consolidated plan proposes at most 90 minutes operator time and one controlled
upgrade. These are planning bounds, not promises or authority. If artifact trust
means a single upgrade cannot establish both package and end-to-end worker proof,
state that explicitly instead of weakening trust or hiding another operation.

### 5. Testing build, owner UAT and later release decisions

After the necessary implementation/native proofs and **separate build permission**,
produce a Linux testing artifact and a short native UAT handoff. The owner handles
desktop UAT. Windows proof follows separately later. PR merge, production enablement,
release publication, stable promotion and rollout all remain independent decisions.

## Suggested opening instruction for the new thread

```text
Use this handoff to continue #72 from PR #73's current branch. Reverify the latest
HEAD and authorization boundaries. Prioritize the smallest reviewable Linux native
driver/artifact plan and targeted Mint authorization-agent diagnosis; do not repeat
the stopped attempt or restart optional infrastructure. Finish any necessary gated
engineering with focused QA, then present exact additional native/package/build
operations for approval. Keep updates/close disabled, PR #73 draft and unmerged,
and execution, installer dispatch and release work deferred unless separately
specifically authorized. Make routine engineering decisions autonomously and tell
me only about concrete blockers or product decisions requiring my input.
```
