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
  vi.useRealTimers();
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
