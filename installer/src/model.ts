export type Mode = "install" | "repair" | "validate" | "update";
export type Check = {
  status: "PASS" | "WARNING" | "FAIL" | "INFO";
  message: string;
};
export type Event = { kind: string; key: string; message: string };
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
  const managed = checks.filter((c) =>
    /^(Git:|GitHub CLI:|Node.js:|Python:|VSCodium:|DBeaver:|PyCharm:|Chrome:|Firefox:|Git$|GitHub CLI$|Node.js$|Python 3.14$|VSCodium$|DBeaver$|PyCharm$|Firefox$|Google Chrome)/.test(
      c.message,
    ),
  );
  const installed = managed.filter((c) => c.status === "PASS").length;
  const failed = checks.some((c) => c.status === "FAIL");
  if (!checks.length) return "Not checked";
  if (!installed && failed) return "Not installed";
  if (failed && installed < managed.length) return "Partially installed";
  if (failed) return "Needs repair";
  return updates ? "Needs update" : "Ready";
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
      updates: a.report.lines.some((l) => parseEvent(l)?.kind === "update"),
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
      updates: a.report.lines.some((l) => parseEvent(l)?.kind === "update"),
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
  return next;
}
