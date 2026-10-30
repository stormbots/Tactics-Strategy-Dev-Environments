import { collectionTime, type Check } from "./model";
import type {
  MaintenanceObservation,
  OperationIncident,
  SupportReportSnapshot,
} from "./safeOperations";

export type SupportContext = {
  deviceName: string;
  logs: string | null;
};

const escape = (value: string) =>
  value.replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[character]!,
  );

export function supportSnapshot(input: {
  context: SupportContext;
  platform: string;
  applicationVersion: string;
  checks: Check[];
  validationComplete: boolean;
  validationCollectedAt?: number | null;
  incident: OperationIncident | null;
  maintenance: MaintenanceObservation | null;
  includeLogs: boolean;
}): SupportReportSnapshot {
  const outcome = input.checks.some((check) => check.status === "FAIL")
    ? "needsAttention"
    : input.validationComplete
      ? "ready"
      : "unavailable";
  return {
    schema: 1,
    createdAt: new Date().toISOString(),
    deviceName: input.context.deviceName,
    platform: input.platform,
    applicationVersion: input.applicationVersion,
    validation: {
      collectedAt:
        input.checks.length && collectionTime(input.validationCollectedAt)
          ? new Date(input.validationCollectedAt! * 1000).toISOString()
          : null,
      outcome,
      checks: input.checks.map(({ status, message }) => ({ status, message })),
    },
    operation: input.incident
      ? {
          kind: input.incident.operation,
          stage: input.incident.stage,
          outcome: "interrupted",
          observedAt: new Date(input.incident.observedAt * 1000).toISOString(),
        }
      : null,
    maintenance: input.maintenance,
    logs: {
      included: input.includeLogs && input.context.logs !== null,
      content: input.includeLogs ? input.context.logs : null,
      omission: input.includeLogs
        ? input.context.logs === null
          ? "No recent application log was available."
          : null
        : "Logs were not included by the student.",
    },
  };
}

export function supportHtml(report: SupportReportSnapshot): string {
  const outcome = {
    ready: "Ready",
    needsAttention: "Needs attention",
    unavailable: "Unavailable",
  }[report.validation.outcome];
  const checks = report.validation.checks.length
    ? report.validation.checks
        .map(
          (check) =>
            `<tr><td>${escape(check.status)}</td><td>${escape(check.message)}</td></tr>`,
        )
        .join("")
    : '<tr><td colspan="2">No validation results were available.</td></tr>';
  const maintenance = report.maintenance
    ? `${report.maintenance.status}; last result: ${report.maintenance.lastResult}; last success: ${report.maintenance.lastSuccess ?? "unavailable"}`
    : "Maintenance status was unavailable.";
  const operation = report.operation
    ? `${report.operation.kind}; ${report.operation.outcome} during ${report.operation.stage}`
    : "No interrupted operation was recorded.";
  const log = report.logs.included
    ? `<pre>${escape(report.logs.content ?? "")}</pre>`
    : `<p>${escape(report.logs.omission ?? "Logs were not included.")}</p>`;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Skyview SDE Support Report</title><style>body{font:15px system-ui,sans-serif;color:#172b4d;max-width:900px;margin:32px auto;padding:0 24px;line-height:1.5}h1{font-size:26px}h2{margin-top:28px;font-size:18px}dl{display:grid;grid-template-columns:180px 1fr;gap:6px 16px}dt{font-weight:700}dd{margin:0}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd5df;padding:8px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#edf2f7;padding:14px;border-radius:6px}</style></head><body><h1>Skyview SDE Support Report</h1><p>Created ${escape(report.createdAt)}</p><h2>Device</h2><dl><dt>Device name</dt><dd>${escape(report.deviceName)}</dd><dt>Platform</dt><dd>${escape(report.platform)}</dd><dt>SDE version</dt><dd>${escape(report.applicationVersion)}</dd></dl><h2>Validation</h2><p>Outcome: ${escape(outcome)}</p><table><thead><tr><th>Status</th><th>Check</th></tr></thead><tbody>${checks}</tbody></table><h2>Interrupted operation</h2><p>${escape(operation)}</p><h2>Maintenance</h2><p>${escape(maintenance)}</p><h2>Application logs</h2>${log}</body></html>`;
}
