# W2n isolated observer and local checks

Implemented only the owner's **observer + local-check** authorization, against
published specification `0f33b20`. **No native N1/N2, W2m rerun, Unix-socket
experiment, real descriptor transfer, preload activation or production work.**
No native schedule driver is included. No PR/publication/build dispatch belongs
to this step.

**53 distinct local checks pass: 26 C memory/mock checks and 27 Python
byte-fixture/mock checks.** AddressSanitizer/UndefinedBehaviorSanitizer pass on
the same 26 C checks, not 26 additional schedules. LeakSanitizer is unavailable
in the observed sandbox (ptrace restriction); no leak-freedom claim follows.
Native N1/N2: **NotRun**. Authentication safety: **Unproven**. Production
readiness: **false**. W2m's native M2 remains **Fail**, W2h remains an
authentication counterexample, W2i–W2l retain their limits and B01–B06 remain open.

## Files and authority boundary

| File | Implemented behavior |
| --- | --- |
| `observer.h` / `observer.c` | Exactly seven ABI-v1 control exports plus recvmsg. Fixed wire encoders, measured ABI block, startup-only provider resolution/metadata, one armed bounded capture, raw-storage isolation, sanitizer, immutable export and live coverage flags. No command execution or transaction authority. |
| `check_local.c` | Includes the same core with constructor disabled and receive symbol renamed. The only next-target is a memory-only fake. Resets and abort interception exist only in this test translation unit, never the shared-library exports. No real receive/socket API, signals, children or FD transfers. |
| `evidence.py` | Explicit ctypes binding for a caller-verified already-loaded handle; never loads one itself. Range checks, independent byte/mask parser, exact chunk framing/assembly, live-status consistency checks and bounded in-memory reporting. No native driver or authority decision. |
| `test_evidence.py` | Mocks and fabricated bytes, plus independent decoding of the C-generated synthetic corpus. No shared-library load, socket or actor creation. |
| `run_local_checks.py` | Builds/inspects the shared object **without loading it**; compiles/runs the mock executable, Python checks and memory-only sanitizer executable in a private temporary root. Records commands/hashes/results and removes successful local build artifacts. |

The shared library's receive wrapper forwards unchanged FD/msg pointer/flags to
its resolved target exactly once on its supported path. Entry errno is restored
before forwarding; returned ssize_t and post-call errno are restored after
capture. Volatile bounded byte loops prevent optimizer substitution with lazy
external copy helpers. The wrapper uses a cached startup-thread errno address,
not a TLS helper call on each receive; **only the trusted single-threaded startup
thread is supported**. Forking, foreign threads, async handlers accessing the
observer and arbitrary invalid caller pointers are not made safe by this design.

Provider resolution, dladdr/file metadata and any realpath temporary allocation
are constructor-only, before admission. They are source-reviewed/compiled but
**not executed by these local checks**. ABI queries serialize actual header
measurements; they do not establish `_socket` or loaded-libc provenance. The
future parent still has to verify intended provider, loaded-file identity,
run/process/namespace ownership and actual interception using the existing Hello.

No control API resets an instance or supplies an expected outcome/command. The
observer never closes, probes or acts upon raw FD integers. Control errors leave
caller output untouched and set sticky live issues (NotReady excepted). Freeze
sanitizes only observer-owned storage, clears private raw arrays, and exposes a
fixed 1536-byte generation in three exact chunks. Later receive/API misuse can
invalidate live status while leaving the old capture byte-for-byte unchanged.
A successful API result or structurally Valid capture is not authentication,
validator acceptance or correct resource cleanup.

## Local QA and review

[Source-pinned report](evidence/local-checks.json) contains exact compiler and
check commands, outputs, hashes, disassembly and the explicitly synthetic capture.
The synthetic PID is 101 and the mock rights FD is 77; neither is OS enrollment
or proof that a descriptor was installed. The 18-record C corpus covers Valid,
Invalid and Incomplete records and is independently parsed by Python. Its hash
is recorded; it is reproduced by the local runner rather than called native
kernel evidence.

Local checks cover:

- Actual argument identity/input-memory preservation and single-target-call
  counts in the mock; success errno both changed and unchanged; EINTR/failed
  receives with deliberately unusable returned pointers, without reading them.
- Supported measured ABI sizes; fixed 52-byte synthetic layout; final unpadded
  rights header; padding masks; unchanged original control data; clearing of raw
  observer storage before readable export.
- Oversized control/payload results, unsupported incoming shape, replaced
  pointers/iovec counts/base/lengths, overflow/header bounds, unknown controls,
  partial/negative rights and duplicate credentials. No raw-FD cleanup occurs.
- Immutable freeze/read, output preservation on bad ranges/generation,
  saturating counters, wrong FD, initialization/API misuse and late-call live
  invalidation. Recursion/corruption abort **branches** use test-only longjmp;
  actual `_exit(125)`/process teardown behavior is not natively exercised.
- Independent byte/mask/schema validation, unknown/reserved values, missing,
  duplicate, foreign or malformed chunks/IDs, explicit ctypes widths and Python
  integer-range checks. Report overflow retains a bounded terminal failure.

Review tightened sanitizer privacy before final evidence: the entire unverified
or malformed header/tail is redacted, retaining only earlier verified fields and
an error offset. This avoids exporting guessed/uninitialized header data. The
offline parser cannot infer the hidden error bytes or exact cause. It accepts
those records only as Invalid partial evidence; hiding an inconsistency in a
claimed Valid capture is rejected. Original native caller buffers are untouched.

