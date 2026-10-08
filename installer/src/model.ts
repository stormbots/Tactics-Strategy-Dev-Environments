export type Mode = "install" | "repair" | "validate" | "update";
export type Check = {
  status: "PASS" | "WARNING" | "FAIL" | "INFO";
  message: string;
};
export type Event = { kind: string; key: string; message: string };
export type ToolRecord = {
  tool: string;
  installedVersion: string | null;
  availableVersion: string | null;
  updateAvailable: boolean;
  updateCheck: "current" | "notChecked" | "unavailable" | "native";
};
export type Schedule = {
  status: "enabled" | "disabled" | "missing" | "unavailable";
  active: boolean;
  identifier: string;
  frequency: string;
  nextRun: string | null;
  lastRun: string | null;
  lastResult: "success" | "failure" | "never" | "running" | "unavailable";
  resultDetail: string;
  catchUp: boolean | null;
  logFolder: string;
  logsAvailable: boolean;
  note: string;
};
export const toolNames = [
  "Git",
  "GitHub CLI",
  "Node.js",
  "Python",
  "Python venv",
  "VSCodium",
  "DBeaver",
  "PyCharm",
  "Chrome",
  "Firefox",
  "PowerShell 7",
  "OpenSSH",
  "7-Zip",
  "npm",
] as const;
export function toolRecord(e: Event | null): ToolRecord | null {
  if (e?.kind !== "tool") return null;
  try {
    const r = JSON.parse(e.message);
    const version = (v: unknown) =>
      v === null ||
      (typeof v === "string" &&
        v.length > 0 &&
        v.length <= 120 &&
        !/[\r\n|]/.test(v));
    if (
      !toolNames.includes(r.tool) ||
      e.key !== r.tool ||
      !version(r.installedVersion) ||
      !version(r.availableVersion) ||
      typeof r.updateAvailable !== "boolean" ||
      !["current", "notChecked", "unavailable", "native"].includes(
        r.updateCheck,
      ) ||
      (r.updateAvailable &&
        (!r.installedVersion ||
          !r.availableVersion ||
          r.updateCheck !== "current"))
    )
      return null;
    return r;
  } catch {
    return null;
  }
}
export function toolsFrom(lines: string[]): ToolRecord[] {
  const records = new Map<string, ToolRecord>();
  for (const line of lines) {
    const r = toolRecord(parseEvent(line));
    if (r) records.set(r.tool, r);
  }
  return [...records.values()];
}
export function toolForCheck(c: Check): string | undefined {
  if (
    [
      "Python 3.14 venv and project-local pip work",
      "Python 3.14 could not create a venv with pip",
    ].includes(c.message)
  )
    return "Python venv";
  if (/^Python(?: 3\.14)?(?::|$| not found)/.test(c.message)) return "Python";
  if (/^Google Chrome (found|not found)$/.test(c.message)) return "Chrome";
  return toolNames.find(
    (name) =>
      c.message === name ||
      c.message.startsWith(`${name}:`) ||
      c.message === `${name} not found`,
  );
}
export function toolStatus(c: Check, r?: ToolRecord): string {
  if (c.status !== "PASS") return "Missing / needs repair";
  if (r?.updateAvailable)
    return `Update available · ${r.installedVersion} → ${r.availableVersion}`;
  return `Ready · ${r?.installedVersion || "Version unavailable"}`;
}
export function updateInspectionIncomplete(
  checks: Check[],
  tools: ToolRecord[],
): boolean {
  return (
    !tools.length ||
    checks.some((c) => {
      const name = toolForCheck(c);
      if (c.status !== "PASS" || !name) return false;
      const record = tools.find((t) => t.tool === name);
      return (
        !record || ["unavailable", "notChecked"].includes(record.updateCheck)
      );
    })
  );
}
export type Report = {
  code: number;
  success: boolean;
  lines: string[];
  log_path: string;
  platform: { label: string; supported: boolean };
};
export function parseEvent(line: string): Event | null {
  const match = /^SKYVIEW_EVENT\|([^|]+)\|([^|]*)\|([^\r\n]*)\r?$/.exec(line);
  if (!match) return null;
  const [, kind, key, message] = match;
  if (
    ![
      "progress",
      "phase",
      "status",
      "validation",
      "warning",
      "error",
      "summary",
      "update",
      "tool",
    ].includes(kind)
  )
    return null;
  if (kind === "progress" && (!/^\d+$/.test(key) || Number(key) > 100))
    return null;
  if (kind === "summary" && !/^\d+$/.test(key)) return null;
  if (
    kind === "validation" &&
    !["PASS", "WARNING", "FAIL", "INFO"].includes(key)
  )
    return null;
  return { kind, key, message };
}
export function checksFrom(lines: string[]): Check[] {
  return lines.flatMap((line) => {
    const e = parseEvent(line);
    return e?.kind === "validation"
      ? [{ status: e.key as Check["status"], message: e.message }]
      : [];
  });
}
export function environmentStatus(checks: Check[], updates = false) {
  const managed = checks.filter((c) => toolForCheck(c));
  const installed = managed.filter((c) => c.status === "PASS").length;
  const failed = checks.some((c) => c.status === "FAIL");
  if (!checks.length) return "Not checked";
  if (!installed && failed) return "Not installed";
  if (failed && installed < managed.length) return "Partially installed";
  if (failed) return "Needs repair";
  return updates ? "Updates available" : "Ready";
}
export type State = {
  stage: "checking" | "idle" | "running" | "success" | "failure";
  mode: Mode;
  progress: number;
  phase: string;
  checks: Check[];
  logs: string[];
  warnings: string[];
  error: string;
  logPath: string;
  updates: boolean;
  tools: ToolRecord[];
  platform: Report["platform"];
};
export const initialState: State = {
  stage: "checking",
  mode: "install",
  progress: 0,
  phase: "Checking this workstation",
  checks: [],
  logs: [],
  warnings: [],
  error: "",
  logPath: "",
  updates: false,
  tools: [],
  platform: { label: "Detecting system…", supported: false },
};
export type Action =
  | { type: "initial"; report: Report }
  | { type: "start"; mode: Mode }
  | { type: "line"; line: string }
  | { type: "complete"; report: Report }
  | { type: "error"; message: string };
