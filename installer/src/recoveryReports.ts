import { nativeRead } from "./nativeReadQueue";
import { invoke, isTauri } from "@tauri-apps/api/core";
export type RecoveryReportEntry = {
  reportId: string;
  incidentId: string | null;
  capturedAt: number | null;
  status: "saved" | "incomplete_or_unreadable";
};
export type RecoveryReportPage = {
  entries: RecoveryReportEntry[];
  nextCursor: string | null;
};
export type RecoveryReportDetails = {
  reportId: string;
  html: string;
  acknowledgment: {
    source: "machine" | "user" | null;
    status: "observed" | "unknown" | "unavailable";
    acknowledgedAt: number | null;
    observedAt: number;
    note: string;
    continuation: "not_recorded";
  };
};
export async function listRecoveryReports(
  cursor: string | null = null,
): Promise<RecoveryReportPage> {
  return isTauri()
    ? invoke("list_recovery_reports", { cursor, limit: 25 })
    : { entries: [], nextCursor: null };
}
export async function readRecoveryReport(
  reportId: string,
): Promise<RecoveryReportDetails> {
  if (!isTauri()) throw new Error("Preview has no saved workstation reports.");
  return nativeRead(() => invoke("read_recovery_report_details", { reportId }));
}
export async function exportRecoveryReport(
  reportId: string,
): Promise<string | null> {
  if (!isTauri()) throw new Error("Preview cannot export workstation reports.");
  return invoke("export_recovery_report", { reportId });
}
export async function deleteRecoveryReport(reportId: string): Promise<void> {
  if (!isTauri()) throw new Error("Preview cannot delete workstation reports.");
  await invoke("delete_recovery_report", { reportId, confirmed: true });
}
