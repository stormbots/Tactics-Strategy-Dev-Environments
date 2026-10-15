import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { initializeZoom, ZoomControl, zoomLevels } from "./ZoomControl";

beforeEach(() => localStorage.clear());
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
  document.documentElement.style.removeProperty("--ui-scale");
});
it("defaults to 100%, has no slider, and steps through bounded levels", () => {
  render(<ZoomControl />);
  expect(screen.queryByRole("slider")).toBeNull();
  expect(screen.getByText("100%")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Decrease zoom" }));
  expect(
    (screen.getByRole("button", { name: "Decrease zoom" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  for (const value of zoomLevels.slice(1)) {
    fireEvent.click(screen.getByRole("button", { name: "Increase zoom" }));
    expect(screen.getByText(`${value}%`)).toBeTruthy();
    expect(localStorage.getItem("sde.uiZoom")).toBe(String(value));
    expect(document.documentElement.style.getPropertyValue("--ui-scale")).toBe(
      String(value / 100),
    );
  }
  expect(
    (screen.getByRole("button", { name: "Increase zoom" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
});
it("restores the saved scale before rendering and on remount", () => {
  localStorage.setItem("sde.uiZoom", "130");
  initializeZoom();
  expect(document.documentElement.style.getPropertyValue("--ui-scale")).toBe(
    "1.3",
  );
  render(<ZoomControl />);
  expect(screen.getByText("130%")).toBeTruthy();
});
it("rejects saved scales outside the five supported values", () => {
  for (const value of ["", "1", "120", "150px", "NaN", "Infinity", "1000"]) {
    localStorage.setItem("sde.uiZoom", value);
    initializeZoom();
    expect(document.documentElement.style.getPropertyValue("--ui-scale")).toBe(
      "1",
    );
  }
});
it("works when preference storage is blocked", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw Error("blocked");
  });
  initializeZoom();
  render(<ZoomControl />);
  fireEvent.click(screen.getByRole("button", { name: "Increase zoom" }));
  expect(document.documentElement.style.getPropertyValue("--ui-scale")).toBe(
    "1.15",
  );
});
