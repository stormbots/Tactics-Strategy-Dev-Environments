# Accessibility and UI Usability: audit and native UAT

## Current acceptance state

The milestone remains open. Themes (#4 / PR #64), zoom (#5 / PR #65), and
validation guidance (#6 / PR #66) provide the planned implementation. Merge and
CI results are engineering evidence, not native acceptance. Issues #4, #5, and
#6 stay open until their required platform UAT is recorded.

The owner confirmed the banner removal (#57, closed) on the Windows v1.2.7
installation. The combined milestone build still needs native regression checks.
The Overview question is now “Are you ready to build?”; the status card supplies
the actual readiness result.

No test build, version change, signing dispatch, publication or stable promotion
is authorized by this plan. Release preparation remains deferred.

## Requirement audit

| Requirement | Implementation / evidence | Remaining acceptance |
| --- | --- | --- |
| Must: System / Light / Dark (#4) | Top-level radio group; saved preference; live system signal; Light fallback; modern and legacy listeners tested | Windows WebView2 and Mint WebKitGTK system changes, restart persistence and visual acceptance |
| Must: five-step whole-UI zoom (#5) | Exactly 90/100/115/130/150%; saved preference; document scaling and container reflow; exact font/icon scaling and pointer/keyboard tests | Native scale, OS scaling interaction, persistence and all surfaces |
| Must: remove Overview banner (#57) | Removed markup/CSS; browser regression checks; owner confirmation on Windows v1.2.7 | Recheck the combined build, including Mint |
| Must: keyboard, focus, names, announcements | Native radio/range semantics, visible focus, skip link, page/result focus, live phase/result and Schedule statuses; axe and interaction tests | Actual keyboard traversal and screen-reader announcement quality on both platforms |
| Must: contrast and layout | Light/dark palette checks (4.5:1 text, 3:1 controls/focus), axe, all zooms at 640/1040px; default-scale 390/900/1140px checks | Native visual inspection at the minimum window, ordinary laptop size and actual OS scaling |
| Must: preserve work and operations | Selection/navigation/checkbox/log continuity and explicit operation starts tested with simulated operations | Actual Validate and approved tool operation/elevation on both platforms |
| Should: actionable failures (#6) | Recognized backend message catalog, original diagnostics, Repair/Update/manual/mentor guidance, no automatic work, unknown fallback; Windows/Mint fixtures | Representative native cases and safe action flow |
| Should: Install / Repair / Update scope | Existing Overview descriptions; full Repair and managed-tool Update scope explained in guidance and before starting | Student/mentor comprehension; assess whether further wording is needed |
| Should: compact controls, spacing, progress | Theme/range/detail targets, responsive controls, focus/progress/live log behavior covered by browser QA | Native comfort/readability; additional polish beyond implemented work is proposed for later |
| Could: Overview maintenance prominence (#10) | Separate open work; existing Schedule remains the detailed view | Proposed deferral; not an acceptance gate for this implementation |
| Could: reduced motion | Existing CSS disables animations/transitions; reduced-motion browser check passes | Confirm native system preference and usable non-animated progress |
| Could: appearance reset / extra log presentation | No dedicated reset; existing log wrapping, contrast, scaling and scrolling retained | Proposed deferral; existing controls can select System and 100% |

The should/could deferrals above are recommendations for owner acceptance, not
claims those enhancements shipped or that unrelated issues were completed.
No additional mandatory code gap was identified beyond the PR #66 summary fix:
missing-installation labels now require a complete known missing-tool message;
command errors merely ending in “not found” remain Needs attention.

## Codex preparation before asking for UAT

1. Finish code review and successful CI on the exact proposed source; record its
   commit, merged PRs, supported platforms and known limitations below.
2. Once build preparation is separately authorized, provide an explicitly versioned
   native test build and installation/authentication instructions for each OS.
   **Ordinary current CI bundles retain development identity 1.2.1. They are not
   suitable upgrade instructions for the owner's v1.2.7 installation.** Codex must
   resolve test-build identity before handing an installer to the owner.
3. Supply the exact artifact locations, hashes/authentication evidence, and the
   app version expected in the window. Published releases/tags/assets remain
   immutable. Preparing or promoting a release is a separate authorized step.
4. Confirm a Windows 11 desktop and Linux Mint Cinnamon 22.x amd64 desktop/tester
   are available. A Linux container, native package CI, or Chromium preview is not
   a substitute for these desktop sessions. Record a missing platform as blocked.
5. Prepare controlled fixture/workstation cases for #6 without requiring the owner
   to write code, remove development tools, alter project data or improvise repair
   commands. Synthetic report UI tests are labeled simulated; they are not proof
   of a real native failure or native repair.
6. Retain all automated evidence. The PR #66 review used 103 unit/model tests and
   a production build; its established browser suite has 42 checks. The summary
   correction adds regression tests and a targeted desktop/mobile/guidance rerun.
   Check the final PR head's CI rather than treating older green checks as current.

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

| Theme | 90% | 100% | 115% | 130% | 150% |
| --- | --- | --- | --- | --- | --- |
| Light | Pending | Pending | Pending | Pending | Pending |
| Dark | Pending | Pending | Pending | Pending | Pending |

- Text, icons, buttons, navigation, tables and logs should scale together. No
  clipping, overlapping content or horizontal page scrolling; sidebar and logs
  remain scrollable and controls remain reachable. Appearance controls may wrap.
- Use pointer and arrow keys, Home and End on UI zoom. The label, endpoints and
  displayed percentage must be understandable; there are exactly five choices.
- Reopen after selecting a non-default percentage. Confirm it is restored.
- Repeat the largest zoom at the laptop's normal OS scaling; note any limitations.

### 4. Keyboard and assistive technology

- Use Tab / Shift+Tab to traverse navigation, theme, zoom, operation choices,
  buttons, checkboxes, details and log regions. Focus remains visible in both
  themes; Enter / Space / arrow keys activate the appropriate native controls.
- Try the skip link, each page, expandable diagnostics, and scrolling a focused
  log with the keyboard. There should be no focus trap or unreachable control.
- With the platform screen reader, confirm meaningful names, selected theme,
  zoom percentage, PASS / WARNING / FAIL / INFORMATION, operation phase and
  completion/failure messages, and Schedule refresh results. Record missing,
  duplicate, confusing or excessively repeated announcements; axe cannot certify
  their spoken quality. Codex investigates any such issue before acceptance.
- Enable the OS reduced-motion preference. Progress should remain understandable
  while spinners/transitions stop. Assess text/controls in both themes and any
  normally used system contrast/text-scale mode.

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

On the controlled cases supplied by Codex:

- Inspect one Repair case, one manual step, one runtime/platform or mentor case,
  a known available tool update, and unknown-failure fallback where available.
  Explanations should match the problem and the next safe step.
- Expand Technical details and compare the original diagnostic. Failures appear
  first. Warnings and optional Git identity/authentication remain distinct.
- Review Repair and Review Update should only select the operation on Overview.
  Confirm no operation/progress/elevation starts until the explicit start click.
  Repair's full tools/configuration/maintenance scope must be clear.
- View Schedule is read-only navigation. Maintenance uncertainty should not tell
  students to blindly enable or repair an intentionally disabled schedule.
- Record native scenarios that could not be exercised as Not run, including
  unknown failures. Automated fixture coverage is recorded separately; Codex and
  the owner must assess remaining evidence before marking #6 accepted.

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

For each platform, record Pass / Fail / Blocked / Not run for sections 1–7. For a
problem, provide the page, theme, zoom, window size, OS scale, what happened versus
what was expected, and a screenshot/log where useful. Never convert Not run into
Pass based on another platform's result.

| Section | Windows result / evidence | Mint result / evidence |
| --- | --- | --- |
| Overview / banner / default operation | Pending | Pending |
| Theme, live OS changes, persistence | Pending | Pending |
| All page/theme/zoom/window combinations | Pending | Pending |
| Keyboard, focus, names, announcements, reduced motion | Pending | Pending |
| Preserved selections and native operations | Pending | Pending |
| Failure/manual/update/mentor/fallback guidance | Pending | Pending |
| Schedule, pause policy and baseline retention | Pending | Pending |

Codex reviews the evidence, fixes reproducible defects, reruns relevant QA, and
supplies a fresh test build only when authorized. Do not overwrite published
assets or silently reuse an earlier version for changed binaries. The owner
explicitly accepts the tested behavior and any documented limitations/deferrals.
Only then close the accepted issues/milestone. Stable promotion and any fleet
rollout/policy changes remain separate decisions; no such action is part of this
plan.
