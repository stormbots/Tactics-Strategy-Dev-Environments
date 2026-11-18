import { afterEach, beforeEach, expect, it, vi } from "../testing/unitApi";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { StrictMode } from "react";
import { SchedulePage } from "./DetailsPages";
import { maintenanceFinding } from "./MaintenanceInspectionReview";
import {
  inspectSchedule,
  inspectSelfUpdate,
  setSelfUpdatePaused,
} from "./bridge";
import type { Schedule } from "./model";
import { maintenanceHealth } from "./safeOperations";
vi.mock("./bridge", () => ({
  native: false,
  appVersion: "1.2.1",
  inspectSchedule: vi.fn(),
  inspectSelfUpdate: vi.fn(),
  setSelfUpdatePaused: vi.fn(),
}));
const observation = (changes: Partial<Schedule> = {}): Schedule => ({
  status: "unavailable",
  active: false,
  identifier: "skyview-student-dev-update.timer",
  inspectionScope: "schedule",
  inspectionReason: "accessDenied",
  frequency: "Unavailable",
  nextRun: null,
  lastRun: null,
  lastResult: "unavailable",
  resultDetail: "Unavailable",
  catchUp: null,
  logFolder: "/logs",
  logsAvailable: false,
  note: "Native diagnostic",
  observedAt: "2026-11-18T00:00:00Z",
  createdAt: null,
  lastSuccess: null,
  ...changes,
});
const disabled = () =>
  observation({
    status: "disabled",
    inspectionReason: "verified",
    lastResult: "failure",
    resultDetail: "Earlier failed attempt",
  });
const enabled = () =>
  observation({
    status: "enabled",
    active: true,
    inspectionReason: "verified",
    lastResult: "success",
    resultDetail: "Earlier successful attempt",
  });
const openTarget = vi.fn(),
  support = vi.fn(),
  observed = vi.fn();
function page() {
  return (
    <SchedulePage
      openTarget={openTarget}
      onSupport={support}
      onObservation={observed}
    />
  );
}
beforeEach(() => {
  vi.mocked(inspectSchedule).mockReset().mockResolvedValue(observation());
  vi.mocked(inspectSelfUpdate)
    .mockReset()
    .mockRejectedValue(
      new Error("App update status unavailable in this fixture"),
    );
  vi.mocked(setSelfUpdatePaused).mockReset();
});
afterEach(cleanup);

it("rechecks denied access in place, rejects duplicate clicks and reports actual Disabled", async () => {
  render(page());
  await screen.findByText(
    /SDE did not have permission to read the maintenance schedule/,
  );
  const policyReads = vi.mocked(inspectSelfUpdate).mock.calls.length;
  let finish!: (value: Schedule) => void;
  vi.mocked(inspectSchedule).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const button = screen.getByRole("button", {
    name: "Check maintenance status again",
  });
  fireEvent.click(button);
  fireEvent.click(button);
  await waitFor(() => expect(finish).toBeTypeOf("function"));
  expect(vi.mocked(inspectSchedule)).toHaveBeenCalledTimes(2);
  expect(
    screen.getByRole("region", { name: "Maintenance status review" }),
  ).toBeTruthy();
  await act(async () => finish(disabled()));
  await screen.findByRole("heading", {
    name: "Weekly maintenance is disabled",
  });
  expect(
    screen.queryByRole("heading", {
      name: "We couldn’t check weekly maintenance",
    }),
  ).toBeNull();
  expect(document.activeElement).toBe(
    screen.getByRole("heading", { name: "Scheduled maintenance" }),
  );
  expect(vi.mocked(inspectSelfUpdate).mock.calls.length).toBe(policyReads);
  expect(vi.mocked(setSelfUpdatePaused)).not.toHaveBeenCalled();
  expect(openTarget).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Create maintenance support report" }),
  );
  expect(support).toHaveBeenCalledOnce();
});

it("keeps a failed retry and earlier evidence visible without calling it a current result", async () => {
  vi.mocked(inspectSchedule).mockResolvedValueOnce(enabled());
  render(page());
  await screen.findByText("Earlier successful attempt");
  vi.mocked(inspectSchedule).mockRejectedValueOnce(
    new Error("Transport failed"),
  );
  fireEvent.click(screen.getByRole("button", { name: /^Refresh$/ }));
  await screen.findByText(/Schedule unavailable.*Transport failed/);
  expect(screen.queryByText("Earlier maintenance observation")).toBeNull();
  vi.mocked(inspectSchedule).mockRejectedValueOnce(
    new Error("Still unavailable"),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Check maintenance status again" }),
  );
  await screen.findByText(/Schedule unavailable.*Still unavailable/);
  expect(screen.getByText("Earlier maintenance observation")).toBeTruthy();
  expect(
    screen.getByText(/These are earlier results, not a completed new check/),
  ).toBeTruthy();
  expect(screen.getByText(/Earlier successful attempt/)).toBeTruthy();
  expect(observed).toHaveBeenLastCalledWith(null);
  vi.mocked(inspectSchedule).mockResolvedValueOnce(enabled());
  fireEvent.click(
    screen.getByRole("button", { name: "Check maintenance status again" }),
  );
  await waitFor(() =>
    expect(
      screen.queryByRole("region", { name: "Maintenance status review" }),
    ).toBeNull(),
  );
  expect(screen.queryByText("Earlier maintenance observation")).toBeNull();
  expect(screen.getByText(/Enabled · Last result: Succeeded/)).toBeTruthy();
});

