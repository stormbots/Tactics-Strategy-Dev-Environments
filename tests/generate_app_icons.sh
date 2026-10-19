#!/usr/bin/env bash
# Build platform icons from the unchanged shared artwork. Requires ImageMagick 7.
set -euo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source_image="$root/installer/public/skyview-logo.png"
output="$root/installer/src-tauri/icons"
for size in 32 128 256; do
  name="${size}x${size}.png"
  if [[ "$size" = 256 ]]; then name=128x128@2x.png; fi
  magick "$source_image" -resize "${size}x${size}" \
    -background white -alpha remove -alpha off "$output/$name"
done
magick "$source_image" -background white -alpha remove -alpha off \
  -define icon:auto-resize=256,128,64,48,32,16 "$output/icon.ico"
