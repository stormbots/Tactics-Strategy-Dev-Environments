import { afterEach, expect, it, vi } from "../testing/unitApi";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { EditorAccessOverviewCard } from "./EditorAccessOverviewCard";
import { editorAccessMessage } from "./editorPreferences";
import type { Report } from "./model";
const path = "/home/student/.config/VSCodium/User/settings.json";
function report(patch = {}): Report {
  const value = {
    schema: 1,
    component: "VSCodium",
    scope: "standardUserFile",
    path,
    status: "unreadable",
    reason: "accessDenied",
    recommendations: [],
    ...patch,
  };
  return {
    code: 0,
    success: true,
    validation_collected_at: Math.floor(Date.now() / 1000),
    lines: [
      `SKYVIEW_EVENT|preferences|VSCodium|${JSON.stringify(value)}`,
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      `SKYVIEW_EVENT|validation|WARNING|${editorAccessMessage}`,
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "sample",
    platform: { label: "Linux Mint 22.3", supported: true },
  };
}
function props(r: Report | null = report()) {
  return {
    report: r,
    stale: false,
    busy: false,
    onCheck: vi.fn(),
    onSupport: vi.fn(),
  };
}
afterEach(cleanup);
it("Overview names VSCodium and confirms access denial without labeling settings broken", () => {
  render(<EditorAccessOverviewCard {...props()} />);
  expect(
    screen.getByRole("heading", {
      name: "We couldn’t finish checking VSCodium",
    }),
  ).toBeTruthy();
  expect(screen.getByText(editorAccessMessage)).toBeTruthy();
  expect(screen.getByText("Check incomplete")).toBeTruthy();
  expect(screen.queryByText(/malformed|Python|Separate finding/)).toBeNull();
});
it("opening review starts no check and reveals normal-account guidance", () => {
  const options = props();
  render(<EditorAccessOverviewCard {...options} />);
  fireEvent.click(
    screen.getByRole("button", { name: "Review access problem" }),
  );
  expect(
    screen.getByRole("region", { name: "VSCodium access review" }),
  ).toBeTruthy();
  expect(screen.getByText(path)).toBeTruthy();
  expect(screen.getByText(/Keep SDE open as your/)).toBeTruthy();
  expect(options.onCheck).not.toHaveBeenCalled();
  expect(options.onSupport).not.toHaveBeenCalled();
});
it("check and support callbacks require explicit actions and do not alter the report", () => {
  const options = props(),
    before = JSON.stringify(options.report);
  render(<EditorAccessOverviewCard {...options} />);
  fireEvent.click(
    screen.getByRole("button", { name: "Review access problem" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Check VSCodium again" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Create access support report" }),
  );
  expect(options.onCheck).toHaveBeenCalledTimes(1);
  expect(options.onSupport).toHaveBeenCalledTimes(1);
  expect(JSON.stringify(options.report)).toBe(before);
});
it("earlier evidence and an expanded review stay in place through busy and failed collection", () => {
  const options = props(),
    view = render(<EditorAccessOverviewCard {...options} />);
  fireEvent.click(
    screen.getByRole("button", { name: "Review access problem" }),
  );
  view.rerender(<EditorAccessOverviewCard {...options} stale busy />);
  expect(screen.getByText(/earlier access finding stays below/)).toBeTruthy();
  expect(
    (screen.getByRole("button", { name: "Checking…" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  view.rerender(<EditorAccessOverviewCard {...options} stale />);
  expect(screen.getByText(/These are earlier findings/)).toBeTruthy();
  expect(
    screen.getByRole("region", { name: "VSCodium access review" }),
  ).toBeTruthy();
});
it("a complete defaults result removes the access card without claiming settings were repaired", () => {
  const options = props(),
    view = render(<EditorAccessOverviewCard {...options} />);
  view.rerender(
    <EditorAccessOverviewCard
      {...props(report({ status: "missing", reason: "defaults" }))}
    />,
  );
  expect(screen.queryByRole("heading")).toBeNull();
  expect(options.onCheck).not.toHaveBeenCalled();
});
it("generic read failure and incomplete collection cannot be called permission denial", () => {
  const view = render(
    <EditorAccessOverviewCard {...props(report({ reason: "readFailed" }))} />,
  );
  expect(screen.queryByRole("heading")).toBeNull();
  const partial = report();
  partial.lines.pop();
  view.rerender(<EditorAccessOverviewCard {...props(partial)} />);
  expect(screen.queryByRole("heading")).toBeNull();
  view.rerender(<EditorAccessOverviewCard {...props(null)} />);
  expect(screen.queryByRole("heading")).toBeNull();
});
it("a changed confirmed path requires opening a new review and never becomes a native path argument", () => {
  const options = props(),
    view = render(<EditorAccessOverviewCard {...options} />);
  fireEvent.click(
    screen.getByRole("button", { name: "Review access problem" }),
  );
  view.rerender(
    <EditorAccessOverviewCard
      {...props(report({ path: "/home/other/settings.json" }))}
    />,
  );
  expect(
    screen.queryByRole("region", { name: "VSCodium access review" }),
  ).toBeNull();
  expect(options.onCheck).not.toHaveBeenCalled();
  expect(options.onSupport).not.toHaveBeenCalled();
});
it("malformed metadata cannot manufacture an access finding", () => {
  render(
    <EditorAccessOverviewCard
      {...props(report({ command: "change permissions" }))}
    />,
  );
  expect(screen.queryByRole("heading")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});
