# #72 reduced-scope Phase 1: shared app-only installation core

**Scope:** Separately authorized implementation of Phase 1 of the
[approved decision](APP-UPDATE-NOW-REDUCED-SCOPE-DECISION.md). Local QA only; no
installed updater, elevation, task/service registration, native package operation,
PR, workflow/build dispatch, version allocation or release preparation.

## Change and authority boundary

`updater/src/install_core.rs` provides one installation state machine, used by
both native platform backends. It borrows an existing installation lease through
an internal context. The core has no lease-acquisition, tool, discovery, network,
privilege-launch or package-command implementation. Its only production ownership
implementation begins/completes a transaction on the caller's existing
`sde_coordination::Installation`. Borrowed lifetimes retain that ownership through
native work/postchecks; error/drop does not clear durable intent.

The scheduled wrappers still acquire installation ownership in their existing
place. Their preceding preparation operation gate is still released before that
acquisition, as before. No second acquisition occurs in the shared core or the
new app-only entry; Phase 2 must supply the approved admission-aware ownership
boundary rather than copying that scheduled drop/reacquire sequence into manual
handoff. No coordination code is changed in this phase.

Private Linux/Windows `install_app_only` boundaries accept caller-held ownership,
retain root/SYSTEM checks, select fixed app-only scope and pinned authentication,
and dispatch into the same installation core as scheduled maintenance. They are
not wired to a CLI, GUI, bootstrap, scheduler or public library interface. Their
reports/native implementation remain internal. They do **not** prove consent,
admission, request freshness, compatibility or privilege setup; those remain later
gates before a reachable manual-update path is allowed.

`tools_for` invokes the existing tool callback exactly once in scheduled mode and
never invokes it in app-only mode. Existing platform-specific handling of tool
exit codes is retained. The installation backend has no tool-maintenance hook.
No app-only discovery/staging/supervisor pipeline is added in this phase.

## Preserved checks and behavior

Both scopes share initial pause, installed identity/version comparison, staged
re-authentication, native preflight, durable intent, native outcome, postchecks,
recovery receipts and final journal completion. No scope branch skips signature,
hash, native identity, postcheck or recovery validation.

Platform backend functions retain their original checks and fixed commands:

- Linux: trusted staging/files, signature/hash, DEB package/version/architecture,
  package-manager lock preflight, dpkg audit, unchanged narrow APT arguments and
  sanitized environment, native exit, resource/engine and recovery checks.
- Windows: protected staging/files, signature/hash, unchanged fixed installer and
  `/S /UPDATE` arguments/sanitized environment, native exit/3010 distinction,
  installed identity/resources/engine and recovery checks. Reboot code 3010 is not
  promoted to success, and uncertain completion retains intent.

Linux app-only busy detail requests a new authorized attempt rather than promising
a scheduled retry; scheduled busy text remains unchanged.

Scheduled maintenance retains its existing second pause read **after** intent
publication, including platform-specific paused record behavior and journal
completion before reporting Paused. App-only performs its final read **before**
intent, matching the approved commitment decision. There is no post-intent manual
pause read, network/user interaction or new preparation step in the core. The
15-minute/two-minute lifecycle/deadline enforcement is **not implemented here**;
the later worker must check it before entering this boundary.

## Local QA and review

[Local report](evidence/ISSUE72-SHARED-CORE-LOCAL.json) records final source hashes,
exact commands, outputs and limitations. Commands use the existing cached Rust
1.99 toolchain/dependencies, `--offline --locked`, and a local target directory.
No toolchain components/dependencies were installed and no network release was
queried. Tests use local byte fixtures/ephemeral test keys, not published release
assets or release signing credentials.

- `cargo check --all-targets`: Pass on Linux, including local test compilation.
- Unprivileged updater library regression suite: **37 passed**, including **16
  new shared-core tests**. Four privileged/native/protected-staging cases were
  explicitly filtered; they were not counted as passing. Windows-only native
  modules/tests are not compiled or executed on this Linux target.
- New tests exercise tool exclusion, scheduled callback results/errors, equivalent
  validation/completion steps in both scopes, initial/final pause, current/downgrade,
  malformed versions, preflight deferral, failures before/after intent, uncertain
  publication, native non-success/reboot code, and failed journal completion.
- Shared-core tests use memory-only fake ownership/backend/journal: no installation
  lock, policy/journal file, installed updater, dpkg/APT/installer process, privilege
  operation or package-state mutation is invoked by them.
- First regression attempt: 36 passed, one existing loopback HTTP test failed at
  listener creation with sandbox EPERM. The affected test passed with socket
  permission; the final complete allowed suite also passed. Only the local test
  server was exercised, not a live release endpoint or updater experiment.
- Source review checked lease acquisition remains in scheduled wrappers, pinned
  authentication remains at the app-only boundary, native trust/preflight/commands
  and receipts remain in backends, and existing tool-result handling is unchanged.
- `git diff --check`: Pass.

Limits: rustfmt and clippy components are absent; formatter/lint validation was
unavailable and no components were installed under this scope. A Windows Rust
standard-library target is also absent. Windows native backend changes received
source review only, not Windows compilation or native validation. These checks
must be completed before merge/release readiness is claimed. Existing protected
staging, native Mint and SYSTEM upgrade fixtures were deliberately not run.

## Stop gates and remaining work

No evidence showed tools invoked in app-only scope, trust checks bypassed by scope,
or leases reacquired in the shared core. Local tests do not establish native
behavior or platform readiness. Application Update Now remains unreachable until
later authorization, ownership/admission, capability, request/deadline, progress,
supervision and recovery integration is implemented and reviewed.

Next: review this Phase 1 change and its coverage/format/Windows compilation gaps
before advancing Phase 2. Do not infer permission for native package operations,
elevation, bootstrap/task registration, application builds, PR creation, release
preparation or further W2n/W2/W3 work. W2h/W2m findings remain preserved, native
N1/N2 remain NotRun, authentication safety Unproven and production readiness false.
