# White-background application icons (#63)

The canonical artwork is `installer/public/skyview-logo.png`. It remains
unchanged for in-app branding. `tests/generate_app_icons.sh` uses ImageMagick 7
to resize that same artwork and composite transparency over opaque white;
there is no redraw, recoloring, cropping or added decoration.

Run from the repository with ImageMagick 7 installed:

```bash
bash tests/generate_app_icons.sh
```

Outputs match every icon referenced in `installer/src-tauri/tauri.conf.json`:
32x32, 128x128, 256x256 (`128x128@2x.png`) and an ICO with 16, 32, 48, 64, 128
and 256 pixel frames. Every frame is opaque with white corners. Rasterized
antialiased edge pixels blend the original artwork against white.

PNGs retain an 8-bit RGBA format with alpha 255 throughout: Tauri's build-time
icon loader requires RGBA even for a fully opaque background. `PNG32:` enforces
that encoding instead of allowing an RGB-only optimization.

Asset inspection verifies all sizes/alpha/corners and the unchanged canonical
artwork. Taskbar-size asset previews on light/dark backgrounds are engineering
evidence. The actual installed Windows taskbar/Mint dock and shortcut-cache
behavior remain owner UAT in [the candidate sheet](UI-UAT-1.2.10.md).
