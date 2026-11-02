# Recovery clear-state v1.2.22 preparation ledger

Status: recipe preparation, not signing-ready or owner UAT-ready.
Branch `codex/recovery-clear-uat-1.2.22`. Exact preparation head and run URLs belong
in the PR checkpoint to avoid a status-only commit after final-main validation.

## Source and candidate contract

- Recovery-card PR #143 passed at `1cb53b39f40ad94efb701b3b93079d23f3167c50`
  in Build 41321708372 (200 frontend tests, browser/native/trust/signed upgrades).
  It merged as `cae697dfa956305d7d4fdf3419ac35a3b5a523c8`, including the preceding
  cache/timing-only PR #144. The duplicate-provisioning CI experiment was removed;
  efficiency tuning is finished, not part of this release task.
- Exact combined-main Build 41480117203 was still running at this preparation's
  initial inspection. That run does not replace final recipe PR/main validation.
- v1.2.21 is published. v1.2.22 tag lookup returned zero and release lookup 404
  during preparation. Recheck before dispatch and publication; never overwrite
  existing tags/releases/assets or historical UAT results.
- Build **1.2.21/1.2.22** from the same reviewed source in disposable checkouts;
  publish **only 1.2.22** through protected signing. Rebuilt 1.2.21 is an
  unpublished test fixture, not proof of upgrade from historical published bytes.
- Extend the fixed identity/probe support through 1.2.22, reject unknown 1.2.23,
  preserve prior-version probe/policy coverage and exclude candidate tag 22 from
  ordinary release publication. Stamp application identity only in build copies;
  tool baseline/dependencies and production recovery behavior stay unchanged.

## Required next steps

1. Require all applicable exact-head PR checks: full Build, both candidate pair
   native builds/upgrade checks, probe and fixture workflows. Diagnose failures;
   do not substitute skipped or earlier-head evidence.
2. Merge only after verified success, then require full Build success on that
   exact final combined-main commit. Never use the earlier implementation run
   as the release-source gate.
3. Recheck unused v1.2.22 tag/release, source main and release-branch ancestry.
   Fast-forward `release/v1.2.uat` without force to the verified main commit.
   Inspect that commit's recipe: only 22 publishes, both source fixes are included.
4. Inspect workflow_dispatch history for that commit before dispatching once with
   `deployment_readiness=true`. Review both native pair/upgrade results.
5. When both pass and pending_deployments identifies `sde-release-signing`
   awaiting owner `rdpollard`, stop and provide the run URL and **Review
   deployments → sde-release-signing → Approve and deploy**. Never approve via
   CLI, API or browser.
6. After owner approval/publication, authenticate package identities, signatures
   and all five assets; provide exact hashes and installation instructions with
   the [focused UAT sheet](RECOVERY-CLEAR-UAT-1.2.22.md). Stop for owner UAT.

Windows interruption evidence and Mint v1.2.18 **35/0/0** acceptance remain intact.
No signing, publishing, automatic repair, journal clearing, stable promotion,
fleet rollout, milestone closure or automation resumption during preparation.
