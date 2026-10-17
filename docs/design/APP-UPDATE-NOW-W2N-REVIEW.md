# #72 W2n documentation review — revisions 2–3

Reviewed draft `51a038e` for feasibility, memory safety, observer effects,
evidence integrity, cleanup and coverage. Documentation only: no implementation,
compilation, tests, native experiments, elevation, registration, package action,
workflow/build dispatch or release preparation. No GitHub publication/PR is
part of this review.

## Disposition

The [revised specification](APP-UPDATE-NOW-W2N-RECEIVE-OBSERVATION.md) is a
**conditional diagnostic design, not ready for blanket implementation/execution
authorization**. It can observe the intended boundary if the actual runtime
supports verified interposition. That feasibility is untested. Revision 2
identified D1 (missing concrete interface/layout); revision 3 resolves D1 in the
[ABI v1 addendum](APP-UPDATE-NOW-W2N-ABI.md). Implementation review and healthy
native verification remain later, separate gates; no permission follows from
closing the documentation gap.

W2m's preserved M2 remains Fail: a live extra pipe FD was observed, immediate
closure was not established and receiver inventory changed. Zero unauthorized
actions does not repair cleanup. W2h remains an authentication counterexample;
W2i–W2l retain their limited results. B01–B06 remain open, authentication safety
Unproven and production readiness false. New instrumentation could change
reproduction; it cannot invalidate the original stopped finding.

## Findings and documentation corrections

| Finding in the initial draft | Revision-2 decision |
| --- | --- |
| A next-symbol address outside the observer is insufficient provider verification; a second loaded observer could supply plausible but unrelated status. | Require the intended loaded libc provider, reject unexplained interposer chains without disabling platform controls, and bind the interface instance/token/generation to actual Hello/action interception. No alternate receiver or fallback. |
| Exactly-once preservation was asserted even for unresolved symbols or recursive/corrupt observer state. | Resolve/warm before ready. Preserve forwarding on the valid supported path. Exceptional observer corruption/recursion is an explicit owned-actor abort, Invalid/Incomplete evidence, never a fabricated recvmsg result or claimed noninterference. No async/thread safety claim. |
| Post-call errno preservation omitted entry errno, and bounded copies alone did not establish safe pointer lifetimes. | Restore caller errno before forwarding and real-call errno after capture. Restrict the caller to verified single-threaded test Python; check original pointer/iovec identities and bounded lengths before copying. Unknown memory and crashes yield Incomplete, not guessed recovery. |
| Raw snapshot export and padding redaction had an ambiguous order and a circular parser trust assumption. | Sanitize in fixed observer storage before exports. Expose only checked headers/known data with explicit masks; clear private raw storage. Independently parse sanitized output offline. Allow a final unpadded cmsg, but reject malformed/unknown data without inventing FD integers. Neither parser proves the other is correct. |
| Storage limits lacked explicit scalar/copy accounting and reserved space for overflow reporting. | Maximum 4096-byte capture arena including copies/masks plus 512-byte scalar state. Bound chunk copies at 512 bytes and lines at 4096; enforce generation/range consistency. Reserve 4 KiB within the 128-KiB report ceiling for terminal failures. Do not silently truncate. |
| Exceptions could lose the snapshot or erase a more important authorization failure; the draft implied snapshot survival even after actor death. | After original closure/inventory stages, export immutable captured memory on the normal or exception finalization path, preserving original errors/effects. Never insert retrieval into the immediate-close interval or take new probes after stopping. Lost crash snapshots are explicitly Incomplete. |
| Absence of a native rights header plus a later added FD was over-attributed to the forwarding boundary. | The observations span two times; no exact-return FD inventory exists. They do not establish when installation occurred or prove a kernel cause. Maintain limited metadata-relation labels and Unknown provenance. |
| Observation completion and complete owned teardown could be conflated. | Separate observation, metadata relation, immediate cleanup, authorization, ownership teardown and authentication outcomes. A leak can coexist with complete observation; unaccounted teardown prevents overall session completion. Process exit never becomes immediate EBADF evidence. |

These are source/specification findings, not reproduced runtime failures or
synthetic/native test results. No empirical feasibility or safety claims arise
from this review.

## D1 finding from revision 2 — now resolved in documentation

Revision 2 found **D1 — concrete interface and record ABI not yet specified**.
That historical finding is closed by the documentation-only ABI v1 addendum,
which defines all seven exports, ctypes conversions, fixed return codes,
1536-byte capture, capability/status/provider blocks, field offsets, generation,
visibility masks and exact chunk framing. Raw storage is unreachable through
read before freeze/sanitization. Storage accounting fits the prior ceilings.
No observer or native diagnostic was implemented or executed to close D1.

Do not confuse closure of D1 with the following **later evidence gates**, which cannot be
cleared by another prose review:

- Existing compiler/headers and actual preload/libc-provider support are not
  checked. No installation or privilege request follows automatically from a
  missing prerequisite.
- A future implementation must be reviewed for hidden allocation/TLS/PLT/IFUNC
  work, errno preservation, exactly-once forwarding, arithmetic bounds and
  exceptional aborts. Local mocks cannot prove the installed Python call passes
  through that observer.
- Future local checks must cover malformed/unpadded headers, pointer/length
  mismatch, masks and sensitive padding, immutable snapshots, chunk loss/mixing,
  duplicate entries, overflow reporting and original-error/counterexample
  preservation. These would not be additional native evidence.
- Native N1 must prove actual same-instance capture, matching healthy data,
  correct action result and normal cleanup before N2. Neither native schedule
  is authorized by this review, and no native failure-injection schedule is
  added. Unsupported provider/interception remains Blocked with no substitution.

## Recommended next scope and stopping boundary

Publish the reviewed documentation if requested. With D1 now specified and
reviewed at documentation level, the next smallest separately authorized unit
is observer + local checks only, with native N1/N2 still deferred until that
code and its evidence are reviewed. This separates unresolved design from empirical prerequisites
without promising a successful interception or a W2m repair.

All other W2/W3, production implementation, elevation, registration, package
operations, build dispatch and release preparation remain deferred. No production
transport, capacity, validator, prior harness or native artifact was modified.


## Revision-3 D1 consistency review

The ABI addendum separates fixed wire bytes from host C struct layout, binds
ctypes widths explicitly, specifies errno-neutral control statuses and prevents
OK from implying capture validity or authorization. It defines setup before the
existing Hello, one arm/capture, freeze-before-export, immutable generation 1,
later live-status invalidation and failed-call availability flags. Three capture
chunks cover 1536 bytes exactly; query blocks and raw/sanitized storage fit the
4096-byte arena plus 512-byte scalar ceiling. Padding masks and final-unpadded
cmsg handling preserve the fixed 52-byte case without a receiver workaround.

Review also reconciles prior draft terminology: the wire capture is 1536 bytes,
not the full 4096-byte arena; a freeze operation precedes exports; and status,
provider/ABI queries, chunk framing and unknown/reserved-value rejection now
have exact contracts. No C function or field layout remains intentionally
unspecified. Local implementation/linkage checks and actual native interception
are still unverified, not newly cleared gates. W2m's failure, W2h's
counterexample and all outcome distinctions remain unchanged.
