import { describe, expect, it } from "vitest";
import {
  beginObservation,
  overviewDecision,
  overviewReviewBinding,
  settleObservation,
  type Observation,
  type OverviewInput,
} from "./overviewDecision";
import { previewRecovery, type RecoveryState } from "./recovery";
import type { Report, Schedule, ToolRecord } from "./model";

const observed = <T>(value: T | null): Observation<T> => ({
  epoch: 1,
  request: value === null ? 0 : 1,
  value,
  pending: false,
});
const report = (messages = ["PASS|Git: 2.49"], complete = true): Report => {
  const failures = messages.filter((m) => m.startsWith("FAIL|")).length;
  return {
    code: failures ? 1 : 0,
    success: !failures,
    platform: { label: "fixture", supported: true },
    log_path: "fixture.log",
    validation_collected_at: 100,
    lines: [
      ...messages.map((m) => `SKYVIEW_EVENT|validation|${m}`),
      ...(complete ? [`SKYVIEW_EVENT|summary|${failures}|Finished`] : []),
    ],
  };
};
const fixture = (): OverviewInput => ({
  epoch: 1,
  validation: observed(report()),
  recovery: observed(previewRecovery()),
  tools: observed<ToolRecord[]>(null),
  maintenance: observed<Schedule>(null),
  task: null,
});
const safety = (patch: Partial<RecoveryState>) => ({
  ...previewRecovery(),
  readiness: "blocked" as const,
  ...patch,
});
const update: ToolRecord = {
  tool: "Git",
  installedVersion: "2.49",
  availableVersion: "2.50",
  updateAvailable: true,
  updateCheck: "current",
};

describe("shared Overview recommendation", () => {
  it("existing tools are ready without account history or package-health proof", () => {
    const d = overviewDecision(fixture());
    expect(d.state).toBe("ready");
    expect(d.primary?.id).toBe("open-editor");
    expect(d.details.safety?.nativeSafety.packageHealth).toBe("unknown");
    expect(d.details.updatesUnknown).toBe(true);
    expect(d.secondary).not.toContain("open-editor");
  });
  it("keeps exact optional-update wording, editor alternative and a single review action", () => {
    const i = fixture();
    i.tools = observed([update]);
    const d = overviewDecision(i);
    expect([d.headline, d.heading, d.body, d.primary?.label]).toEqual([
      "Ready!",
      "Install updates",
      "Your setup works, but there are updates available if you would like to install them.",
      "Review updates",
    ]);
    expect(d.secondary).toContain("open-editor");
    expect(d.secondary).not.toContain("review-updates");
  });
  it.each(["notChecked", "unavailable", "inconsistent"] as const)(
    "does not infer updates from %s metadata",
    (updateCheck) => {
      const i = fixture();
      i.tools = observed([{ ...update, updateCheck }]);
      expect(overviewDecision(i).state).toBe("ready");
      expect(overviewDecision(i).details.updatesUnknown).toBe(true);
    },
  );
  it("uses neutral setup scope for missing tools without inventing prior setup", () => {
    const i = fixture();
    i.validation = observed(
      report(["PASS|Git: 2.49", "FAIL|Python 3.14: not installed"]),
    );
    expect(overviewDecision(i).primary?.id).toBe("review-install");
  });
  it("maps only supported repair findings to Repair", () => {
    const i = fixture();
    i.validation = observed(
      report(["FAIL|Python 3.14 could not create a venv with pip"]),
    );
    expect(overviewDecision(i).state).toBe("repair");
    i.validation = observed(
      report([
        "FAIL|Python 3.14 could not create a venv with pip",
        "FAIL|Unrecognized requirement",
      ]),
    );
    expect(overviewDecision(i).state).toBe("attention");
    i.validation = observed(report(["FAIL|Git fetch.prune is not true"]));
    expect(overviewDecision(i).primary?.id).toBe("review-issue");
  });
  it.each([null, 0, -1, NaN])(
    "timestamp %s cannot establish readiness",
    (timestamp) => {
      const i = fixture();
      i.validation = observed({
        ...report(),
        validation_collected_at: timestamp,
      });
      expect(overviewDecision(i).state).toBe("check-incomplete");
    },
  );
  it("requires completed validation, not partial passes or installer exit success", () => {
    const i = fixture();
    i.validation = observed(report(undefined, false));
    expect(overviewDecision(i).state).toBe("check-incomplete");
    expect(overviewDecision(i).details.checks).toHaveLength(1);
    i.validation = observed(report([], true));
    expect(overviewDecision(i).state).toBe("check-incomplete");
    i.validation = observed({ ...report(), code: 1, success: false });
    expect(overviewDecision(i).state).toBe("check-incomplete");
  });
  it("rejects mismatched summaries and validation/errors after the summary", () => {
    for (const line of [
      "SKYVIEW_EVENT|validation|PASS|Python",
      "SKYVIEW_EVENT|error|x|Failed",
      "SKYVIEW_EVENT|summary|1|Contradiction",
    ]) {
      const i = fixture();
      i.validation = observed({
        ...report(),
        lines: [...report().lines, line],
      });
      expect(overviewDecision(i).state).toBe("check-incomplete");
    }
  });
  it("permits tool metadata after terminal validation without requiring a fixed check count", () => {
    const r = report([
      "PASS|Git: 2.49",
      "PASS|VSCodium: installed",
      "INFO|Optional identity",
    ]);
    r.lines.push(`SKYVIEW_EVENT|tool|Git|${JSON.stringify(update)}`);
    const i = fixture();
    i.validation = observed(r);
    expect(overviewDecision(i).state).toBe("updates");
  });
  it("shows checking then failed collection without a manufactured incident", () => {
    const i = fixture();
    i.validation = beginObservation(i.validation, 1);
    expect(overviewDecision(i).state).toBe("checking");
    expect(overviewDecision(i).secondary).toEqual([]);
    i.validation = settleObservation(i.validation, i.validation, null);
    expect(overviewDecision(i).state).toBe("check-incomplete");
  });
  it("unsupported platforms cannot recommend setup or Ready", () => {
    const i = fixture();
    i.validation = observed({
      ...report(),
      platform: { supported: false, label: "unknown" },
    });
    const d = overviewDecision(i);
    expect(d.state).toBe("attention");
    expect(d.secondary).not.toContain("review-install");
  });
  it.each([
    [
      "active",
      safety({ effectiveActivity: "active", decision: "block_active" }),
    ],
    [
      "unknown",
      safety({
        effectiveActivity: "unknown",
        decision: "block_activity_unknown",
      }),
    ],
    [
      "untrusted",
      safety({
        machine: { ...previewRecovery().machine, available: false },
        decision: "block_trust_unknown",
      }),
    ],
    ["native-incomplete", safety({ decision: "block_incomplete" })],
    [
      "incident",
      safety({
        readiness: "needs_acknowledgment",
        decision: "needs_acknowledgment",
      }),
    ],
    ["attention", safety({ decision: "future_native_blocker" })],
  ] as const)(
    "%s overrides ready, missing tools and updates; retains findings",
    (state, recovery) => {
      for (const r of [report(), report(["FAIL|Git not found"])]) {
        const i = fixture();
        i.validation = observed(r);
        i.tools = observed([update]);
        i.recovery = observed(recovery);
        const d = overviewDecision(i);
        expect(d.state).toBe(state);
        expect(d.details.checks).toHaveLength(1);
        expect(d.secondary).not.toContain("review-install");
        expect(d.secondary).not.toContain("review-repair");
        expect(d.secondary).not.toContain("review-updates");
        if (state === "active") expect(d.heading).toBe("Let setup finish");
      }
    },
  );
  it("missing or refreshing safety is not clear; never infers a setup incident", () => {
    const i = fixture();
    i.recovery = observed<RecoveryState>(null);
    expect(overviewDecision(i).reason).toBe("safety-unavailable");
    i.recovery = beginObservation(i.recovery, 1);
    expect(overviewDecision(i).state).toBe("checking");
  });
  it("a task owns the card while new blockers remain in Details and alternatives are suppressed", () => {
    for (const phase of [
      "review",
      "running",
      "verification",
      "result",
    ] as const) {
      const i = fixture();
      i.task = { phase, mode: "install" };
      i.recovery = observed(safety({ effectiveActivity: "active" }));
      const d = overviewDecision(i);
      expect(d.state).toBe("task");
      expect(d.primary).toBeNull();
      expect(d.secondary).toEqual([]);
      expect(d.details.safety?.effectiveActivity).toBe("active");
    }
  });
});

