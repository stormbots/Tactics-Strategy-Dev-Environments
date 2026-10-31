import { expect, it, vi } from "vitest";
import { supportHtml, supportSnapshot } from "./supportReport";

it("produces a self-contained script-free report and omits logs by default", () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-26T12:00:00Z"));
  const snapshot = supportSnapshot({
    context: { deviceName: "STUDENT<&>", logs: "secret path" },
    platform: "Linux Mint 22.3 · x86_64",
    applicationVersion: "1.2.1",
    checks: [{ status: "FAIL", message: "Git <missing>" }],
    validationComplete: true,
    validationCollectedAt: 1792929600,
    incident: null,
    maintenance: null,
    includeLogs: false,
  });
  const html = supportHtml(snapshot);
  expect(snapshot.logs).toEqual({
    included: false,
    content: null,
    omission: "Logs were not included by the student.",
  });
  expect(html).toContain("STUDENT&lt;&amp;&gt;");
  expect(html).toContain("Git &lt;missing&gt;");
  expect(html).toContain("Outcome: Needs attention");
  expect(html).not.toContain("secret path");
  expect(html).not.toMatch(/<script|https?:\/\//i);
  expect(snapshot.validation.collectedAt).toBe(
    new Date(1792929600 * 1000).toISOString(),
  );
  expect(snapshot.validation.collectedAt).not.toBe(snapshot.createdAt);
  vi.useRealTimers();
});

it("does not substitute report time for missing Validation time, even after a pass", () => {
  const input = {
    context: { deviceName: "TEST", logs: null },
    platform: "Windows 11",
    applicationVersion: "1",
    checks: [{ status: "PASS" as const, message: "Git" }],
    validationComplete: true,
    incident: null,
    maintenance: null,
    includeLogs: false,
  };
  for (const validationCollectedAt of [
    undefined,
    null,
    0,
    NaN,
    Infinity,
    -1,
    1.5,
    1e15,
  ]) {
    expect(
      supportSnapshot({ ...input, validationCollectedAt }).validation
        .collectedAt,
    ).toBeNull();
  }
  expect(
    supportSnapshot({ ...input, checks: [], validationCollectedAt: 50 })
      .validation.collectedAt,
  ).toBeNull();
  const failed = supportSnapshot({
    ...input,
    validationComplete: false,
    checks: [{ status: "FAIL", message: "Git" }],
    validationCollectedAt: 50,
  });
  expect(failed.validation.collectedAt).toBe(new Date(50000).toISOString());
});

it("includes only explicitly requested log content", () => {
  const snapshot = supportSnapshot({
    context: { deviceName: "TEST", logs: "line <one>" },
    platform: "Windows 11",
    applicationVersion: "1",
    checks: [],
    validationComplete: false,
    incident: null,
    maintenance: null,
    includeLogs: true,
  });
  expect(supportHtml(snapshot)).toContain("line &lt;one&gt;");
});
