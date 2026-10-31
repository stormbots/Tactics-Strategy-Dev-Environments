import { beforeEach, expect, it, vi } from "vitest";
import { invoke, isTauri } from "@tauri-apps/api/core";
import {
  listRecoveryReports,
  readRecoveryReport,
  exportRecoveryReport,
  deleteRecoveryReport,
} from "./recoveryReports";
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
  isTauri: vi.fn(() => true),
}));
beforeEach(() => {
  vi.mocked(invoke).mockReset();
  vi.mocked(isTauri).mockReturnValue(true);
});
it("pages with bounded fixed input and selects reports by ID, never path or caller HTML", async () => {
  await listRecoveryReports("opaque-cursor");
  await readRecoveryReport("selected-report");
  await exportRecoveryReport("selected-report");
  await deleteRecoveryReport("selected-report");
  expect(vi.mocked(invoke).mock.calls).toEqual([
    ["list_recovery_reports", { cursor: "opaque-cursor", limit: 25 }],
    ["read_recovery_report_details", { reportId: "selected-report" }],
    ["export_recovery_report", { reportId: "selected-report" }],
    [
      "delete_recovery_report",
      { reportId: "selected-report", confirmed: true },
    ],
  ]);
});
it("browser preview has no workstation reports and cannot export or delete them", async () => {
  vi.mocked(isTauri).mockReturnValue(false);
  expect(await listRecoveryReports()).toEqual({
    entries: [],
    nextCursor: null,
  });
  await expect(readRecoveryReport("id")).rejects.toThrow("Preview");
  await expect(exportRecoveryReport("id")).rejects.toThrow("Preview");
  await expect(deleteRecoveryReport("id")).rejects.toThrow("Preview");
  expect(invoke).not.toHaveBeenCalled();
});
