# Guided Overview release — draft validation and UAT plan

Status: **acceptance plan; #150 automated/native validation complete; #151 candidate preparation in progress; owner UAT Not run.**

Planned candidate **1.2.23**. Automated/native implementation source:
`8e3c4463a475ed9fc7f89c88669fb12c129cf618`, final-main Build 42959957444 passed.
Candidate-preparation source/tag, signed asset hashes and owner execution results
remain **Pending / Not run** in the [candidate record](OVERVIEW-UAT-1.2.23.md).
Stable v1.2.22 acceptance remains separate.

Implementation execution is tracked separately in the
[WF01–WF31 evidence ledger](OVERVIEW-WORKFLOW-EVIDENCE.md). It records tested
source/layers, remaining native fixture gaps and unrun candidate/owner checks;
this draft remains the acceptance plan, not an execution result.

## 1. Goal and design baseline

Prove that SDE gives the student the right next action from real findings, keeps
the reviewed journeys understandable and provides a safe way forward when an
operation cannot finish. A successful happy path alone is not release acceptance.

References:

- [Overview design and acceptance criteria](OVERVIEW-NEXT-STEP-DESIGN.md).
- [Reviewed offline prototype](overview-next-step-demo/index.html).
- [Prototype scope and checks](overview-next-step-demo/README.md).
- [Accepted Recovery clear-state contract](RECOVERY-CLEAR-STATE.md).
- [Acknowledgment boundary](adr/0001-interruption-acknowledgment-boundary.md).
- [Fresh native safety contract](adr/0002-lease-bound-recovery-transition.md).

The owner followed every demo scenario and reported no unnatural workflows,
loops or undesirable destinations. Treat that as design review, **not production
UAT or native execution evidence**. The demo intentionally remains unchanged.

The design now makes these acceptance paths explicit in sections 9, 10 and 13:
failed/incomplete results without retry loops; proven-not-started versus uncertain
cancellation; fresh reconstruction after reopen; changed evidence before execution;
combined-finding precedence; verified readiness rather than installer-exit success;
and secondary actions with the same admission/busy guards. The matrix below is
the traceable checklist for those rules, not a claim that tests already exist.

The owner's later correction controls the ready-with-updates state:

- Top Development environment card: prominent **Ready!**.
- Your next step heading: **Install updates**.
- Exact body: **Your setup works, but there are updates available if you would like to install them.**
- Primary action: **Review updates**, replacing Open VSCodium and the duplicate
  review link. Reviewing must not install anything.
- Editor and other alternatives remain under **Other actions**. Results, logs
  and reports remain under **Details**. Updates are optional, not a work blocker.

## 2. Responsibilities and test environments

| Layer | Responsible party | Environment | Required evidence |
| --- | --- | --- | --- |
| A — decision and browser regression | Codex | Isolated synthetic observations; production frontend components | Deterministic assertions, accessibility results and relevant screenshots |
| N — native/platform integration | Codex through existing CI | Disposable Windows runner and actual Mint 22.3/root fixtures | Real exit/status/permission checks, retained logs and required markers |
| O — release acceptance | Owner | Authenticated installed candidate on supported Windows 11 and Mint laptops | Short workflow checklist, observed results and acceptance decision |

Codex prepares fixtures, diagnoses defects and completes all testing other than
owner UAT. No mentor is required. Do not make the owner corrupt a journal, kill
an installer, remove a lock, disable protection, manufacture an interruption or
reprovision an already healthy laptop for coverage.

Synthetic browser transitions, native fixture execution and owner observations
must remain distinct. Separate browser/native passes do not establish a real
packaged end-to-end UI pass unless that interaction was actually exercised.
An absent fixture or missing observation is a coverage gap, not a pass.

## 3. Entry gates and exact-candidate record

Before requesting owner UAT, Codex must fill in:

