#!/usr/bin/env bash
# Build platform icons from the owner-supplied SVG. Requires librsvg/ImageMagick 7.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
output="$root/installer/src-tauri/icons"
source_image="$output/skyview_logo_rounded_square.svg"
temporary="$(mktemp -d)"
trap 'rm -rf -- "$temporary"' EXIT
# Keep the SVG's white rounded tile and transparent exterior. Flattening onto
# white would restore the square corners rejected during native desktop UAT.
rsvg-convert --width 1024 --height 1024 --output "$temporary/icon.png" "$source_image"
for size in 32 128 256; do
  name="${size}x${size}.png"
  if [[ "$size" = 256 ]]; then name=128x128@2x.png; fi
  magick "$temporary/icon.png" -resize "${size}x${size}" \
    -alpha on -strip "PNG32:$output/$name"
done
magick "$temporary/icon.png" -alpha on -strip \
  -define icon:auto-resize=256,128,64,48,32,16 "$output/icon.ico"
