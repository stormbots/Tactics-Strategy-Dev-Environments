import { afterEach, beforeEach, expect, it, vi } from "../testing/unitApi";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MaintenanceOverviewCard } from "./MaintenanceOverviewCard";
import {
  disabledChoiceKey,
  saveDisabledChoice,
} from "./maintenanceDisabledChoice";
import type { Schedule } from "./model";
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
const review = vi.fn(),
  support = vi.fn();
const card = (data: Schedule | null, pending = false, busy = false) => (
  <MaintenanceOverviewCard
    data={data}
    pending={pending}
    busy={busy}
    onReview={review}
    onSupport={support}
  />
);
async function mountCard(node: Parameters<typeof render>[0]) {
  let view!: ReturnType<typeof render>;
  await act(async () => {
    view = render(node);
  });
  return view;
}
beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  review.mockReset();
  support.mockReset();
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("disabled Overview is actionable and reads without writing or changing its observation", async () => {
  const data = record(),
    before = JSON.stringify(data);
  const write = vi.spyOn(Storage.prototype, "setItem");
  await mountCard(card(data));
  expect(
    screen.getByRole("heading", { name: "Weekly maintenance is disabled" }),
  ).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Review weekly maintenance" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Create maintenance report" }),
  );
  expect(review).toHaveBeenCalledTimes(1);
  expect(support).toHaveBeenCalledTimes(1);
  expect(write).not.toHaveBeenCalled();
  expect(JSON.stringify(data)).toBe(before);
});
it("saved choice stays distinct from Disabled, active timer and failed history", async () => {
  const data = record();
  await saveDisabledChoice(context, data, localStorage);
  const write = vi.spyOn(Storage.prototype, "setItem");
  await mountCard(card(data));
  await screen.findByRole("heading", {
    name: "You chose to leave weekly maintenance disabled",
  });
  expect(
    screen.getByText(/timer is still active in this session/),
  ).toBeTruthy();
  expect(
    screen.getByText(/An earlier maintenance attempt failed/),
  ).toBeTruthy();
  expect(screen.getByText(/The schedule is still disabled/)).toBeTruthy();
  expect(
    screen.getByRole("button", { name: "View maintenance details" }),
  ).toBeTruthy();
  expect(write).not.toHaveBeenCalled();
  expect(data.status).toBe("disabled");
  expect(data.lastResult).toBe("failure");
});
it("changed definitions invalidate the displayed choice immediately", async () => {
  const data = record();
  await saveDisabledChoice(context, data, localStorage);
  const view = await mountCard(card(data));
  await screen.findByRole("heading", {
    name: "You chose to leave weekly maintenance disabled",
  });
  view.rerender(
    card(
      record({ choiceContext: { ...context, definitionId: "c".repeat(64) } }),
    ),
  );
  expect(
    screen.queryByRole("heading", {
      name: "You chose to leave weekly maintenance disabled",
    }),
  ).toBeNull();
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Review weekly maintenance" }),
    ).toBeTruthy(),
  );
});
it("pending and unavailable reads cannot reuse a saved choice", async () => {
  const data = record();
  await saveDisabledChoice(context, data, localStorage);
  const view = await mountCard(card(data));
  await screen.findByRole("heading", {
    name: "You chose to leave weekly maintenance disabled",
  });
  view.rerender(card(data, true));
  expect(
    screen.getByRole("heading", { name: "Checking weekly maintenance…" }),
  ).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Review weekly maintenance",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  view.rerender(card(null));
  expect(screen.queryByText(/Your choice is saved/)).toBeNull();
  expect(
    screen.getByRole("heading", {
      name: "We couldn’t finish checking weekly maintenance",
    }),
  ).toBeTruthy();
});
it("incomplete history and stale observations cannot claim the choice is settled", async () => {
  const data = record();
  await saveDisabledChoice(context, data, localStorage);
  const view = render(
    card(
      record({ inspectionScope: "history", inspectionReason: "accessDenied" }),
    ),
  );
  expect(
    screen.getByRole("heading", {
      name: "We couldn’t check the maintenance history",
    }),
  ).toBeTruthy();
  expect(screen.queryByText(/Your choice is saved/)).toBeNull();
  view.rerender(
    card(record({ observedAt: new Date(Date.now() - 600_000).toISOString() })),
  );
  expect(
    screen.getByRole("heading", { name: "Weekly maintenance is disabled" }),
  ).toBeTruthy();
  expect(screen.queryByText(/Your choice is saved/)).toBeNull();
});
it("blocked preference storage leaves ordinary review available without altering the saved record", async () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("denied");
  });
  const write = vi.spyOn(Storage.prototype, "setItem");
  await mountCard(card(record()));
  expect(
    screen.getByRole("button", { name: "Review weekly maintenance" }),
  ).toBeTruthy();
  expect(write).not.toHaveBeenCalled();
  expect(screen.queryByText(/Your choice is saved/)).toBeNull();
});
it("successful active maintenance needs no findings card but running and unknown history remain visible", async () => {
  const view = render(
    card(record({ status: "enabled", active: true, lastResult: "success" })),
  );
  expect(screen.queryByRole("heading")).toBeNull();
  view.rerender(
    card(record({ status: "enabled", active: true, lastResult: "running" })),
  );
  expect(
    screen.getByRole("heading", { name: "Weekly maintenance is running" }),
  ).toBeTruthy();
  view.rerender(
    card(
      record({ status: "enabled", active: true, lastResult: "unavailable" }),
    ),
  );
  expect(
    screen.getByText(/could not confirm the result of earlier maintenance/),
  ).toBeTruthy();
});
it("missing context and missing schedules never manufacture a saved decision", async () => {
  const data = record();
  await saveDisabledChoice(context, data, localStorage);
  const view = await mountCard(card(record({ choiceContext: undefined })));
  expect(screen.queryByText(/Your choice is saved/)).toBeNull();
  view.rerender(
    card(
      record({
        status: "missing",
        inspectionReason: "notInstalled",
        choiceContext: undefined,
      }),
    ),
  );
  expect(
    screen.getByRole("heading", { name: "Weekly maintenance wasn’t found" }),
  ).toBeTruthy();
  expect(localStorage.getItem(disabledChoiceKey)).not.toBeNull();
});
