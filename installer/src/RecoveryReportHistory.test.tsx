import { beforeEach, afterEach, expect, it, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { RecoveryReportHistory } from "./RecoveryReportHistory";
import {
  listRecoveryReports,
  readRecoveryReport,
  exportRecoveryReport,
  deleteRecoveryReport,
  type RecoveryReportDetails,
} from "./recoveryReports";
vi.mock("./recoveryReports", () => ({
  listRecoveryReports: vi.fn(),
  readRecoveryReport: vi.fn(),
  exportRecoveryReport: vi.fn(),
  deleteRecoveryReport: vi.fn(),
}));
const id = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
const entry = {
  reportId: id,
  incidentId: id,
  capturedAt: 100,
  status: "saved" as const,
};
const details: RecoveryReportDetails = {
  reportId: id,
  html: "<!doctype html><html><body><h1>Safe summary</h1></body></html>",
  acknowledgment: {
    source: "user",
    status: "unknown",
    acknowledgedAt: null,
    observedAt: 200,
    note: "No matching acknowledgment was established; this does not prove completion.",
    continuation: "not_recorded",
  },
};
beforeEach(() => {
  vi.mocked(listRecoveryReports)
    .mockReset()
    .mockResolvedValue({ entries: [entry], nextCursor: null });
  vi.mocked(readRecoveryReport).mockReset().mockResolvedValue(details);
  vi.mocked(exportRecoveryReport)
    .mockReset()
    .mockResolvedValue("/chosen/report.html");
  vi.mocked(deleteRecoveryReport).mockReset().mockResolvedValue(undefined);
});
afterEach(cleanup);
async function view() {
  fireEvent.click(
    await screen.findByRole("button", { name: `View report ${id}` }),
  );
  await screen.findByRole("heading", { name: "Selected recovery summary" });
}
it("shows separate unavailable versus empty history and never implies completion", async () => {
  vi.mocked(listRecoveryReports).mockRejectedValueOnce(new Error("private"));
  render(<RecoveryReportHistory />);
  await screen.findByRole("alert");
  expect(screen.queryByText(/No saved reports were found/)).toBeNull();
  expect(screen.getByRole("alert").textContent).not.toContain("private");
  vi.mocked(listRecoveryReports).mockResolvedValue({
    entries: [],
    nextCursor: null,
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Refresh report history" }),
  );
  await screen.findByText(/No saved reports were found/);
  expect(readRecoveryReport).not.toHaveBeenCalled();
});
it("loads bounded pages without purging and deduplicates overlapping results", async () => {
  vi.mocked(listRecoveryReports).mockResolvedValueOnce({
    entries: [entry],
    nextCursor: id,
  });
  render(<RecoveryReportHistory />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Load more reports" }),
  );
  await waitFor(() => expect(listRecoveryReports).toHaveBeenLastCalledWith(id));
  expect(
    screen.getAllByRole("button", { name: `View report ${id}` }),
  ).toHaveLength(1);
  expect(deleteRecoveryReport).not.toHaveBeenCalled();
});
it("renders only a sandboxed preview, preserving unknown acknowledgment and no completion claim", async () => {
  render(<RecoveryReportHistory />);
  await view();
  const frame = screen.getByTitle("Retained recovery summary preview");
  expect(frame.getAttribute("sandbox")).toBe("");
  expect(frame.getAttribute("srcdoc")).toBe(details.html);
  expect(screen.getByText(/Acknowledgment observation: unknown/)).toBeTruthy();
  expect(
    screen.getByText(/Continuation\/completion: not recorded/),
  ).toBeTruthy();
  await waitFor(() =>
    expect(document.activeElement?.textContent).toBe(
      "Selected recovery summary",
    ),
  );
  expect(exportRecoveryReport).not.toHaveBeenCalled();
});
it("export is explicit, cancel is not success, and the original report stays retained", async () => {
  vi.mocked(exportRecoveryReport).mockResolvedValueOnce(null);
  render(<RecoveryReportHistory />);
  await view();
  fireEvent.click(screen.getByRole("button", { name: "Export report copy" }));
  await screen.findByText(/Export canceled/);
  expect(exportRecoveryReport).toHaveBeenCalledExactlyOnceWith(id);
  expect(deleteRecoveryReport).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Export report copy" }));
  await screen.findByText(/Exported a copy to \/chosen\/report.html/);
});
it("requires explicit selected-report deletion confirmation and prevents duplicate commits", async () => {
  let resolve!: () => void;
  vi.mocked(deleteRecoveryReport).mockImplementation(
    () =>
      new Promise<void>((done) => {
        resolve = done;
      }),
  );
  render(<RecoveryReportHistory />);
  await view();
  fireEvent.click(
    screen.getByRole("button", { name: "Delete selected local report" }),
  );
  expect(deleteRecoveryReport).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Keep local report" }));
  expect(deleteRecoveryReport).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Delete selected local report" }),
  );
  const confirm = screen.getByRole("button", {
    name: "Confirm delete local report",
  });
  fireEvent.click(confirm);
  fireEvent.click(confirm);
  expect(deleteRecoveryReport).toHaveBeenCalledExactlyOnceWith(id);
  resolve();
  await screen.findByText(/Selected local report deleted/);
  expect(screen.queryByTitle("Retained recovery summary preview")).toBeNull();
  expect(
    screen.getByText(/Selected local report deleted/).textContent,
  ).toContain("minimum acknowledgment state remain");
});
it("an unreadable bundle is not exported, but selected deletion remains explicit", async () => {
  vi.mocked(listRecoveryReports).mockResolvedValue({
    entries: [
      { ...entry, status: "incomplete_or_unreadable", capturedAt: null },
    ],
    nextCursor: null,
  });
  render(<RecoveryReportHistory />);
  const button = await screen.findByRole("button", {
    name: `View report ${id}`,
  });
  expect((button as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(
    screen.getByRole("button", { name: `Delete local report ${id}` }),
  );
  expect(deleteRecoveryReport).not.toHaveBeenCalled();
  expect(
    screen.getByRole("group", { name: "Confirm local report deletion" }),
  ).toBeTruthy();
});
it("a changed report's failed export/delete is not success or implicit state clearance", async () => {
  vi.mocked(exportRecoveryReport).mockRejectedValue(
    new Error("Changed evidence"),
  );
  vi.mocked(deleteRecoveryReport).mockRejectedValue(
    new Error("Unexpected contents"),
  );
  render(<RecoveryReportHistory />);
  await view();
  fireEvent.click(screen.getByRole("button", { name: "Export report copy" }));
  await screen.findByRole("alert");
  expect(screen.queryByText(/Exported a copy/)).toBeNull();
  fireEvent.click(
    screen.getByRole("button", { name: "Delete selected local report" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Confirm delete local report" }),
  );
  await screen.findByRole("alert");
  expect(screen.queryByText(/^Selected local report deleted/)).toBeNull();
  expect(screen.getByTitle("Retained recovery summary preview")).toBeTruthy();
});
it("recent report references are directly viewable without falsely assuming first-page ordering", async () => {
  vi.mocked(listRecoveryReports).mockResolvedValue({
    entries: [],
    nextCursor: null,
  });
  render(<RecoveryReportHistory recentReports={[id, id]} />);
  const recent = screen.getByRole("button", {
    name: `View recent report ${id}`,
  });
  await waitFor(() =>
    expect((recent as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(recent);
  await screen.findByRole("heading", { name: "Selected recovery summary" });
  expect(readRecoveryReport).toHaveBeenCalledExactlyOnceWith(id);
});
