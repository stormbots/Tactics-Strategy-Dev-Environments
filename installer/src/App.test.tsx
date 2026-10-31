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
  operate,
  inspectSchedule,
  open,
} from "./bridge";
import {
  inspectRecovery,
  previewRecovery,
  acknowledgeMachine,
  acknowledgeUser,
  type RecoveryState,
} from "./recovery";
vi.mock("./recovery", async () => {
  const actual =
    await vi.importActual<typeof import("./recovery")>("./recovery");
  return {
    ...actual,
    inspectRecovery: vi.fn(async () => actual.previewRecovery()),
    acknowledgeMachine: vi.fn(),
    acknowledgeUser: vi.fn(),
  };
});
function interrupted(source: "machine" | "user" = "machine"): RecoveryState {
  const state = previewRecovery();
  state.decision = "needs_acknowledgment";
  state.readiness = "needs_acknowledgment";
  state.guidance = {
    code: "review_interruption",
    title: "Review the interrupted operation",
    steps: ["Passing Validation does not acknowledge an incident."],
  };
  if (source === "machine") {
    state.machine.incidentId = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
    state.canAcknowledgeMachine = true;
  } else {
    state.user.incident = {
      id: "b564efb0-e4b1-42b4-8c17-e794011bd734",
      operation: "update",
      stage: "system",
      startedAt: 1,
      observedAt: 2,
    };
    state.user.viewToken = "display-bound-nonce";
    state.canAcknowledgeUser = true;
  }
  return state;
}
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
  vi.mocked(inspectRecovery)
    .mockReset()
    .mockImplementation(async () => previewRecovery());
  vi.mocked(acknowledgeMachine).mockReset();
  vi.mocked(acknowledgeUser).mockReset();
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
  const acknowledgmentsBefore = vi.mocked(acknowledgeOperationIncident).mock
    .calls.length;
  vi.mocked(inspectRecovery).mockResolvedValue(interrupted("user"));
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
    name: "Recovery findings",
  });
  expect(
    screen.queryByRole("button", { name: "Dismiss recovery notice" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Run validation" }));
  await screen.findByRole("heading", { name: "Validation passed." });
  expect(vi.mocked(acknowledgeOperationIncident).mock.calls.length).toBe(
    acknowledgmentsBefore,
  );
  expect(acknowledgeUser).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "Recovery" })).toBeTruthy();
  expect(
    screen.getByText(/does not acknowledge the interruption/),
  ).toBeTruthy();
});

it("shows machine-only interruptions and keeps changes blocked after passing validation", async () => {
  vi.mocked(inspectRecovery).mockResolvedValue(interrupted());
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
    name: "Recovery findings",
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
    name: "Recovery findings",
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
  expect(screen.getByRole("button", { name: "Recovery" })).toBeTruthy();
});

