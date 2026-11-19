import { afterEach, beforeEach, expect, it, vi } from "../testing/unitApi";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { SchedulePage } from "./DetailsPages";
import {
  inspectSchedule,
  inspectSelfUpdate,
  setSelfUpdatePaused,
} from "./bridge";
import {
  disabledChoiceKey,
  saveDisabledChoice,
} from "./maintenanceDisabledChoice";
import type { Schedule } from "./model";
vi.mock("./bridge", () => ({
  native: false,
  appVersion: "1.2.1",
  inspectSchedule: vi.fn(),
  inspectSelfUpdate: vi.fn(),
  setSelfUpdatePaused: vi.fn(),
}));
const context = {
  machineId: "a".repeat(64),
  identifier: "skyview-student-dev-update.timer",
  definitionId: "b".repeat(64),
};
function record(changes: Partial<Schedule> = {}): Schedule {
  return {
    status: "disabled",
    active: true,
    identifier: context.identifier,
    inspectionScope: "schedule",
    inspectionReason: "verified",
    choiceContext: context,
    frequency: "Weekly",
    nextRun: null,
    lastRun: null,
    lastResult: "failure",
    resultDetail: "Earlier failed attempt",
    catchUp: true,
    logFolder: "/logs",
    logsAvailable: false,
    note: "",
    observedAt: new Date().toISOString(),
    createdAt: null,
    lastSuccess: null,
    ...changes,
  };
}
const observed = vi.fn(),
  support = vi.fn(),
  openTarget = vi.fn();
const page = () => (
  <SchedulePage
    openTarget={openTarget}
    onSupport={support}
    onObservation={observed}
  />
);
const saveButton = () =>
  screen.getByRole("button", { name: "Leave maintenance disabled" });
