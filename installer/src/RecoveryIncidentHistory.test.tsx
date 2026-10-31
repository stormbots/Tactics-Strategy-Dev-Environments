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
  type IncidentHistoryPage,
} from "./recoveryIncidents";
vi.mock("./recoveryIncidents", () => ({ listRecoveryIncidents: vi.fn() }));
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
  vi.mocked(listRecoveryIncidents)
    .mockReset()
    .mockImplementation(async (source) => page(source));
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
  expect(error.textContent).toContain(
    "Machine incident history is unavailable",
  );
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
