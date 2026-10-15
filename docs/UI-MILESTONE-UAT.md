# Accessibility and UI Usability: audit and native UAT

## Current acceptance state — audited 2026-10-15

GitHub milestone **Accessibility and UI Usability** contains four issues: #57
closed; #4, #5 and #6 open. Keep those three open until native acceptance and any
explicitly accepted limitations are recorded. Implementation is merged, not yet
accepted on the target desktops.

Themes (#4 / PR #64), zoom (#5 / PR #65), and validation guidance (#6 / PR #66)
are implemented. PR #69 refines theme/zoom size and responsive placement. Audited
merged source: `3af352d8d9cba3d77c7d8e216522c3add0673144`; reviewed PR #69 head:
`cae15dbb22ea83defc37d05e1aa78a6b01073969`.

The owner confirmed banner removal on Windows v1.2.7 and successful Windows 11
installation of v1.2.8. The v1.2.8 visual review identified oversized appearance
controls and an unstable slider; PR #69 addresses that feedback. **Published
v1.2.8 installers do not contain PR #69 and cannot accept these refinements.**
Their installation pass is retained historical evidence, not a complete UI pass.
The Overview question is “Are you ready to build?”; readiness comes from its card.

**Release preparation remains deferred.** No version allocation/change, application
build dispatch, signing, tag, publication, stable promotion, policy resume or rollout
is authorized by this audit. A later authorized candidate must contain PR #69 and
use a fresh version; never replace published v1.2.8 binaries. The existing
[v1.2.8 guide](UI-UAT-1.2.8.md) applies only to that older candidate.

Windows 11/WebView2 desktop acceptance is pending a suitable candidate. Mint
Cinnamon 22.x/WebKitGTK desktop acceptance is blocked by desktop availability.
The owner has no disposable VMs; do not ask them to supply VMs merely to repeat
CI. Real destructive/Repair scenarios remain blocked without a disposable desktop
and reliable full-environment restoration.

## Requirement audit

| Issue / requirement | Merged implementation and engineering evidence | Remaining native acceptance |
| --- | --- | --- |
| #4: System/Light/Dark, default and persistence | Named icon buttons with pressed state; System first-launch default; live system signal and Light fallback; stored manual overrides | Windows and Mint live OS change, explicit override, restart persistence; document detection limitations |
| #4: consistent accessible appearance | Navy dark palette; shared application surfaces; contrast/axe checks; focus and non-color selection indicator | Both themes across all pages and app-owned dialogs; native high contrast, keyboard, Narrator/Orca; external OS dialogs follow OS settings |
| #5: five-step whole-UI zoom | Exactly 90/100/115/130/150%, default 100%, immediate document scaling, stored selection | Exact steps, native scaling across surfaces, OS scaling interaction and restart persistence |
| #4/#5 approved refinement: compact controls | PR #69 replaces text/radio theme choices and slider with icon buttons and minus/percentage/plus; shared 1100-logical-pixel responsive transition | Wide heading placement; compact branded header/settings icon and nonmodal panel; no controls wrapping below heading |
| #4/#5: accessible interactions | Named native buttons, pressed/expanded states, one polite zoom announcement; tooltips; focus transfer at zoom limits and responsive transitions; held-key reversal guard | Spoken names/states/value, limit behavior, tooltip dismissal, outside click/Escape/navigation behavior, short-window reachability |
| #4/#5: preserve work | Browser operation/log, navigation, selection and checkbox continuity | Actual Validate plus a separately prepared native tool operation/elevation on each platform |
| #6: plain-language failed-check guidance | Recognized diagnostic catalog: what failed, readiness impact, safe Repair/Update/manual/mentor next step; expandable original diagnostics | Representative actual native reports, understandable wording and correct next action on each platform |
| #6: explicit action and scope | Review actions select Overview operation without starting; broad Repair scope explained; Schedule read-only | No work/elevation until explicit start; full Repair scope understood; disabled schedule not blindly enabled |
| #6: distinctions and fallback | PASS/WARNING/FAIL/INFORMATION retained; optional identity/auth informational; unknown fallback does not invent diagnosis | Healthy/informational report and representative failure cases; retain unexercised native branches as Not run |
| #57: banner removal (closed) | Removed markup/CSS, browser checks and owner Windows confirmation | Combined-build regression on both platforms; preserve branding/default Install/content order |

The issue #5 slider/arrow-key requirements and #4 persistent text labels are
superseded by the owner's approved button refinement merged in PR #69. Test
Tab/Shift+Tab and Enter/Space on appearance buttons, not slider arrows/Home/End.
Keep the issue history; do not mistake the obsolete interaction for a regression.

No additional mandatory implementation gap was identified in this audit; native
acceptance remains outstanding. #10 (maintenance prominence) and #63 (icon white
background) are open **outside this milestone**; they are not silently accepted,
closed or added to this milestone. Extra reset controls and log presentation are
not requirements of its four issues. Reduced motion remains an accessibility
regression check, not a reason to waive a discovered defect.