async function ready() {
  await screen.findByRole("button", { name: "Leave maintenance disabled" });
  await waitFor(() =>
    expect((saveButton() as HTMLButtonElement).disabled).toBe(false),
  );
}
beforeEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  observed.mockReset();
  support.mockReset();
  openTarget.mockReset();
  vi.mocked(inspectSchedule)
    .mockReset()
    .mockImplementation(async () => record());
  vi.mocked(inspectSelfUpdate)
    .mockReset()
    .mockRejectedValue(new Error("No update policy in sample"));
  vi.mocked(setSelfUpdatePaused).mockReset();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("opening a disabled schedule does not save a choice or change independent policy", async () => {
  render(page());
  await ready();
  expect(window.localStorage.getItem(disabledChoiceKey)).toBeNull();
  expect(vi.mocked(inspectSchedule)).toHaveBeenCalledTimes(1);
  expect(vi.mocked(setSelfUpdatePaused)).not.toHaveBeenCalled();
  expect(
    screen.getByText(/timer is still active in this session/),
  ).toBeTruthy();
});
it("explicit choice checks once and saves in place while keeping Disabled and earlier failure visible", async () => {
  render(page());
  await ready();
  let finish!: (value: Schedule) => void;
  vi.mocked(inspectSchedule).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const button = saveButton();
  fireEvent.click(button);
  fireEvent.click(button);
  await waitFor(() => expect(finish).toBeTypeOf("function"));
  expect(vi.mocked(inspectSchedule)).toHaveBeenCalledTimes(2);
  expect(window.localStorage.getItem(disabledChoiceKey)).toBeNull();
  await act(async () => finish(record()));
  await screen.findByText(/Your choice to leave maintenance disabled is saved/);
  expect(window.localStorage.getItem(disabledChoiceKey)).not.toBeNull();
  expect(
    screen.getByRole("heading", { name: "Weekly maintenance is disabled" }),
  ).toBeTruthy();
  expect(screen.getByText("Earlier failed attempt")).toBeTruthy();
  expect(observed.mock.calls.at(-1)?.[0].status).toBe("disabled");
  expect(document.activeElement).toBe(
    screen.getByRole("heading", { name: "Scheduled maintenance" }),
  );
  expect(vi.mocked(setSelfUpdatePaused)).not.toHaveBeenCalled();
});
it("saved choice is recognized after reopening without writing or claiming maintenance is enabled", async () => {
  await saveDisabledChoice(context, record(), window.localStorage);
  const write = vi.spyOn(Storage.prototype, "setItem");
  render(page());
  await screen.findByText(/Your choice to leave maintenance disabled is saved/);
  expect(write).not.toHaveBeenCalled();
  expect(
    screen.queryByRole("button", { name: "Leave maintenance disabled" }),
  ).toBeNull();
  expect(observed.mock.calls.at(-1)?.[0].status).toBe("disabled");
});
it("changed definition remains in the flow and requires a new explicit choice", async () => {
  render(page());
  await ready();
  vi.mocked(inspectSchedule).mockResolvedValue(
    record({ choiceContext: { ...context, definitionId: "c".repeat(64) } }),
  );
  fireEvent.click(saveButton());
  await screen.findByText(/The schedule changed or could not be confirmed/);
  expect(window.localStorage.getItem(disabledChoiceKey)).toBeNull();
  await waitFor(() =>
    expect((saveButton() as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(saveButton());
  await screen.findByText(/Your choice to leave maintenance disabled is saved/);
});
it("an enabled follow-up updates the observation and does not save a disabled choice", async () => {
  render(page());
  await ready();
  vi.mocked(inspectSchedule).mockResolvedValue(
    record({ status: "enabled", active: true }),
  );
  fireEvent.click(saveButton());
  await screen.findByText(/The schedule changed or could not be confirmed/);
  expect(window.localStorage.getItem(disabledChoiceKey)).toBeNull();
  expect(observed.mock.calls.at(-1)?.[0].status).toBe("enabled");
  expect(
    screen.queryByRole("button", { name: "Leave maintenance disabled" }),
  ).toBeNull();
});
it("storage denial stays unsaved and permits retry in the same flow", async () => {
  render(page());
  await ready();
  const write = vi
    .spyOn(Storage.prototype, "setItem")
    .mockImplementation(() => {
      throw new Error("denied");
    });
  fireEvent.click(saveButton());
  await screen.findByText(/SDE couldn’t save your choice/);
  expect(window.localStorage.getItem(disabledChoiceKey)).toBeNull();
  await waitFor(() =>
    expect((saveButton() as HTMLButtonElement).disabled).toBe(false),
  );
  write.mockRestore();
  fireEvent.click(saveButton());
  await screen.findByText(/Your choice to leave maintenance disabled is saved/);
});
it("failed follow-up keeps retry and support actions without saving", async () => {
  render(page());
  await ready();
  vi.mocked(inspectSchedule).mockRejectedValueOnce(
    new Error("collection failed"),
  );
  fireEvent.click(saveButton());
  await screen.findByText(
    /The check did not finish, so your choice was not saved/,
  );
  expect(window.localStorage.getItem(disabledChoiceKey)).toBeNull();
  expect(
    screen.getByRole("button", { name: "Check maintenance status again" }),
  ).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Create maintenance support report" }),
  );
  expect(support).toHaveBeenCalledTimes(1);
});
it("leaving during the follow-up cannot write a late saved choice", async () => {
  const view = render(page());
  await ready();
  let finish!: (value: Schedule) => void;
  vi.mocked(inspectSchedule).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  fireEvent.click(saveButton());
  view.unmount();
  await act(async () => finish(record()));
  expect(window.localStorage.getItem(disabledChoiceKey)).toBeNull();
});
it("invalidated asynchronous save cannot persist after fingerprinting", async () => {
  const result = await saveDisabledChoice(
    context,
    record(),
    window.localStorage,
    Date.now(),
    () => false,
  );
  expect(result.saved).toBe(false);
  expect(window.localStorage.getItem(disabledChoiceKey)).toBeNull();
});
it("unrecognized context and incomplete history do not offer Save", async () => {
  vi.mocked(inspectSchedule).mockResolvedValueOnce(
    record({ choiceContext: undefined }),
  );
  const view = render(page());
  await screen.findByText(/Saving a choice is not available for this schedule/);
  expect(
    screen.queryByRole("button", { name: "Leave maintenance disabled" }),
  ).toBeNull();
  view.unmount();
  vi.mocked(inspectSchedule).mockResolvedValueOnce(
    record({ inspectionScope: "history", inspectionReason: "accessDenied" }),
  );
  render(page());
  await screen.findByRole("heading", {
    name: "We couldn’t check the maintenance history",
  });
  expect(
    screen.queryByRole("button", { name: "Leave maintenance disabled" }),
  ).toBeNull();
});
