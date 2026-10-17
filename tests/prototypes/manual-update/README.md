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

Current revision-3 checks: **44 tests passed**; see
[revision-3 evidence](evidence/revision3-results.json),
[test output](evidence/revision3-tests.txt) and [reviewed results](EVIDENCE.md).
The unchanged actor graph still explores **1,438 states / 3,535 edges**, maximum
 depth 24 and cap 150,000, without truncation or a baseline safety counterexample.
That graph does not include the new numeric timing/client/cache state space.
Three graph mutants and the missing-directory-flush control remain detected.

The [original revision-2 report](evidence/local-results.json) and
[original output](evidence/local-tests.txt) are preserved, not overwritten.

The parser tests cover every split and nonempty truncated prefix of the fixture
Commit frame, bytewise input, coalesced frames, a maximum-length whitespace-padded
legal frame, 500 seeded malformed byte strings, duplicate/unknown keys/types,
UTF-8/depth/integer/string limits, frame/chunk lengths, slow partial input and
clock discontinuity. The temporary receive high-water bound includes at most one
4096-byte incoming chunk in addition to the 16-KiB framed payload. This is an
allocation bound of this parser, not measured native IPC memory use.

## Counterexamples and prototype limitations

Revision-2 counterexamples remain documented in [EVIDENCE.md](EVIDENCE.md).
Revision-3 regressions now check commit-time freshness, bounded continuation,
current deadline-bound close grants and separate query accounting. They do not
establish real peer authentication or atomic GUI-close/install behavior.
PrepareLatestStable remains outside the already-Ready controller fixture; the
three-slot mutation rule is modeled with commit/cancel only (at most one accepted
branch). There is no complete preparation/retry orchestration implementation.

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
proved in later authorized work. Controller/bridge gate, live-channel and shared-clock checks use injected facts,
not proof of native admission ownership or clock mapping.

The report gives **28 cases partial L1 model evidence, 20 Not run**, and marks native
status Not run for all F01–F48. A partial row does not mean all aspects of that row
passed. F33 desktop/accessibility, privilege/polkit/UAC, package hooks, actual
legacy upgrades, power-loss durability and real recovery remain unverified.
B01–B06 all remain unresolved; no native acceptance or implementation-readiness
claim is made. W2/W3, production integration and any workflow/build/release actions
need separate authorization. The approved v1.2.9 fleet rollout is unchanged.

## Subsequent specification review

[Protocol revision-3 decisions](../../../docs/design/APP-UPDATE-NOW-W1-REVIEW.md)
resolve the three findings. The current isolated harness checks the selected revision-3 rules locally.
Original revision-2 reports remain historical; native validation is pending.
