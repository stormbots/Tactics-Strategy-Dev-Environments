import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { SlidersHorizontal } from "lucide-react";
import { ThemeButtons, useThemePreference } from "./ThemeControl";
import { ZoomButtons, useZoomPreference } from "./ZoomControl";

// Preference owners remain mounted across layout changes and panel dismissal.
export function AppearanceControls({ page }: { page: string }) {
  const theme = useThemePreference();
  const zoom = useZoomPreference();
  const [compact, setCompact] = useState(false);
  const [ready, setReady] = useState(false);
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const restoreKey = useRef<string | null>(null);
  const previousPage = useRef(page);
  const compactRef = useRef(false);
  const focusedControl = useRef<string | null>(null);

  useLayoutEffect(() => {
    const update = () => {
      // CSS sentinel keeps JS in sync with the zoom-aware container query.
      const slot = document.getElementById("compact-appearance-slot");
      const next = !!slot && getComputedStyle(slot).display !== "none";
      if (compactRef.current !== next) {
        const active = document.activeElement as HTMLElement | null;
        if (root.current?.contains(active) || focusedControl.current)
          restoreKey.current =
            focusedControl.current ?? active?.dataset.appearanceKey ?? "system";
        compactRef.current = next;
        setCompact(next);
      }
      setReady(true);
    };
    update();
    const observer = new ResizeObserver(update);
    observer.observe(document.documentElement);
    return () => observer.disconnect();
  }, []);

  useLayoutEffect(() => {
    setOpen(false);
    if (restoreKey.current) {
      if (compact) trigger.current?.focus();
      else {
        const equivalent = root.current?.querySelector<HTMLButtonElement>(
          `[data-appearance-key="${restoreKey.current}"]:not(:disabled)`,
        );
        (
          equivalent ??
          root.current?.querySelector<HTMLButtonElement>(
            "button:not(:disabled)",
          )
        )?.focus();
      }
      restoreKey.current = null;
    }
  }, [compact]);

  useLayoutEffect(() => {
    if (!compact || !open) return;
    const fit = () => {
      const bounds = trigger.current?.getBoundingClientRect();
      if (!bounds) return;
      const available = Math.max(
        0,
        (window.innerHeight - bounds.bottom) / (zoom.zoom / 100) - 16,
      );
      panel.current?.style.setProperty(
        "--appearance-max-height",
        `${available}px`,
      );
    };
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [compact, open, zoom.zoom]);

  useEffect(() => {
    if (previousPage.current !== page) setOpen(false);
    previousPage.current = page;
  }, [page]);

  useEffect(() => {
    if (!open) return;
    const pointer = (event: PointerEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false);
    };
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        trigger.current?.focus();
      }
    };
    document.addEventListener("pointerdown", pointer);
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("pointerdown", pointer);
      document.removeEventListener("keydown", key);
    };
  }, [open]);

  if (!ready) return null;
  const target = document.getElementById(
    compact ? "compact-appearance-slot" : "wide-appearance-slot",
  );
  if (!target) return null;
  const controls = (
    <>
      <div className="appearance-row">
        <span className="appearance-label">Theme</span>
        <ThemeButtons {...theme} />
      </div>
      <div className="appearance-row">
        <span className="appearance-label">Zoom</span>
        <ZoomButtons {...zoom} />
      </div>
    </>
  );
  return createPortal(
    <div
      ref={root}
      className={compact ? "appearance-settings" : "appearance-toolbar"}
      onFocusCapture={(event) => {
        focusedControl.current =
          (event.target as HTMLElement).dataset.appearanceKey ?? "system";
      }}
      onBlurCapture={(event) => {
        if (root.current?.contains(event.relatedTarget as Node)) return;
        const slot = document.getElementById("compact-appearance-slot");
        const layoutChanged =
          !!slot &&
          (getComputedStyle(slot).display !== "none") !== compactRef.current;
        // CSS can hide the focused slot before ResizeObserver runs.
        if (!layoutChanged) focusedControl.current = null;
      }}
    >
      {compact ? (
        <>
          <button
            ref={trigger}
            type="button"
            className="appearance-button settings-trigger"
            aria-label="Appearance settings"
            aria-expanded={open}
            aria-controls="appearance-panel"
            onClick={(event) => {
              const keyboard = event.detail === 0;
              setOpen(!open);
              if (!open && keyboard)
                requestAnimationFrame(() =>
                  panel.current
                    ?.querySelector<HTMLButtonElement>("button")
                    ?.focus(),
                );
            }}
          >
            <SlidersHorizontal size={19} aria-hidden="true" />
          </button>
          <div
            ref={panel}
            id="appearance-panel"
            role="group"
            aria-label="Appearance settings"
            className="appearance-popover"
            hidden={!open}
          >
            {controls}
          </div>
        </>
      ) : (
        controls
      )}
    </div>,
    target,
  );
}
