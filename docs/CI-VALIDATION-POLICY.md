# CI validation scope and runner cost

## Current rules

The owner approved three categories: full application validation, lightweight/targeted validation and activities that need no automated CI. The workflow implements these categories without changing the required `checks` and `acceptance` names or any release signing/promotion authority.

| Change or activity | Required validation |
| --- | --- |
| Native application/API code, operation/consent/safety behavior, validation/discovery, installers, maintenance, recovery, trust, runtime configuration, dependencies/lockfiles, packaging and release identity | Full common checks, Windows and Linux/Mint native jobs, both trust jobs, acceptance |
| Workflow changes, the scope classifier, reference checker and their tests | Full validation of the policy change itself |
| Unknown executable formats, unclassified files, mixed changes containing full-scope work | Full validation |
| Reference-only Markdown and static images in approved locations | Offline document checks and acceptance, on PRs and main |
| Explicitly allowlisted pure presentation components/tests and the existing standalone prototype files, optionally with reference changes | Common frontend/build/browser/backend checks and acceptance on PRs; no native matrix |
| Existing explicitly named fixture/Mint-infrastructure work | Existing targeted helper workflows; their platform needs remain separate from application packaging |
| Application/presentation changes pushed to main, release branches/tags, manual full runs and unknown events | Full validation, except the existing exact Mint-infrastructure main exception |
| Viewing files/logs/artifacts, issue or PR-description edits, review comments, planning and recording UAT observations | No new CI run; human review, authentication or UAT requirements still apply to the underlying activity |

Ordinary local edits, commits and branches start no GitHub jobs by themselves. Opening or synchronizing a PR does. Draft PRs also trigger the configured checks. Trigger rules are unchanged; approving a protected job can resume existing work and is a separate authorization.

## Reference-only lane

