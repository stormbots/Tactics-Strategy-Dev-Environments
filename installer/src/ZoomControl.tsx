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

export function useZoomPreference() {
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
  return { zoom, choose };
}

export function ZoomButtons({
  zoom,
  choose,
}: ReturnType<typeof useZoomPreference>) {
  const position = zoomLevels.indexOf(zoom);
  return (
    <div className="zoom-control" role="group" aria-label="UI zoom">
      <button
        type="button"
        className="appearance-button"
        aria-label="Decrease zoom"
        data-appearance-key="decrease"
        disabled={position === 0}
        onClick={() => choose(position - 1)}
      >
        −
      </button>
      <span className="zoom-value" aria-live="polite" aria-atomic="true">
        {zoom}%
      </span>
      <button
        type="button"
        className="appearance-button"
        aria-label="Increase zoom"
        data-appearance-key="increase"
        disabled={position === zoomLevels.length - 1}
        onClick={() => choose(position + 1)}
      >
        +
      </button>
    </div>
  );
}

export function ZoomControl() {
  return <ZoomButtons {...useZoomPreference()} />;
}
