import { useLayoutEffect, useState } from "react";

export type ThemePreference = "system" | "light" | "dark";
const storageKey = "sde.theme";

function readPreference(): ThemePreference {
  try {
    const value = localStorage.getItem(storageKey);
    if (value === "light" || value === "dark") return value;
  } catch {
    // Appearance remains usable when local storage is unavailable.
  }
  return "system";
}
function systemTheme(): MediaQueryList | null {
  try {
    return window.matchMedia?.("(prefers-color-scheme: dark)") ?? null;
  } catch {
    return null;
  }
}
function applyTheme(preference: ThemePreference, dark: boolean) {
  document.documentElement.dataset.theme =
    preference === "system" ? (dark ? "dark" : "light") : preference;
}

// Run before React renders so a saved dark preference does not flash light.
export function initializeTheme() {
  applyTheme(readPreference(), systemTheme()?.matches ?? false);
}

export function ThemeControl() {
  const [preference, setPreference] = useState(readPreference);
  useLayoutEffect(() => {
    const query = systemTheme();
    const update = () => applyTheme(preference, query?.matches ?? false);
    update();
    if (query?.addEventListener) {
      query.addEventListener("change", update);
      return () => query.removeEventListener("change", update);
    }
    // Older webviews expose only the original MediaQueryList listener API.
    query?.addListener?.(update);
    return () => query?.removeListener?.(update);
  }, [preference]);

  function choose(value: ThemePreference) {
    setPreference(value);
    try {
      localStorage.setItem(storageKey, value);
    } catch {
      // Keep the current selection for this window even if it cannot be saved.
    }
  }

  return (
    <fieldset className="theme-control">
      <legend>Theme</legend>
      <div className="theme-options">
        {(["system", "light", "dark"] as const).map((value) => (
          <label key={value}>
            <input
              type="radio"
              name="theme"
              value={value}
              checked={preference === value}
              onChange={() => choose(value)}
            />
            <span>{value[0].toUpperCase() + value.slice(1)}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