describe("request/operation freshness", () => {
  it("changed evidence invalidates a reviewed scope without repurposing its action", () => {
    const i = fixture();
    const binding = overviewReviewBinding(i);
    const action = overviewDecision(i).primary;
    i.recovery = beginObservation(i.recovery, i.epoch);
    expect(overviewReviewBinding(i)).not.toBe(binding);
    expect(action?.id).toBe("open-editor");
    expect(overviewDecision(i).primary).toBeNull();
  });
  it("maintenance failure remains available without inventing a recovery incident", () => {
    const i = fixture();
    i.maintenance = observed({
      status: "enabled",
      active: true,
      identifier: "fixture",
      frequency: "weekly",
      nextRun: null,
      lastRun: null,
      lastResult: "failure",
      resultDetail: "Fixture failure",
      catchUp: null,
      logFolder: "fixture",
      logsAvailable: true,
      note: "",
      observedAt: "2026-11-06T00:00:00Z",
      createdAt: null,
      lastSuccess: null,
    });
    const d = overviewDecision(i);
    expect(d.state).toBe("ready");
    expect(d.details.maintenance?.lastResult).toBe("failure");
  });
  it("late success cannot replace a newer failure or settle a request twice", () => {
    const old = beginObservation(observed(report()), 1);
    const fresh = beginObservation(old, 1);
    const failed = settleObservation(
      fresh,
      fresh,
      report(["FAIL|Unknown failure"]),
    );
    expect(settleObservation(failed, old, report())).toBe(failed);
    expect(settleObservation(failed, fresh, report())).toBe(failed);
  });
  it("a new operation epoch rejects pre-mutation validation, tools and safety", () => {
    const i = fixture();
    i.epoch = 2;
    expect(overviewDecision(i).state).toBe("untrusted");
    i.recovery = { ...i.recovery, epoch: 2 };
    expect(overviewDecision(i).state).toBe("unchecked");
    const before = i.validation;
    const after = beginObservation(before, 2);
    expect(after.value).toBeNull();
    expect(settleObservation(after, before, report())).toBe(after);
  });
  it("reopen starts from absent observations rather than a saved success", () => {
    const i = fixture();
    i.validation = observed<Report>(null);
    i.tools = observed<ToolRecord[]>(null);
    expect(overviewDecision(i).state).toBe("unchecked");
  });
});