| Item | Evidence / status |
| --- | --- |
| Approved design, including update-state correction | Owner-authorized implementation completed; prototype approval remains distinct from installed UAT |
| Release version and tested source | Planned 1.2.23; implementation baseline `8e3c4463a475ed9fc7f89c88669fb12c129cf618`; final candidate-preparation/tag SHA pending |
| Implementation PRs and exact accepted heads | See exact heads below; candidate-preparation PR/head pending |
| Full final-main Build run and applicable native/trust/browser results | [Build 42959957444](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/42959957444) Pass on implementation baseline; candidate-preparation exact-main CI still required |
| Native candidate-pair/upgrade evidence and its historical-binary limitations | Existing Windows SYSTEM/Mint upgrade gates passed at baseline; new same-source 1.2.22 → 1.2.23 pair Pending; not historical released-binary coverage |
| Human signing approval and publishing run | TBD; never approve through tools |
| Published tag/source and five asset identities/digests | TBD |
| Independent pinned-key signature and both payload checks | TBD |
| Candidate install instructions and owner checklist | [Focused checklist](OVERVIEW-UAT-1.2.23.md) prepared; verified asset-specific install instructions pending authenticated publication |


Accepted implementation/audit heads (all integrated in the implementation baseline):

| PR | Exact PR head | Merge commit |
| --- | --- | --- |
| #152 | `9bf97da31b58650f699f5365e4e31dfbc25f28ac` | `a8fb6542cdd79fd5f5a0d9dd915b4fdfc4a535df` |
| #155 | `90ff20dc0dae4f9603943357bc2660603e24584a` | `f15e72b17f6257d5b297b2935371a07f4d92942b` |
| #156 | `fcf7139ba7e434c8f1855f43d701a1abfc88d6ae` | `6e251b771c13b40ae5c62c76703ff47084e33db1` |
| #157 | `5a7c4a6ed030c3be97635f8c0b3e49ab490000cc` | `84a5ce3f24f5381a2651408853c8d051c9b4be28` |
| #158 | `694b9bfc12534ea7aff5d8e0eb9d79fd89f907a0` | `8e3c4463a475ed9fc7f89c88669fb12c129cf618` |

Keep every existing applicable native, trust, package identity, signed SYSTEM and
actual Mint upgrade gate. Do not replace them with prototype tests. Do not rebuild
or replace accepted assets midway through UAT. Any replacement is a new identified
candidate with affected checks rerun and a clearly scoped owner retest.

Preserve the original Windows interruption evidence and the historical Mint
v1.2.18 Install/Validate **35 passed, 0 warnings, 0 failed** acceptance. Do not
mislabel that historical pass as testing of this new candidate.

## 4. Evidence and preservation rules

Each scenario starts **Not run**. Record platform, layer, candidate SHA/version,
starting observations, steps actually taken, expected versus actual result,
evidence link and any defect. Use **Pass**, **Fail**, **Blocked** or **Not observed**
as applicable; only the owner can supply owner acceptance.

For mutating native fixtures, record sentinel projects and relevant existing
editor/workspace settings before and after, plus journal/receipt/history and
permission invariants required by the operation. Standard configuration changes
explicitly disclosed in the review are not silently treated as data loss; they
must match the real backend scope. No new selective-repair behavior is assumed.

Do not publish credentials, private journal bytes, real personal logs or temporary
signed download URLs. Support sharing stays optional. Review diagnostics before
sharing; an assertion/category, synthetic sentinel and sanitized excerpt are
usually sufficient evidence.

## 5. Workflow coverage matrix

**A+N** means the visible mapping and the corresponding native boundary both need
proof; it does not imply that existing fixtures already cover the whole case.
Owner rows are a safe usability review of naturally available states, not a
substitute for difficult failure fixtures.

### A. Entry, setup and readiness

