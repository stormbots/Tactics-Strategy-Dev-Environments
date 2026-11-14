import { nativeRead } from "./nativeReadQueue";
import { invoke, isTauri } from "@tauri-apps/api/core";
export type HistorySource = "machine" | "user";
export type IncidentHistoryEntry = {
  incidentId: string;
  status:
    | "archive_observed_acknowledgment_unknown"
    | "acknowledgment_observed"
    | "acknowledgment_unknown"
    | "ambiguous_generations"
    | "unavailable";
  context?: {
    source: "user";
    incident: {
      operation: string;
      stage: string;
      startedAt: number;
      observedAt: number;
    };
  } | null;
  acknowledgment?: { acknowledgedAt: number; reportId: string | null } | null;
  continuation: "not_recorded";
  viewToken?: string | null;
};
type Page = {
  entries: IncidentHistoryEntry[];
  nextCursor: string | null;
  unexpectedEntries?: boolean;
};
export type IncidentHistoryPage = {
  observedAt: number;
  machine: Page | null;
  user: Page | null;
  hiddenViews?: number;
  viewStateUnavailable?: boolean;
};
export async function deleteRecoveryHistoryView(
  viewToken: string,
): Promise<void> {
  if (!isTauri())
    throw new Error("Preview cannot delete workstation history views.");
  await invoke("delete_recovery_history_view", { viewToken, confirmed: true });
}
export async function listRecoveryIncidents(
  source: HistorySource,
  cursor: string | null = null,
): Promise<IncidentHistoryPage> {
  return isTauri()
    ? source === "machine"
      ? nativeRead(() =>
          invoke("list_recovery_incidents", { source, cursor, limit: 25 }),
        )
      : invoke("list_recovery_incidents", { source, cursor, limit: 25 })
    : {
        observedAt: Math.floor(Date.now() / 1000),
        machine:
          source === "machine" ? { entries: [], nextCursor: null } : null,
        user:
          source === "user"
            ? { entries: [], nextCursor: null, unexpectedEntries: false }
            : null,
      };
}
