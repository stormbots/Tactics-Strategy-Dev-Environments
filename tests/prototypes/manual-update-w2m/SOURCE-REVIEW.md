# W2m stopped-failure source review

Documentation and local evidence-check review only. No native experiment,
ancillary-capacity change, transport change or validator change occurred.

## Conclusion and evidence boundary

The original M2 failure stands. Its six-to-seven FD inventory change exposes a
live CLOEXEC pipe end matching the sender's pipe, while Python's returned
ancillary tuples expose credentials only. No returned rights integer reaches
`rights_from` or the unchanged validator, so both cleanup loops have empty lists.
The receiver rejects the command with zero authorized actions; its resource
cleanup invariant fails independently of that authorization result.

**Reviewed upstream source does not explain the discrepancy.** On the reviewed
64-bit layout, 52 bytes should accommodate credentials plus one descriptor and
permit normal ancillary traversal. The source supports that layout expectation,
not a claim that the installed runtime actually traversed those headers.

The report does not contain raw syscall control-buffer memory, returned native
`msg_controllen`, header offsets/lengths or a verified build provenance for the
installed interpreter/kernel/libc. Exact deployment source, runtime patches or
syscall mediation are not established. No such mechanism is asserted as the
cause. Treat this as an unresolved test-path discrepancy, not a confirmed generic
Linux/glibc/CPython vulnerability or a reason to bypass the stop rule.

## Sources reviewed

Retrieved text was read only; it was not compiled or executed. SHA256 pins below
identify the reviewed contents. Upstream tags are comparison references, not
attestation of the installed binaries.

