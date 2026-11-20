import { afterEach, expect, it, vi } from "../testing/unitApi";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import {
  PythonReadinessCard,
  completePythonObservation,
} from "./PythonReadinessCard";
import type { Report } from "./model";
const value = {
  schema: 1,
  component: "Python",
  requiredFamily: "3.14",
  status: "notFound",
  reason: "notDiscovered",
  version: null,
  executable: null,
  pipVersion: null,
};
const line = (v: unknown) =>
  `SKYVIEW_EVENT|runtime|Python|${JSON.stringify(v)}`;
function report(patch = {}, success = false): Report {
  return {
    code: success ? 0 : 1,
    success,
    validation_collected_at: Math.floor(Date.now() / 1000),
    lines: [
      line({ ...value, ...patch }),
      `SKYVIEW_EVENT|validation|${success ? "PASS" : "FAIL"}|Python: observed result`,
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
it("a complete supported search is distinct from an incomplete collection", () => {
  expect(completePythonObservation(report())).toEqual(value);
  for (const change of [
    { validation_collected_at: null },
    { code: 2 },
    { success: true },
    { lines: [line(value), "SKYVIEW_EVENT|validation|FAIL|Python: partial"] },
    {
      lines: [
        line(value),
        line(value),
        "SKYVIEW_EVENT|validation|FAIL|Python: result",
        "SKYVIEW_EVENT|summary|1|Done",
      ],
    },
  ])
    expect(completePythonObservation({ ...report(), ...change })).toBeNull();
});
it("wrong-family, inconsistent and capability-without-identity records cannot establish absence or a pass", () => {
  for (const change of [
    { requiredFamily: "3.15" },
    { status: "notFound", version: "3.14.9" },
    { status: "unusable", reason: "venvFailed" },
    { status: "incomplete", reason: "interpreterFailed" },
  ])
    expect(completePythonObservation(report(change))).toBeNull();
  const contradictory = report();
  contradictory.lines[1] = "SKYVIEW_EVENT|validation|PASS|Python: result";
  contradictory.lines[2] = "SKYVIEW_EVENT|summary|0|Done";
  contradictory.code = 0;
  contradictory.success = true;
  expect(completePythonObservation(contradictory)).toBeNull();
});
it("a verified required family produces no error card even when other versions exist", () => {
  render(
    <PythonReadinessCard
      {...props(
        report(
          {
            status: "passed",
            reason: "verified",
            version: "3.14.9",
            executable: "C:\\Python314\\python.exe",
            pipVersion: "25.3",
          },
          true,
        ),
      )}
    />,
  );
  expect(screen.queryByRole("region")).toBeNull();
});
it("absence explains the requirement without inferring a conflicting default version", () => {
  const options = props();
  render(<PythonReadinessCard {...options} />);
  expect(
    screen.getByRole("heading", {
      name: "Python 3.14 wasn’t found by this check",
    }),
  ).toBeTruthy();
  expect(
    screen.getByText(/Other Python versions can stay installed/),
  ).toBeTruthy();
  expect(screen.queryByText(/3.15|Restart/)).toBeNull();
  expect(options.onReview).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Review Python check" }));
  fireEvent.click(screen.getByRole("button", { name: "Check setup again" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Create Python support report" }),
  );
  expect(options.onReview).toHaveBeenCalledTimes(1);
  expect(options.onCheck).toHaveBeenCalledTimes(1);
  expect(options.onSupport).toHaveBeenCalledTimes(1);
});
it("timeouts remain incomplete and do not claim Python is absent", () => {
  render(
    <PythonReadinessCard
      {...props(report({ status: "incomplete", reason: "interpreterTimeout" }))}
    />,
  );
  expect(
    screen.getByRole("heading", { name: "The Python check took too long" }),
  ).toBeTruthy();
  expect(screen.getByText(/does not mean Python is missing/)).toBeTruthy();
  expect(
    screen.queryByRole("heading", {
      name: "Python 3.14 wasn’t found by this check",
    }),
  ).toBeNull();
});
it("capability failures show the verified family and the affected test capability", () => {
  const options = props(
    report({
      status: "unusable",
      reason: "venvFailed",
      version: "3.14.9",
      executable: "C:\\Python314\\python.exe",
    }),
  );
  render(<PythonReadinessCard {...options} />);
  expect(
    screen.getByRole("heading", {
      name: "Python’s test project could not be set up",
    }),
  ).toBeTruthy();
  expect(screen.getByText("3.14.9")).toBeTruthy();
  expect(screen.getByText("C:\\Python314\\python.exe")).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Install|Repair/ })).toBeNull();
});
it("malformed or legacy diagnostics offer review without interpreting arbitrary text as a new cause", () => {
  const r = report();
  r.lines[0] = line({ ...value, extra: "command" });
  render(<PythonReadinessCard {...props(r)} />);
  expect(
    screen.getByRole("heading", {
      name: "We couldn’t confirm the Python result",
    }),
  ).toBeTruthy();
  expect(
    screen.queryByRole("heading", {
      name: "Python 3.14 wasn’t found by this check",
    }),
  ).toBeNull();
});
it("rechecking keeps earlier findings labeled and disabled then removes the card after a verified pass", () => {
  const options = props();
  const view = render(<PythonReadinessCard {...options} />);
  view.rerender(
    <PythonReadinessCard {...options} report={null} pending busy />,
  );
  expect(screen.getByText(/earlier Python result stays below/)).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Check setup again",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  view.rerender(<PythonReadinessCard {...options} report={null} />);
  expect(screen.getByText(/These are earlier findings/)).toBeTruthy();
  view.rerender(
    <PythonReadinessCard
      {...props(
        report(
          {
            status: "passed",
            reason: "verified",
            version: "3.14.9",
            executable: "C:\\Python314\\python.exe",
            pipVersion: "25.3",
          },
          true,
        ),
      )}
    />,
  );
  expect(screen.queryByRole("region")).toBeNull();
});
