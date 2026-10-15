import { useEffect, useLayoutEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

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

export function useThemePreference() {
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

  return { preference, choose };
}

export function ThemeButtons({
  preference,
  choose,
}: ReturnType<typeof useThemePreference>) {
  const [dismissed, setDismissed] = useState<string | null>(null);
  useEffect(() => {
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDismissed("all");
    };
    document.addEventListener("keydown", dismiss);
    return () => document.removeEventListener("keydown", dismiss);
  }, []);
  return (
    <div className="theme-control" role="group" aria-label="Theme">
      {(["system", "light", "dark"] as const).map((value) => {
        const label = value[0].toUpperCase() + value.slice(1);
        const Icon = value === "light" ? Sun : Moon;
        return (
          <span
            className="theme-option"
            key={value}
            data-tip-dismissed={dismissed === value || dismissed === "all"}
            onKeyDown={(event) => {
              if (event.key === "Escape") setDismissed(value);
            }}
            onMouseLeave={() => setDismissed(null)}
            onBlur={() => setDismissed(null)}
          >
            <button
              type="button"
              className="appearance-button"
              aria-label={label}
              data-appearance-key={value}
              aria-pressed={preference === value}
              onClick={() => choose(value)}
            >
              {value === "system" ? (
                <svg
                  width="17"
                  height="17"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <circle
                    cx="12"
                    cy="12"
                    r="9"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.6"
                  />
                  <path d="M12 3a9 9 0 0 0 0 18Z" fill="currentColor" />
                </svg>
              ) : (
                <Icon size={17} aria-hidden="true" />
              )}
            </button>
            <span className="appearance-tooltip" aria-hidden="true">
              {label}
            </span>
          </span>
        );
      })}
    </div>
  );
}

export function ThemeControl() {
  return <ThemeButtons {...useThemePreference()} />;
}
