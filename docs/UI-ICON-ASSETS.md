# Rounded-square application icons (#63)

The owner supplied `installer/src-tauri/icons/skyview_logo_rounded_square.svg`
after Windows 11/Mint Cinnamon UAT of v1.2.10. Its white rounded-square tile
replaces the rejected square white background. Preserve the supplied SVG bytes,
artwork, colors, proportions and transparent exterior; do not flatten its corners
onto white. The separate `installer/public/skyview-logo.png` stays unchanged for
in-app branding.

Run from the repository with librsvg's `rsvg-convert` and ImageMagick 7 installed
(Debian/Ubuntu package for the renderer: `librsvg2-bin`):

```bash
bash tests/generate_app_icons.sh
```

Outputs match every icon referenced in `installer/src-tauri/tauri.conf.json`:
32x32, 128x128, 256x256 (`128x128@2x.png`) and an ICO with 16, 32, 48, 64, 128
and 256 pixel frames. The SVG is rendered at 1024px, then resampled for each
output. Every frame has transparent outer corners, an opaque white tile interior
and antialiased rounded edges. ICO frames retain this alpha channel too.
At 16px, the curve partially covers the corner pixels; retain that antialiasing
rather than clipping the supplied shape. Generated metadata is stripped so
repeated generation with the same tools does not introduce timestamp-only changes.

PNGs retain an 8-bit RGBA format: Tauri's build-time icon loader requires RGBA.
`PNG32:` enforces that encoding, preserving the transparent exterior and opaque
interior instead of allowing an RGB-only optimization.

Asset inspection verifies all sizes, transparent corners, white tile interior,
alpha edges and unchanged in-app artwork. Taskbar-size previews on light/dark
backgrounds are engineering evidence. Actual installed Windows taskbar/Mint dock
and shortcut-cache behavior remain focused UAT in [the candidate sheet](UI-UAT-1.2.11.md).


## Windows Shell caching follow-up

The published v1.2.11 EXE contains the correct rounded frames, matching the
installed Windows 11 binary reported by the owner. A disposable native probe
reproduced old Shell pixels after replacing the v1.2.10 EXE at the same path;
direct resource extraction remained correct. Updating an existing shortcut to
a new ICO path rendered rounded through the Shell at 16 and 32px.
[Native evidence](https://github.com/stormbots/Tactics-Strategy-Dev-Environments/actions/runs/39372604666)
authenticates both published fixtures before extraction and retains PNG/JSON.
The shortcut-arrow badge covers the bottom-left corner, so shortcut shape checks
use the other three corners while retaining all four pixel measurements.

Windows builds generate `gen/app-icons/skyview-dev-setup-<version>.ico` as a
byte-identical copy of the reviewed ICO. The Windows-only Tauri configuration
bundles it under `app-icons/`. The NSIS postinstall hook updates owned Start and
existing desktop shortcut icon references, preserving their targets/AppUserModelID,
and notifies the Shell. The running window explicitly fills its large icon slot
from embedded resource 32512, avoiding the fallback to cached executable pixels.
No Linux icon/runtime changes are required: the owner accepted Mint v1.2.11.
The [v1.2.12 Windows UAT sheet](UI-UAT-1.2.12.md) tracks actual desktop acceptance.
