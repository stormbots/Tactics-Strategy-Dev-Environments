import { beforeEach, afterEach, expect, it, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import axe from "axe-core";
import App from "./App";
import {
  acknowledgeOperationIncident,
  inspect,
  inspectOperationIncident,
  operate,
  inspectSchedule,
  open,
} from "./bridge";
vi.mock("./bridge", () => ({
  native: false,
  appVersion: "1.2.0",
  inspectSelfUpdate: vi.fn(async () => ({
    paused: true,
    policyChangedAt: null,
    outcome: "unavailable",
    phase: "unknown",
    checkedAt: null,
    completedAt: null,
    applicationVersion: null,
    candidateVersion: null,
    maintenanceEngineVersion: null,
    appliedBaselineVersion: null,
    toolExit: null,
    nativeExit: null,
    rebootRequired: false,
    recoveryAvailable: false,
    logReference: null,
    logFolder: "/protected/logs",
    coordination: "busy",
    action: "No completed attempt recorded.",
  })),
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
    observedAt: "2026-10-26T12:00:00Z",
    createdAt: null,
    lastSuccess: null,
  })),
  inspectOperationIncident: vi.fn(async () => ({
    incident: null,
    backendActive: false,
  })),
  acknowledgeOperationIncident: vi.fn(async () => {}),
  supportContext: vi.fn(async (includeLogs: boolean) => ({
    deviceName: "TEST-LAPTOP",
    logs: includeLogs ? "test log" : null,
  })),
  saveSupportReport: vi.fn(async () => "/downloads/support.html"),
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
beforeEach(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  );
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("keeps an interrupted operation unacknowledged after successful validation", async () => {
  const acknowledgmentsBefore = vi.mocked(acknowledgeOperationIncident).mock.calls.length;
  const id = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
  vi.mocked(inspectOperationIncident).mockResolvedValueOnce({
    backendActive: false,
    incident: {
      schema: 1,
      id,
      operation: "update",
      stage: "system",
      startedAt: 1,
      observedAt: 2,
      logPath: "/logs/update.log",
      acknowledged: false,
    },
  });
  vi.mocked(operate).mockResolvedValueOnce({
    code: 0,
    success: true,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "validate.log",
    platform: { label: "Windows 11 x64", supported: true },
  });
  render(<App />);
  await screen.findByRole("heading", {
    name: "A previous operation was interrupted",
  });
  fireEvent.click(screen.getByRole("button", { name: "Run validation" }));
  await screen.findByRole("heading", { name: "Validation passed." });
  expect(vi.mocked(acknowledgeOperationIncident).mock.calls.length).toBe(acknowledgmentsBefore);
  expect(screen.getByRole("button", { name: "Recovery" })).toBeTruthy();
  expect(
    screen.getByText(/does not acknowledge the interruption/),
  ).toBeTruthy();
});

it("shows machine-only interruptions and keeps changes blocked after passing validation", async () => {
  vi.mocked(inspectOperationIncident).mockResolvedValueOnce({
    incident: null,
    backendActive: false,
    backendInterrupted: true,
  });
  vi.mocked(operate).mockResolvedValueOnce({
    code: 0,
    success: true,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "validate.log",
    platform: { label: "Windows 11 x64", supported: true },
  });
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", {
    name: "A previous operation was interrupted",
  });
  expect(
    screen.queryByRole("button", { name: "Dismiss recovery notice" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Run validation" }));
  await screen.findByRole("heading", { name: "Validation passed." });
  fireEvent.click(screen.getByRole("button", { name: "Install" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Install Development Environment" }),
  );
  await screen.findByRole("heading", {
    name: "A previous operation was interrupted",
  });
  expect(
    vi
      .mocked(operate)
      .mock.calls.slice(before)
      .map((call) => call[0]),
  ).toEqual(["validate"]);
  expect(
    screen.queryByRole("button", { name: "Repair environment" }),
  ).toBeNull();
  expect(
    screen.getByRole("button", { name: "Recovery" }),
  ).toBeTruthy();
});

it("retries startup validation without starting Install", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    code: 1,
    success: false,
    lines: [
      "An interrupted system operation needs mentor review before another change.",
    ],
    log_path: "validate.log",
    platform: { label: "Windows 11 x64", supported: true },
  });
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Retry validation" }),
  );
  await waitFor(() =>
    expect(vi.mocked(operate).mock.calls.length).toBeGreaterThan(before),
  );
  expect(vi.mocked(operate).mock.calls[before][0]).toBe("validate");
  expect(screen.queryByRole("button", { name: "Retry install" })).toBeNull();
});

