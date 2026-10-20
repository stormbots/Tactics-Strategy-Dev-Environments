# Trustworthy Update Discovery and Preview — Part 1 completion plan

Owner instruction: finish Part 1 quickly, follow this plan to completion, and provide a candidate for owner UAT. Plan recorded October 20, 2026. Target one reviewed implementation and one new immutable signed candidate; fix genuine findings before acceptance. Track execution in this chat and the PR.

## Scope and finish line

All six issues in milestone 4 are included: #11 stable SDE release notifications and actionable failures; #12 managed-tool preview; #30 accurate Windows PowerShell availability; #87 readiness independent of update currency; #90 current stable download guidance; #91 responsive startup with bounded advisory checks.

#12 requires preflight before tool changes. Deliver the operation-specific read-only Update preflight integration needed by this release, including supported platform, disk, required source connectivity, package activity and detectable restart conditions. Show blockers, warnings and unavailable checks, allow Check again/Cancel, and retain native operation coordination/rechecks. Do not claim the broader Install/Update story #7 is complete solely from this integration.

Part 2 (#86, #88, #89, #92–#94) stays in its milestone. Update Now/protected close (#72) remains shelved. No new baseline policies, automatic GUI installation, tool selection, fleet rollout or policy resume are included.

Finish line: reviewed source; passing automated/native GitHub checks; published and independently authenticated new candidate; Windows 11/Mint owner UAT; addressed findings; recorded acceptance; existing candidate promoted stable/latest without replacement of tag/assets; accepted issues and milestone closed. Do not infer desktop acceptance from CI or close issues with untested criteria.

## Execution order

1. Establish current source, issue acceptance matrix and release identity. Work on an isolated feature branch from reviewed main. Use current reusable discovery/trust/coordination and backend metadata rather than the shelved branch. Keep applied tool baseline unchanged.
2. Implement backend contracts first: independent local validation; bounded/deduplicated advisory SDE and managed-tool checks; fixed official release/download navigation; typed sanitized failure/partial outcomes; version-aware Windows PowerShell reconciliation; Update preflight. Preserve process/session/operation gates and reject stale results after mutations.
3. Implement a cohesive UI: independent readiness and update state; launch/About SDE check and per-version dismissal; read-only managed-tool preview with Refresh preview/Continue with Update/Cancel; policy/scope/freshness explanations; preflight result review; no action automatically performs an update. Keep accessible themes/zoom/focus and genuine result reporting.
4. Replace current introductory version links with official evergreen stable entry points. Add a check/promotion step that catches stale introductions and verifies both supported installer assets without requiring a prerelease to be stable. Preserve historical evidence and fallback links.
5. Verify meaningful regressions locally where tools are available, then run full GitHub frontend/browser/accessibility/security/backend/native checks. Prefer GitHub for native tests; local Mint is a fallback only. Review changes and fix failures before merging. Attach the PR to this chat and record actual evidence, limitations and source SHA.
6. Allocate a fresh unused release identity after checking tags/releases. Update candidate preparation fixtures coherently and use the established native upgrade and protected signing pipeline. Exact-main CI and actual Windows SYSTEM/Mint upgrades must pass before requesting human signing approval. Authenticate all five published assets with the pinned verifier and checksums; never overwrite published assets.
7. Hand the owner one concise Windows 11/Mint UAT sheet with verified download/install instructions and exact candidate identity. Cover local readiness while checks wait, SDE current/available/failure/dismissal, managed-tool preview/partial/offline and PowerShell consistency, Update preflight/confirmation and actual results, preserved baseline/settings/schedule/pause, themes/zoom/keyboard/speech. Use clearly labeled test fixtures for states that cannot naturally occur against production; fixtures do not prove live-source/native integration.
8. Resolve owner findings with fresh immutable versions when binaries change. Record exact observed passes or explicit accepted limitations. After owner acceptance and authorized promotion, recheck source and assets, mark that exact release stable/latest, verify unchanged tag/assets and correct public links, then close accepted issues and milestone.

## Required owner participation

The protected `sde-release-signing` environment requires a human review of the exact source/workflow/artifact inputs before releasing signing secrets. Follow docs/SELF-UPDATE-SIGNING.md; do not approve on the owner's behalf or weaken protections. Prepare the concrete passing candidate inputs before asking.

The owner performs Windows 11/Mint desktop UAT and reports results. CI/browser simulation cannot supply that acceptance. This session's release goal authorizes engineering and preparation; obtain the required exact-candidate acceptance/promotion disposition after UAT. Keep fleet pause/resume and deployment separate.

## Working verification matrix

- #11: semantic ordering, canonical stable filtering, incompatible/missing assets, current/newer/offline/rate limit/partial scan, safe URLs, per-version dismissal and a later new version.
- #12/#30: executable ahead of package record, genuine update/current/unknown metadata, per-tool source/partial state, family constraints, stale APT explanation, preview refresh/cancel/confirmed operation, preflight blockers/unavailable checks, actual outcomes.
- #87/#91: readiness independent of update currency, no network-held startup busy state, request bounds/deduplication, stale-response rejection, operation safety and accessible announcements.
- #90: evergreen official entry point, both canonical installers, deliberately stale introductory fixture rejected, historical links retained, candidate-versus-stable release sequencing.
