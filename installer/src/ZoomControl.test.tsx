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
it("defaults to the second position at exactly 100%", () => {
  render(<ZoomControl />);
  const slider = screen.getByRole("slider", {
    name: "UI zoom",
  }) as HTMLInputElement;
  expect(slider.value).toBe("1");
  expect(slider.min).toBe("0");
  expect(slider.max).toBe("4");
  expect(slider.step).toBe("1");
  expect(slider.getAttribute("aria-valuetext")).toBe("100%");
  expect(document.documentElement.style.getPropertyValue("--ui-scale")).toBe(
    "1",
  );
});
it("applies and saves each exact scale and restores it before rendering", () => {
  const view = render(<ZoomControl />);
  const slider = screen.getByRole("slider", { name: "UI zoom" });
  zoomLevels.forEach((value, position) => {
    fireEvent.change(slider, { target: { value: position } });
    expect(slider.getAttribute("aria-valuetext")).toBe(`${value}%`);
    expect(document.documentElement.style.getPropertyValue("--ui-scale")).toBe(
      String(value / 100),
    );
    expect(localStorage.getItem("sde.uiZoom")).toBe(String(value));
  });
  view.unmount();
  document.documentElement.style.removeProperty("--ui-scale");
  initializeZoom();
  expect(document.documentElement.style.getPropertyValue("--ui-scale")).toBe(
    "1.5",
  );
  render(<ZoomControl />);
  expect(
    (screen.getByRole("slider", { name: "UI zoom" }) as HTMLInputElement).value,
  ).toBe("4");
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
  fireEvent.change(screen.getByRole("slider", { name: "UI zoom" }), {
    target: { value: 4 },
  });
  expect(document.documentElement.style.getPropertyValue("--ui-scale")).toBe(
    "1.5",
  );
});
