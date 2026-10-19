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
