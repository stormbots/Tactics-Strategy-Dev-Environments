# #72 Phase 3: Linux authorized request and app-only worker

Status: implemented for local review; **not installed, enabled or natively
validated**. Builds, native package workflows and releases remain deferred.
PR #73 stays draft and unmerged. The approved reduced-scope decision remains the
product contract; this document does not approve another feature or platform.

## Fixed authorization boundary

`linux/self-update/app_request.py` is intended to be installed as the root-owned,
non-user-writable regular executable
`/usr/local/libexec/skyview-app-update-request`. Its isolated Python shebang is
`#!/usr/bin/python3 -I`. Invoke that exact path through `/usr/bin/pkexec`, without
arguments. The supplied policy has one fixed `exec.path`, active-session
`auth_admin` authorization without `_keep`, and denies inactive/other subjects.
Never grant a policy for the interpreter, use a general sudo rule or launch the
GUI as root. Alternate-admin authorization retains the original `PKEXEC_UID` as
progress reader. A root caller already has machine authority; an arbitrary
unprivileged environment variable is not treated as proof of authorization.

The broker validates euid, fixed installed path, argument count, canonical
non-root requesting UID, protected paths and active engine receipt. It creates a
UUID request with boot identity and CLOCK_BOOTTIME timestamps, snapshots the
bounded active worker and version receipt, syncs them, and starts the fixed
`app-only-linux` command with sanitized environment, cwd `/`, closed inherited
FDs, `/dev/null` stdio and a new session. It returns only request correlation.
It does not wait for the worker, run maintenance or invoke a package command.
GUI/authorization-agent/desktop exit survival is a native proof obligation, not
established by mocked Popen arguments.

## One-shot ownership and deadlines

The worker must execute from the exact protected
`self-update/app-only/runs/<UUID>/sde-update-trust` location. It validates the
bounded request, boot, UID and exact 900,000-ms lifetime. An exclusive, durable
`claimed` file records request/boot/PID correlation and permits one attempt only; it is never removed to replay a request.
The worker compares its snapshot with the deployed capability-bound worker.
Competing attempts fail O promptly; they never queue or reset another request.

Ownership is retained through `Preparation(O)` -> `Admission(O,A)` ->
`Installation(O,A,S)`. Existing coordination's V2 compatibility prerequisite and
all durable-intent checks remain mandatory. Preparation uses existing pinned
stable discovery, authenticated staging and authenticated recovery. Missing
signed recovery is a hard manual-update deferral, not reduced recovery permission.
Installed identity and release eligibility are rechecked before admission.

Sample the ready-wait origin immediately before the nonblocking admission closure,
so scheduling latency cannot extend authorization. Publish Ready only after A is
held. Poll S every 50 ms while retaining O/A, checking the earlier of overall and
120,000-ms ready deadlines. Suspend counts; reboot or clock uncertainty invalidates
precommit continuation. The actual shared-core guard runs after authentication,
native preflight and final pause read, immediately before intent publication.
Read-only dpkg-deb identity/dpkg audit probes use trusted coreutils timeout, capped
at ten seconds and remaining request lifetime. Scheduled probes retain their
existing execution. **Installation APT/DPKG is never timed out or killed.** Blocking
filesystem/durability operations are not certified real-time deadlines; uncertainty
once intent publication starts remains recovery-required, never an unsafe rollback.

The final sequence contains no network or user interaction. The shared core still
authenticates the staged package, checks native identity/health, records intent,
waits for native completion, verifies resources/engine activation and records
recovery. It never reacquires leases or runs the app-only tool callback.

## Protected progress and bounded retention

Per-request `progress.json` has an exact bounded schema: request/reader/boot
identity, sequence, observed CLOCK_BOOTTIME time, deadlines, fixed state, optional
verified candidate version/SHA-256, actual native exit and a bounded code-generated failure detail (never native stdout/stderr). No commands, URLs,
secrets or raw installer output are exposed. Atomic writes sync the file and
parent. Each attempt permits at most 32 publications, each <=4096 bytes.

A Linux access ACL grants owner root read/write, the requesting UID read only,
and no group/other access; its mask permits read only. Traversal directories are
root-owned and non-writable by students. Do not substitute shared-primary-group
or world-readable files if ACL setup fails. The read-only
`app-only-progress <UUID>` command uses a fixed location, bounded parsing,
protected-path checks, exact request/reader/boot correlation and schema checks.
Observed time/deadlines let the later UI report age/expiry; no progress value
proves worker liveness, authorizes closure/installation or clears recovery.

Progress failure before readiness/commit prevents continuation. After intent,
Installing/Postchecking publication errors cannot interrupt package supervision.
A failed terminal write after successful installation must not become Deferred;
the last observation may remain stale. Post-intent failure preserves journal and
scope hint; no recovery evidence is cleared by this worker's error handler.

