# #72 W1 review: protocol revision 3

Status: specification decisions only. W2/W3, production implementation, elevation,
registration, package operations, workflows, build dispatch and releases remain deferred.

## Reviewed evidence

Reviewed the W1 controller, framing, timing budget, graph exploration, synthetic
persistence checks, runner and recorded evidence at
`18ab9750ff421a7a29f97911ee3055424a7c80bb`. An unchanged local rerun passed
38 tests and reproduced 1,438 states / 3,535 edges, all three deliberate graph
counterexamples and the three reported protocol findings. No baseline safety
counterexample was found within that finite graph. The modules are separate
abstractions, not an integrated supervisor; authentication is injected, locks and
filesystem durability are synthetic, and no native desktop validation occurred.
The original 28 partial / 20 not-run fault ledger remains historical L1 evidence.

## Decisions

| Finding | Revision-3 rule | Consequence |
| --- | --- | --- |
| W1-C01 | Eligibility age ≤10 seconds at accepted commit while acquiring A; drain <30 seconds; final launch decision <45 seconds from A acquisition | An 11-second drain no longer fails merely because evidence aged. Evidence age at final launch decision is <55 seconds. No network after admission closure, deadline renewal or candidate substitution. |
| W1-C02 | Preserve accepted effect history, regenerate current close authority, bind replies to the authenticated attempt and absolute drain deadline | A replay after Deferred cannot authorize closing. Delayed replies expire independently of delivery. Native bridge clock mapping and peer/lease proof remain blockers. |
| W1-C03 | Queries have separate IDs and bounded coalesced replies; reserve non-evicting mutation slots by logical action | Arbitrarily many sequential polls cannot consume commit capacity. Rate and queue bounds still apply; no duplicate effects through ID eviction or alternate IDs. |

The deadline bounds the final local decision immediately before spawn, not an OS
scheduling guarantee. Once intent is durable, timeout cannot erase uncertainty.
A signed, bound snapshot can become remotely outdated during the bounded handoff;
there is no atomic GitHub-to-spawn guarantee. Policy and local integrity are still
checked immediately before launch.

A close grant is current at generation and must remain within its absolute
monotonic deadline at bridge validation. No asynchronous reply can guarantee the
supervisor survives until GUI exit. A crash in that gap can close SDE without an
update; it must never permit mutation without locks/intent. This limitation is
explicit rather than treated as a guaranteed install or automatic reopen.

## Required W1 alignment before claiming revision-3 coverage

1. Timing: eligibility ages 10 and just over 10 at A acquisition; A contention
   crossing freshness; drains 11, 29.999 and 30 seconds; final decisions 44.999 and
   45 seconds; intent flush crossing the deadline; candidate changes, pause,
   sleep/boot changes, and no post-admission network work. Check maximum snapshot
   age and retain uncertain intent rather than timer-clearing it.
2. Close grants: accepted effect retained after timeout but close authority false;
   lost ACK retry; delayed first response and duplicate response; terminal sequence
   superseding older response; wrong incarnation/channel/Ready/digest; missing O/A;
   expired or unmappable clock; disconnect and supervisor crash between bridge
   validation and GUI exit. Count one commit effect throughout.
3. Cache accounting: more than 32 sequential polls followed by a valid commit;
   query/mutation ID collision; repeated and altered mutation payloads; different
   IDs for one logical action; rejected-request floods; bounded outstanding query,
   coalesced reply and permanent mutation memory. Polls must not advance event
   sequence or extend Ready/drain/launch deadlines.

The unchanged W1 harness deliberately still models revision-2 timing and the
all-command cache. Its phase-only close check does not establish the full grant
conditions above. Do not relabel those passing tests as revision-3 conformance.
Updating that isolated harness is the next proposed step, not production work.
All B01–B06 remain open; native privilege, lifetime, durability and compatibility
proof are still required under separately authorized W2/W3 work.


## Subsequent authorized W1 alignment

The [revision-3 execution record](../../tests/prototypes/manual-update/EVIDENCE.md#revision-3-alignment-execution)
records 44 passing local tests of selected rules above. The old reports remain
unchanged historical evidence. Preparation orchestration, native clock/peer/gate
proof, full integrated race coverage and W2/W3 remain pending. This follow-up does
not clear B01–B06 or authorize production implementation/build dispatch.
