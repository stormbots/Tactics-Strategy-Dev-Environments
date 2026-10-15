import { useLayoutEffect, useState } from "react";

export const zoomLevels = [90, 100, 115, 130, 150] as const;
type ZoomLevel = (typeof zoomLevels)[number];
const storageKey = "sde.uiZoom";

function readZoom(): ZoomLevel {
  try {
    const value = Number(localStorage.getItem(storageKey));
    if (zoomLevels.includes(value as ZoomLevel)) return value as ZoomLevel;
  } catch {
    // Zoom remains available for this window if preference storage is blocked.
  }
  return 100;
}
function applyZoom(value: ZoomLevel) {
  document.documentElement.style.setProperty("--ui-scale", String(value / 100));
}

// Restore the scale before rendering, alongside the saved theme preference.
export function initializeZoom() {
  applyZoom(readZoom());
}

export function ZoomControl() {
  const [zoom, setZoom] = useState(readZoom);
  useLayoutEffect(() => applyZoom(zoom), [zoom]);

  function choose(position: number) {
    const value = zoomLevels[position];
    if (value === undefined) return;
    setZoom(value);
    try {
      localStorage.setItem(storageKey, String(value));
    } catch {
      // Keep the current scale even if it cannot be saved for the next launch.
    }
  }
  return (
    <div className="zoom-control">
      <div className="zoom-heading">
        <label htmlFor="ui-zoom">UI zoom</label>
        <output htmlFor="ui-zoom" aria-hidden="true">
          {zoom}%
        </output>
      </div>
      <div className="zoom-slider">
        <span aria-hidden="true">−</span>
        <input
          id="ui-zoom"
          type="range"
          min={0}
          max={4}
          step={1}
          value={zoomLevels.indexOf(zoom)}
          aria-valuetext={`${zoom}%`}
          onChange={(event) => choose(Number(event.target.value))}
        />
        <span aria-hidden="true">+</span>
      </div>
    </div>
  );
}