it("a fresh unavailable response retains earlier observations and offers another check", async () => {
  vi.mocked(inspectSchedule).mockResolvedValueOnce(disabled());
  render(page());
  await screen.findByRole("heading", {
    name: "Weekly maintenance is disabled",
  });
  vi.mocked(inspectSchedule).mockResolvedValueOnce(
    observation({ inspectionReason: "timedOut" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Check maintenance status again" }),
  );
  await screen.findByText(
    /The maintenance check took too long and did not finish/,
  );
  expect(screen.getByText("Earlier maintenance observation")).toBeTruthy();
  expect(screen.getByText(/Earlier failed attempt/)).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: "Check maintenance status again" })
      .hasAttribute("disabled"),
  ).toBe(false);
  expect(
    screen.queryByRole("heading", { name: "Weekly maintenance is disabled" }),
  ).toBeNull();
});

it("keeps a verified schedule separate from incomplete history", async () => {
  vi.mocked(inspectSchedule).mockResolvedValueOnce(
    observation({
      status: "enabled",
      active: true,
      inspectionScope: "history",
    }),
  );
  render(page());
  await screen.findByRole("heading", {
    name: "We couldn’t check the maintenance history",
  });
  expect(screen.getByText(/Enabled · Last result: Unavailable/)).toBeTruthy();
  expect(
    screen.getByText(
      /The schedule was read, but its earlier results could not be checked/,
    ),
  ).toBeTruthy();
});

it("ignores a completed read after leaving the schedule page", async () => {
  render(page());
  await screen.findByRole("region", { name: "Maintenance status review" });
  let finish!: (value: Schedule) => void;
  vi.mocked(inspectSchedule).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Check maintenance status again" }),
  );
  await waitFor(() => expect(finish).toBeTypeOf("function"));
  const before = observed.mock.calls.length;
  cleanup();
  await act(async () => finish(enabled()));
  expect(observed.mock.calls.length).toBe(before);
});

it("StrictMode abandoned reads cannot block or replace the current inspection", async () => {
  let abandoned!: (value: Schedule) => void;
  vi.mocked(inspectSchedule).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        abandoned = resolve;
      }),
  );
  render(<StrictMode>{page()}</StrictMode>);
  await screen.findByRole("region", { name: "Maintenance status review" });
  expect(vi.mocked(inspectSchedule)).toHaveBeenCalledTimes(2);
  await act(async () => abandoned(enabled()));
  expect(
    screen.getByRole("heading", {
      name: "We couldn’t check weekly maintenance",
    }),
  ).toBeTruthy();
  expect(observed).not.toHaveBeenCalledWith(
    expect.objectContaining({ status: "enabled" }),
  );
});

it("uses confirmed causes without confusing missing, timeout or active disabled timers", () => {
  expect(
    maintenanceFinding(
      observation({ status: "missing", inspectionReason: "notInstalled" }),
    )?.title,
  ).toBe("Weekly maintenance wasn’t found");
  expect(
    maintenanceFinding(observation({ inspectionReason: "timedOut" }))?.detail,
  ).toContain("took too long");
  expect(
    maintenanceFinding(observation({ inspectionReason: "readFailed" }))?.detail,
  ).not.toContain("permission");
  expect(
    maintenanceFinding(observation(), "arbitrary access denied text")?.detail,
  ).not.toContain("permission");
  expect(
    maintenanceFinding(
      observation({
        status: "disabled",
        active: true,
        inspectionReason: "verified",
      }),
    )?.detail,
  ).toContain("may run");
  expect(
    maintenanceFinding(
      observation({
        status: "enabled",
        active: false,
        inspectionReason: "verified",
      }),
    )?.title,
  ).toBe("Weekly maintenance is enabled but not waiting");
  expect(maintenanceHealth(observation())).toBe("unavailable");
  expect(
    maintenanceHealth(
      observation({
        status: "enabled",
        active: false,
        inspectionReason: "verified",
      }),
    ),
  ).toBe("unavailable");
  expect(maintenanceFinding(enabled())).toBeNull();
});