it("acknowledges both sources in one action and returns to ordinary Install preflight without launching", async () => {
  const state = interrupted();
  Object.assign(state.user, interrupted("user").user);
  state.canAcknowledgeUser = true;
  vi.mocked(inspectRecovery).mockResolvedValue(state);
  vi.mocked(acknowledgeMachine).mockResolvedValue({
    incidentId: state.machine.incidentId!,
    reportId: "machine-report",
    reportWarning: null,
    intentStatus: "submitted",
  });
  vi.mocked(acknowledgeUser).mockImplementation(async () => {
    vi.mocked(inspectRecovery).mockResolvedValue(previewRecovery());
    return {
      incidentId: state.user.incident!.id,
      reportId: null,
      reportWarning: "Summary could not be saved; original evidence remains.",
      acknowledgment: {
        incidentId: state.user.incident!.id,
        acknowledgedAt: 50,
        reportId: null,
      },
    };
  });
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Recovery findings" });
  fireEvent.click(screen.getByRole("button", { name: "Overview" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Install Development Environment" }),
  );
  const acknowledge = await screen.findByRole("button", {
    name: "Acknowledge and continue",
  });
  fireEvent.click(acknowledge);
  fireEvent.click(acknowledge);
  await screen.findByRole("heading", { name: "Before Install begins" });
  expect(acknowledgeMachine).toHaveBeenCalledTimes(1);
  expect(acknowledgeUser).toHaveBeenCalledTimes(1);
  expect(acknowledgeUser).toHaveBeenCalledWith(
    state,
    expect.objectContaining({ collectedAt: null }),
  );
  expect(
    screen.getByText(/Summary could not be saved; original evidence remains/),
  ).toBeTruthy();
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
});

it("does not resume a partially acknowledged pair and keeps its saved report reference", async () => {
  const state = interrupted();
  Object.assign(state.user, interrupted("user").user);
  state.canAcknowledgeUser = true;
  vi.mocked(inspectRecovery).mockResolvedValue(state);
  vi.mocked(acknowledgeMachine).mockResolvedValue({
    incidentId: state.machine.incidentId!,
    reportId: "saved-first-report",
    reportWarning: null,
    intentStatus: "submitted",
  });
  vi.mocked(acknowledgeUser).mockRejectedValue(
    new Error("The displayed user incident is stale. Check Again."),
  );
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Acknowledge interruption" }),
  );
  await screen.findByRole("alert");
  expect(
    screen.getByText("Local summary saved: saved-first-report."),
  ).toBeTruthy();
  expect(screen.getByRole("alert").textContent).toContain("stale");
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(
    screen.queryByRole("button", { name: "Acknowledge interruption" }),
  ).toBeNull();
});

it("unknown activity permits acknowledgment but not continuation; Check Again does not replay work", async () => {
  const state = interrupted("user");
  state.effectiveActivity = "unknown";
  state.readiness = "blocked";
  vi.mocked(inspectRecovery).mockResolvedValue(state);
  vi.mocked(acknowledgeUser).mockResolvedValue({
    incidentId: state.user.incident!.id,
    reportId: "saved-report",
    reportWarning: null,
    acknowledgment: {
      incidentId: state.user.incident!.id,
      acknowledgedAt: 22,
      reportId: "saved-report",
    },
  });
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Acknowledge interruption" }),
  );
  await waitFor(() => expect(acknowledgeUser).toHaveBeenCalledTimes(1));
  vi.mocked(inspectRecovery).mockResolvedValue(previewRecovery());
  const check = screen.getByRole("button", { name: "Check Again" });
  await waitFor(() =>
    expect((check as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(check);
  await screen.findByText("No current account incident recorded.");
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
});

it("unconfirmed machine submission cannot resume or silently retry consent", async () => {
  const state = interrupted();
  vi.mocked(inspectRecovery).mockResolvedValue(state);
  vi.mocked(acknowledgeMachine).mockResolvedValue({
    incidentId: state.machine.incidentId!,
    reportId: "retained-report",
    reportWarning: null,
    intentStatus: "unconfirmed",
    intentWarning: "Submission could not be confirmed.",
  });
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  fireEvent.click(
    await screen.findByRole("button", { name: "Acknowledge interruption" }),
  );
  await screen.findByRole("alert");
  expect(
    screen.getByText("Local summary saved: retained-report."),
  ).toBeTruthy();
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(acknowledgeMachine).toHaveBeenCalledTimes(1);
});

it("cancel forgets the pending request and a later Check Again does not launch it", async () => {
  vi.mocked(inspectRecovery).mockResolvedValue(interrupted());
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Recovery findings" });
  fireEvent.click(screen.getByRole("button", { name: "Overview" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Install Development Environment" }),
  );
  await screen.findByRole("button", { name: "Acknowledge and continue" });
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  vi.mocked(inspectRecovery).mockResolvedValue(previewRecovery());
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
  fireEvent.click(screen.getByRole("button", { name: "Check Again" }));
  await screen.findByText("No current machine incident recorded.");
  expect(screen.queryByRole("button", { name: /Continue with/ })).toBeNull();
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(acknowledgeMachine).not.toHaveBeenCalled();
});

it("refreshes safety after Install confirmation rather than using stale ready findings", async () => {
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(
    screen.getByRole("button", { name: "Install Development Environment" }),
  );
  const proceed = await screen.findByRole("button", {
    name: "Continue with Install",
  });
  await waitFor(() =>
    expect((proceed as HTMLButtonElement).disabled).toBe(false),
  );
  const active = interrupted();
  active.effectiveActivity = "active";
  active.readiness = "blocked";
  active.canAcknowledgeMachine = false;
  vi.mocked(inspectRecovery).mockResolvedValue(active);
  fireEvent.click(proceed);
  await screen.findByRole("heading", { name: "An operation is still active" });
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(
    screen.queryByRole("button", { name: "Acknowledge and continue" }),
  ).toBeNull();
});

it("shows unavailable findings as blocked, with diagnostics still accessible", async () => {
  vi.mocked(inspectRecovery).mockRejectedValue(new Error("Unavailable"));
  const before = vi.mocked(operate).mock.calls.length;
  const { container } = render(<App />);
  await screen.findByRole("heading", { name: "Recovery findings" });
  expect(screen.getByRole("alert").textContent).toContain("could not be read");
  expect(screen.getByRole("button", { name: "Open logs" })).toBeTruthy();
  expect(
    screen.getByRole("button", { name: "Create support report" }),
  ).toBeTruthy();
  expect(
    (
      await axe.run(container, {
        rules: { "color-contrast": { enabled: false } },
      })
    ).violations,
  ).toEqual([]);
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
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
  const before = vi.mocked(operate).mock.calls.length;
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
  await waitFor(() =>
    expect(vi.mocked(operate).mock.calls.length).toBe(before + 1),
  );
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
  const continueUpdate = await screen.findByRole("button", {
    name: "Continue with Update",
  });
  await waitFor(() =>
    expect((continueUpdate as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(continueUpdate);
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
