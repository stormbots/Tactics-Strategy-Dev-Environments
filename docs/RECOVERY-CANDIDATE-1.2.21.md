# Student Recovery v1.2.21 preparation ledger

Status: recipe preparation, not signing-ready or owner UAT-ready.
Branch `codex/student-recovery-uat-1.2.21`. Exact preparation head and workflow
URLs belong in its PR checkpoint; avoid a status-only source change after final
main validation.

## Verified implementation

PR #141 passed at `8879f9b607f60fdd2a99ac05bd40d8a583dff5a8` in
[Build 41278626292](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41278626292):
188 frontend/109 browser checks, root Linux coordination 151/151, Windows trust
136/136, native Tauri Windows 106/106 / Linux 104/104. Windows signed SYSTEM and
actual Mint 22.3 signed upgrades and all inherited recovery gates passed. This
includes computed normal/focus/hover primary styling and full axe audits; the
initial contrast defect was fixed, not waived.

The rewrite was squash-merged as main
`75a7da2bebed0e8e6750a1f4b61d7b5871c0fdd9`; its tree matches the verified head.
Automatic exact-main [Build 41281411205](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41281411205)
was pending at its initial inspection. The recipe preparation still requires
verified PR CI, merge, and full Build success on the resulting final main SHA.

## Candidate contract

- Live v1.2.20 is already published. v1.2.21 tag lookup returned zero and release
  lookup returned not found during preparation. Recheck before dispatch/publication;
  preserve existing assets, tags and historical UAT results.
- Reuse the protected recipe for same-source **1.2.20/1.2.21** native pair builds.
  Publish **only 1.2.21** after protected signing approval. Rebuilt 1.2.20 remains
  an unpublished disposable fixture, not a replacement for the published binary
  or proof of the historical-binary upgrade. Keep that limitation explicit.
- Extend fixed version identity/probe coverage, including SYSTEM/Mint pair markers,
  pause/resume and enabled-default/preservation checks. Tool baseline/dependencies,
  native safety, signature checks and five-asset authentication remain unchanged.
- Exclude the candidate tag from the general release trigger/job to keep the
  protected candidate workflow as its sole publication path. No required native,
  trust, browser, source-guard or signing environment gate is removed.
- Stamp version identities only in disposable build checkouts. This preparation
  changes no student Recovery logic or owner workstation state.

## Remaining gates

Local preparation checks passed: three identity/recipe invariance tests, 20
CI-scope/inherited-gate contracts, Bash syntax and whitespace. ShellCheck,
PowerShell analysis and full native pair/build checks remain existing CI work;
no native package test ran on owner workstations. The already accepted Recovery
runtime source is unchanged in this recipe increment.

1. Require all applicable exact-head PR workflows: full Build, both native pair
   builds/upgrade checks, probe and fixture workflows. Diagnose failures, not skips
   or waivers. Record head/run URLs and end while long jobs remain.
2. Merge the verified preparation head and require full successful Build on that
   exact final combined-main SHA. Do not substitute the earlier 75a7da2 run.
3. Recheck unused v1.2.21 tag/release, live source and release-branch ancestry.
   Fast-forward `release/v1.2.uat` without force to the exact verified main SHA;
   verify the workflow on that source targets only 1.2.21 publication.
4. Inspect existing workflow_dispatch runs for that source. Dispatch once with
   `deployment_readiness=true`; review both native candidate builds/upgrade checks.
5. When they pass and pending_deployments shows `sde-release-signing` awaiting
   owner `rdpollard`, stop and supply that run URL plus **Review deployments →
   sde-release-signing → Approve and deploy**. Never approve through CLI/API/browser.
6. After owner approval/publication, authenticate all five assets and provide
   exact hashes/install instructions plus the [focused UI UAT sheet](RECOVERY-STUDENT-UAT-1.2.21.md).

Windows original interruption evidence, existing releases/UAT state and Mint
v1.2.18 **35/0/0** remain intact. No signing, publication, UAT, automatic repair,
journal clearing, stable promotion, fleet rollout, milestone closure or automation
resumption occurs during recipe preparation.