| Source | Relevant locations | SHA256 |
| --- | --- | --- |
| [CPython v3.12.14 socketmodule.c](https://github.com/python/cpython/blob/v3.12.14/Modules/socketmodule.c#L4082) | `cmsg_min_space` / `get_cmsg_data_len` (2814–2900), `sock_recvmsg_guts` (4082–4210) | `d0089780e209ce9f0297d54cf9ec488e90f6b84f98d6bbf48310ba3da4c49314` |
| [Linux v6.18 net/core/scm.c](https://github.com/torvalds/linux/blob/v6.18/net/core/scm.c#L255) | `put_cmsg` (255–301), `scm_max_fds` / `scm_detach_fds` (349–406), `__scm_recv_common` (502–531) | `e66ffbd376d67bce8b0f7c12c45ea9fb6a5fb300c20c0fa02a86c08dfe954078` |
| Local `/usr/include/x86_64-linux-gnu/bits/socket.h` | CMSG macros and `__cmsg_nxthdr` (303–363) | `54658ef138fe725785e8458253497fe894ec17456324b1731e75fe80fd20b856` |

The installed report says Python 3.12.14 and Linux 6.18.44/glibc 2.41. The Linux
v6.18 reference is **not** the exact 6.18.44 build source. The local libc header
need not be the header used to build the installed `_socket` extension. These
limitations prevent source review from identifying the actual execution path.

## Expected layout from the reviewed sources

The local header defines `CMSG_ALIGN(n)` using `sizeof(size_t)`, `CMSG_LEN(n)` as
aligned header size plus n, and `CMSG_SPACE(n)` as aligned header plus aligned n.
The saved run's fixed formula gives 32 + 20 = 52 bytes. On the reviewed x86-64
layout the header is 16 bytes and alignment is eight bytes.

1. Linux's credential path emits credentials before rights. `put_cmsg` writes
   a header length of CMSG_LEN(12)=28 and advances by CMSG_SPACE(12)=32, leaving
   20 bytes. Other enabled control types would need separate consideration;
   the saved returned metadata contains credentials only.
2. `scm_max_fds` computes `(20 - 16) / 4 = 1`. `scm_detach_fds` can install one
   FD with O_CLOEXEC, write a rights header length CMSG_LEN(4)=20, and advance
   by the lesser of CMSG_SPACE(4)=24 and the remaining 20 bytes. With two sent
   descriptors, the partial count also sets MSG_CTRUNC. This path predicts a
   rights header at offset 32 and FD data at offset 48 through 51.
3. For a returned native control length of 52, the local glibc `CMSG_NXTHDR`
   check on the first length-28 header needs 16 + 4 padding + 28 = 48 bytes.
   Fifty-two is sufficient; the next header is at aligned offset 32.
4. CPython's success path iterates CMSG_FIRSTHDR/CMSG_NXTHDR and
   `get_cmsg_data_len`. If that second header has length 20 within 52 bytes,
   its four-byte FD data fits and should become an SCM_RIGHTS tuple. MSG_CTRUNC
   by itself does not suppress that iteration. Its exception-cleanup path also
   uses header traversal, but the saved call returned normally and reached the
   validator; no wrapper exception was recorded.

Consequently, the claim "CMSG_LEN lacks padding, so Python necessarily skips the
FD" is **not supported** by these sources. Nor is "the kernel automatically
closed every excess FD" consistent with the additional live receiver FD. One
can reject those explanations without asserting where the actual discrepancy
originated.

## Harness and evidence audit

Source review of the fixed harness confirms:

- The server has no transfer-pipe creation operation in this schedule. The
  sender alone creates a pipe, and its metadata is captured before sending.
- The inventory scanner keeps its directory handle live, excludes exactly one
  matching directory identity, and does not silently ignore EBADF. The new
  FIFO entry cannot be explained as that excluded directory descriptor.
- `installed` is an inventory of integers from returned SCM_RIGHTS tuples,
  not a complete inventory of every kernel-installed FD. `raw_ancillary` is
  hex-encoded **Python-returned tuple data**, not raw syscall memory.
- The unchanged validator first collects returned rights, then rejects
  MSG_CTRUNC. This gives correct fixed-action rejection but cannot close an
  FD whose integer was absent from the returned tuples. Returning zero actions
  is not a resource-cleanup pass.
- M2 stops immediately on inventory mismatch. Later sender validity, final
  instance checks and graceful stops were not collected. Forced owned-actor
  cleanup is explicit; process teardown does not establish immediate EBADF.

The original local audits had gaps: dictionary conversion hid duplicate FD
entries, validator flags were not bound to raw receive flags, and the runner
PID was not bound to actor parent identities. The preserved
[before-fix audit-gap record](evidence/review-audit-gaps-before-fixes.txt) shows
three corrupted reports accepted by selected original audit methods. Those are
synthetic evidence-assurance counterexamples, not additional native failures or
authentication counterexamples.

The revised test file adds an offline stopped-prefix relationship audit:
barrier/index/time order, runner/actor/enrollment identities, socket options,
initial credential checks, sender pipe ownership, both attachments, complete
payload hash/length, counters, actual receive/validator flags, unique typed FD
inventories, receiver endpoint and forced cleanup accounting. Ten corruption
variants must be rejected. Existing checks preserve the observed extra FD,
returned credentials, absent rights, missing immediate closure and stopped
failure classification.

[Reviewed checks](evidence/review-checks.txt): **31 pass** (23 synthetic/mocked
checks and eight saved-report audit methods). The ten corruption variants are
subtests, not native schedules. Local tests import definitions and use mocks or
the preserved JSON; they do not execute actor entrypoints. The one existing
mocked main check uses a fake `run_case`, so it cannot rerun M1 or M2.

The original runner, shared helper, native report, pre-native log and original
29-check output remain byte-for-byte unchanged. Only documentation, local
checks and artifact hashes changed. No native acceptance criterion has been
relaxed and M2 remains Fail; diagnostic success=false, authentication
safety=Unproven and production readiness=false. W2h's authentication
counterexample and W2i–W2l's limits remain unchanged.

## Next decision and deferrals

Review and publish this stopped finding before authorizing further native work.
Any later proposal must explicitly identify the missing raw control-buffer /
returned-length observation and a bounded way to distinguish source expectations
from actual runtime behavior. It must be separately authorized; this review does
not authorize raw-syscall probes, alternate receivers, capacity tuning, retries,
FD-inventory-based production cleanup or a validator workaround.

All other W2/W3, production implementation, elevation, registration, package
operations, build dispatch and release preparation remain deferred. B01–B06
remain open. No GitHub publication or PR belongs to this review.
