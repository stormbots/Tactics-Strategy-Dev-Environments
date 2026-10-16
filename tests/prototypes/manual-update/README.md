# #72 W1: isolated local protocol harness

**Evidence level L1 only. Not a production updater or privileged IPC library.**
Implemented under the owner's W1-only authorization. Python 3.12 standard library;
Rust was unavailable and the approved plan permits a standalone test harness.
No third-party installation is needed.

## Run locally

From the repository root:

```bash
python tests/prototypes/manual-update/run_checks.py > work/w1-results.json
```

Create `work/` first if it does not exist. Tests go to stderr and the complete JSON
report goes to stdout. Exit zero means local checks passed, baseline exploration
found no modeled safety violation within its bounds, and all deliberately broken
graph controls were detected. It does not mean the protocol is ready to ship.

For tests alone:

```bash
python -m unittest discover -s tests/prototypes/manual-update -p test_harness.py -v
```

The runner never invokes a shell, installed updater, privilege prompt, real lock,
socket/pipe, scheduler, package manager or downloaded executable. It does not create
workflows or dispatch jobs. Its only test disk mutation is a fixed-name sentinel
inside a fresh TemporaryDirectory, removed afterward; the crash filesystem is
synthetic in-memory state. Reports are written only by the caller's stdout redirect.
No production modules are imported or modified. No release version is allocated;
1.2.9/1.2.10 are fixed illustrative test strings.

## Components

| File | What is actually implemented |
| --- | --- |
| `model.py` | Immutable finite actor state, named scheduling barriers, independent state/edge invariants, BFS with shortest counterexample and explicit depth/state limits. |
| `framing.py` | Incremental in-memory length framing, strict schema/JSON bounds, synthetic frame deadlines, fake authenticated controller, command-ID replay/rate/cache bounds and coalesced output slot. |
| `durability.py` | Chosen volatile/durable inode/namespace semantics, crash boundaries and an in-process fake child that writes one temporary sentinel. No actual filesystem durability claim. |
| `timing.py` | Injected clock budgets for Ready/drain/freshness/intent and suspend/boot invalidation. No OS clock/suspend test. |
| `test_harness.py` | Deterministic local scenarios, malformed input corpus, every split/truncation boundary, negative controls and regression checks. |
| `run_checks.py` | Local runner, source hashes, scope-audit aid, computed findings and F01–F48 evidence ledger. |

The import allowlist/dynamic-execution check is a static review aid, not an OS
sandbox or proof against arbitrary malicious Python. Review the source before use.
Native authentication is a deliberately injected Boolean fact. The public fixture
capability does not authenticate any real OS peer. None of these modules is an
approved shortcut for implementing B01/B02.

## Local results

See [results and findings](EVIDENCE.md), [machine-readable report](evidence/local-results.json)
and [test output](evidence/local-tests.txt). Final run: **38 tests passed**;
**1,438 states / 3,535 edges** exhausted in the chosen finite model. Maximum depth
24, state limit 150,000; no depth frontier/state-limit truncation was encountered.
This is the whole reachable graph of this particular small abstraction, not the
whole application protocol or arbitrary multi-process executions.

Three graph negative controls yield shortest counterexamples: omit admission,
skip post-session journal validation, or spawn before intent. A fourth synthetic
filesystem control omits directory persistence and is detected before accepting
mutation as protected. See the JSON report for actual traces.

The parser tests cover every split and nonempty truncated prefix of the fixture
Commit frame, bytewise input, coalesced frames, a maximum-length whitespace-padded
legal frame, 500 seeded malformed byte strings, duplicate/unknown keys/types,
UTF-8/depth/integer/string limits, frame/chunk lengths, slow partial input and
clock discontinuity. The temporary receive high-water bound includes at most one
4096-byte incoming chunk in addition to the 16-KiB framed payload. This is an
allocation bound of this parser, not measured native IPC memory use.

## Counterexamples and prototype limitations

1. **W1-C01:** fresh eligibility at t=0, commit at t=0, valid session drain at t=11
   yields `deferred_stale_eligibility`, despite the 30-second drain allowance.
   Safe but potentially frustrating; D01 needs an explicit freshness/cutoff decision.
2. **W1-C02:** blindly replaying a cached accepted Commit after the handoff has
   already deferred would tell the GUI to close without an active reservation.
   The prototype returns idempotent effect history plus current state and grants
   close authority only while currently committed. The protocol must specify the
   required current-state/deadline/lock validation for a real acknowledgement.
3. **W1-C03:** the intentionally conservative all-command cache fills after 32
   ordinary GetStatus polls. A subsequent Commit is rejected, even inside the
   five-minute Ready period. Define query accounting/reserved mutation capacity;
   do not silently evict replay protection or treat this controller as shippable.

These are counterexamples to timing/ACK/cache interpretations, not proof of defects
in released v1.2.9. They are retained even though the tests confirming their safe
or guarded outcomes pass. Three explicit mutant failures are negative controls,
not failures of the baseline graph.

The first development run also found an overly broad harness oracle: a successful
historical manual receipt may coexist with a newer legacy transaction's journal.
The corrected decision gives current intent precedence, rather than forbidding
historical receipt retention. Its regression is in the current suite; the
[initial failed development run](evidence/initial-oracle-failure.txt) is retained
and is not final acceptance evidence or a run of the final source hashes.

## Scope of the evidence

The graph models one manual attempt, an initiating GUI, one additional participating
GUI and one legacy O/S-only actor. Locks are logical ownership fields. A legacy
actor persists intent but is not an actual legacy package process. There is no
unbounded sequence of repeated launches, real process death/handle inheritance,
OS scheduling fairness, package hook, target capability parser, signature validation,
real privilege/account check, native startup notice or actual GUI.

The frame/controller, graph, synthetic storage and clock are **separate abstractions**,
not one integrated root supervisor. Graph deadlines are explicit transitions;
numerical deadlines are checked in focused clock scenarios. There is no universal
liveness proof. Real lock ownership/IPC acknowledgement/deadline binding must be
proved in later authorized work. In particular the controller's phase guard is
not proof of native admission ownership.

The report gives **28 cases partial L1 model evidence, 20 Not run**, and marks native
status Not run for all F01–F48. A partial row does not mean all aspects of that row
passed. F33 desktop/accessibility, privilege/polkit/UAC, package hooks, actual
legacy upgrades, power-loss durability and real recovery remain unverified.
B01–B06 all remain unresolved; no native acceptance or implementation-readiness
claim is made. W2/W3, production integration and any workflow/build/release actions
need separate authorization. The approved v1.2.9 fleet rollout is unchanged.

## Subsequent specification review

[Protocol revision-3 decisions](../../../docs/design/APP-UPDATE-NOW-W1-REVIEW.md)
resolve the three findings. This unchanged harness and recorded evidence remain
a revision-2 baseline; revision-3 conformance and all native validation are pending.
