# W1 local evidence and protocol findings

**Current:** the 51-test revision-3 harness review appears at the end. The original table and
traces in this document describe the preserved revision-2 run.

Status: local L1 evidence only. Source hashes are in
[evidence/local-results.json](evidence/local-results.json). The JSON runner
computes all three scenario findings from live in-memory fixture execution.

| Check | Result | Limit |
| --- | --- | --- |
| Standard-library test suite | 38 passed; zero failures/errors | Local Python 3.12.14 on Linux; no Windows/Mint native proof |
| Chosen actor graph | 1,438 states, 3,535 transitions; exhausted under depth bound 24 and cap 150,000 | One attempt, two GUIs, one legacy surrogate; logical locks only |
| Baseline safety counterexample | None in that graph | Does not prove the real protocol or universal liveness |
| Deliberate graph defects | All three detected with shortest traces | Admission omission, post-session journal omission, spawn without intent |
| Synthetic crash filesystem | 11 persistence boundaries checked; missing-directory-flush control detected | Assumed inode/namespace model, no NTFS/ext4/power-loss validation |
| Framing/control | Split/truncation corpus, seeded malformed bytes, bounds, replay and cancellation checks passed | In-memory adapter; native peer authentication is injected, not implemented |
| Fault ledger | 28 partially modeled; 20 Not run | All 48 native statuses remain Not run |
| Production/workflow changes | None | No elevation, task/service registration, package operation, build dispatch or release preparation |

## Required protocol decisions before integration

### W1-C01: freshness versus drain allowance

Trace: eligibility refreshed at 0 → commit at 0 → existing sessions finish at 11.
The strict ten-second freshness interpretation yields safe Deferred before the
thirty-second drain allowance expires. Decide whether freshness is checked at
commit or spawn and what maximum bounded handoff staleness is acceptable. Do not
fetch over the network after closing SDE or silently lengthen a security deadline.

### W1-C02: historical ACK is not current close authority

Trace: Commit accepted and its ACK cached → session-drain deadline yields Deferred
and releases admission → original command ID is replayed. Blindly returning the
old ACK as a new close instruction causes an unnecessary close after the install
reservation ended. Preserve exactly-once/idempotent effect history but separately
validate current transaction state, deadline, supervisor incarnation and admission
ownership before authorizing GUI close. The W1 fake controller checks current
phase; this is not proof of those native conditions.

### W1-C03: read-only polling exhausts an all-command cache

Trace: 32 GetStatus queries with unique IDs at seconds 1–32 → Commit at second 33.
The conservative bounded cache rejects Commit with no installation effect. This
is safe resource behavior but unsuitable UX. Specify whether queries bypass the
mutation replay cache, use separate sequence accounting, or reserve consent
capacity. Reusing/evicting a mutation command ID must never permit duplicate effects.
The W1 conservative controller intentionally retains this behavior for review.

## Development oracle correction

The [initial development output](evidence/initial-oracle-failure.txt) includes a
failed invariant when a historical Updated manual attempt was followed by a new
legacy journal. The model decision must consult current trusted intent, while
retaining historical results. The corrected oracle and a dedicated regression
cover this. This was a harness-oracle error, not a production defect or native
experiment. Final checks pass; the earlier failure is not concealed.

## Blocker disposition

B01 SYSTEM broker, B02 OS-authenticated IPC, B03 independent process lifetime,
B04 real hook/target migration, B05 native durability/recovery, and B06 native
coordination/desktop proof remain open. W1 supplies only bounded model evidence
for selected state, ordering, parsing and timing aspects. Do not proceed directly
to production implementation or claim that native UAT has passed.

## Subsequent specification review

[Protocol revision-3 decisions](../../../docs/design/APP-UPDATE-NOW-W1-REVIEW.md)
resolve the three findings. Original recorded evidence remains a revision-2 baseline. Selected revision-3
rules now have isolated local checks, as recorded below; native validation is pending.


## Revision-3 alignment execution

[Machine-readable report](evidence/revision3-results.json) and
[test output](evidence/revision3-tests.txt): **44 tests passed**, zero errors/failures.
Source hashes bind that historical report to commit `3aa0c0e`, not the
subsequently reviewed files. Graph results
remain 1,438 states / 3,535 edges, no baseline counterexample within the chosen
abstraction; all three graph mutants and the synthetic persistence defect are detected.
The 28 partial / 20 not-run ledger is unchanged; every native status is Not run.