| ID / layers | Starting conditions | Steps | Expected result and preserved behavior | Evidence |
| --- | --- | --- | --- | --- |
| WF01 — A+N, O where natural | Fresh SDE launch; no complete readiness result | Open app; let startup checks finish | Overview opens with Checking/Not checked, not Install selected or an invented incident. Check is read-only. Completed startup validation is not redundantly repeated. | Initial/final screens; check invocation count; no mutation/elevation |
| WF02 — A+N | First launch for this account; tools already present | Complete startup check | Ready → Start building. No setup recommendation merely because this account has no history. | Existing-tool fixture; recommendation assertion |
| WF03 — A+N | Genuine missing essentials; no safety blocker | Check → Review setup → Back; reopen review → approve Install → complete verification | Full scope is disclosed before mutation. Back does nothing. One operation starts after normal review/OS approval; successful verification leads to Ready. | Review/progress/result captures; native sentinel checks |
| WF04 — A+N | Partially configured workstation | Review missing findings; run approved setup | Existing projects and editor settings are preserved according to backend contract; reapplied defaults/schedule changes match review. No false promise of missing-items-only installation. | Before/after fixture records and actual operation scope |
| WF05 — A+N, O | Required checks complete; no safety blocker or available updates | Open Overview → Open VSCodium; open workspace through Other actions | Prominent Ready!, one primary Open VSCodium action, correct destinations and no setup/elevation. | Screens and launch-target assertions; owner observation |
| WF06 — A+N | A known outcome says installation completed, but validation is unavailable/incomplete | Finish operation; select Check my setup | “Setup finished, but checking did not finish,” not Ready and not an automatic reinstall. Partial check rows cannot establish full readiness. | Separated operation/check outcomes; mutation count unchanged on recheck |
| WF07 — A+N | Inspection unavailable, incomplete or stale; some rows passed | Retry Check; later deliver a complete result | Honest Check not finished state; partial results accessible. No inferred damage, incident, completion time or pass. New results supersede stale observations without focus churn. | Failure/delayed-result fixtures; current-generation assertions |

### B. Repair and updates

| ID / layers | Starting conditions | Steps | Expected result and preserved behavior | Evidence |
| --- | --- | --- | --- | --- |
| WF08 — A+N | Existing setup; identified repairable missing tool | Review fixes → Back; return → approve Repair → verify | Specific finding and real full repair scope shown. No automatic repair; projects/settings preserved. Verification determines result. | Review copy; real repair/verification boundaries; sentinels |
| WF09 — A+N | Repair completes but the same finding remains | Read result; inspect Details/support; recheck | No automatic Repair → Check → Repair loop or repeated permission prompt. Explain unresolved finding; retry is explicit and not promised to succeed. | Bounded invocation counts; useful result/support route |
| WF10 — A+N | Failure is not fixable by existing SDE repair, or package-native incomplete state needs specific handling | Review the issue | Do not blindly recommend generic Repair. Show supported guidance and preserve native blocking conditions. | Finding-to-action mapping; no unsupported operation launched |
| WF11 — A+N, O where updates exist | Ready; tool updates available | Read card → Review updates → Back; open editor through Other actions | Exact owner wording from section 1. Ready remains reassuring. One primary Review updates action; no duplicate link. No update starts on review; continuing work remains possible. | Exact-copy/button assertions, update preview and owner review |
| WF12 — A+N | Update review open; valid updates selected | Approve update → complete → refresh observations | Actual updates retain approved version boundaries and normal authorization. Recommendation reflects fresh remaining updates/readiness, not forced Start building if issues remain. | Selected scope, actual result, refreshed-state assertions |
| WF13 — A+N | Update fails, is declined or is partly complete | Cancel before start, or inspect failure after start; revisit Overview | Cancelled review makes no change. Partial/failed changes are not called success or safe cancellation. Useful explicit next step; no implicit retry loop. | Invocation/outcome proof; retained diagnostics/evidence |
| WF14 — A+N | Tool update observation unavailable, or app and tool updates coexist | Open Overview/Details and each relevant review | Unknown update availability is not “0 updates” or broken readiness. Distinguish app updates from tool updates; no new pause/default-policy behavior. | Separate discovery results and unchanged policy contracts |

### C. Recovery and changing safety conditions