## Engineering evidence and handoff gates

- PR #69's exact reviewed head passed all six verification jobs:
  [CI run 38795492101](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/38795492101).
  The release job was skipped. Local evidence: 103 unit/model/component tests,
  70 browser checks, frontend compilation, formatting and whitespace checks.
- The browser matrix covers both themes/all zooms at 320/640/1100/1101/1440/1920px,
  with all-page regressions and accessibility checks. Browser machine operations
  are simulated. These results do not certify WebView2/WebKitGTK desktop behavior.
- [Fixture evidence](UI-NATIVE-UAT-EVIDENCE.md) records successful helper-only
  Windows Server 2022 and Mint 22.3 Xfce-userland/container automation. It proves
  setup/restoration behavior, not Windows 11/Cinnamon UI, native Repair or speech.
- Post-merge CI is a separate run; do not infer its completion from PR checks.
  Before any later candidate handoff, Codex rechecks the exact candidate source,
  authentication, package identities and known limitations. Development-identity
  1.2.1 CI packages are not upgrade candidates for the owner's installed v1.2.8.
- Only after separate build authorization does Codex supply a versioned,
  authenticated candidate and precise installation instructions. Until then,
  preparation is documentary and native execution of the refinements is pending.

Codex owns fixtures, evidence interpretation, diagnosis and follow-up QA. The
owner handles desktop UAT without writing code or manufacturing failures.
[Controlled fixture instructions](UI-NATIVE-UAT-FIXTURES.md) remain the authority
for enrollment, preconditions and restoration; helper execution evidence is
already recorded, while actual installed-app fixture UAT remains pending.

## Record before testing

| Field | Windows | Linux Mint |
| --- | --- | --- |
| Test build version / source SHA | Pending | Pending |
| Installer source and authentication | Pending | Pending |
| OS, webview, desktop, display resolution | Pending | Pending |
| OS display scale and text/accessibility scale | Pending | Pending |
| Existing app / baseline / application-update policy | Pending | Pending |
| Screen reader and version | Pending | Pending |
| Tester and local date | Pending | Pending |

Use a clean application preference profile for first-launch checks, prepared by
Codex without deleting user data. Other checks use the same profile across app
restarts to prove persistence. Save normal work before planned native operations.

## Owner UAT sequence, once Codex supplies the test build

Use the same sequence on both operating systems. Report results in ordinary
language; Codex will interpret logs and maintain the acceptance record.

### 1. Open and understand Overview

- Confirm the expected app version on About and Schedule's “App version in this
  window.” The decorative banner is absent; the question heading remains visible;
  Install is the default operation even when the workstation is Ready.
- Read the status card. Its result should agree with actual validation, without
  treating the heading as a readiness claim. Check navigation and sidebar branding.

### 2. Theme behavior and persistence

- On the prepared first-launch profile, System is selected and matches the OS.
- With System selected, change the OS between Light and Dark while SDE stays open.
  Appearance should follow live; if the system signal is unavailable, document
  the Light fallback with System still selected rather than claiming live support.
- Select Light, then Dark. Each should override OS changes. Return to System.
- Close and reopen SDE when no operation is active. The selected preference must
  survive. Also check restoration with explicit Light and Dark.

### 3. Zoom / page / window matrix

Check Overview, Validation, Schedule and About at every cell below. Use a typical
1040×820 window and the 640×600 minimum; allow normal vertical scrolling.
Record a separate copy of this matrix for each platform/window size, noting OS
scale and results on all four pages. On the clean first-launch profile, verify
100% is selected before changing it.

| Theme | 90% | 100% | 115% | 130% | 150% |
| --- | --- | --- | --- | --- | --- |
| Light | Pending | Pending | Pending | Pending | Pending |
| Dark | Pending | Pending | Pending | Pending | Pending |