- Timing: age 10 accepted versus 10.001 requiring refresh at A acquisition;
  11/29.999-second drains continue versus 30 deferring; final launch decision at
  44.999 versus 45 seconds includes intent work. Intent is retained on uncertain
  expiry. Pause/integrity failures, Ready expiry, boot/suspend/invalid clocks and
  commit retries are checked. No spawn, actual network or durable I/O occurs.
- Close grant: historical effect retained after deferral but authority false;
  delayed first/replayed ACK expiry; binding changes, lost O/A, terminal ordering,
  unmappable clocks, suspend, EOF/liveness and clock rollback reject close. A
  supervisor crash after validation remains an explicit non-atomic boundary.
- Cache: 200 sequential queries leave zero mutation entries and allow one commit
  after modeled pre-admission eligibility refresh. Colliding query/mutation UUIDs,
  different IDs for one accepted action, conflicting payloads, rejected floods,
  rate limit and one outstanding query are checked. Queries do not advance event
  sequence, authorize close or renew deadlines. Accepted mutation records persist.

No new baseline counterexample arose in these checks. This is selected L1 rule
alignment, not full revision-3 protocol conformance. The controller starts Ready;
preparation orchestration, OS ownership/authentication, clock mapping and real
supervisor/client races remain unimplemented. Numeric checks and actor exploration
are separate abstractions, not an integrated updater or universal liveness proof.
B01–B06 remain unresolved. W2/W3, production implementation, elevation, task/service
registration, package operations, workflows, build dispatch and releases remain deferred.


## Revision-3 harness review

Reviewed alignment commit `3aa0c0e`. Four added regressions failed against that
implementation; [pre-fix output](evidence/revision3-review-counterexamples.txt)
records the 48-test development run (the original 44 plus four new regressions).
These are isolated harness counterexamples, not released-app findings:

| Finding | Reproduced behavior | Fix |
| --- | --- | --- |
| H3-R01 Abort resurrection | Pause/integrity/clock failure returned Deferred; a later call could return may_write_intent | Sticky attempt stop/clock invalidation; uncertain intent remains retained |
| H3-R02 Cross-message ordering | A terminal status with query correlation was ignored, allowing an older commit grant | Observe authenticated bound status/progress sequence and terminal state before checking commit correlation; status itself never grants close |
| H3-R03 Grant resurrection | After rejected clock mapping/suspend/EOF, the same grant could later be accepted | Permanently invalidate that bridge attempt on uncertainty/loss; a new attempt is required |
| H3-R04 Queued status staleness | Queued Ready snapshot could be consumed after commit as Ready | Regenerate the bounded pending-query response from current state at consumption |
| H3-R05 Rate boundary gap | Fixed buckets permitted ten frames at .999 and another at 1.0 | Bounded sliding one-second window; a focused cross-boundary regression rejects the extra frame |

The explicit controller timeout barrier now checks Ready and drain expiry and
releases its fake reservation without a client read. Added regressions also cover
progress with different correlation, boolean epoch confusion, and paused/failed
terminal states. Status/progress observation still assumes an authenticated native
channel; it does not implement or prove that assumption.

[Reviewed report](evidence/revision3-reviewed-results.json) and
[reviewed test output](evidence/revision3-reviewed-tests.txt): **51 tests passed**,
zero errors/failures. The report hashes the reviewed Python files and computes
observations for abort, stale status, terminal ordering, clock uncertainty, rate
boundary and fake timeout release. Original revision-2 and 44-test revision-3
reports are preserved unchanged. The actor graph remains 1,438 states / 3,535
edges with all three graph negative controls detected, and synthetic missing-
directory-flush detection remains intact. No baseline counterexample arose in
that graph. The graph is unchanged and does not explore these new numeric rules.

Remaining gaps: preparation and full mutation-slot lifecycle are not implemented
(the controller starts Ready); close-grant responses are Python snapshots, not a
native response decoder; queues, gates, channel/process identities and clocks
remain injected facts; explicit ticks are not scheduler/liveness proof. The
controller and numeric budget are not an integrated installer supervisor. Real
clock mapping, ACL/IPC authentication, process death, package operations, power
loss, migration and desktop behavior remain unvalidated. All 48 native fault
statuses remain Not run; B01–B06 remain open. No W2/W3, production implementation,
elevation/registration, workflow/build dispatch or release work was performed.