The production-configuration object exposes only recvmsg + seven specified
control symbols. Build flags enforce immediate binding and RELRO. Inspection of
the compiled recvmsg shows **one indirect target call and exceptional _exit call
sites only**; no allocator, logger, symbol resolver, lock, metadata syscall or
TLS helper call appears in that wrapper. This is evidence for this compiler /
artifact, not proof about the libc target or another build. The unit executable
has no undefined socket/connect/accept/sendmsg/recvmsg/syscall symbol.

Early local development had two compile-only test-driver issues (comma-sensitive
macro and misleading indentation), both corrected. The initial sanitizer run
failed at LeakSanitizer's ptrace limitation; the recorded final address/undefined
checks explicitly use `detect_leaks=0`. These are local development/tooling
results, not authentication counterexamples or additional native experiments.
No sanitizer or host security setting was changed globally.

## Reproduction: local checks only

From the repository root, with existing `cc`, `nm`, `objdump`, `readelf`, Python
standard library and compiler sanitizer support:

```sh
python tests/prototypes/manual-update-w2n/run_local_checks.py work/w2n-local-report.json
```

This creates a 0700 temporary build root under `work/`, waits for every local
command, inspects binaries without preloading them, and removes the successful
root. Missing tools/failing checks stop and preserve local artifacts, with no
installation/elevation/fallback. The final observed successful report records
root removal. There are no native actors, transferred FDs, service registrations
or observer preload settings to restore. Existing W2m/W2i files are unchanged.

Do **not** run the shared object under LD_PRELOAD or add an N1/N2 driver under
this authorization. The checked-in evidence does not contain or imply such a
command. A later implementation review and separate native authorization are
required first.

## Remaining gates

1. Review the C code, startup resolver, Python decoding and failure/export
   integration. Local fake receives cannot prove actual Python-path symbol
   interception, provider identity, platform mediation, cancellation or loader
   behavior. Native source/build provenance is still unverified.
2. A future separately authorized N1/N2 driver must add trusted process/pidfd
   enrollment, secure fixture/evidence publication, explicit barriers, live
   library/provider validation, stop-aware export after original closure checks,
   independent FD inventories and owned-process cleanup. None is implemented as
   a native schedule here. `BoundedReport` is an in-memory helper, not secure
   on-disk persistence or evidence of its successful recovery.
3. Actual aborts, crashes, snapshot loss, signal/retry behavior, hostile writers,
   resource exhaustion, partial kernel FD delivery/cleanup and protected bootstrap
   remain unvalidated. No all-threads memory isolation or same-UID adversary
   defense is claimed for the observer itself.

Native observation completion, immediate FD cleanup, authorization, owned
teardown and authentication safety must remain independent outcomes. A future
instrumented non-reproduction cannot invalidate W2m, and teardown cannot repair
its missing immediate closure proof. All production implementation, other W2/W3,
elevation, registration, package operations, build dispatch and release
preparation remain deferred.

## Isolated implementation and local-evidence review

Reviewed baseline `12f3f0b` against ABI-v1 and the receive-observation specification.
Source review covered forwarding and errno preservation, bounded copies and
sanitization, immutable export, lifecycle/error handling, and ctypes/serialized
record agreement. No change to the C observer, transport, receive capacity or
validator was required by this review. This is source and mock evidence, not
native interception or authentication validation.

Two local evidence-helper defects were reproduced before correction:

* Final consistency accepted seven status/capture disagreements: resolution,
  quality, selected FD, arm baseline, window entry count, window exit count and
  last FD. Decoding now checks lifecycle/process/counter invariants and final
  consistency binds those status fields to the capture. The synthetic status
  fixtures now encode the actual final FD and unselected `-1` sentinels.
* Report overflow silently discarded the caller's final outcome. Finalization
  now retains a bounded original outcome under the explicit Incomplete overflow
  result, preserves the first terminal record, and rejects an oversized terminal
  outcome rather than silently discarding a failure or counterexample. A future
  driver must handle that explicit failure; this helper does not persist reports.

`evidence/review-regressions-before-fixes.txt` records the eight baseline
reproductions (seven inconsistent-status acceptances and one discarded outcome).
They are local evidence-integrity failures, not native authorization results.
`evidence/local-checks.json` is preserved unchanged as historical evidence.
`evidence/reviewed-local-checks.json` records the corrected source hashes and
**57 passing checks: 26 memory-only C checks and 31 Python checks**. ASan/UBSan
repeat the same C checks successfully; LeakSanitizer remains unavailable and is
not claimed passing. The 18-record C-generated synthetic capture corpus is
unchanged. The private build root was removed and settings were unchanged.

Remaining ABI coverage limits: fake ctypes binding and synthetic bytes do not
prove calls through a dynamically loaded library, real constructor/resolver or
provider metadata, runtime native structure compatibility, or the native Python
recvmsg path. Actual process aborts, native FD ownership/closure and secure
stop-aware report persistence also remain untested. The existing remaining gates
above still apply; this review closes neither native N1/N2 nor B01–B06.

Diagnostic native completion: **NotRun**. W2m immediate cleanup: **Fail,
unchanged**. Current native authorization and owned-actor cleanup: **NotRun**.
Authentication safety: **Unproven**. Production readiness: **false**. W2h's
counterexample and W2i–W2l's limited results remain intact. No native experiment,
preload, W2m rerun, production change, publication or build dispatch occurred.
