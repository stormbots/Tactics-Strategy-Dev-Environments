import { invoke, isTauri } from "@tauri-apps/api/core";
import type { Mode, Report, Schedule } from "./model";
import { version } from "../package.json";
export const appVersion = version;
export type Destination =
  "editor" | "workspace" | "logs" | "maintenance" | "repository" | "skyview";
export const native = isTauri();
const sample = [
  "SKYVIEW_EVENT|validation|PASS|Git: git version 2.49.0",
  "SKYVIEW_EVENT|validation|PASS|GitHub CLI: 2.76.0",
  "SKYVIEW_EVENT|validation|PASS|Node.js: v24.10.0",
  "SKYVIEW_EVENT|validation|PASS|npm: 11.6.0",
  "SKYVIEW_EVENT|validation|FAIL|Python 3.14: not installed",
  "SKYVIEW_EVENT|validation|FAIL|VSCodium: not installed",
  "SKYVIEW_EVENT|validation|FAIL|DBeaver: not installed",
  "SKYVIEW_EVENT|validation|FAIL|PyCharm: not installed",
  "SKYVIEW_EVENT|validation|PASS|Firefox: installed",
  "SKYVIEW_EVENT|validation|FAIL|Chrome: not installed",
  "SKYVIEW_EVENT|validation|FAIL|Weekly maintenance enabled",
  "SKYVIEW_EVENT|validation|INFO|Git identity: not configured (optional)",
  "SKYVIEW_EVENT|validation|INFO|GitHub authentication: not configured (optional)",
  "SKYVIEW_EVENT|summary|6|Some components are missing",
];
const previewTools = [
  {
    tool: "Git",
    installedVersion: "2.49.0",
    availableVersion: "2.50.0",
    updateAvailable: true,
    updateCheck: "current",
  },
  {
    tool: "GitHub CLI",
    installedVersion: "2.76.0",
    availableVersion: null,
    updateAvailable: false,
    updateCheck: "current",
  },
  {
    tool: "Node.js",
    installedVersion: "24.10.0",
    availableVersion: "24.11.0",
    updateAvailable: true,
    updateCheck: "current",
  },
  {
    tool: "Firefox",
    installedVersion: "144.0",
    availableVersion: null,
    updateAvailable: false,
    updateCheck: "unavailable",
  },
];
const metadata = previewTools.map(
  (t) => `SKYVIEW_EVENT|tool|${t.tool}|${JSON.stringify(t)}`,
);
const previewReport: Report = {
  code: 1,
  success: false,
  lines: [...sample, ...metadata],
  log_path: "Preview — no files are written",
  platform: { label: "Linux Mint 22.2 · amd64", supported: true },
};
export async function inspect(): Promise<Report> {
  return native ? invoke("inspect_system") : previewReport;
}
export async function operate(
  mode: Mode,
  id: string,
  checkUpdates: boolean,
  emit: (line: string) => void,
): Promise<Report> {
  if (native)
    return invoke("run_operation", {
      operation: mode,
      runId: id,
      checkUpdates,
    });
  const lines: string[] = [];
  for (const [percent, message] of [
    [5, "Checking system"],
    [20, "Configuring package sources"],
    [40, "Installing development tools"],
    [72, "Verifying PyCharm download"],
    [82, "Configuring your workspace"],
    [95, "Validating environment"],
  ] as const) {
    await new Promise((resolve) => setTimeout(resolve, 450));
    const line = `SKYVIEW_EVENT|progress|${percent}|${message}`;
    lines.push(line);
    emit(line);
  }
  const results =
    mode === "validate"
      ? sample
      : sample.map((s) =>
          s
            .replace("|FAIL|", "|PASS|")
            .replace(": not installed", ": installed")
            .replace(
              "|summary|6|Some components are missing",
              "|summary|0|All required checks passed",
            ),
        );
  const records = previewTools.map((t) => ({
    ...t,
    updateAvailable: checkUpdates && mode !== "update" && t.updateAvailable,
    availableVersion:
      checkUpdates && mode !== "update" ? t.availableVersion : null,
    installedVersion:
      mode === "update"
        ? t.availableVersion || t.installedVersion
        : t.installedVersion,
    updateCheck: checkUpdates ? t.updateCheck : "notChecked",
  }));
  [
    ...results,
    ...records.map((t) => `SKYVIEW_EVENT|tool|${t.tool}|${JSON.stringify(t)}`),
  ].forEach((line) => {
    lines.push(line);
    emit(line);
  });
  return {
    ...previewReport,
    lines,
    code: mode === "validate" ? 1 : 0,
    success: mode !== "validate",
  };
}
export async function inspectSchedule(): Promise<Schedule> {
  if (native) return invoke("inspect_schedule");
  return {
    status: "enabled",
    active: true,
    identifier: "skyview-student-dev-update.timer",
    frequency: "Sunday at 03:00; randomized delay up to 1 hour (local time)",
    nextRun: "2026-10-11T10:40:00Z",
    lastRun: "2026-10-04T10:20:00Z",
    lastResult: "success",
    resultDetail: "Service result: success; exit status: 0",
    catchUp: true,
    logFolder: "/var/log/skyview-robotics/student-dev",
    logsAvailable: true,
    note: "",
  };
}
export async function open(destination: Destination) {
  if (native) await invoke("open_destination", { destination });
}
