import { afterEach, expect, it, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import axe from "axe-core";
import App from "./App";
import { inspect, operate, inspectSchedule, open } from "./bridge";
vi.mock("./bridge", () => ({
  native: false,
  appVersion: "1.2.0",
  inspectSchedule: vi.fn(async () => ({
    status: "enabled",
    active: true,
    identifier: "Test timer",
    frequency: "Sunday at 03:00",
    nextRun: null,
    lastRun: null,
    lastResult: "never",
    resultDetail: "No history",
    catchUp: true,
    logFolder: "/logs",
    logsAvailable: false,
    note: "",
  })),
  inspect: vi.fn(async () => ({
    code: 0,
    success: true,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "Preview",
    platform: { label: "Windows 11 x64", supported: true },
  })),
  operate: vi.fn(async () => ({
    code: 1,
    success: false,
    lines: [
      "SKYVIEW_EVENT|error|test|A test package failed",
      "SKYVIEW_EVENT|summary|1|Failed",
    ],
    log_path: "test.log",
    platform: { label: "Windows 11", supported: true },
  })),
  open: vi.fn(async () => {}),
}));
afterEach(cleanup);
it("shows a prominent busy indicator while startup validation is pending", async () => {
  vi.mocked(inspect).mockReturnValueOnce(new Promise(() => {}));
  const { container } = render(<App />);
  expect(
    screen
      .getByRole("region", { name: "Workstation check" })
      .getAttribute("aria-busy"),
  ).toBe("true");
  expect(
    screen.getByRole("heading", { name: "Checking your workstation…" }),
  ).toBeTruthy();
  expect(container.querySelector(".checking-panel .spinner")).toBeTruthy();
  expect(
    (
      await axe.run(container, {
        rules: { "color-contrast": { enabled: false } },
      })
    ).violations,
  ).toEqual([]);
});
it("puts streaming installation output beside progress without expanding details", async () => {
  vi.mocked(operate).mockImplementationOnce(
    async (_mode, _id, _updates, emit) => {
      emit("Installing Git…");
      return new Promise(() => {});
    },
  );
  render(<App />);
  await screen.findByRole("heading", { name: "Ready" });
  fireEvent.click(
    screen.getByRole("button", { name: "Install Development Environment" }),
  );
  expect(
    screen.getByRole("region", { name: "Provisioning log" }).textContent,
  ).toBe("Installing Git…");
  expect(screen.getByRole("heading", { name: "Live details" })).toBeTruthy();
  expect(screen.queryByText("Show details")).toBeNull();
  expect(document.activeElement?.getAttribute("role")).toBe("status");
});
it("shows a keyboard-accessible UI with no detected axe violations", async () => {
  const { container } = render(<App />);
  await screen.findByRole("heading", { name: "Ready" });
  const results = await axe.run(container, {
    rules: { "color-contrast": { enabled: false } },
  });
  expect(results.violations).toEqual([]);
  expect(
    screen.getByRole("button", { name: "Install Development Environment" }),
  ).toBeTruthy();
});
it("shows graphical validation and labels optional statuses", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "Ready" });
  fireEvent.click(screen.getByRole("button", { name: "Validation" }));
  expect(screen.getByRole("table")).toBeTruthy();
  expect(screen.getByText("PASS")).toBeTruthy();
});
it("offers a retry and focuses the result after a child failure", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "Ready" });
  fireEvent.click(
    screen.getByRole("button", { name: "Install Development Environment" }),
  );
  await screen.findByText("A test package failed");
  expect(screen.getByRole("button", { name: "Retry install" })).toBeTruthy();
  await waitFor(() =>
    expect(document.activeElement?.textContent).toBe(
      "Your environment needs attention.",
    ),
  );
});
it("shows updates separately from successful validation, including both versions", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    code: 0,
    success: true,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.43.0",
      'SKYVIEW_EVENT|tool|Git|{"tool":"Git","installedVersion":"2.43.0","availableVersion":"2.44.0","updateAvailable":true,"updateCheck":"current"}',
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "",
    platform: { label: "Windows 11", supported: true },
  });
  render(<App />);
  await screen.findByRole("heading", {
    name: "Updates available",
  });
  expect(screen.getByText("Update available · 2.43.0 → 2.44.0")).toBeTruthy();
  expect(screen.getByText(/need attention/).textContent).toContain("0");
  expect(
    screen.getByText(/update available$/, { selector: ".update-count" })
      .textContent,
  ).toContain("1");
});
it("reads and refreshes Schedule, displays never-run history, and recovers from errors", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "Ready" });
  fireEvent.click(screen.getByRole("button", { name: "Schedule" }));
  await screen.findByText("Test timer");
  expect(screen.getByRole("heading", { name: "Maintenance schedule" })).toBe(
    document.activeElement,
  );
  expect(screen.getAllByText("Never run").length).toBe(2);
  expect(screen.queryByText("Show details")).toBeNull();
  vi.mocked(inspectSchedule).mockRejectedValueOnce(
    new Error("Test access denied"),
  );
  fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
  await screen.findByText(/Schedule unavailable.*Test access denied/);
  expect(screen.queryByText("Test timer")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
  await screen.findByText("Test timer");
  expect(vi.mocked(open)).not.toHaveBeenCalled();
});
it("shows the version and approved external links on About", async () => {
  const { container } = render(<App />);
  await screen.findByRole("heading", { name: "Ready" });
  fireEvent.click(screen.getByRole("button", { name: "About" }));
  expect(screen.getByText("1.2.0", { selector: "dd" })).toBeTruthy();
  expect(
    screen
      .getByRole("link", { name: /View the project on GitHub/ })
      .getAttribute("href"),
  ).toBe("https://github.com/stormbots/Tactics-Strategy-Dev-Environments");
  expect(
    screen
      .getByRole("link", { name: /Visit Skyview Robotics/ })
      .getAttribute("rel"),
  ).toContain("noopener");
  expect(
    (
      await axe.run(container, {
        rules: { "color-contrast": { enabled: false } },
      })
    ).violations,
  ).toEqual([]);
});
