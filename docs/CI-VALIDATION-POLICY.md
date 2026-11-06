# CI validation scope and runner cost

## Policy

PRs changing only the explicit `PRESENTATION_PATHS` allowlist in
`tests/ci_scope.py` run the existing Linux checks job: all frontend tests,
TypeScript/production build, dependency audit, script/backend contracts and
browser/accessibility regression. They do not repeat Windows/Mint native builds
or standalone trust tests. This is PR feedback, not native/candidate acceptance.

The allowlist covers named existing presentation components/models/tests and the
guided Overview planning documents. New/unknown files, native bridges, recovery
APIs, dependencies/lockfiles, packaging, platform scripts and CI changes require
full application validation. Mixed and renamed paths fail closed; classification
uses every changed path from the merge base with rename detection disabled.
Changes to the classifier or its tests now require full validation themselves.
Existing narrowly defined fixture/Mint infrastructure exceptions remain, apart
from this stricter treatment of classifier changes.

Main application pushes, release branches/tags, manual dispatch and unknown events
retain full native/trust validation. The existing exact Mint-infrastructure-only
main exception remains; it cannot suppress an application or classifier change.
Full runs now wait for `checks` before allocating native/trust matrices. This
reduces wasted native runner time on failing PRs, at the cost of longer elapsed
time for successful full runs. No duplicated provisioning or new native runners.

The always-evaluated `acceptance` job requires successful scope classification,
valid scope outputs and success for every applicable job. A failure, cancellation,
unexpected skip or missing scope output cannot be reported as acceptance. Release
retains every prior dependency and additionally depends on acceptance. Signing
still requires its existing human environment approval; candidate owner UAT and
separate stable-promotion authorization are unchanged.

Repository administrators should require the stable `acceptance` check alongside
existing required checks. Branch-protection inspection returns HTTP 403 for the
current integration, so this work does not claim to inspect or change those
settings. Review that configuration before adopting the narrower merge policy.
All final-main, Windows feasibility/bootstrap, coordinator/trust, signed SYSTEM,
actual Mint 22.3 bootstrap/manual/scheduled-tool and signed-upgrade gates remain
mandatory where applicable. A presentation-only PR pass does not fulfill them.

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