| ID / layers | Starting conditions | Steps | Expected result and preserved behavior | Evidence |
| --- | --- | --- | --- | --- |
| WF15 — A+N | Another package operation is known active | View next step → Check again → inspect Details | Changes paused; wait guidance, never Restart/kill instructions. Primary and Other actions cannot launch competing mutations. Diagnostics stay available. | Active-process/gate fixture; denied competing start |
| WF16 — A+N, O only if naturally present | Activity unknown after a real/fixture interruption | Read guidance; recheck; inspect Recovery | Uncertainty is explicit. Existing applicable normal-Restart guidance retained; no promise that restart repairs packages or a free lock proves safety. Still blocked until fresh evidence permits. | Unknown/restart-provenance fixtures; unchanged evidence |
| WF17 — A+N | Native records unavailable or untrusted | Check again; access Validation/log/report routes | No false clear state, setup fallback or promise that restart repairs trust. Read-only diagnostic access obeys its existing constraints. | Trust/source-unavailability cases and native denials |
| WF18 — A+N | Current machine/account incident needs acknowledgment | Review interruption → acknowledge; return/recheck | Summary attempted automatically without an extra save step. Original evidence remains; consent is source/generation-bound and is not permission to execute. No operation replay. | Consent/summary counts, source binding, retained bytes/receipts |
| WF19 — A+N | Report save fails, acknowledgment is unconfirmed, or only one incident source succeeds | Acknowledge; inspect result and available support/history | Distinguish report failure from consent failure. Partial success cannot acknowledge another source or release a pending request. Warn without discarding evidence. | Each partial-result fixture, original evidence and invocation count |
| WF20 — A+N | Review was valid; another installer starts or incident evidence changes before confirmation | Confirm the previously reviewed action | Fresh native check rejects/stops the stale request; show the current reason. No old consent or UI snapshot grants authority. | Race fixture at confirmation/execution; no child mutation |
| WF21 — A+N | Tools pass while safety blocks; missing tools and updates also coexist | Check, inspect recommendation and disclosures | Current blocker takes priority; other findings remain accessible. No contradictory Install primary plus Recovery warning, or unqualified Ready granting unsafe changes. | Combination/precedence matrix and native admission proof |
| WF22 — A+N, O | No current incident; unknown package health alone or unavailable maintenance history | View Overview and voluntarily open Recovery | No fabricated recovery incident. Preserve separate uncertainty; accepted neutral Recovery clear card appears only when its conditions are met. Known maintenance failures remain visible. | Nonblocking-vs-blocking classification; clear-card regression |

### D. Operation lifecycle, interruption and user control

| ID / layers | Starting conditions | Steps | Expected result and preserved behavior | Evidence |
| --- | --- | --- | --- | --- |
| WF23 — A+N, O | Install/Repair/Update review open; nothing started | Back/Cancel; reopen; cancel/deny OS approval | Return to a useful review/Overview state. Proven-not-started cancellation does not create a false interruption. Unknown launch outcomes stay uncertain. | OS result distinctions; child-start and journal assertions |
| WF24 — A+N | Download/network failure before or after package changes begin | Observe failure → inspect Details → explicitly retry when safe | Identify network failure without implying nothing changed. Never auto-clear a protected journal or remove locks to retry; preserve partial changes and safety checks. | Before/after mutation failure injection; safe retry/denial proof |
| WF25 — A+N, O for normal navigation | Operation running | Navigate to another page and return; repeat primary click rapidly | Current progress remains recoverable; no second operation, silent cancellation or fabricated rollback. One operation at a time. | Busy-state and duplicate-submission assertions |
| WF26 — A+N, O for ordinary reopen | Unstarted review or safely completed operation; separate fixture for interrupted running work | Close/reopen SDE; normal OS restart only in disposable interruption fixture | Unstarted requests forgotten, not replayed. Fresh observations rebuild the recommendation. Unknown operation outcomes retain evidence and do not become Ready from UI storage. | Reopen/persistence tests; independent restart-provenance evidence |
| WF27 — A+N, O | Startup query or refresh results arrive out of order | Trigger safe refresh/navigation; complete old result after new result | Stale result cannot overwrite newer findings or switch a focused action into an unsafe operation. No unexpected redirect or focus stealing. | Controlled ordering/generation tests and keyboard focus checks |

### E. Secondary paths, accessibility and installed-candidate regression

| ID / layers | Starting conditions | Steps | Expected result and preserved behavior | Evidence |
| --- | --- | --- | --- | --- |
| WF28 — A+N, O | Ready and blocked states | Expand Other actions/Details; visit Validation, Recovery, Schedule, About; return | Correct existing routes/scopes; no lost diagnostics or safety bypass. One primary action; no reintroduced tab selection or duplicated editor/update/result buttons. | Route/action assertions and owner walkthrough |
| WF29 — A+N, O | Reports, histories and relevant findings present or unavailable | View logs/results; prepare report; cancel sharing/export; inspect histories | Distinguish unavailable/empty/deleted report views from operational evidence. Sharing optional; warnings visible. Normal retention/deletion confirmation remains, with no incident acknowledgment or operation as a side effect. | Synthetic data/privacy fixtures; existing protected storage tests |
| WF30 — A, O | Every state and key transition | Keyboard-only review, focus/hover, screen-reader announcements, both themes, all supported zoom levels, narrow/desktop layouts | Readable hierarchy and primary controls; no color-only findings, focus trap, horizontal scrolling, hover-only action or repeated log announcements. Review Cancel and modal Escape restore useful focus. | Automated accessibility/reflow plus actual installed owner observations |
| WF31 — A+N, O | Candidate installed/upgraded over supported existing app | Confirm identity; inspect projects/settings, launch editor/workspace, reopen and review Schedule/About | Correct candidate version, preserved data and unchanged update/schedule policy semantics. No unexpected repair, maintenance run or policy resume caused by opening Overview. | Existing signed Windows/Mint upgrade gates, identity/hash record and owner check |

