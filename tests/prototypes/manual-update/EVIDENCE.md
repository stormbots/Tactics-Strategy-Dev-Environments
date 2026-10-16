# W1 local evidence and protocol findings

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
