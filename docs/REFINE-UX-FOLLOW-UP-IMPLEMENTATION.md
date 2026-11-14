# Refine UX follow-up: implementation and release starting point

## Current status

The owner accepted the Version 4 HTML mockup and asked to update GitHub and prepare for release work. This checkpoint prepares that work. Application implementation has not started.

The accepted rule is:

> Keep related steps together, automate required follow-up checks, and update findings in place.

Explicit decisions remain required for installation/Repair approval, interruption acknowledgment, saving a location, and leaving maintenance disabled. Automatic verification is not automatic approval or an automatic retry loop.

Current main is `f6715a728bd6017ad6b6d8294cf2f1bf914da2ca`, the published v1.2.23 source. This preparation branch starts from that exact commit. It does not replace the v1.2.23 tag, installers or evidence. The older startup design is retained unchanged as a historical design source; live issues and later owner decisions take priority.

## Accepted reference

- [Version 4 HTML](refine-ux-follow-up-demo/index.html).
- [Walkthrough and capability limits](refine-ux-follow-up-demo/README.md).
- [Artifact hashes](refine-ux-follow-up-demo/manifest.json).
- [Earlier prototype validation](refine-ux-follow-up-demo/prototype-validation.json).
- [Portable prototype verifier](refine-ux-follow-up-demo/verify.cjs).
- [#160: startup sequence](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/160).
- [#161: all accepted plans and wording](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161).
- [Version 4 acceptance and preparation request](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/issues/161#issuecomment-6872951134).
- [Earlier startup design](STARTUP-CHECK-SEQUENCING-DESIGN.md).
- [Original milestone handoff](OVERVIEW-NEXT-STEP-HANDOFF.md), [design](OVERVIEW-NEXT-STEP-DESIGN.md), [WF01–WF31 UAT draft](OVERVIEW-NEXT-STEP-UAT-DRAFT.md) and [existing evidence ledger](OVERVIEW-WORKFLOW-EVIDENCE.md).
- [Recovery clear-state contract](RECOVERY-CLEAR-STATE.md) and ADRs [0001](adr/0001-interruption-acknowledgment-boundary.md) / [0002](adr/0002-lease-bound-recovery-transition.md).

The mockup's operation names, timestamps and successful feature results are examples. The owner confirmed that Python 3.14.9 runs alongside 3.15 on one Windows PC. That does not establish pip/environment passes or the cause of the retained interruption. Prototype acceptance is not acceptance of v1.2.23 or any later real candidate. #151 and #146 remain open.

## Requirements and first code locations

| Plan | Required result | Start reviewing here | Required proof |
| --- | --- | --- | --- |
| Automatic startup | One bounded safety-then-tools sequence; no manual retry for self-contention | `installer/src/App.tsx`, `bridge.ts`, `recovery.ts`; Tauri recovery/status adapters | Delayed safety, simultaneous gate-taking readers, actual native gate contention, duplicate effects/clicks, navigation and packaged launches |
| Procedural Overview | Your next step links current findings; individual cards explain only their own situation | `overviewDecision.ts`, `model.ts`, `validationGuidance.ts`, `ValidationCheck.tsx`, `App.tsx` | Combined/single findings, resolved-card removal, plain wording, keyboard focus and stale-result rejection |
| Python coexistence | Explicit required interpreter and matching pip/capability checks; other defaults preserved | Windows `Validate-SkyviewEnvironment.ps1`, Linux validator, metadata adapters | Newer/older defaults, missing launcher, failed discovery, selected path, pip mismatch and actual Windows/Mint checks |
| Node/npm coexistence | Explicit usable Node 24 and its own npm; no manager switch or global reassignment | Windows validator and `Node24.ps1`; Linux validator; package metadata | Matching/mismatched pairs, version-manager shims, ownership conflicts and unchanged defaults |
| VSCodium preferences | Required functionality stays separate from optional recommendations; confirmed access errors have useful troubleshooting | Validators, profile scripts, guidance/UI | JSONC, absent file, access denied, parser unavailable, effective-setting scope and preserved settings |
| Git preferences | Recommendations do not fail working Git; configuration preserves intentional values | Windows/Linux profile scripts and validators | Unset/different/unreadable values, equivalent Booleans, overrides and preservation tests |
| Application locations | Supported alternate installation discovery; checked launch target; maintenance trust stays separate | Validators and Tauri `open_destination` | Product identity, multiple candidates, stale registration, access errors, disappearance before launch and no arbitrary elevated path |
| Maintenance | Current tools, scheduling, history and SDE app policy remain distinct | `ScheduledMaintenance.ps1`, `Inspect-SkyviewSchedule.ps1`, `linux/lib/schedule.py`, `DetailsPages.tsx` | Unknown-to-disabled continuation, explicit leave-disabled, real full-scope restoration and fresh verification |
| Project locations | Explicit saved reference used by validation, Open and supported setup | Repository setup/validators; Tauri destination and persistence contracts | Worktrees/forks, wrong identity, missing/disconnected drive, selection-change invalidation, explicit Save, no duplicate clone or lost work |

Read live issue comments before implementation. Their later refinements are required, including the shorter interruption flow and the shared in-place continuation rule.

## Gaps that must be resolved before offering real actions

1. **Structured findings.** Current checks are primarily status/message records. Add bounded typed evidence where needed for component identity, failure cause, selected interpreter/location and verification status. Do not infer executable commands or repair permission from arbitrary diagnostic text.
2. **Full operation scope and preservation.** The mockup uses full Repair as an illustration. Existing profile scripts write global Git defaults; Windows Node provisioning can reject/switch registrations. Audit actual effects and implement the approved preservation behavior before promising safe coexistence. If the supported operation cannot meet it, report the gap and keep that execution path unavailable. No new selective installer is approved.
3. **Maintenance restoration.** Confirm the actual supported full operation. Do not invent a schedule-only Enable endpoint. A disabled task does not prove intent. A saved leave-disabled choice must be narrowly scoped and must not become native policy or execution authority.
4. **Locations and persistence.** Current destinations are fixed enums/paths. A new user location must use a narrow, validated native contract. It cannot become an arbitrary command, elevated script source or project-code execution path. Define ownership, record format, verification identity, changed-path handling and per-user persistence before wiring Save.
5. **Read-only queue.** Classify actual gate-taking readers, including nested About/recovery/status reads. Do not serialize unrelated network calls, change native lock semantics or recursively enqueue the sequence into its own queue.
6. **Acknowledgment and safety.** Reuse existing source/generation-bound acknowledgment and report behavior. The explicit button replaces the UI checkbox only. Automatically refresh safety after saved acknowledgment; retain original evidence and keep failures visible. No UI result is a native execution permit.

These are engineering tasks inside the accepted plans, not excuses to weaken acceptance checks. Material new privileged capability or a broader operation engine needs a separately reviewed scope.

## Bounded implementation order

1. **#160: establish and test startup ordering.** Reproduce safely or capture the initial status; complete the gate-use map. Add deterministic production-App ordering tests, then the smallest coordinator/adapter change. Keep real external deferral and all native authority. Do not label the owner's cause proven without evidence.
2. **#161: observation and discovery contracts.** Add/test typed findings and compatible interpreter/toolchain discovery. Keep defaults and project settings unchanged. Define precise Windows/Mint behavior before replacing checks.
3. **#161: preferences, locations and maintenance contracts.** Resolve the gaps above, including profile preservation and narrow persistence. Do not expose a button that promises an unsupported operation.
4. **#161: integrate accepted cards and continuations.** Reuse normal operation review and native dispatch. Retain explicit decisions. Automatically run only permitted required follow-up checks; reuse suitable fresh final verification. On failure, keep context and direct actions rather than starting the workflow again.
5. **Consolidate evidence and release preparation.** Reconcile old WF01–WF31 requirements and new accepted scenarios, run full exact-head and exact-main checks, then prepare one candidate for human signing and owner testing.

Use scoped branches/PRs for independently reviewable increments. Do not reopen completed #147–#150 merely to reuse their old ticket numbers. Keep #160/#161 acceptance open until their real requirements and evidence are satisfied.

## Validation and release gates

### During implementation

- Run targeted production-App/unit tests for each changed boundary.
- Run backend contracts, CI-policy tests, formatting/static checks and applicable Bash/PowerShell/native tests.
- Preserve profile/project sentinels, native gate/identity/ACL/report/history tests, complete summary/time requirements and no-false-Ready assertions.
- Browser tests cover light/dark, supported zoom/width, keyboard/focus, seven continuation flows, failures, cancellation, denial, changed evidence, duplicate submissions and late results.
- Disposable Windows and actual Mint fixtures prove native behavior. Browser simulation and Debian checks cannot replace those results. Do not induce faults on owner laptops.

### CI cost and checkpoints

Use the existing workflow and its current scope policy. Do not broaden exceptions, reduce the check matrix or waive `acceptance` to save runners. Batch related edits before dispatch. Avoid a docs-only PR now because this preparation path would receive full application/native classification under the existing policy; a push to the `codex/` preparation branch does not match the build's push filters.

When an implementation PR exists, its applicable checks must pass. Full exact-main evidence remains required before candidate preparation. Preserve useful previous runs and cancel only genuinely superseded runs. Diagnose failures before retrying.

Record exact head/base, run URLs, completed/pending/blocked checks, evidence limits and the next action in GitHub before ending a CI wait. Do not poll continuously or occupy a session waiting for long jobs.

### Candidate and human decisions

No version is reserved. `v1.2.24` had no remote tag at this preparation check and is only a possible next version. Recheck before allocation.

The source package identities intentionally remain `1.2.1`; the existing candidate workflow sets the published candidate identity. Its fixed supported-version lists, identity tests and release safeguards currently stop at `1.2.23`. A later candidate increment must update all relevant version/identity/upgrade contracts deliberately, not blindly bump unrelated package manifests.

Required sequence:

1. Reviewed implementation and all applicable exact-head CI/native/trust results.
2. Protected merge and full exact-main CI, including `acceptance`. Confirm current required-check protection before merging; do not use a bypass.
3. Supported Windows/Mint native and upgrade evidence for the actual changed contracts.
4. Human approval at the actual protected `sde-release-signing` gate. The assistant must not approve it.
5. Independent pinned-key authentication of the exact source/tag and all five release assets, including payload/package identity.
6. Owner UAT of that exact authenticated candidate. Record Pass/Fail/Blocked/Not observed and preserve limits.
7. Separate explicit owner authorization before stable/latest promotion. No fleet rollout or policy resumption is implied.

If v1.2.23 remains unaccepted, retain its record as the earlier candidate and map retests honestly to the follow-up. Never mark its failures resolved merely because a new mockup was accepted.

## Preparation checks already completed

- Fresh `origin/main`: `f6715a728bd6017ad6b6d8294cf2f1bf914da2ca`.
- Original checkout was clean on `codex/startup-check-sequencing-design`, head `9f3f366ca2ddeb7c8003f0b91d26723d7a922a07`; preserved unchanged.
- Separate worktree/branch: `codex/refine-ux-follow-up-prep`, based on main.
- GitHub reads and issue writes work. Git transport fetch works; the branch publication receipt supplies write evidence.
- Existing `/workspace/.sde-tools/env.sh` enables cached Cargo/Rust, GTK 3.24.49 and WebKitGTK 2.54.0. Cargo/rustc report 1.99.0. Node reports 24.19.0, npm 11.9.0 and Python 3.12.14. System Chromium and existing installer development dependencies are available.
- Offline Cargo metadata for `coordination/Cargo.toml` succeeds. This is toolchain/manifest readiness, not a compile or native test pass.
- Local baseline backend contracts: **35 passed**. CI-scope policy: **26 passed**. CI-timing checks: **4 passed**.
- Current branch-protection inspection returns HTTP 403 for this integration. Workflow inspection confirms the aggregate `acceptance` gate and release dependency, but does not prove GitHub settings. Confirm required-check protection, including `acceptance`, before a later merge.
- Published-copy browser smoke passed: Python verification removes its finding while safety remains paused. This is still simulation evidence.
- Prototype verifier syntax and snapshot hashes checked. The retained prototype report records the earlier 24 workflow branches / 77 accessibility-layout checks, not a new full run or production evidence.
- No application source, workflow, lockfile, package version, tag or release asset changed. No CI, package build, native operation or signing workflow was dispatched.

## First coding action

Start #160 from current main on its own implementation branch. Read this plan, the published startup design and live issue refinements. Reproduce/observe the startup failure safely, map the real lock-taking reads and add the smallest production-App ordering regression. Only then change the coordinator. Broader #161 backend contracts follow in the order above.

This preparation checkpoint does not itself start application implementation or claim that all capability gaps are resolved.