Approved reference formats are root `README.md` and `.md`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` and `.svg` files under `docs/`. New ordinary references in these locations qualify automatically. There is no blanket exception for every file under `docs/`: scripts, HTML/JSON not already classified, runtime assets, agent instructions and unknown formats keep their stronger routing.

A reference must be a regular non-executable file. The classifier checks Git modes in both compared trees; a symlink, executable or mode-changing reference cannot earn the documentation shortcut. Paths are checked without rename detection, so both sides of a rename matter.

Markdown used as execution/configuration input must be registered in `FULL_REFERENCE_PATHS` when its consumer is added. Ordinary prose used for release notes remains documentation; an actual release/candidate run still requires the complete release gates.

The `scope` job emits `application_required`, `native_required`, `documentation_required` and a JSON list of changed reference paths. The JSON travels as data in an environment variable, never shell command text.

The stable `checks` job prepares Python and a small pinned Markdown parser, tests the reference checker, then validates changed references. It checks UTF-8, nonempty Markdown, final newlines, closed code fences, local destinations, Markdown heading anchors in changed sources, references to removed documents/images, and basic image/SVG structure. It also runs the existing version/reference consistency tests. Unrelated historical broken links do not block a new guide.

External/private URLs are not fetched. Code samples are parsed as documentation, not run. Image signatures/SVG XML checks do not replace visual review; Mermaid fences are checked structurally rather than rendered. These limits are deliberate and documented.

For reference-only changes, npm setup, application builds/tests/audit, browser installation/tests, native jobs and trust jobs do not run. A few short Linux jobs still perform classification, reference validation and acceptance. `checks` stays successful only when its actual document checks pass, so existing branch protection needs no renamed required context.

Documentation-only pushes to main use the same lane. The push payload and exact before/after commit range must be valid; malformed/missing data falls back to full validation. Release refs and manual runs cannot use this main-only exception.

## Presentation and targeted work

`PRESENTATION_PATHS` now covers only the named CSS/appearance/theme/zoom files and their tests, plus the already classified Overview prototype HTML/verifier. Operation, consent, readiness and startup files such as `App.tsx`, `model.ts`, `overviewDecision.ts`, Recovery and preflight controls no longer qualify by filename alone. A wording-only edit inside such a file conservatively takes full validation because the same file also controls behavior. Pure presentation can be separated into a reviewed component when appropriate.

The common checks retain their existing frontend/build/audit, script/backend, accessibility and browser coverage. This is a targeted PR lane, not native/candidate acceptance. A targeted native fixture may still require a Windows or Mint runner; targeted does not mean zero cost.

## Acceptance and release protections

The always-evaluated `acceptance` job validates all three boolean scope flags. `checks` must succeed whenever either application or documentation checks are required. Native/trust jobs must succeed when required and be skipped only when their scope permits it. A failure, cancellation, missing output or unexpected skip cannot become acceptance. Native scope also requires application checks.

The full native/trust job definitions, supported matrices, privileged feasibility/installed/upgrade probes, integrity assertions, and release dependencies are unchanged. Release still requires `checks`, `native`, `update-trust` and `acceptance`, with human approval at the existing signing environment. Exact-candidate owner UAT and separate stable promotion authorization remain mandatory.

Application changes need full exact-main evidence. Reference-only merges do not rebuild both installers. Before candidate preparation, retain the complete applicable application/native/trust evidence for the exact release source and authenticate its published assets. A document pass never substitutes for that evidence.

## Verification and checkpoints

Tests execute classification for PRs and exact main ranges, mixed/unknown/new/renamed paths, file modes, releases and malformed events. They execute the acceptance script for passing and failed/canceled/skipped results. Reference-checker tests cover links, anchors, removed targets, encoding/fences, inert examples, path boundaries and image structure.

Use normal protected merge. Preserve useful historical results and cancel only genuinely superseded runs. Before a CI wait, record the exact head/base, run links, completed/pending checks, evidence limits and next action. Explain when a policy or mixed change needs full validation even though ordinary reference edits now take the lightweight lane.

## Historical implementation notes

The following ancestry and measurements describe the earlier policy. The current routing above supersedes earlier statements about new reference files and broad presentation exceptions.

## Ancestry and redundant triggers

The #147 implementation initially inherited pre-squash #145 history from the
published planning branch. GitHub's three-dot PR comparison therefore included
workflow and upgrade-fixture paths even though those files matched current main.
That correctly triggered the path-filtered native probe and UAT-pair workflows.
Merging main into the implementation branch (without changing its tree) removes
those inherited paths while preserving the published planning baseline. Check
PR ancestry before launching more expensive validation; do not broaden path
exceptions to hide unrelated changes.

No automatic triggers or protected signing/publication rules in those auxiliary
workflows are changed by this policy. Superseded runs may be cancelled after
recording their identity; cancellation is not passing evidence.

## Measurement and verification

Use `python3 tests/ci_timings.py --run RUN_ID` on naturally occurring completed
runs. Runner seconds differ from elapsed duration and billed minutes; no dollar
savings or performance guarantee is claimed. Existing cache/migration measurements
remain in `CI-WINDOWS-MIGRATION-PARALLELISM.md` as historical evidence. This policy
supersedes that document's statement that all jobs start in their original topology.

Observed on #147's original source `087d176c37333da7df72602a976954e90dda080a`:

- Native upgrade probe 42274763395 completed successfully: 45 seconds of job span,
  72 summed runner seconds. Correcting ancestry avoids retriggering that probe
  for the same frontend change. This is one observation, not a typical-cost claim.
- Build 42274763391 snapshot was incomplete: only scope and both standalone trust
  jobs had completed, totaling 380 runner seconds. Remaining running work was
  excluded by the timing tool; this is not total cost or successful acceptance.
- No extra native run was dispatched solely to collect timing samples.

Local validation: 26 scope/gate tests, four timing/topology tests and eight Mint
infrastructure policy tests passed. Actionlint 1.7.7 passed the changed workflow
(optional shellcheck integration disabled because shellcheck is not installed;
the unchanged script/static-analysis CI gate remains). Direct parsed comparison
against main confirmed all existing checks/native/trust/release steps, matrices
and Build triggers unchanged. Tests execute the acceptance shell for full,
presentation and fixture scenarios, including failed/cancelled/skipped jobs and
missing outputs. The CI-policy PR itself requires full validation.

Before acceptance, inspect exact-head CI and branch protection configuration.
After policy adoption, verify the narrower path on a real presentation-only PR
and retain full exact-main/candidate evidence before signing or owner UAT.
