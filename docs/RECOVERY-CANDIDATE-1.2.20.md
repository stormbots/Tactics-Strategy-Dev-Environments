# Recovery v1.2.20 candidate preparation ledger

Status: recipe preparation only; no signed candidate or owner UAT yet.
Branch `codex/recovery-uat-1.2.20`. Exact branch head and workflow URLs are recorded
in the preparation PR checkpoint; do not infer acceptance from this document.

## Consolidated implementation evidence

PR #139 passed at `d4bb9953f2ea064f50c9cd2088dd8ebe17d9a408` in
[Build 41259004375](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41259004375):
175 frontend/105 browser checks, Linux root coordination 151/151, Windows trust
136/136, native Tauri Windows 106/106 and Linux 104/104. Both signed SYSTEM/actual
Mint 22.3 upgrades and all inherited recovery, feasibility, installed, manual,
read-only Validation and trust gates passed. The earlier browser-fixture mismatch
is fixed, not waived. Applicable policy/helper workflows also succeeded.

The complete cumulative recovery stack was squash-consolidated through #139 into
`main` as `f6befee68ce38ed07b99ccb1093f7b2e45d08b79`. Its tree matches the verified
PR head exactly. No partial-stack merge or unrelated-main overwrite occurred.
Full exact-main [Build 41266416577](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/41266416577)
was started automatically and was pending at the initial inspection. This is
not yet the final candidate source: the recipe change also needs verified PR
checks, merge and a full successful workflow on its exact combined-main commit.

## Version and recipe decisions

- Live v1.2.19 is already published at `3b0e8d7ec05d1b6d62535cb5b1368056abe3ac04`.
  v1.2.20 tag lookup returned zero and release lookup returned not found during
  preparation. Recheck before dispatch and before publication; never edit an
  existing release/tag/assets to reuse a version.
- Reuse the existing protected `prepare-self-update-uat.yml`. Build only the
  same-source 1.2.19/1.2.20 pair for disposable native upgrade validation; publish
  **only 1.2.20** after human signing approval. Do not download, replace or publish
  the rebuilt older fixture over the real v1.2.19 release.
- Extend the fixed identity whitelist/probes to 1.2.20 while retaining dependency
  and tool-baseline invariance, pause/resume and enabled-default upgrade checks,
  real Windows SYSTEM and Mint 22.3 pair markers. The published older fixtures
  are not proof of the historical-binary upgrade path; this is explicitly a
  same-source packaging probe, supplemented by inherited signed-upgrade CI/UAT.
- Exclude the candidate tag from the general Build release trigger/job, as for
  prior candidates, so protected candidate publication remains the sole path.
  Keep native/general/trust checks, exact-main source guard, `sde-release-signing`,
  five-asset authentication and immutable-prerelease checks unchanged.
- Application version stamping remains confined to the disposable build checkout.
  Do not bump the development-tool baseline or provision working owner machines.

## Remaining execution gate

Local preparation validation: three identity/recipe invariance tests, 20 CI-scope
and inherited-gate contracts, Bash syntax and whitespace checks passed. No native
installer/package probe ran locally; ShellCheck/PowerShell/native pair execution
and full builds remain required through existing CI. Application runtime code
did not change, so already successful frontend/native suites were not needlessly
rerun locally. This is not a candidate build or publication result.

1. Require complete applicable PR CI, including the candidate-pair workflow on
   both native platforms, probe/fixture checks and inherited Build checks.
2. Merge only the verified preparation head, then require complete successful
   Build on that exact final combined-main source. Preserve later unrelated work.
3. Recheck version availability and release-branch ancestry. Fast-forward
   `release/v1.2.uat` to the verified exact main commit, without force. Confirm the
   workflow on that source targets only 1.2.20 publication and includes recovery.
4. Inspect existing `workflow_dispatch` runs for the source before dispatching
   once with `deployment_readiness=true`. Review pair build/upgrade results. End
   while long jobs run; retain exact source, run URL and remaining gate in PR.
5. When both builds pass and pending deployments identifies `sde-release-signing`
   waiting for `rdpollard`, stop and provide **Review deployments →
   sde-release-signing → Approve and deploy** with the exact run URL. Never approve
   it through CLI, API or browser. Candidate publication follows that owner gate.
6. After authorized signing/publication, authenticate all five assets and supply
   exact installation instructions/hashes plus [focused owner UAT](RECOVERY-FOCUSED-UAT.md).

No signing, candidate dispatch, release publication, owner UAT, automation
resumption, stable promotion, fleet rollout or milestone closure occurred during
recipe preparation. Windows original interruption evidence and Mint v1.2.18
Install/Validate **35/0/0** remain untouched; no failures are manufactured on them.
