# System-aware themes (#4)

## Implemented behavior

The Theme radio group at the top of every page provides System, Light, and Dark.
System is the first-launch default and uses the webview's live
`prefers-color-scheme` signal. If that API is unavailable or throws, System stays
selected with the light palette. Explicit Light/Dark choices ignore system
changes. The preference is local (`sde.theme`) and is restored before rendering.
If local storage is blocked, the control still works for the current window.

Theme changes only update the root palette. They do not reload or remount the
application, navigate, invoke native commands, or restart an operation. Log panels,
status badges, tables, links, checkboxes, progress, focus indicators, and buttons
use the same theme palette. Dark backgrounds are muted navy; the shared logo has
a silver backing in dark mode for legibility. The radio selection uses an outline
and underline in addition to color. Native radio keyboard behavior is retained.

## Automated and visual verification

Verified in Linux-hosted system Chromium using a temporary Playwright launch
configuration selecting `/usr/bin/chromium`. This substitutes for the Playwright
browser download blocked by this environment; it is not native WebView acceptance.

- Production TypeScript/Vite build passed.
- All 40 component/model tests passed, including live system changes, manual
  overrides, preference restoration, unavailable/throwing detection, blocked storage,
  and legacy media-query listener updates and cleanup.
- Four existing accessibility/interaction browser checks passed.
- Eleven theme browser checks passed: Overview, Validation, Schedule, and About in
  both palettes at 390, 900, and 1140 CSS pixels; WCAG A/AA axe checks; no horizontal
  overflow; radio arrow-key selection and visible focus; reload persistence;
  system changes and unavailable-detection fallback; preservation of selected operation and advanced checkbox; and
  an uninterrupted simulated operation with visible log and successful completion.
- Explicit palette checks passed for normal text at 4.5:1 and control boundaries,
  progress, and focus indicators at 3:1. These complement axe rather than treating
  axe as complete WCAG certification.
- Overview screenshots in light and dark, desktop and narrow layouts, were
  visually reviewed. Browser preview operations/status are simulated.

Run the repository commands from `installer`: `npm test`, `npm run build`, and
`npm run test:browser`. Browser screenshots are written to `test-results/`.

## Native acceptance still required

| Platform | Status | Remaining checks |
| --- | --- | --- |
| Windows 11 / WebView2 | Pending | System default, live OS theme changes, manual override, relaunch persistence, keyboard/focus, all pages, small window, active native operation preserved |
| Linux Mint Cinnamon 22.x / WebKitGTK | Pending | Same checks; verify system signal or documented Light fallback where unavailable |

Also verify representative error/completion states and assistive-technology
announcements during native testing. External system-owned elevation prompts and
applications retain their own appearance settings. No release or stable-promotion
action is part of this change. Keep #4 open until required native acceptance and
visual acceptance are recorded.

## Implementation review

The review found and fixed missing live updates in webviews that expose the
legacy `MediaQueryList.addListener` API instead of `addEventListener`. Both APIs
now remove their listeners on cleanup, including React Strict Mode remounts.
The browser suite also switches themes on each page and verifies navigation is
preserved. It covers the unavailable detection fallback in a browser, alongside
component tests for throwing APIs and blocked storage.

No backend, permissions, dependency, version, or release workflow changes are
included. The previously committed Overview question is included in this PR.
Native theme detection, actual process preservation, screen-reader behavior, and
relaunch persistence remain platform acceptance checks, not claims made by the
simulated Chromium tests.