Retain snapshots, request and claim, including launch failures. Cap retained runs
at eight and snapshots at 64 MiB each; reject further requests rather than prune
unknown workers/evidence. Normal progress temps are removed on publication error;
failed removal is not claimed as cleanup success. There is no unbounded native
stdout log. Automated retention/recovery tooling is not implemented; an owned,
reviewed terminal cleanup policy is required before fleet enablement. Never delete
runs because a PID disappeared or a deadline elapsed.

## Fail-closed compatibility and deployment gates

No hook installs the new launcher/policy, provisions its directories, writes an
enablement receipt or migrates V1 helpers in this phase. No existing schedule or
pause policy changes. Existing installations therefore remain disabled.

A protected <=16-KiB `app-only-capabilities.json` is an explicit **temporary native
validation gate**, not a self-issued feature flag or complete migration mechanism:

- `schemaVersion: 1`, `nativeValidation: "linux-app-only-v1"`;
- `files`: exact SHA-256 bindings for the fixed launcher, policy, startup binary,
  bundled bootstrap, bundled worker and bundled coordination helper, plus both
  external maintenance entry/helper when present;
- `validatedCandidateSha256`: one to eight exact candidate installer digests.

The worker validates all current file hashes, rejects unexpected capability paths,
rechecks the candidate binding and still requires maintenance V2 participation.
A version string/marker alone never enables this path. No receipt is generated
by the implementation or local tests. Native Phase 4 must establish the evidence
before provisioning one in a disposable fixture. The candidate allowlist prevents
an unvalidated target package's hooks from bypassing the preservation boundary;
a reviewed sustainable migration/candidate-capability deployment mechanism remains
required before general release. Do not manually assert native validation on a
student machine to bypass these gates.

Future provisioning must explicitly create root-owned app-only/runs traversal
directories (0711), request.gate (0600), install the fixed launcher (0755) and policy
(0644), and ensure all ancestors permit intended-reader traversal. Receipt and
snapshot contents remain root-only. These operations and their cleanup must be
reviewed and specifically authorized; they have not occurred here.

## Local review and evidence

Evidence: `evidence/ISSUE72-PHASE3-LOCAL.json`. Core tests verify the late guard
runs after preflight/final pause, failure creates no intent/native effect and
scheduled behavior remains unchanged. Broker tests mock native launch, exercise
fixed invocation, bounded/exclusive files, detached/sanitized launch contract,
capacity rejection and failed-spawn retention. Rust tests cover exact deadline
edges, suspend-aware arithmetic, boot mismatch, malformed request rejection,
ACL encoding and progress publication bounds. These do not constitute an
end-to-end root worker, authentication or lifecycle proof.

A deliberately added owned-scratch-file ACL syscall probe **failed** on this
managed filesystem: fsetxattr returned EOPNOTSUPP (95). The scratch file was
removed before the test reported failure. A direct owned-file Python probe
confirmed errno 95 and removed its file. Preserve this result: the ACL gate is
unproven here. The filesystem-dependent Rust probe remains explicitly ignored by
ordinary checks and can be separately selected on supported disposable storage:

```text
cargo test --locked --manifest-path updater/Cargo.toml --lib linux_request::tests::named_reader_acl_roundtrips_on_an_unprivileged_owned_file -- --ignored --exact
```

This selects only an owned-file ACL probe, not package tests. Do not use broad
`--ignored` selection on desktop application tests. Native ACL failure must not
trigger a permission fallback or an unbounded replacement experiment.

## Next native gates / stopping conditions

Before activation, review this implementation, then validate
on disposable Mint 22 storage supporting POSIX ACLs and polkit with a real active
session/authorization agent. Separate authorization is needed to provision/remove
the fixed root launcher/policy/fixture directories. Start with denial, exact fixed
action/arguments, alternate-admin requesting UID, root-vs-reader tamper rejection,
ACL cross-user access, independent worker/GUI loss, duplicate claims and ownership,
without any real package operation. Stop on privilege ambiguity, broader read or
write access, replay, premature readiness, ownership loss or missing recovery
barriers. Mock results cannot close these gates.

Later, explicitly authorized disposable native package validation must cover the
current/candidate hook capability contract, legacy migration, multiple users and
windows/reopen, suspend/expiry, worker failure around intent/native launch,
known/unknown package children, postcheck failure, recovery and one complete
app-only upgrade. Installed updates, task/service registration, package workflows,
installer builds and release work were not performed in this phase. Windows
privilege implementation and native Win11 proof remain separate.

Historical W2h stays an authentication counterexample. W2i-W2l remain limited;
W2m immediate cleanup remains Fail; W2n N1/N2 remain NotRun. Local diagnostic
completion, cleanup correctness, authentication safety and production readiness
remain separate. This feature is not production-ready or enabled by local tests.

## Parallel disabled Schedule integration — 2026-10-18

The owner now authorizes UI/backend work in parallel with native validation; the
previous prohibition on Schedule wiring is superseded only for capability-disabled
development. The decision record documents the sequencing adjustment. Native
proof, deployed compatibility and privilege gates still block enablement.