- Text, icons, buttons, navigation, tables and logs should scale together. No
  clipping, overlapping content or horizontal page scrolling; sidebar and logs
  remain scrollable and controls remain reachable. Controls must not wrap beneath
  the heading: use inline controls when wide and the settings popover when compact.
- Use minus/plus by pointer and Tab then Enter/Space. Each activation moves one
  step; the percentage remains readable in its fixed-width segment. At 90% minus
  is disabled; at 150% plus is disabled. Focus moves to the enabled opposite button
  when reaching a limit. Holding Enter/Space must not reverse direction after
  that transfer. There is no slider or slider-specific keyboard interaction.
- Reopen after selecting a non-default percentage. Confirm it is restored.
- Repeat the largest zoom at the laptop's normal OS scaling; note any limitations.

### 3a. Compact settings and responsive transitions

- Start at 1440×820 and 100%, then resize through the layout transition to
  640×600. Branding/navigation move to the top header and a settings icon appears
  opposite the branding. No appearance row should wrap below the heading.
- At each zoom, resize both ways across the transition. The breakpoint is 1100
  logical pixels: application zoom and OS scaling can change its apparent width.
  Judge the resulting layout, not a fixed physical-pixel screenshot.
- Open Appearance settings by keyboard: focus enters the first theme button.
  System/Light/Dark use half-circle/sun/moon icons with accessible names and a
  selected border/fill. Zoom uses minus, current percentage, plus. Choices apply
  immediately; the panel stays open while the layout stays compact.
- Tab and Shift+Tab can leave the nonmodal panel. Escape closes it and restores
  trigger focus; the trigger toggles it; outside clicks preserve clicked focus;
  page navigation dismisses it. Test resizing to wide with panel focus, and
  resizing to compact with inline-control focus: focus must remain meaningful.
- Shorten the window at 150% with the panel open. It remains within the available
  area beneath the trigger, scrolls internally as needed, and all controls remain
  reachable. No overlay blocks unrelated controls after dismissal.
- Test hover/focus theme tooltips: Escape dismisses them, including when pointer
  hover and keyboard focus are separate; renewed hover/focus shows them again.

### 4. Keyboard and assistive technology

- Use Tab / Shift+Tab to traverse navigation, theme, zoom, operation choices,
  buttons, checkboxes, details and log regions. Focus remains visible in both
  themes; Enter / Space / arrow keys activate the appropriate native controls.
- Try the skip link, each page, expandable diagnostics, and scrolling a focused
  log with the keyboard. There should be no focus trap or unreachable control.
- With the platform screen reader, confirm meaningful names, selected theme,
  Appearance settings expanded/collapsed state, theme pressed state and one useful
  zoom announcement per change, PASS / WARNING / FAIL / INFORMATION, operation phase and
  completion/failure messages, and Schedule refresh results. Record missing,
  duplicate, confusing or excessively repeated announcements; axe cannot certify
  their spoken quality. Codex investigates any such issue before acceptance.
- Enable the OS reduced-motion preference. Progress should remain understandable
  while spinners/transitions stop. Assess text/controls in both themes and any
  normally used system contrast/text-scale mode. In Windows high contrast, a
  selected theme must retain a distinct outer keyboard-focus ring.

### 5. Preserve current work and live operations

- Select Update and change the Advanced checkbox; navigate to another page.
  Switch theme/zoom. The selected operation, checkbox, current page and expanded
  content should remain as selected; nothing should reload or start work.
- Run Validate and change theme/zoom while it runs. Progress and log history must
  continue and the operation should complete once, with understandable focus and
  result. Export its log for Codex.
- In a planned controlled native tool operation, repeat the appearance changes
  across administrator approval and active work. Codex prepares the case and
  explains its scope first. Record operation completion, preserved work and log;
  do not use a synthetic browser operation as evidence for this item.

### 6. Actionable failure guidance

Codex prepares one case at a time only on a disposable environment. Never
manufacture these failures on the owner's working machine. Record the original
native diagnostic, plain-language impact/next step, technical details, action
behavior, restored state and post-restore Validate result.

