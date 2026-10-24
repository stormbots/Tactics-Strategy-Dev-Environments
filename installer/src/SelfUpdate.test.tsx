import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { setSelfUpdatePaused } from "./bridge";
vi.mock("./bridge", () => ({
  appVersion: "1.2.16",
  setSelfUpdatePaused: vi.fn(),
}));
import { SelfUpdatePanel } from "./DetailsPages";
import type { SelfUpdate } from "./model";
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
function fixture(outcome: SelfUpdate["outcome"]): SelfUpdate {
  return {
    paused: true,
    policyChangedAt: 100,
    outcome,
    phase: "postcheck",
    checkedAt: 100,
    completedAt: 101,
    applicationVersion: "1.2.2",
    candidateVersion: "1.2.2",
    maintenanceEngineVersion: "1.2.2",
    appliedBaselineVersion: "1.1.5",
    toolExit: 1,
    nativeExit: 0,
    rebootRequired: false,
    recoveryAvailable: false,
    logReference: null,
    logFolder: "/protected/logs",
    action: "Ask a mentor.",
    coordination: "interrupted",
  };
}
it.each([
  ["current", "Current at last check"],
  ["paused", "Paused at last attempt"],
  ["deferred", "Deferred"],
  ["unavailable", "Unavailable"],
  ["failed", "Failed"],
  ["updated", "Successfully updated"],
] as const)(
  "displays %s without concealing tool failure or current pause",
  (outcome, label) => {
    render(<SelfUpdatePanel data={fixture(outcome)} error="" />);
    expect(screen.getByText(label)).toBeTruthy();
    expect(screen.getByText("Failed (exit 1)")).toBeTruthy();
    expect(screen.getByText("Paused", { exact: true })).toBeTruthy();
    expect(screen.getByText(/Interrupted operation/)).toBeTruthy();
    expect(
      screen.getByText(/previous successful result does not resolve/),
    ).toBeTruthy();
    expect(screen.getByText("1.1.5")).toBeTruthy();
    expect(
      screen
        .getByRole("switch", { name: "Automatic SDE updates" })
        .getAttribute("aria-checked"),
    ).toBe("false");
  },
);
it("missing history and policy do not mean current or enabled", () => {
  const data = fixture("unavailable");
  data.paused = null;
  data.checkedAt = null;
  data.completedAt = null;
  data.policyChangedAt = null;
  render(<SelfUpdatePanel data={data} error="" />);
  expect(screen.getByText(/Installation setting unavailable/)).toBeTruthy();
  expect((screen.getByRole("switch") as HTMLButtonElement).disabled).toBe(true);
  expect(screen.queryByText("Current at last check")).toBeNull();
  expect(screen.queryByText("Enabled", { exact: true })).toBeNull();
});
it("saves only one boolean request while pending and keeps last-attempt history", async () => {
  const previous = fixture("paused");
  let finish!: (value: SelfUpdate) => void;
  vi.mocked(setSelfUpdatePaused).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  render(<SelfUpdatePanel data={previous} error="" />);
  const toggle = screen.getByRole("switch");
  fireEvent.click(toggle);
  fireEvent.click(toggle);
  expect(vi.mocked(setSelfUpdatePaused).mock.calls).toEqual([[false]]);
  expect((toggle as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("Paused at last attempt")).toBeTruthy();
  finish({ ...previous, paused: false, policyChangedAt: 102 });
  await waitFor(() => expect(toggle.getAttribute("aria-checked")).toBe("true"));
  expect(screen.getByText("Paused at last attempt")).toBeTruthy();
  expect(screen.getByText("Failed (exit 1)")).toBeTruthy();
  expect(
    screen.getByText(/No maintenance or installation was started/),
  ).toBeTruthy();
});
it("does not claim a confirmed policy after a failed save; refresh restores availability", async () => {
  vi.mocked(setSelfUpdatePaused).mockRejectedValue(
    new Error("write interrupted"),
  );
  const before = fixture("current");
  const view = render(<SelfUpdatePanel data={before} error="" />);
  fireEvent.click(screen.getByRole("switch"));
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toMatch(/Couldn’t confirm/),
  );
  expect((screen.getByRole("switch") as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("Current at last check")).toBeTruthy();
  view.rerender(
    <SelfUpdatePanel data={{ ...before, paused: false }} error="" />,
  );
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.getByRole("switch").getAttribute("aria-checked")).toBe("true");
});
