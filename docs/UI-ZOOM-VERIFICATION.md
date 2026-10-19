# Five-step UI zoom (#5)

This is the original slider implementation's engineering record. The owner-
approved PR #69 replaced the slider with minus/percentage/plus buttons, retaining
the same five scales. See [approved controls](UI-APPEARANCE-CONTROLS.md) and the
[current acceptance record](UI-MILESTONE-UAT.md). Slider/arrow-key checks below
are historical; test Tab and Enter/Space on the current buttons.

## Behavior and implementation

The UI zoom slider sits beside Theme, with visible − / + endpoints and the
selected percentage. Its five positions are exactly 90%, 100% (first-launch
default), 115%, 130%, and 150%. Native range keyboard behavior supports arrows,
Home, and End; the accessible name is UI zoom and `aria-valuetext` announces the
percentage rather than the internal position. A visible output mirrors that value
without adding duplicate screen-reader announcements.

The local `sde.uiZoom` preference is restored before React renders. Missing,
unsupported, and unreadable values fall back to 100%. Blocked storage does not
prevent changes for the current window. A change updates only the root scale;
there is no navigation, reload, native operation, or component remount.

CSS zoom scales the entire document, including fixed-pixel fonts, icons, controls,
tables, and logs. A 12px operation description therefore renders at 10.8, 12, 13.8,
15.6, and 18px. Existing width breakpoints are now root-container queries so the
layout responds to the logical width available after scaling. Ordinary viewport
media queries would retain a desktop layout even when large zoom needs reflow.
Viewport-height dimensions are divided by the scale to keep a fixed sidebar
within the visible window; its existing independent vertical scrolling remains
available. The appearance toolbar wraps when both controls cannot fit on one row.
Reduced-motion and forced-color media preferences remain viewport/system queries.

## Verification completed

Linux-hosted system Chromium, via a temporary Playwright configuration selecting
`/usr/bin/chromium` (the environment blocks Playwright's browser downloads):

- All 44 component/model tests passed. Zoom tests cover default position, all
  exact scales, restoration, invalid stored values, and blocked storage.
- Production TypeScript/Vite build passed.
- All 38 browser checks passed, including the 15 existing theme and
  accessibility checks and 23 zoom checks.
- Both themes, all five levels, every page at 640×600 (native minimum) and
  1040×600 CSS pixels passed axe WCAG A/AA and overflow checks. The theme suite
  also retains its 390/900/1140px coverage at default zoom.
- Rendered description size and icon width match each exact factor. Fixed
  sidebars stay within the viewport. Keyboard bounds, focus visibility, local
  preference restoration, navigation/checkbox/operation selection preservation,
  pointer selection of every position, and a continuous simulated operation/log
  passed.
- Light and dark maximum-zoom desktop and small-window screenshots were reviewed.
  The earlier theme palette tests retain 4.5:1 text and 3:1 control/focus checks.

From `installer`, run `npm test`, `npm run build`, and `npm run test:browser`.
Screenshots are written to `test-results/`. Browser operations are simulated;
these tests do not establish native webview behavior or real process preservation.

## Deferred native UAT

Keep #5 open until the milestone test build is accepted on Windows 11/WebView2
and Linux Mint Cinnamon 22.x/WebKitGTK. On each platform:

1. Confirm 100% on first launch, all five percentages, and persistence on relaunch.
2. In both themes, visit every page at every zoom in a small laptop window. Check
   readable text, controls/tables/logs, reflow, vertical scrolling, and no clipping
   or horizontal overflow. Check the sidebar can scroll to its footer.
3. Operate the slider with pointer and keyboard; check visible focus and spoken
   label/percentage with assistive technology. Confirm OS/system scaling composes
   sensibly with UI zoom.
4. Change zoom and theme during a real operation and confirm selections, page,
   progress and log history are preserved and work completes once.

No dependency, backend, permissions, version, or release-workflow changes are
included. Release preparation remains deferred until the UI milestone is ready.