it("keeps readiness green/yellow when only maintenance needs attention", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    code: 1,
    success: false,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      "SKYVIEW_EVENT|validation|FAIL|Weekly maintenance timer is not enabled",
      "SKYVIEW_EVENT|summary|1|Maintenance needs attention",
    ],
    log_path: "validation.log",
    platform: { label: "Linux Mint 22.3", supported: true },
  });
  vi.mocked(inspectSchedule).mockResolvedValueOnce({
    status: "missing",
    active: false,
    identifier: "test timer",
    frequency: "Unavailable",
    nextRun: null,
    lastRun: null,
    lastResult: "unavailable",
    resultDetail: "Unavailable",
    catchUp: null,
    logFolder: "/logs",
    logsAvailable: false,
    note: "Missing",
    observedAt: "2026-10-26T12:00:00Z",
    createdAt: null,
    lastSuccess: null,
  });
  const { container } = render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  const card = container.querySelector(".status-card");
  expect(card?.classList.contains("tone-yellow")).toBe(true);
  expect(card?.classList.contains("tone-red")).toBe(false);
  expect(screen.getByText("Maintenance is not installed")).toBeTruthy();
});
async function startInstall() {
  fireEvent.click(
    screen.getByRole("button", { name: "Install Development Environment" }),
  );
  await screen.findByRole("heading", { name: "Before Install begins" });
  const continueButton = await screen.findByRole("button", {
    name: "Continue with Install",
  });
  await waitFor(() =>
    expect((continueButton as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(continueButton);
}
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
    async (_mode, _id, _updates, _acknowledged, emit) => {
      emit("Installing Git…");
      return new Promise(() => {});
    },
  );
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  await startInstall();
  expect(
    screen.getByRole("region", { name: "Provisioning log" }).textContent,
  ).toBe("Installing Git…");
  expect(screen.getByRole("heading", { name: "Live details" })).toBeTruthy();
  expect(screen.queryByText("Show details")).toBeNull();
  expect(document.activeElement?.getAttribute("role")).toBe("status");
});
it("shows a keyboard-accessible UI with no detected axe violations", async () => {
  const { container } = render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
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
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(screen.getByRole("button", { name: "Validation" }));
  expect(screen.getByRole("table")).toBeTruthy();
  expect(screen.getByText("PASS")).toBeTruthy();
});
it("offers a retry and focuses the result after a child failure", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  await startInstall();
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
    name: "Ready!",
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
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(screen.getByRole("button", { name: "Schedule" }));
  await screen.findByText("Test timer");
  await screen.findByText("Paused", { exact: true });
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
  await screen.findByRole("heading", { name: "Ready!" });
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

it("reviews Repair without starting it and retains the explicit start action", async () => {
  vi.mocked(operate).mockClear();
  vi.mocked(inspect).mockResolvedValueOnce({
    code: 1,
    success: false,
    lines: [
      "SKYVIEW_EVENT|validation|FAIL|Git: not installed",
      "SKYVIEW_EVENT|validation|INFO|Git identity: not configured (optional)",
      "SKYVIEW_EVENT|summary|1|Failed",
    ],
    log_path: "test.log",
    platform: { label: "Windows 11", supported: true },
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Not installed" });
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  expect(screen.getByText("Git could not be found")).toBeTruthy();
  expect(screen.getByText("INFORMATION")).toBeTruthy();
  expect(screen.getByText(/Repair runs the full workflow/)).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: /Review Repair for Git/ }),
  );
  expect(vi.mocked(operate)).not.toHaveBeenCalled();
  const start = screen.getByRole("button", {
    name: "Repair Development Environment",
  });
  expect(start).toBeTruthy();
  expect(screen.getByRole("status").textContent).toContain(
    "choose whether to start",
  );
  fireEvent.click(start);
  await waitFor(() =>
    expect(vi.mocked(operate)).toHaveBeenCalledWith(
      "repair",
      expect.any(String),
      false,
      false,
      expect.any(Function),
    ),
  );
});
it("reviews Update for an available managed update without starting it", async () => {
  vi.mocked(operate).mockClear();
  vi.mocked(inspect).mockResolvedValueOnce({
    code: 0,
    success: true,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49.0",
      'SKYVIEW_EVENT|tool|Git|{"tool":"Git","installedVersion":"2.49.0","availableVersion":"2.50.0","updateAvailable":true,"updateCheck":"current"}',
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "test.log",
    platform: { label: "Linux Mint 22.3", supported: true },
  });
  render(<App />);
  await screen.findByRole("heading", {
    name: "Ready!",
  });
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  expect(screen.getByText("PASS")).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", {
      name: /Review Update for Managed update available for Git/,
    }),
  );
  expect(vi.mocked(operate)).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Update Development Tools" }),
  );
  expect(vi.mocked(operate)).not.toHaveBeenCalled();
  fireEvent.click(
    await screen.findByRole("button", { name: "Continue with Update" }),
  );
  await waitFor(() =>
    expect(vi.mocked(operate)).toHaveBeenCalledWith(
      "update",
      expect.any(String),
      false,
      false,
      expect.any(Function),
    ),
  );
});
it("retains unknown diagnostics as plain text and offers diagnostic review", async () => {
  const message = "Unknown check <script>alert('example')</script>";
  vi.mocked(operate).mockClear();
  vi.mocked(inspect).mockResolvedValueOnce({
    code: 1,
    success: false,
    lines: [
      `SKYVIEW_EVENT|validation|FAIL|${message}`,
      "SKYVIEW_EVENT|summary|1|Failed",
    ],
    log_path: "test.log",
    platform: { label: "Linux Mint 22.3", supported: true },
  });
  const { container } = render(<App />);
  await screen.findByRole("heading", { name: "Needs attention" });
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  expect(screen.getByText("This check needs diagnostic review")).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Review Repair/ })).toBeNull();
  const details = container.querySelector(
    ".check-diagnostics",
  ) as HTMLDetailsElement;
  expect(details.open).toBe(false);
  fireEvent.click(screen.getByText("Technical details", { exact: true }));
  expect(screen.getByText(message)).toBeTruthy();
  expect(container.querySelector("script")).toBeNull();
  expect(vi.mocked(operate)).not.toHaveBeenCalled();
});