| Case | Preparation and expected acceptance | Current native status |
| --- | --- | --- |
| Healthy / optional identity/auth | Dedicated baseline account; actual Validate. Optional Git identity/auth stays INFORMATION; warnings remain distinct | Pending candidate/environment |
| Repair guidance | Helper `workspace`, only with empty workspace; missing workspace shows Repair guidance. Review Repair selects Overview/Repair without work/elevation | Pending disposable desktop |
| Manual guidance | Helper `git-manual`; non-main default branch shows manual next step, original diagnostic, no automatic Repair for the row | Pending disposable desktop |
| Mentor guidance | Helper `mentor-repository`; missing synthetic configured repository shows mentor guidance without implying project loss | Pending disposable desktop; Validate only, restore before any tool operation |
| Disabled/uncertain schedule | Separate disposable snapshot, not supported by helpers; read-only Schedule/mentor guidance, no blind enable/Repair recommendation | Not run |
| Genuine managed tool update | Known supported older-tool snapshot plus genuine package metadata; Review Update selects without work; show managed-tool scope | Not run; no fabricated update metadata or owner-tool downgrade |
| Runtime / unknown failure | Independently available real report; safe mentor/details fallback, no invented diagnosis/command; command ending “not found” is not automatically a missing installation | Not run; simulated regression tests are separate evidence |
| Real elevated tool operation | Separately approved full-scope operation on workspace snapshot; theme/zoom changes preserve progress/logs across elevation | Blocked without disposable desktop and full snapshot recovery |

Failures should appear first; technical details retain the original diagnostic.
Repair's broader tools/configuration/maintenance scope must be clear. No Review
button starts work: only the explicit operation start may do so. For repository
fixtures run Validate only. Restore between cases using the documented helper;
never upload its private backup/ledger. If restoration refuses changed content,
stop and use full snapshot recovery. Full Repair requires full snapshot recovery,
not helper-only rollback. Missing runtime/update/fallback native cases remain
Not run until exercised or explicitly accepted as limitations by the owner.

### 7. Schedule and retained behavior

- Confirm weekly maintenance and its existing settings remain intact and SDE
  application-installation pause remains as previously configured. No policy
  resume is part of this UI milestone.
- A manual app install can leave “Last observed installed app version” and engine
  history at the previous completed maintenance attempt. Judge those fields with
  their timestamps; use “App version in this window” for the current UI version.
  An open SDE window can itself cause “SDE or maintenance is active.”
- The development-tool baseline remains separate from the app version. Record
  results and send logs/screenshots to Codex for interpretation.

## Result sheet and acceptance gate

For each platform, record Pass / Fail / Blocked / Not run for sections 1–7 (including 3a). For a
problem, provide the page, theme, zoom, window size, OS scale, what happened versus
what was expected, and a screenshot/log where useful. Never convert Not run into
Pass based on another platform's result.

| Section | Windows result / evidence | Mint result / evidence |
| --- | --- | --- |
| Overview / banner / default operation | Pending new candidate | Blocked: no desktop |
| Theme, live OS changes, persistence | Pending new candidate | Blocked: no desktop |
| All page/theme/zoom/window combinations | Pending new candidate | Blocked: no desktop |
| Compact panel, transitions, tooltips and zoom limits | Pending new candidate | Blocked: no desktop |
| Keyboard, focus, names, announcements, reduced motion | Pending new candidate | Blocked: no desktop |
| Preserved selections and native operations | Pending candidate; tool operation blocked without disposable desktop | Blocked: no desktop |
| Failure/manual/update/mentor/fallback guidance | Controlled cases blocked without disposable desktop; other cases Not run | Blocked: no desktop |
| Schedule, pause policy and baseline retention | Pending new candidate | Blocked: no desktop |

Codex reviews the evidence, fixes reproducible defects, reruns relevant QA, and
supplies a fresh test build only when authorized. Do not overwrite published
assets or silently reuse an earlier version for changed binaries. The owner
explicitly accepts the tested behavior and any documented limitations/deferrals.
Only then close the accepted issues/milestone. Stable promotion and any fleet
rollout/policy changes remain separate decisions; no such action is part of this
plan.

## Next phase and closure checklist

After plan review, Codex keeps the acceptance record current and investigates any
newly reported defects. No owner execution is requested while the authenticated
candidate containing PR #69 is unavailable. Build authorization remains a separate
later decision.

Before closure, Codex links exact candidate/source/authentication evidence and
per-platform results, fixes reproducible defects and reruns relevant QA. The
owner then accepts each issue and any named limitations explicitly. Pending,
Blocked and Not run are never converted to Pass by CI or another platform's
success. Keep #4/#5/#6 and the milestone open until that decision. Stable
promotion, fleet rollout and application-update policy changes require separate
authorization even after UI acceptance.
