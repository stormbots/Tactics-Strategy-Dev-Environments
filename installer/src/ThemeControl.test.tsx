import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { initializeTheme, ThemeControl } from "./ThemeControl";

let query: MediaQueryList;
let listeners: Set<() => void>;
beforeEach(() => {
  localStorage.clear();
  listeners = new Set();
  query = {
    matches: false,
    addEventListener: vi.fn((_type, listener) => listeners.add(listener)),
    removeEventListener: vi.fn((_type, listener) => listeners.delete(listener)),
  } as unknown as MediaQueryList;
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => query),
  );
});
afterEach(() => {
  cleanup();
  localStorage.clear();
  delete document.documentElement.dataset.theme;
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
function systemChange(dark: boolean) {
  Object.defineProperty(query, "matches", { value: dark, configurable: true });
  listeners.forEach((listener) => listener());
}
it("defaults to System, follows live changes, and unsubscribes", () => {
  const view = render(<ThemeControl />);
  expect((screen.getByLabelText("System") as HTMLInputElement).checked).toBe(
    true,
  );
  expect(document.documentElement.dataset.theme).toBe("light");
  systemChange(true);
  expect(document.documentElement.dataset.theme).toBe("dark");
  systemChange(false);
  expect(document.documentElement.dataset.theme).toBe("light");
  view.unmount();
  expect(listeners.size).toBe(0);
});
it("persists manual overrides and restores them before rendering", () => {
  const view = render(<ThemeControl />);
  fireEvent.click(screen.getByLabelText("Dark"));
  expect(localStorage.getItem("sde.theme")).toBe("dark");
  systemChange(false);
  expect(document.documentElement.dataset.theme).toBe("dark");
  view.unmount();
  document.documentElement.dataset.theme = "light";
  initializeTheme();
  expect(document.documentElement.dataset.theme).toBe("dark");
  render(<ThemeControl />);
  expect((screen.getByLabelText("Dark") as HTMLInputElement).checked).toBe(
    true,
  );
  fireEvent.click(screen.getByLabelText("Light"));
  systemChange(true);
  expect(document.documentElement.dataset.theme).toBe("light");
  fireEvent.click(screen.getByLabelText("System"));
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(localStorage.getItem("sde.theme")).toBe("system");
});
it("falls back to Light with System selected if theme detection is unavailable", () => {
  vi.stubGlobal("matchMedia", undefined);
  localStorage.setItem("sde.theme", "invalid");
  initializeTheme();
  render(<ThemeControl />);
  expect(document.documentElement.dataset.theme).toBe("light");
  expect((screen.getByLabelText("System") as HTMLInputElement).checked).toBe(
    true,
  );
  fireEvent.click(screen.getByLabelText("Dark"));
  expect(document.documentElement.dataset.theme).toBe("dark");
});
it("continues working when preference storage is blocked", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw Error("blocked");
  });
  render(<ThemeControl />);
  fireEvent.click(screen.getByLabelText("Dark"));
  expect(document.documentElement.dataset.theme).toBe("dark");
});

it("follows and cleans up system changes in webviews with legacy listeners", () => {
  query = {
    matches: false,
    addListener: vi.fn((listener) => listeners.add(listener)),
    removeListener: vi.fn((listener) => listeners.delete(listener)),
  } as unknown as MediaQueryList;
  const view = render(<ThemeControl />);
  systemChange(true);
  expect(document.documentElement.dataset.theme).toBe("dark");
  view.unmount();
  expect(listeners.size).toBe(0);
});
it("falls back safely when system detection throws", () => {
  vi.stubGlobal("matchMedia", () => {
    throw Error("unavailable");
  });
  initializeTheme();
  render(<ThemeControl />);
  expect((screen.getByLabelText("System") as HTMLInputElement).checked).toBe(
    true,
  );
  expect(document.documentElement.dataset.theme).toBe("light");
});
