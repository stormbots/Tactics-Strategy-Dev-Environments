# Accessibility and UI Usability: completion plan

Prepared October 19, 2026 for milestone 1. Codex owns engineering, review,
automated verification, candidate preparation, evidence and follow-up fixes.
The owner performs desktop UAT after the candidate handoff.

## Finish line

Deliver a reviewed, authenticated Windows/Mint testing candidate and a concise
UAT checklist. After owner UAT, fix reported defects, record the tested scope
and explicitly accepted limitations, and close the accepted issues and milestone.

The remaining scope is #4 (themes), #5 (zoom), #6 (validation guidance) and #63
(white-background application icon). #57 (banner removal) is already closed.
Themes, zoom and guidance are already merged. PR #69's approved theme icon
buttons and minus/percentage/plus zoom supersede the original radio/slider UI.

## Execution sequence

1. **Establish one source and acceptance record.** Work on a focused branch from
   current main, preserving the separate draft #72/#73 work. Reconcile the
   published v1.2.9 owner-UAT/stable-promotion statement with the older pending
   checklist. Preserve that acceptance and identify platform-specific evidence
   that was not supplied. Keep the milestone open for this new UAT handoff.

2. **Finish #63.** Preserve the logo artwork, colors, proportions and placement;
   give the application icon an opaque white background. Update every PNG/ICO
   variant referenced by Tauri. Keep the shared in-app logo unchanged. Inspect
   taskbar-size previews on dark and light backgrounds and check ICO sizes and
   alpha handling. Document how the assets were produced.

3. **Refresh the UAT instructions.** Update the consolidated milestone record
   to include #63 and the current approved appearance controls. Retain historical
   verification separately. Provide a short results sheet covering installed
   version/OS, icon visibility, appearance/persistence, small-window layout,
   keyboard/speech, validation guidance and preserved active work. Link deeper
   cases only where evidence remains outstanding; do not ask the owner to
   manufacture failures on a working computer.

4. **Verify and review.** Run the frontend production build, existing
   unit/component suite and browser accessibility/appearance/guidance suite;
   inspect relevant screenshots. Check icon artifacts and whitespace. Run
   candidate-identity/workflow checks if candidate preparation changes. Open a
   focused PR and require the applicable full CI/native packaging and upgrade
   checks on its final source. Diagnose failures before repeating affected
   checks. Review the final complete diff; no unrelated feature work.

5. **Deliver one fresh candidate.** Select the next unused immutable application
   version after checking remote tags/releases and active candidate work. Use
   the existing protected signing and prerelease process, adapting only the
   fixed candidate/version path where needed. Merge reviewed source after its
   required checks, verify exact-main CI, and start candidate preparation.
   Preserve published v1.2.9 and earlier assets. Verify package identities,
   native upgrade results, all five published assets, signatures and hashes
   before giving installation instructions. Record exact source/version and
   download links in the UAT handoff.

6. **Owner UAT and closeout.** The owner tests the authenticated candidate and
   reports Pass/Fail/Blocked/Not run. Codex interprets the results, fixes
   reproducible defects and reruns affected verification. Changed published
   binaries require another unused candidate version. Record explicit owner
   acceptance and any named limitations, then close #4/#5/#6/#63 as accepted
   and the milestone when all are resolved. Unsupported/unrun cases are never
   inferred to pass from browser, Windows Server or container evidence.

## UAT handoff contents

- Exact candidate version/source, authenticated downloads and installation steps.
- A short summary of changes since the accepted v1.2.9 appearance build.
- A prefilled results sheet separating Windows 11/WebView2 and Mint
  Cinnamon/WebKitGTK. Record OS scaling, app zoom and assistive technology.
- Focused checks: dark/light taskbar icon; System/Light/Dark and persistence;
  five zoom values on each page; compact panel and focus; Validate continuity;
  plain-language guidance/details and Review actions that do not start work.
- Explicit remaining native/screen-reader cases and safe fixture requirements.

## Timing and external checkpoint

Target the remaining engineering and review in the current afternoon (roughly
2–4 hours), subject to findings, CI queues and native build time. UAT and defect
resolution are separate elapsed time; the milestone is not closed merely
because a candidate is available.

The existing `sde-release-signing` GitHub environment requires the owner's human
approval. Prepare the exact reviewed source, passing checks and signing run
before requesting that approval. Do not bypass the checkpoint. If access or
approval blocks publication, retain the completed engineering and report the
exact run/action needed; unsigned artifacts are not the final UAT handoff.

Stable promotion, fleet rollout, application-update policy changes, #72 native
host work and unrelated milestone work are outside this completion plan.
