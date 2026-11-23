import { afterEach, expect, it, vi } from "../testing/unitApi";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { nodeObservation, completeNodeObservation } from "./nodeObservation";
import { NodeReadinessCard } from "./NodeReadinessCard";
import type { Report } from "./model";
const missing = {
  schema: 1,
  component: "Node.js",
  requiredFamily: "24",
  status: "notFound",
  reason: "notDiscovered",
  version: null,
  executable: null,
  npmVersion: null,
  npmCli: null,
  maintenanceEligibility: "notEvaluated",
};
const passed = {
  ...missing,
  status: "passed",
  reason: "verified",
  version: "24.19.0",
  executable: "C:\\Node24\\node.exe",
  npmVersion: "11.9.0",
  npmCli: "C:\\Node24\\node_modules\\npm\\bin\\npm-cli.js",
};
const line = (v: unknown) =>
  `SKYVIEW_EVENT|runtime|Node.js|${JSON.stringify(v)}`;
function report(value: unknown = missing, success = false): Report {
  return {
    code: success ? 0 : 1,
    success,
    validation_collected_at: Math.floor(Date.now() / 1000),
    lines: [
      line(value),
      `SKYVIEW_EVENT|validation|${success ? "PASS" : "FAIL"}|Node.js: observed result`,
      `SKYVIEW_EVENT|summary|${success ? 0 : 1}|Done`,
    ],
    log_path: "sample",
    platform: { label: "Windows 11", supported: true },
  };
}
function props(r: Report | null = report()) {
  return {
    report: r,
    pending: false,
    busy: false,
    onReview: vi.fn(),
    onCheck: vi.fn(),
    onSupport: vi.fn(),
  };
}
afterEach(cleanup);
it("accepts verified Windows and Linux pairs without converting recognition to maintenance permission", () => {
  expect(nodeObservation(line(passed))).toEqual(passed);
  const linux = {
    ...passed,
    executable: "/opt/node24/bin/node",
    npmCli: "/opt/node24/lib/node_modules/npm/bin/npm-cli.js",
  };
  expect(nodeObservation(line(linux))).toEqual(linux);
  const system = {
    ...passed,
    executable: "/usr/bin/node",
    npmCli: "/usr/share/nodejs/npm/bin/npm-cli.js",
  };
  expect(nodeObservation(line(system))).toEqual(system);
  expect(
    completeNodeObservation(report(passed, true))?.maintenanceEligibility,
  ).toBe("notEvaluated");
});
it("rejects wrong-family, unrelated npm, unsafe paths, extra fields and invented ownership", () => {
  for (const change of [
    { version: "26.1.0" },
    { npmCli: "C:\\OtherNode\\node_modules\\npm\\bin\\npm-cli.js" },
    { executable: "node" },
    { npmCli: "C:\\Node24\\npm\ncli.js" },
    { maintenanceEligibility: "approved" },
    { permit: true },
    { npmVersion: null },
    { reason: "npmFailed" },
  ])
    expect(nodeObservation(line({ ...passed, ...change }))).toBeNull();
  expect(nodeObservation("SKYVIEW_EVENT|runtime|Node.js|{bad json")).toBeNull();
  expect(
    nodeObservation(line({ ...passed, npmCli: "C:\\" + "x".repeat(17000) })),
  ).toBeNull();
});
it("requires one consistent record, paired check and complete collection", () => {
  expect(completeNodeObservation(report())).toEqual(missing);
  for (const change of [
    { validation_collected_at: null },
    { success: true },
    { code: 2 },
    {
      lines: [line(missing), "SKYVIEW_EVENT|validation|FAIL|Node.js: partial"],
    },
    {
      lines: [
        line(missing),
        line(missing),
        "SKYVIEW_EVENT|validation|FAIL|Node.js: observed result",
        "SKYVIEW_EVENT|summary|1|Done",
      ],
    },
  ])
    expect(completeNodeObservation({ ...report(), ...change })).toBeNull();
  expect(completeNodeObservation(report(passed, false))).toBeNull();
});
it("negative npm and incomplete results preserve their distinctions without claiming absence", () => {
  const failed = {
    ...missing,
    status: "unusable",
    reason: "npmFailed",
    version: "24.19.0",
    executable: "C:\\Node24\\node.exe",
  };
  expect(nodeObservation(line(failed))).toEqual(failed);
  expect(
    nodeObservation(
      line({ ...failed, status: "incomplete", reason: "npmTimeout" }),
    )?.status,
  ).toBe("incomplete");
  expect(
    nodeObservation(line({ ...failed, version: null, executable: null })),
  ).toBeNull();
  expect(nodeObservation(line({ ...missing, status: "unusable" }))).toBeNull();
  render(<NodeReadinessCard {...props(report(failed))} />);
  expect(
    screen.getByRole("heading", {
      name: "Node.js 24 was found, but its npm check failed",
    }),
  ).toBeTruthy();
  expect(
    screen.getByText(
      /does not show that another installed Node.js version caused/,
    ),
  ).toBeTruthy();
});
it("a verified pair hides the card while another runtime may remain installed", () => {
  render(<NodeReadinessCard {...props(report(passed, true))} />);
  expect(screen.queryByRole("region")).toBeNull();
});
it("review, full setup check and support are explicit read-only callback paths", () => {
  const options = props(),
    before = JSON.stringify(options.report);
  render(<NodeReadinessCard {...options} />);
  expect(
    screen.getByText(/does not give SDE permission to replace/),
  ).toBeTruthy();
  expect(options.onCheck).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Review Node.js/npm check" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Check setup again" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Create Node.js support report" }),
  );
  expect(options.onReview).toHaveBeenCalledTimes(1);
  expect(options.onCheck).toHaveBeenCalledTimes(1);
  expect(options.onSupport).toHaveBeenCalledTimes(1);
  expect(JSON.stringify(options.report)).toBe(before);
  expect(
    screen.queryByRole("button", { name: /Install|Repair|Remove/ }),
  ).toBeNull();
});
it("earlier findings remain labeled and disabled during a failed follow-up then clear on a verified pair", () => {
  const options = props(),
    view = render(<NodeReadinessCard {...options} />);
  view.rerender(<NodeReadinessCard {...options} report={null} pending busy />);
  expect(
    screen.getByText(/earlier Node.js\/npm result stays below/),
  ).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Check setup again",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  view.rerender(<NodeReadinessCard {...options} report={null} />);
  expect(screen.getByText(/These are earlier findings/)).toBeTruthy();
  view.rerender(<NodeReadinessCard {...props(report(passed, true))} />);
  expect(screen.queryByRole("region")).toBeNull();
});
it("unknown legacy diagnostics stay uncertain instead of becoming a missing-runtime claim", () => {
  const r = report();
  r.lines[0] = line({ ...missing, reason: "unsafe-guess" });
  render(<NodeReadinessCard {...props(r)} />);
  expect(
    screen.getByRole("heading", {
      name: "We couldn’t confirm the Node.js/npm result",
    }),
  ).toBeTruthy();
  expect(
    screen.queryByRole("heading", {
      name: "Node.js 24 wasn’t found by this check",
    }),
  ).toBeNull();
});
