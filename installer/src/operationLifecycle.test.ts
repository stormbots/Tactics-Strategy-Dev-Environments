import { describe, expect, it } from "vitest";
import {
  operationResult,
  reviewFingerprint,
  checkingResult,
  type OperationOutcome,
  type ReviewContext,
} from "./operationLifecycle";
import type { Report } from "./model";
import { previewRecovery } from "./recovery";

const report = (mutation_outcome: Report["mutation_outcome"]): Report => ({
  mutation_outcome,
  code: 0,
  success: true,
  validation_collected_at: 100,
  lines: [
    "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
    "SKYVIEW_EVENT|summary|0|Done",
  ],
  log_path: "fixture",
  platform: { supported: true, label: "Fixture" },
});
const outcome = (
  r: Report | null,
  mode: OperationOutcome["mode"] = "install",
): OperationOutcome => ({ mode, report: r, error: "", before: [] });

describe("native operation outcomes", () => {
  it("only native evidence establishes a non-start", () => {
    expect(operationResult(outcome(report("not_started")))?.kind).toBe(
      "not-started",
    );
    for (const code of [0, 1, 75, 126, 127, 1223]) {
      const r = { ...report(undefined), code, success: code === 0 };
      expect(
        operationResult({
          ...outcome(r),
          error: "Administrator approval was cancelled",
        })?.kind,
      ).toBe("uncertain");
    }
  });
  it.each([undefined, "uncertain", "not_requested"] as const)(
    "%s never becomes completed from passed checks",
    (flag) => {
      const r = operationResult(outcome(report(flag)));
      expect(r?.kind).toBe("uncertain");
      expect(r?.body).toContain("not a confirmed cancellation or rollback");
    },
  );
  it("a transport failure remains uncertain and keeps the actual diagnostic", () => {
    const r = operationResult({
      ...outcome(null, "update"),
      error: "Download failed: network unavailable",
    });
    expect(r?.kind).toBe("uncertain");
    expect(r?.body).toContain("Some tools may already have changed");
    expect(r?.error).toBe("Download failed: network unavailable");
    expect(r?.next).toBe("check");
  });
  it("known completion with missing verification recommends a check, never another mutation", () => {
    for (const r of [
      { ...report("completed"), lines: [] },
      { ...report("completed"), validation_collected_at: null },
      { ...report("completed"), code: 1, success: false },
    ]) {
      const result = operationResult(outcome(r));
      expect(result?.kind).toBe("verification-incomplete");
      expect(result?.next).toBe("check");
    }
  });
  it("keeps an unresolved repair and its uncertainty explicit without retrying", () => {
    const failure = {
      status: "FAIL" as const,
      message: "Python 3.14 not found",
    };
    const r = operationResult({
      ...outcome(
        {
          ...report("uncertain"),
          code: 1,
          success: false,
          lines: [
            "SKYVIEW_EVENT|validation|FAIL|Python 3.14 not found",
            "SKYVIEW_EVENT|summary|1|Failed",
          ],
        },
        "repair",
      ),
      before: [failure],
    });
    expect(r?.heading).toBe("The repair has not confirmed a resolution");
    expect(r?.body).toContain("A reported finding still needs attention");
    expect(r?.kind).toBe("uncertain");
  });
  it("native completion does not turn failed required checks into Ready", () => {
    const r = operationResult(
      outcome({
        ...report("completed"),
        code: 1,
        success: false,
        lines: [
          "SKYVIEW_EVENT|validation|FAIL|Unsupported finding",
          "SKYVIEW_EVENT|summary|1|Failed",
        ],
      }),
    );
    expect(r?.kind).toBe("unresolved");
    expect(r?.next).toBe("review-issue");
  });
  it("verified completion returns to the shared recommendation, not a forced editor action", () => {
    expect(operationResult(outcome(report("completed"), "update"))).toBeNull();
    expect(operationResult(null)).toBeNull();
  });
  it("shows verification only from the existing reported phase", () => {
    expect(checkingResult("validate", "Waiting")).toBe(true);
    expect(
      checkingResult("install", "Validating your development environment"),
    ).toBe(true);
    expect(checkingResult("install", "Installing package 95")).toBe(false);
  });
});

describe("review binding", () => {
  const context = (): ReviewContext => ({
    validationRequest: 1,
    checkUpdates: false,
    platformSupported: true,
    tools: [
      {
        tool: "Git",
        installedVersion: "2.49",
        availableVersion: "2.50",
        updateAvailable: true,
        updateCheck: "current",
      },
    ],
    recovery: previewRecovery(),
  });
  it("equivalent fresh native observations do not cause repeated confirmation", () => {
    const a = context(),
      b = context();
    b.recovery!.nativeSafety.observedAt++;
    b.recovery!.user.observedAt++;
    expect(reviewFingerprint("install", a)).toBe(
      reviewFingerprint("install", b),
    );
  });
  it("versions, options, platform, validation and incident identity invalidate a review", () => {
    const original = reviewFingerprint("update", context());
    const changes: Array<(c: ReviewContext) => void> = [
      (c) => {
        c.checkUpdates = true;
      },
      (c) => {
        c.validationRequest++;
      },
      (c) => {
        c.platformSupported = false;
      },
      (c) => {
        c.tools[0].availableVersion = "2.51";
      },
      (c) => {
        c.recovery!.machine.incidentId = "new-source";
      },
      (c) => {
        c.recovery!.user.viewToken = "new-generation";
      },
      (c) => {
        c.recovery!.effectiveActivity = "active";
      },
    ];
    for (const change of changes) {
      const c = context();
      change(c);
      expect(reviewFingerprint("update", c)).not.toBe(original);
    }
    expect(reviewFingerprint("repair", context())).not.toBe(original);
  });
});
