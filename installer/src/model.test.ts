import { describe, it, expect } from "vitest";
import {
  initialState,
  reducer,
  parseEvent,
  environmentStatus,
  checksFrom,
  toolsFrom,
  toolStatus,
  toolForCheck,
  type Mode,
  type Report,
} from "./model";
const report = (lines: string[], code = 0): Report => ({
  lines,
  code,
  success: code === 0,
  log_path: "example.log",
  platform: { label: "Windows 11", supported: true },
});
const valid = [
  "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
  "SKYVIEW_EVENT|validation|INFO|Git identity: not configured",
  "SKYVIEW_EVENT|summary|0|Done",
];
describe("structured protocol", () => {
  it("parses events and preserves message pipes", () =>
    expect(
      parseEvent("SKYVIEW_EVENT|progress|45|Installing | editor")?.message,
    ).toBe("Installing | editor"));
  it("rejects malformed events and arbitrary native output", () => {
    for (const line of [
      "SKYVIEW_EVENT|progress|101|Bad",
      "SKYVIEW_EVENT|progress|-1|Bad",
      "SKYVIEW_EVENT|validation|OK|Bad",
      "SKYVIEW_EVENT|summary|no|Bad",
      "Node installed",
      "SKYVIEW_EVENT|unknown|x|y",
    ])
      expect(parseEvent(line)).toBeNull();
  });
  it("parses all validation severities", () =>
    expect(
      checksFrom(
        ["PASS", "WARNING", "FAIL", "INFO"].map(
          (s) => `SKYVIEW_EVENT|validation|${s}|Check`,
        ),
      ).map((c) => c.status),
    ).toEqual(["PASS", "WARNING", "FAIL", "INFO"]));
});
describe("operation states", () => {
  for (const mode of ["install", "repair", "validate", "update"] as Mode[])
    it(`completes ${mode} only with successful validation`, () => {
      let state = reducer(initialState, { type: "start", mode });
      expect(state.stage).toBe("running");
      expect(state.mode).toBe(mode);
      state = reducer(state, {
        type: "line",
        line: "SKYVIEW_EVENT|progress|45|Working",
      });
      expect(state.progress).toBe(45);
      state = reducer(state, { type: "complete", report: report(valid) });
      expect(state.stage).toBe("success");
      expect(state.progress).toBe(100);
    });
  it("treats child exit failures as failures", () =>
    expect(
      reducer(initialState, { type: "complete", report: report(valid, 5) })
        .stage,
    ).toBe("failure"));
  it("requires a complete validator report", () =>
    expect(
      reducer(initialState, { type: "complete", report: report([]) }).stage,
    ).toBe("failure"));
  it("fails even if a contradictory summary claims success", () =>
    expect(
      reducer(initialState, {
        type: "complete",
        report: report([...valid, "SKYVIEW_EVENT|validation|FAIL|Node"]),
      }).stage,
    ).toBe("failure"));
  it("preserves meaningful backend errors", () =>
    expect(
      reducer(initialState, {
        type: "complete",
        report: report(
          ["SKYVIEW_EVENT|error|pycharm|Checksum verification failed"],
          1,
        ),
      }).error,
    ).toBe("Checksum verification failed"));
  it("allows retry without stale errors or validation", () => {
    const s = reducer(
      {
        ...initialState,
        stage: "failure",
        error: "old",
        checks: [{ status: "FAIL", message: "Old" }],
      },
      { type: "start", mode: "repair" },
    );
    expect(s.error).toBe("");
    expect(s.checks).toEqual([]);
  });
  it("keeps progress monotonic", () => {
    const s = reducer(
      { ...initialState, progress: 60 },
      { type: "line", line: "SKYVIEW_EVENT|progress|30|Phase" },
    );
    expect(s.progress).toBe(60);
  });
});
describe("workstation state detection", () => {
  it("handles all five required states", () => {
    expect(
      environmentStatus([{ status: "FAIL", message: "Git: not installed" }]),
    ).toBe("Not installed");
    expect(
      environmentStatus([
        { status: "PASS", message: "Git: 2.x" },
        { status: "FAIL", message: "Node.js: not installed" },
      ]),
    ).toBe("Partially installed");
    expect(
      environmentStatus([
        { status: "PASS", message: "Git: 2.x" },
        { status: "FAIL", message: "Weekly maintenance" },
      ]),
    ).toBe("Needs repair");
    expect(environmentStatus(checksFrom(valid))).toBe("Ready");
    expect(environmentStatus(checksFrom(valid), true)).toBe(
      "Updates available",
    );
  });
  it("does not fail optional identity or authentication", () =>
    expect(environmentStatus(checksFrom(valid))).toBe("Ready"));
});
describe("tool metadata", () => {
  const record = {
    tool: "Git",
    installedVersion: "2.43.0",
    availableVersion: "2.44.0",
    updateAvailable: true,
    updateCheck: "current",
  };
  const line = (r: unknown) => `SKYVIEW_EVENT|tool|Git|${JSON.stringify(r)}`;
  it("deduplicates records and keeps update availability independent of failures", () => {
    const state = reducer(initialState, {
      type: "initial",
      report: report([...valid, line(record), line(record)]),
    });
    expect(state.tools).toHaveLength(1);
    expect(state.updates).toBe(true);
    expect(state.checks.some((c) => c.status === "FAIL")).toBe(false);
    expect(reducer(state, { type: "start", mode: "validate" }).tools).toEqual(
      [],
    );
  });
  it("rejects incomplete, contradictory, malformed, or mismatched records", () => {
    for (const r of [
      { ...record, installedVersion: null },
      { ...record, availableVersion: null },
      { ...record, updateCheck: "unavailable" },
      { ...record, tool: "Firefox" },
      { ...record, updateAvailable: "true" },
    ])
      expect(toolsFrom([line(r)])).toEqual([]);
    expect(
      toolsFrom(["SKYVIEW_EVENT|tool|Git|{bad", "Git 2.44.0 available"]),
    ).toEqual([]);
  });
  it("displays versions, unavailable versions, and repair status without guessing", () => {
    const check = { status: "PASS" as const, message: "Git: 2.43.0" };
    expect(toolStatus(check, { ...record, updateCheck: "current" })).toBe(
      "Update available · 2.43.0 → 2.44.0",
    );
    expect(
      toolStatus(check, {
        ...record,
        availableVersion: null,
        updateAvailable: false,
        updateCheck: "current",
      }),
    ).toBe("Ready · 2.43.0");
    expect(toolStatus(check)).toBe("Ready · Version unavailable");
    expect(
      toolStatus(
        { ...check, status: "FAIL" },
        { ...record, updateCheck: "current" },
      ),
    ).toBe("Missing / needs repair");
    expect(
      toolForCheck({
        status: "PASS",
        message: "Python is on required 3.14.x family",
      }),
    ).toBeUndefined();
    expect(
      toolForCheck({ status: "PASS", message: "Google Chrome found" }),
    ).toBe("Chrome");
  });
});
