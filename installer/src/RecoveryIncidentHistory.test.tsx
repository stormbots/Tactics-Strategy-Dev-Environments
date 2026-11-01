import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { RecoveryIncidentHistory } from "./RecoveryIncidentHistory";
import {
  listRecoveryIncidents,
  deleteRecoveryHistoryView,
  type IncidentHistoryPage,
} from "./recoveryIncidents";
vi.mock("./recoveryIncidents", () => ({
  listRecoveryIncidents: vi.fn(),
  deleteRecoveryHistoryView: vi.fn(),
}));
const id = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
function page(source: "machine" | "user"): IncidentHistoryPage {
  return {
    observedAt: 100,
    machine:
      source === "machine"
        ? {
            entries: [
              {
                incidentId: id,
                status: "archive_observed_acknowledgment_unknown",
                continuation: "not_recorded",
              },
            ],
            nextCursor: null,
          }
        : null,
    user:
      source === "user"
        ? {
            entries: [
              {
                incidentId: id,
                status: "acknowledgment_observed",
                continuation: "not_recorded",
                acknowledgment: { acknowledgedAt: 50, reportId: null },
              },
            ],
            nextCursor: null,
            unexpectedEntries: false,
          }
        : null,
  };
}
beforeEach(() => {
  vi.mocked(deleteRecoveryHistoryView).mockReset().mockResolvedValue(undefined);
  vi.mocked(listRecoveryIncidents)
    .mockReset()
    .mockImplementation(async (source) => page(source));
});
it("confirms selected per-account view deletion without deleting evidence and rejects duplicate clicks", async () => {
  const user = page("user");
  user.user!.entries[0].viewToken = "native-view-token";
  vi.mocked(listRecoveryIncidents).mockImplementation(async (source) =>
    source === "user" ? user : page(source),
  );
  let finish!: () => void;
  vi.mocked(deleteRecoveryHistoryView).mockImplementation(
    () =>
      new Promise<void>((resolve) => {
        finish = resolve;
      }),
  );
  render(<RecoveryIncidentHistory />);
  fireEvent.click(
    await screen.findByRole("button", {
      name: `Delete user history view ${id}`,
    }),
  );
  expect(deleteRecoveryHistoryView).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Keep user history view" }),
  );
  expect(deleteRecoveryHistoryView).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: `Delete user history view ${id}` }),
  );
  const confirm = screen.getByRole("button", {
    name: "Confirm delete user history view",
  });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  expect(deleteRecoveryHistoryView).toHaveBeenCalledExactlyOnceWith(
    "native-view-token",
  );
  finish();
  await screen.findByRole("status");
  expect(screen.getByRole("status").textContent).toContain(
    "Minimum operational evidence",
  );
  expect(
    screen.queryByRole("button", { name: `Delete user history view ${id}` }),
  ).toBeNull();
  expect(screen.getByText(/Private contents were not read/)).toBeTruthy();
});
it("failed or stale view deletion is not success and leaves the entry available for refresh", async () => {
  const user = page("user");
  user.user!.entries[0].viewToken = "stale-view";
  vi.mocked(listRecoveryIncidents).mockImplementation(async (source) =>
    source === "user" ? user : page(source),
  );
  vi.mocked(deleteRecoveryHistoryView).mockRejectedValue(new Error("stale"));
  render(<RecoveryIncidentHistory />);
  fireEvent.click(
    await screen.findByRole("button", {
      name: `Delete user history view ${id}`,
    }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Confirm delete user history view" }),
  );
  await screen.findByRole("alert");
  expect(screen.queryByRole("status")).toBeNull();
  expect(
    screen.getByRole("button", { name: `Delete user history view ${id}` }),
  ).toBeTruthy();
  expect(screen.getByRole("alert").textContent).toContain("Refresh history");
});
it("a page containing only deleted views is not reported as absent evidence and retains paging", async () => {
  vi.mocked(listRecoveryIncidents).mockImplementation(async (source) =>
    source === "user"
      ? {
          observedAt: 100,
          machine: null,
          user: { entries: [], nextCursor: id },
          hiddenViews: 25,
        }
      : page(source),
  );
  render(<RecoveryIncidentHistory />);
  await screen.findByText(/25 deleted history views are excluded/);
  expect(
    screen.getByRole("button", { name: "Load more user incidents" }),
  ).toBeTruthy();
  expect(
    screen.getByText(/No earlier events are shown for your account/)
      .textContent,
  ).toContain("Hidden views are not listed");
});
it("unavailable cosmetic preferences leave operational observations visible without a delete action", async () => {
  vi.mocked(listRecoveryIncidents).mockImplementation(async (source) => ({
    ...page(source),
    viewStateUnavailable: true,
  }));
  render(<RecoveryIncidentHistory />);
  await screen.findByText(/Matching retained account acknowledgment observed/);
  expect(
    screen.getAllByText(/Some history-view preferences are unavailable/),
  ).toHaveLength(2);
  expect(screen.queryByRole("button", { name: /^Delete/ })).toBeNull();
  expect(deleteRecoveryHistoryView).not.toHaveBeenCalled();
});
afterEach(cleanup);
it("keeps machine uncertainty distinct from observed account consent and never offers execution or deletion", async () => {
  render(<RecoveryIncidentHistory />);
  await screen.findByText(
    /Private contents were not read; acknowledgment status is unknown/,
  );
  await screen.findByText(
    /No saved report reference. The operational decision exists independently/,
  );
  expect(
    screen.getAllByText("Continuation/completion: not recorded."),
  ).toHaveLength(2);
  expect(
    screen.queryByRole("button", {
      name: /Acknowledge|Delete|Continue|Repair/,
    }),
  ).toBeNull();
  expect(listRecoveryIncidents).toHaveBeenCalledTimes(2);
});
it("a failed source does not hide the other source or imply empty history", async () => {
  vi.mocked(listRecoveryIncidents).mockImplementation(async (source) => {
    if (source === "machine") throw new Error("private native detail");
    return page(source);
  });
  render(<RecoveryIncidentHistory />);
  const error = await screen.findByRole("alert");
  expect(error.textContent).toContain("Computer history is unavailable");
  expect(error.textContent).not.toContain("private native detail");
  expect(screen.queryByText(/No retained machine entries/)).toBeNull();
  await screen.findByText(/Matching retained account acknowledgment observed/);
});
it("does not combine ambiguous generations and pages each source independently", async () => {
  const first = page("user");
  first.user!.entries[0].status = "ambiguous_generations";
  first.user!.entries[0].acknowledgment = null;
  first.user!.nextCursor = id;
  vi.mocked(listRecoveryIncidents).mockImplementation(
    async (source, cursor) => {
      if (source === "machine") return page(source);
      return cursor
        ? { ...page("user"), user: { entries: [], nextCursor: null } }
        : first;
    },
  );
  render(<RecoveryIncidentHistory />);
  await screen.findByText(
    /Multiple retained generations share this incident ID/,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Load more user incidents" }),
  );
  await waitFor(() =>
    expect(listRecoveryIncidents).toHaveBeenLastCalledWith("user", id),
  );
  expect(
    screen.queryByText(/Matching retained account acknowledgment observed/),
  ).toBeNull();
});
it("waits while app operations are busy and refresh never replays or acknowledges", async () => {
  const { rerender } = render(<RecoveryIncidentHistory disabled />);
  expect(listRecoveryIncidents).not.toHaveBeenCalled();
  rerender(<RecoveryIncidentHistory />);
  await screen.findByText(/Matching retained account acknowledgment observed/);
  fireEvent.click(
    screen.getByRole("button", { name: "Refresh user incident history" }),
  );
  await waitFor(() => expect(listRecoveryIncidents).toHaveBeenCalledTimes(3));
  expect(
    vi.mocked(listRecoveryIncidents).mock.calls.map((call) => call[0]),
  ).toEqual(["machine", "user", "user"]);
});
