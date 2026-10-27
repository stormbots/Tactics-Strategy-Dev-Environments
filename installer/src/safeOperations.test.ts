import { describe, expect, it } from "vitest";
import {
  maintenanceHealth,
  overviewTone,
  preflightDecision,
  recoveryAction,
  type MaintenanceObservation,
  type OperationIncident,
} from "./safeOperations";

describe("preflight contract", () => {
  it("allows clean checks without acknowledgement", () =>
    expect(
      preflightDecision([
        { name: "Disk", status: "pass", detail: "Enough space" },
      ]),
    ).toMatchObject({
      blocked: false,
      needsAcknowledgement: false,
      canContinue: true,
      passed: 1,
    }));

  it("allows unavailable evidence only after one-attempt acknowledgement", () => {
    const checks = [
      {
        name: "Restart",
        status: "unavailable" as const,
        detail: "Could not inspect restart state",
      },
    ];
    expect(preflightDecision(checks)).toMatchObject({
      blocked: false,
      needsAcknowledgement: true,
      canContinue: false,
      unavailable: 1,
    });
    expect(preflightDecision(checks, true).canContinue).toBe(true);
  });

  it("never permits acknowledgement to bypass a known blocker", () =>
    expect(
      preflightDecision(
        [
          {
            name: "Package manager",
            status: "blocking",
            detail: "Another installation is running",
          },
        ],
        true,
      ),
    ).toMatchObject({ blocked: true, canContinue: false }));

  it("treats a failed or missing result set as unavailable rather than passed", () =>
    expect(preflightDecision(null)).toMatchObject({
      blocked: false,
      needsAcknowledgement: true,
      canContinue: false,
      unavailable: 1,
    }));
});

const incident: OperationIncident = {
  schema: 1,
  id: "6b65c565-7f96-4a21-b1ed-34d196930793",
  operation: "update",
  stage: "system",
  startedAt: 100,
  observedAt: 120,
  logPath: "update.log",
  acknowledged: false,
};

describe("recovery contract", () => {
  it("distinguishes active work from an interruption", () =>
    expect(recoveryAction(incident, true, "notRun")).toBe("wait"));
  it("requires validation before offering Repair", () => {
    expect(recoveryAction(incident, false, "notRun")).toBe("validate");
    expect(recoveryAction(incident, false, "repair")).toBe("repair");
  });
  it("resolves on passing validation or explicit acknowledgement", () => {
    expect(recoveryAction(incident, false, "passed")).toBe("resolved");
    expect(
      recoveryAction({ ...incident, acknowledged: true }, false, "notRun"),
    ).toBe("resolved");
  });
  it("routes unsafe recovery state to a mentor", () =>
    expect(recoveryAction(incident, false, "mentor")).toBe("mentor"));
});

const schedule = (overrides = {}): MaintenanceObservation => ({
  status: "enabled",
  active: true,
  identifier: "maintenance.timer",
  frequency: "Weekly",
  nextRun: null,
  lastRun: null,
  lastResult: "success",
  resultDetail: "Completed",
  catchUp: true,
  logFolder: "/var/log/example",
  logsAvailable: true,
  note: "",
  observedAt: "2026-10-26T12:00:00Z",
  createdAt: "2026-10-01T12:00:00Z",
  lastSuccess: "2026-10-20T12:00:00Z",
  ...overrides,
});

describe("maintenance health contract", () => {
  const now = Date.parse("2026-10-26T12:00:00Z");
  it("prioritizes running, missing, disabled and failed observations", () => {
    expect(maintenanceHealth(schedule({ lastResult: "running" }), now)).toBe(
      "running",
    );
    expect(maintenanceHealth(schedule({ status: "missing" }), now)).toBe(
      "missing",
    );
    expect(maintenanceHealth(schedule({ status: "disabled" }), now)).toBe(
      "disabled",
    );
    expect(maintenanceHealth(schedule({ lastResult: "failure" }), now)).toBe(
      "failed",
    );
  });
  it("uses the last successful run for the fourteen-day overdue rule", () => {
    expect(maintenanceHealth(schedule(), now)).toBe("healthy");
    expect(
      maintenanceHealth(schedule({ lastSuccess: "2026-10-01T12:00:00Z" }), now),
    ).toBe("overdue");
  });
  it("allows a known new schedule a fourteen-day grace period", () =>
    expect(
      maintenanceHealth(
        schedule({
          lastSuccess: null,
          createdAt: "2026-10-20T12:00:00Z",
          lastResult: "never",
        }),
        now,
      ),
    ).toBe("grace"));
  it("does not infer overdue when history and age are unavailable", () =>
    expect(
      maintenanceHealth(
        schedule({ lastSuccess: null, createdAt: null, lastResult: "never" }),
        now,
      ),
    ).toBe("unavailable"));
});

describe("Overview severity", () => {
  it("reserves red for readiness failure", () => {
    expect(overviewTone(true, false, "healthy")).toBe("red");
    expect(overviewTone(false, false, "failed")).toBe("yellow");
  });
  it("keeps healthy readiness and maintenance green", () => {
    expect(overviewTone(false, false, "healthy")).toBe("green");
    expect(overviewTone(false, false, "grace")).toBe("green");
  });
});
