import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { SelfUpdatePanel } from "./DetailsPages";
import type { SelfUpdate } from "./model";
afterEach(cleanup);
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
    expect(screen.getByText(/Paused by administrator/)).toBeTruthy();
    expect(screen.getByText(/Interrupted operation/)).toBeTruthy();
    expect(
      screen.getByText(/previous successful result does not resolve/),
    ).toBeTruthy();
    expect(screen.getByText("1.1.5")).toBeTruthy();
    expect(screen.queryByRole("button")).toBeNull();
  },
);
it("missing history and policy do not mean current or enabled", () => {
  const data = fixture("unavailable");
  data.paused = null;
  data.checkedAt = null;
  data.completedAt = null;
  data.policyChangedAt = null;
  render(<SelfUpdatePanel data={data} error="" />);
  expect(screen.getByText(/Unavailable — ask a mentor/)).toBeTruthy();
  expect(screen.queryByText("Current at last check")).toBeNull();
  expect(screen.queryByText(/Enabled by administrator/)).toBeNull();
});
