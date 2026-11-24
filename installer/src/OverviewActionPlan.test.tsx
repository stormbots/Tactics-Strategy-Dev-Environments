import { afterEach, expect, it, vi } from "../testing/unitApi";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { OverviewActionPlan, overviewFindingLinks } from "./OverviewActionPlan";
import { previewRecovery } from "./recovery";
import { inspectSchedule } from "./bridge";
import type { Report } from "./model";
const record = {
  schema: 1,
  component: "Python",
  requiredFamily: "3.14",
  status: "notFound",
  reason: "notDiscovered",
  version: null,
  executable: null,
  pipVersion: null,
};
function report(passed = false): Report {
  const value = passed
    ? {
        ...record,
        status: "passed",
        reason: "verified",
        version: "3.14.9",
        executable: "C:\\Python314\\python.exe",
        pipVersion: "25.3",
      }
    : record;
  return {
    code: passed ? 0 : 1,
    success: passed,
    validation_collected_at: Math.floor(Date.now() / 1000),
    lines: [
      `SKYVIEW_EVENT|runtime|Python|${JSON.stringify(value)}`,
      `SKYVIEW_EVENT|validation|${passed ? "PASS" : "FAIL"}|Python: checked`,
      `SKYVIEW_EVENT|summary|${passed ? 0 : 1}|Done`,
    ],
    log_path: "test",
    platform: { label: "Windows 11", supported: true },
  };
}
async function options() {
  return {
    report: report(),
    accessReport: null,
    recovery: previewRecovery(),
    safetyError: "",
    maintenance: await inspectSchedule(),
    pending: false,
  };
}
afterEach(cleanup);
it("lists one Python finding without inventing a safety or maintenance problem", async () => {
  const links = overviewFindingLinks(await options());
  expect(links).toEqual([
    {
      heading: "python-readiness-heading",
      label: "Review the Python requirement",
    },
  ]);
});
it("a passing runtime removes only its item while unresolved safety stays", async () => {
  const value = await options();
  value.recovery.readiness = "blocked";
  value.recovery.effectiveActivity = "unknown";
  expect(overviewFindingLinks(value).map((x) => x.heading)).toEqual([
    "change-safety-overview-heading",
    "python-readiness-heading",
  ]);
  value.report = report(true);
  expect(overviewFindingLinks(value).map((x) => x.heading)).toEqual([
    "change-safety-overview-heading",
  ]);
  expect(value.recovery.readiness).toBe("blocked");
});
it("Node and Python use their own cards without combining their causes", async () => {
  const value = await options();
  value.report.lines.unshift(
    `SKYVIEW_EVENT|runtime|Node.js|${JSON.stringify({ schema: 1, component: "Node.js", requiredFamily: "24", status: "notFound", reason: "notDiscovered", version: null, executable: null, npmVersion: null, npmCli: null, maintenanceEligibility: "notEvaluated" })}`,
  );
  value.report.lines.splice(
    -1,
    0,
    "SKYVIEW_EVENT|validation|FAIL|Node.js: checked",
  );
  value.report.lines[value.report.lines.length - 1] =
    "SKYVIEW_EVENT|summary|2|Done";
  expect(overviewFindingLinks(value).map((x) => x.heading)).toEqual([
    "python-readiness-heading",
    "node-readiness-heading",
  ]);
});
it("keeps supported fallback guidance for pending, partial, legacy and unrepresented failures", async () => {
  const value = await options();
  expect(overviewFindingLinks({ ...value, pending: true })).toEqual([]);
  expect(overviewFindingLinks({ ...value, report: null })).toEqual([]);
  expect(
    overviewFindingLinks({
      ...value,
      report: { ...value.report, lines: value.report.lines.slice(0, -1) },
    }),
  ).toEqual([]);
  expect(
    overviewFindingLinks({
      ...value,
      report: { ...value.report, lines: value.report.lines.slice(1) },
    }),
  ).toEqual([]);
  value.report.lines.splice(
    -1,
    0,
    "SKYVIEW_EVENT|validation|FAIL|Git: not found",
  );
  value.report.lines[value.report.lines.length - 1] =
    "SKYVIEW_EVENT|summary|2|Done";
  expect(overviewFindingLinks(value)).toEqual([]);
});
it("links retained confirmed editor denial to its own access card", async () => {
  const value = await options();
  const observation = {
    schema: 1,
    component: "VSCodium",
    scope: "standardUserFile",
    path: "/home/student/.config/VSCodium/User/settings.json",
    status: "unreadable",
    reason: "accessDenied",
    recommendations: [],
  };
  const access = {
    ...report(true),
    lines: [
      `SKYVIEW_EVENT|preferences|VSCodium|${JSON.stringify(observation)}`,
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      "SKYVIEW_EVENT|summary|0|Done",
    ],
  };
  expect(
    overviewFindingLinks({ ...value, accessReport: access }).map(
      (x) => x.heading,
    ),
  ).toEqual(["python-readiness-heading", "editor-access-overview-heading"]);
  expect(
    overviewFindingLinks({
      ...value,
      accessReport: { ...access, lines: [] },
    }).map((x) => x.heading),
  ).toEqual(["python-readiness-heading"]);
});
it("maintenance navigation describes a review item without claiming disabled tools are broken", async () => {
  const value = await options();
  value.report = report(true);
  value.maintenance.status = "disabled";
  expect(overviewFindingLinks(value)).toEqual([
    {
      heading: "maintenance-overview-heading",
      label: "View weekly maintenance details",
    },
  ]);
  expect(value.maintenance.status).toBe("disabled");
  value.maintenance.status = "enabled";
  expect(overviewFindingLinks(value)).toEqual([]);
});
it("links move focus to the current heading and never perform a setup action", () => {
  const scroll = vi.fn();
  render(
    <>
      <OverviewActionPlan
        items={[
          {
            heading: "python-readiness-heading",
            label: "Review the Python requirement",
          },
        ]}
        busy={false}
      />
      <h2 id="python-readiness-heading" tabIndex={-1}>
        Python result
      </h2>
    </>,
  );
  const heading = screen.getByRole("heading", { name: "Python result" });
  heading.scrollIntoView = scroll;
  expect(scroll).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Review the Python requirement" }),
  );
  expect(document.activeElement).toBe(heading);
  expect(scroll).toHaveBeenCalledWith({ block: "center", behavior: "auto" });
  expect(
    screen.queryByRole("button", { name: /Install|Repair|Acknowledge/ }),
  ).toBeNull();
});
it("busy links are disabled and a removed target cannot start another action", () => {
  const items = [{ heading: "gone", label: "Review change safety" }];
  const view = render(<OverviewActionPlan items={items} busy />);
  expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(true);
  view.rerender(<OverviewActionPlan items={items} busy={false} />);
  fireEvent.click(screen.getByRole("button"));
  expect(screen.getByRole("list", { name: "Items to review" })).toBeTruthy();
});