export function reducer(s: State, a: Action): State {
  if (a.type === "initial")
    return {
      ...s,
      stage: checksFrom(a.report.lines).length ? "idle" : "failure",
      error: checksFrom(a.report.lines).length
        ? ""
        : a.report.lines.map(parseEvent).find((e) => e?.kind === "error")
            ?.message ||
          "This workstation could not be checked. Review details and retry validation.",
      checks: checksFrom(a.report.lines),
      logs: a.report.lines.slice(-2000),
      logPath: a.report.log_path,
      platform: a.report.platform,
      updates:
        toolsFrom(a.report.lines).some((t) => t.updateAvailable) ||
        a.report.lines.some((l) => parseEvent(l)?.kind === "update"),
      tools: toolsFrom(a.report.lines),
    };
  if (a.type === "start")
    return {
      ...s,
      stage: "running",
      mode: a.mode,
      progress: 0,
      phase:
        a.mode === "validate"
          ? "Checking your development tools"
          : "Waiting for administrator approval",
      checks: [],
      logs: [],
      warnings: [],
      error: "",
      updates: false,
      tools: [],
    };
  if (a.type === "error") return { ...s, stage: "failure", error: a.message };
  if (a.type === "complete") {
    const checks = checksFrom(a.report.lines);
    const valid =
      a.report.success &&
      a.report.code === 0 &&
      checks.length > 0 &&
      !checks.some((c) => c.status === "FAIL") &&
      a.report.lines.some((l) => {
        const e = parseEvent(l);
        return e?.kind === "summary" && e.key === "0";
      });
    const errors = a.report.lines
      .map(parseEvent)
      .filter((e) => e?.kind === "error");
    return {
      ...s,
      stage: valid ? "success" : "failure",
      checks,
      logs: a.report.lines.slice(-2000),
      progress: valid ? 100 : s.progress,
      platform: a.report.platform,
      logPath: a.report.log_path,
      error: valid
        ? ""
        : errors.at(-1)?.message ||
          "Some checks need attention. Review the validation results and use Repair to restore missing components.",
      updates:
        toolsFrom(a.report.lines).some((t) => t.updateAvailable) ||
        a.report.lines.some((l) => parseEvent(l)?.kind === "update"),
      tools: toolsFrom(a.report.lines),
    };
  }
  const e = parseEvent(a.line);
  let next = { ...s, logs: [...s.logs, a.line].slice(-2000) };
  if (!e) return next;
  if (e.kind === "progress")
    next = {
      ...next,
      progress: Math.max(s.progress, Number(e.key)),
      phase: e.message,
    };
  if (e.kind === "phase") next.phase = e.message;
  if (e.kind === "validation")
    next.checks = [
      ...s.checks,
      { status: e.key as Check["status"], message: e.message },
    ];
  if (e.kind === "warning") next.warnings = [...s.warnings, e.message];
  if (e.kind === "error") next.error = e.message;
  if (e.kind === "update") next.updates = true;
  const record = toolRecord(e);
  if (record) {
    next.tools = [...s.tools.filter((t) => t.tool !== record.tool), record];
    if (record.updateAvailable) next.updates = true;
  }
  return next;
}