## 6. Short owner UAT runbook

Codex supplies the authenticated candidate, exact install instructions and a
pre-filled evidence sheet. Aim for one consolidated candidate and one planned
owner cycle; a defect may require a clearly bounded replacement/retest, not a
promise to ship despite findings.

On each supported owner platform:

1. Confirm the candidate version in About, ordinary app opening/reopening and
   unchanged projects/settings. Do not reinstall the entire tool baseline.
2. Follow the naturally recommended next step. Check the status, wording and
   obvious primary action. Open editor/workspace where the real setup permits.
3. If real updates are available, check the exact approved update wording and
   Review updates → Back flow. Installation is optional unless specifically
   agreed for that device; do not manufacture an update by downgrading tools.
4. Exercise Other actions/Details and relevant existing pages. Open support
   review if useful, then cancel; sharing/deletion is not required for a pass.
5. Review the setup/repair confirmation screens without executing unnecessary
   provisioning; Back must return safely. If a genuine issue already warrants
   repair, Codex first supplies an explicit device-specific procedure.
6. Check your normal theme/zoom, keyboard focus, and navigation/reopen behavior.
   A real safety finding should stay understandable and block unsafe changes;
   do not induce one on an accepted laptop.
7. Report Pass/Fail/Not observed by row and platform. Codex reconciles missing
   owner observations with the required automated/native evidence and identifies
   any remaining owner decision. A state not encountered is not an owner pass.

Clean setup, damaging/interrupted states, repeated provisioning, trust failures,
write failures and races belong to disposable fixtures. If an essential behavior
cannot be demonstrated by those fixtures or normal owner observation, resolve
the coverage gap before acceptance; do not pressure the owner into destructive tests.

## 7. Result sheet and release decision

Copy one row per workflow/platform/layer when execution begins:

| Workflow ID | Platform / account context | Candidate version / SHA | Starting state | Result | Actual observation / defect | Evidence | Tester |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TBD | TBD | TBD | TBD | Not run | TBD | TBD | TBD |

Release exit criteria:

- Every mandatory A/N scenario has passing evidence on the final relevant source
  and candidate; fixtures/calls must actually execute. Document inherited evidence
  reuse and why changes cannot invalidate it; no silent skips or broad waivers.
- Required installed owner checks pass on Windows and Mint, with Not observed
  rows identified honestly and any material usability gap explicitly resolved.
- No unresolved unsafe authorization, data loss, false readiness, missing
  diagnostic access, automatic replay, duplicate mutation or unbounded retry loop.
- All supported operations have successful paths and safe failure/escape paths;
  no known broken workflow is hidden behind an attractive demo.
- Candidate identities/signatures/hashes match the tested assets throughout.
- Owner explicitly accepts the real candidate. Prototype approval is insufficient.
- Stable promotion requires separate owner authorization, preserving the tested
  signed assets. No inferred fleet rollout, policy resume or milestone closure.

For failures: Codex records a reproducible finding, scopes the fix, reruns affected
regression and required CI, and proposes only necessary owner retest. Infrastructure
timeouts are diagnosed separately from application assertions; retries are based
on evidence rather than repeated blind reruns. No CI polling or scheduling change
is part of this plan.

## 8. Remaining planning decisions

Before implementation/UAT execution, fill in the release version and exact state
classification rules from real observations. Identify gaps in fixture coverage,
especially first-account versus new-machine evidence, packaged UI integration and
actual restart proof. Unknown observations may not be filled with invented facts.

The plan deliberately leaves all execution results blank. It changes no demo,
application behavior, native state, release metadata or existing acceptance record.