it("blocks guidance actions while an operation is streaming checks", async () => {
  vi.mocked(operate).mockClear();
  vi.mocked(operate).mockImplementationOnce(
    async (_mode, _id, _updates, _acknowledged, emit) => {
      emit("SKYVIEW_EVENT|validation|FAIL|Git: not installed");
      return new Promise(() => {});
    },
  );
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  await startInstall();
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  const review = screen.getByRole("button", {
    name: /Review Repair for Git/,
  }) as HTMLButtonElement;
  expect(review.disabled).toBe(true);
  fireEvent.click(review);
  expect(vi.mocked(operate)).toHaveBeenCalledTimes(1);
});

it("keeps command diagnostics ending in not found on the diagnostic-review path", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    code: 1,
    success: false,
    lines: [
      "SKYVIEW_EVENT|validation|FAIL|Node.js: expected runtime family or usable command; detected version not found",
      "SKYVIEW_EVENT|summary|1|Failed",
    ],
    log_path: "test.log",
    platform: { label: "Windows 11", supported: true },
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Needs attention" });
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  expect(
    screen.getByText("A required command or runtime could not be verified"),
  ).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Review Repair/ })).toBeNull();
});
it("never reports ready from partial validation without a successful summary", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    code: 1,
    success: false,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.43.0",
      "SKYVIEW_EVENT|error|operation|Validation stopped before completion",
    ],
    log_path: "test.log",
    platform: { label: "Windows 11", supported: true },
  });
  render(<App />);
  await screen.findByRole("heading", { name: "Validation incomplete" });
  expect(screen.queryByRole("heading", { name: "Ready!" })).toBeNull();
  expect(
    screen.getByText(
      /passing individual checks does not establish full readiness/,
    ),
  ).toBeTruthy();
});
