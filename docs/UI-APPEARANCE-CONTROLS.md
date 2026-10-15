# Compact appearance controls

This refinement follows the owner's approved prompt after Windows 11 v1.2.8
installation UAT. It replaces the slider specified in #5 with single-step
minus/percentage/plus buttons and replaces text theme choices with named icon
buttons. #4 and #5 remain open for native acceptance.

## Layout and interaction

- Wide: System, Light, Dark icons beside the page heading, followed by zoom.
  Controls have a 32px visible height at 100%; zoom remains 90/100/115/130/150%.
- Compact: the branding becomes a top header, with an Appearance settings button
  opposite it. Controls live in its nonmodal popover, never beneath the heading.
- Both transitions use the same 1100 logical-pixel container query. This moves
  the previous 650px branding transition earlier to leave room for the heading,
  sidebar, and compact controls. Application zoom changes logical available width.
- The panel stays open during appearance changes while the layout remains compact.
  It closes on toggle, Escape, outside pointer activation, page navigation, or
  transition to wide layout. Keyboard opening focuses the first theme button;
  Escape restores trigger focus. At either zoom limit, focus moves to the enabled
  opposite zoom button instead of falling back to the document. Held-key
  auto-repeat is suppressed so that focus transfer cannot reverse zoom direction. Tab is not trapped. Resizing transfers focus
  between equivalent inline controls and the compact trigger.
- One mounted owner holds both preferences across panel dismissal and layout
  transitions, including when local storage cannot be written.
- Selected themes use a thicker border as well as a filled background. Native
  buttons expose names/pressed states; the trigger exposes expanded/controls.
  In forced colors, the selected inset marker and outer keyboard-focus ring
  remain distinct.
  Theme tooltips appear on hover/focus and can be dismissed with Escape. Only
  one set of controls is exposed. One polite live region reports the zoom value.
- At very narrow logical widths, labels stack above their button group inside
  the panel. The panel is width-constrained and scrolls vertically in short windows.
  Available height is measured beneath the trigger on opening, zoom changes and
  window resizing, including very short windows. Escape also dismisses hovered
  theme tooltips while keyboard focus remains elsewhere; a new hover/focus
  interaction shows them again.

## Engineering verification

Browser verification uses simulated machine operations, not native provisioning.
The matrix covers both themes, all five zoom values, and widths 320, 640, 1100,
1101, 1440, and 1920 pixels; existing regression checks exercise all application
pages at 640/1040 pixels and theme changes at 390/900/1140 pixels. Checks include
WCAG AA axe scans, contrast tokens, preference persistence/live OS theme changes,
keyboard operation, popover focus/dismissal, layout transitions, blocked storage,
a short viewport, and preservation of active validation/provisioning logs.

Final review checks: 103 unit/model/component tests and all 70 browser checks
passed. The review follow-up covers zoom-limit focus, live resizing to a very
short viewport, hovered-tooltip dismissal, and restoring tooltips on renewed
focus/hover, and distinct keyboard focus on selected controls in forced colors.
TypeScript/Vite frontend compilation and formatting passed. Browser verification used Debian Chromium
154.0.8037.57 with a temporary executable override; CI uses Playwright's installed
Chromium with the standard repository configuration. Native desktop UAT is pending.

Implementation screenshots (browser preview, simulated status):

| Layout | Light | Dark |
| --- | --- | --- |
| Wide, 1440×820 at 100% | [Light wide](ui-appearance-controls/light-wide.png) | [Dark wide](ui-appearance-controls/dark-wide.png) |
| Compact, 640×820 at 100%, panel open | [Light compact](ui-appearance-controls/light-compact.png) | [Dark compact](ui-appearance-controls/dark-compact.png) |

## Remaining native UAT

On Windows 11/WebView2 and booted Mint Cinnamon/WebKitGTK, verify visual size and
placement at normal and enlarged OS scaling; all five application zoom values;
System live changes and Light/Dark overrides; restart persistence; compact panel
positioning, short-window scrolling, keyboard focus and Escape across resize/zoom;
and appearance changes during Validate without lost logs, selections or results.
Check Narrator/Orca names, selected/expanded states, and a single useful zoom
announcement. Also inspect hover/focus tooltips, reduced motion, and high contrast.

Native desktop acceptance for this refinement has not run. The owner's successful
v1.2.8 installation does not accept these subsequent changes. Mint desktop UAT
remains blocked by the absence of a desktop environment; CI is engineering evidence.
No installer dispatch, version changes, release preparation, stable promotion,
automatic-installation resume, or rollout is part of this PR.
