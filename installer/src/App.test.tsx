import * as readQueue from "./nativeReadQueue";
import { StrictMode } from "react";
import type { Report } from "./model";
import * as updateApi from "./updateDiscovery";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
  act,
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
    validation_collected_at: 1793990000,
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
    validation_collected_at: 1793990000,
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
    validation_collected_at: 1793990000,
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
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
  await screen.findByRole("heading", {
    name: "Let’s get setup working again",
  });
  expect(
    screen.queryByRole("button", { name: "Dismiss recovery notice" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Run validation" }));
  await screen.findByRole("heading", { name: "Review an interruption" });
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
    validation_collected_at: 1793990000,
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
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
  await screen.findByRole("heading", {
    name: "Let’s get setup working again",
  });
  expect(
    screen.queryByRole("button", { name: "Dismiss recovery notice" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Run validation" }));
  await screen.findByRole("heading", { name: "Review an interruption" });
  openDisclosure("Other actions");
  expect(
    screen.queryByRole("button", {
      name: "Install development tools",
    }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Review interruption" }));
  await screen.findByRole("heading", {
    name: "Let’s get setup working again",
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
  vi.mocked(inspectRecovery).mockResolvedValueOnce(previewRecovery());
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  openDisclosure("Other actions");
  fireEvent.click(
    screen.getByRole("button", {
      name: "Install development tools",
    }),
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
    expect.objectContaining({ collectedAt: 1793990000 }),
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
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
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

it.each(["machine", "user"] as const)(
  "returns to Overview after a safe startup %s acknowledgment without starting a change",
  async (source) => {
    const state = interrupted(source);
    vi.mocked(inspectRecovery).mockResolvedValue(state);
    const acknowledge =
      source === "machine" ? acknowledgeMachine : acknowledgeUser;
    vi.mocked(acknowledge).mockImplementation(async () => {
      vi.mocked(inspectRecovery).mockResolvedValue(previewRecovery());
      return {
        incidentId: (state.machine.incidentId ?? state.user.incident?.id)!,
        reportId: null,
        reportWarning: "Summary could not be saved; original evidence remains.",
        ...(source === "machine"
          ? { intentStatus: "submitted" as const }
          : {
              acknowledgment: {
                incidentId: state.user.incident!.id,
                acknowledgedAt: 50,
                reportId: null,
              },
            }),
      };
    });
    const before = vi.mocked(operate).mock.calls.length;
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
    fireEvent.click(
      await screen.findByRole("button", { name: "Acknowledge interruption" }),
    );
    await screen.findByRole("heading", { name: "Ready!" });
    expect(
      screen
        .getByRole("button", { name: "Overview" })
        .getAttribute("aria-current"),
    ).toBe("page");
    expect(
      screen.queryByRole("heading", { name: "Before Install begins" }),
    ).toBeNull();
    expect(
      screen.getByText(/Summary could not be saved; original evidence remains/),
    ).toBeTruthy();
    expect(vi.mocked(operate).mock.calls.length).toBe(before);
    expect(acknowledge).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
    await screen.findByRole("heading", {
      name: "There is nothing to recover from right now",
    });
    expect(
      screen.getByText(/Summary could not be saved; original evidence remains/),
    ).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Continue with/ })).toBeNull();
  },
);

it.each([false, true])(
  "explains a nonblocking health warning without reviving the interruption (protected receipt: %s)",
  async (committed) => {
    const state = previewRecovery();
    state.machine.incidentId = interrupted().machine.incidentId;
    state.machine.intentSubmitted = true;
    state.machine.acknowledgedAt = committed ? 50 : null;
    state.nativeSafety.interrupted = true;
    state.nativeSafety.acknowledged = committed;
    if (!committed) {
      // Matching submitted intent admits only the next native recheck. It is not
      // a protected receipt, even though another consent click is unnecessary.
      state.decision = state.nativeSafety.decision = "needs_acknowledgment";
      state.guidance = interrupted().guidance;
    }
    vi.mocked(inspectRecovery).mockResolvedValue(state);
    render(<App />);
    await screen.findByRole("heading", { name: "Ready!" });
    const card = screen.getByRole("region", { name: "Workstation status" });
    expect(card.className).toContain("tone-green");
    openDisclosure("Details");
    const reason = screen.getByRole("button", {
      name: "Review Recovery",
    });
    expect(card.contains(reason)).toBe(false);
    expect(
      screen.queryByRole("heading", { name: "Setup needs attention" }),
    ).toBeNull();
    expect(screen.queryByText(/Review the interrupted operation/)).toBeNull();
    fireEvent.click(reason);
    await screen.findByRole("heading", {
      name: "There is nothing to recover from right now",
    });
    expect(screen.queryByRole("button", { name: /Acknowledge/ })).toBeNull();
  },
);

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
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Acknowledge interruption" }),
  );
  await waitFor(() => expect(acknowledgeUser).toHaveBeenCalledTimes(1));
  vi.mocked(inspectRecovery).mockResolvedValue(previewRecovery());
  const check = screen.getByRole("button", { name: "Check again" });
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
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
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
  vi.mocked(inspectRecovery).mockResolvedValueOnce(previewRecovery());
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  openDisclosure("Other actions");
  fireEvent.click(
    screen.getByRole("button", {
      name: "Install development tools",
    }),
  );
  await screen.findByRole("button", { name: "Acknowledge and continue" });
  fireEvent.click(screen.getByRole("button", { name: "Back to Overview" }));
  vi.mocked(inspectRecovery).mockResolvedValue(previewRecovery());
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
  fireEvent.click(screen.getByRole("button", { name: "Check again" }));
  await screen.findByText("No current machine incident recorded.");
  expect(screen.queryByRole("button", { name: /Continue with/ })).toBeNull();
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(acknowledgeMachine).not.toHaveBeenCalled();
});

it("refreshes safety after Install confirmation rather than using stale ready findings", async () => {
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  openDisclosure("Other actions");
  fireEvent.click(
    screen.getByRole("button", {
      name: "Install development tools",
    }),
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
  await screen.findByRole("heading", { name: "Let’s get setup working again" });
  expect(screen.getByText(/A setup or update is still running/)).toBeTruthy();
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(
    screen.queryByRole("button", { name: "Acknowledge and continue" }),
  ).toBeNull();
});

it("shows unavailable findings as blocked, with diagnostics still accessible", async () => {
  vi.mocked(inspectRecovery).mockRejectedValue(new Error("Unavailable"));
  const before = vi.mocked(operate).mock.calls.length;
  const { container } = render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
  await screen.findByRole("heading", { name: "Let’s get setup working again" });
  expect(screen.getByRole("alert").textContent).toContain("could not be read");
  expect(
    (
      screen
        .getByRole("button", { name: "Open logs" })
        .closest("details") as HTMLDetailsElement
    ).open,
  ).toBe(false);
  fireEvent.click(screen.getByText("Technical details", {}));
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

it("unreadable account evidence receives source-specific guidance rather than a false machine repair instruction", async () => {
  const state = interrupted("user");
  state.user.available = false;
  state.canAcknowledgeUser = false;
  state.readiness = "blocked";
  vi.mocked(inspectRecovery).mockResolvedValue(state);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "Recovery" }));
  await screen.findByRole("heading", {
    name: "Let’s get setup working again",
  });
  expect(
    screen.getByText(/SDE couldn’t read or verify its safety records/),
  ).toBeTruthy();
  expect(
    screen.getByText(/does not guarantee those records can be read/),
  ).toBeTruthy();
  fireEvent.click(screen.getByText("Technical details", {}));
  expect(screen.getByText(/Account records could not be read/)).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: "Acknowledge interruption" }),
  ).toBeNull();
});

it("retries startup validation without starting Install", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    validation_collected_at: 1793990000,
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
  fireEvent.click(await screen.findByRole("button", { name: "Check again" }));
  await waitFor(() =>
    expect(vi.mocked(operate).mock.calls.length).toBeGreaterThan(before),
  );
  expect(vi.mocked(operate).mock.calls[before][0]).toBe("validate");
  expect(screen.queryByRole("button", { name: "Retry install" })).toBeNull();
});

it("retains a required schedule failure and its details without inventing an incident", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    validation_collected_at: 1793990000,
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
  await screen.findByRole("heading", { name: "Setup needs attention" });
  const card = container.querySelector(".status-card");
  expect(card?.classList.contains("tone-yellow")).toBe(true);
  expect(card?.classList.contains("tone-red")).toBe(false);
  openDisclosure("Details");
  expect(screen.getByText("Maintenance: missing")).toBeTruthy();
});
function openDisclosure(name: string) {
  const summary = screen.getByText(name, {});
  if (!summary.closest("details")?.open) fireEvent.click(summary);
}
async function startInstall() {
  const before = vi.mocked(operate).mock.calls.length;
  openDisclosure("Other actions");
  fireEvent.click(
    screen.getByRole("button", {
      name: "Install development tools",
    }),
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
      .getByRole("region", { name: "Finding your next step" })
      .getAttribute("aria-busy"),
  ).toBe("true");
  expect(
    screen.getByRole("heading", { name: "Checking your setup…" }),
  ).toBeTruthy();
  expect(
    screen.getByRole("heading", { name: "Finding your next step" }),
  ).toBeTruthy();
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
  openDisclosure("Details");
  expect(
    screen.getByRole("region", { name: "Provisioning log" }).textContent,
  ).toBe("Installing Git…");
  expect(screen.getByText("Details", {}).closest("details")?.open).toBe(true);
  expect(screen.queryByText("Show details")).toBeNull();
  expect(document.activeElement?.id).toBe("next-step-heading");
});
it("shows a keyboard-accessible UI with no detected axe violations", async () => {
  const { container } = render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  const results = await axe.run(container, {
    rules: { "color-contrast": { enabled: false } },
  });
  expect(results.violations).toEqual([]);
  expect(
    screen.getByRole("button", { name: "Install development tools" }),
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
  await screen.findByText(/Reported error: A test package failed/);
  expect(screen.getByRole("button", { name: "Check my setup" })).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Retry install" })).toBeNull();
  await waitFor(() =>
    expect(document.activeElement?.textContent).toBe(
      "Setup outcome is unconfirmed",
    ),
  );
});
it("shows updates separately from successful validation, including both versions", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    validation_collected_at: 1793990000,
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
  openDisclosure("Development tools");
  openDisclosure("Details");
  expect(screen.getByText("Update available · 2.43.0 → 2.44.0")).toBeTruthy();
  expect(screen.getByText(/need attention/).textContent).toContain("0");
  expect(
    screen.getByText(/1 confirmed managed-tool updates available/),
  ).toBeTruthy();
});
it("reads and refreshes Schedule, displays never-run history, and recovers from errors", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(screen.getByRole("button", { name: "Schedule" }));
  await screen.findByText("Test timer");
  await screen.findByText("Paused", {});
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
    validation_collected_at: 1793990000,
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
  await screen.findByRole("heading", { name: "Setup needed" });
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  expect(screen.getByText("Git could not be found")).toBeTruthy();
  expect(screen.getByText("INFORMATION")).toBeTruthy();
  expect(screen.getByText(/Repair runs the full workflow/)).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: /Review Repair for Git/ }),
  );
  expect(vi.mocked(operate)).not.toHaveBeenCalled();
  const start = await screen.findByRole("button", {
    name: "Repair setup",
  });
  expect(start).toBeTruthy();
  expect(screen.getByText(/Repair runs the full workflow/)).toBeTruthy();
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
    validation_collected_at: 1793990000,
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
    validation_collected_at: 1793990000,
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
  await screen.findByRole("heading", { name: "Setup needs attention" });
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  expect(screen.getByText("This check needs diagnostic review")).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Review Repair/ })).toBeNull();
  const details = container.querySelector(
    ".check-diagnostics",
  ) as HTMLDetailsElement;
  expect(details.open).toBe(false);
  fireEvent.click(screen.getByText("Technical details", {}));
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
    validation_collected_at: 1793990000,
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
  await screen.findByRole("heading", { name: "Setup needs attention" });
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  expect(
    screen.getByText("A required command or runtime could not be verified"),
  ).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Review Repair/ })).toBeNull();
});
it("never reports ready from partial validation without a successful summary", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    validation_collected_at: 1793990000,
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
  await screen.findByRole("heading", { name: "Check not finished" });
  expect(screen.queryByRole("heading", { name: "Ready!" })).toBeNull();
  expect(
    screen.getByText(/Partial results remain available in Details/),
  ).toBeTruthy();
});

it("keeps one optional-update action and editor access under Other actions", async () => {
  vi.mocked(inspect).mockResolvedValueOnce({
    validation_collected_at: 1793990000,
    code: 0,
    success: true,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      'SKYVIEW_EVENT|tool|Git|{"tool":"Git","installedVersion":"2.49","availableVersion":"2.50","updateAvailable":true,"updateCheck":"current"}',
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "fixture",
    platform: { supported: true, label: "Fixture" },
  });
  const before = vi.mocked(operate).mock.calls.length;
  const { container } = render(<App />);
  await screen.findByRole("heading", { name: "Install updates" });
  expect(screen.getByRole("heading", { name: "Ready!" })).toBeTruthy();
  expect(
    screen.getByText(
      "Your setup works, but there are updates available if you would like to install them.",
    ),
  ).toBeTruthy();
  expect(
    container.querySelectorAll(".guided-task button.primary"),
  ).toHaveLength(1);
  expect(
    screen.getAllByRole("button", { name: "Review updates" }),
  ).toHaveLength(1);
  expect(
    screen.getByRole("button", { name: "Open VSCodium" }).closest("details")
      ?.open,
  ).toBe(false);
  openDisclosure("Other actions");
  fireEvent.click(screen.getByRole("button", { name: "Open VSCodium" }));
  await waitFor(() => expect(open).toHaveBeenCalledWith("editor"));
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
});

it.each(["active", "unknown", "untrusted", "incident"] as const)(
  "opens Overview with %s safety and no competing mutation",
  async (state) => {
    const observation = interrupted();
    observation.readiness =
      state === "incident" ? "needs_acknowledgment" : "blocked";
    if (state === "active" || state === "unknown")
      observation.effectiveActivity = state;
    if (state === "untrusted") observation.nativeSafety.trust = "untrusted";
    vi.mocked(inspectRecovery).mockResolvedValueOnce(observation);
    const before = vi.mocked(operate).mock.calls.length;
    render(<App />);
    const title =
      state === "incident"
        ? "Review an interruption"
        : state === "untrusted"
          ? "Safety check unavailable"
          : "Changes are paused";
    await screen.findByRole("heading", { name: title });
    expect(
      screen
        .getByRole("button", { name: "Overview" })
        .getAttribute("aria-current"),
    ).toBe("page");
    openDisclosure("Other actions");
    expect(
      screen.queryByRole("button", {
        name: "Install development tools",
      }),
    ).toBeNull();
    expect(vi.mocked(operate).mock.calls.length).toBe(before);
    expect(screen.getByRole("button", { name: "Recovery" })).toBeTruthy();
  },
);

it("keeps a focused editor action stable when delayed update discovery changes the next step", async () => {
  let resolve!: (
    value: Awaited<ReturnType<typeof updateApi.checkTools>>,
  ) => void;
  const spy = vi.spyOn(updateApi, "checkTools").mockImplementationOnce(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  vi.mocked(inspect).mockResolvedValueOnce({
    validation_collected_at: 1793990000,
    code: 0,
    success: true,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      'SKYVIEW_EVENT|tool|Git|{"tool":"Git","installedVersion":"2.49","availableVersion":null,"updateAvailable":false,"updateCheck":"notChecked"}',
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "fixture",
    platform: { supported: true, label: "Fixture" },
  });
  const before = vi.mocked(open).mock.calls.length;
  render(<App />);
  const editor = await screen.findByRole("button", { name: "Open VSCodium" });
  fireEvent.focus(editor);
  resolve({
    checkedAt: 1793990100,
    tools: [
      {
        tool: "Git",
        installedVersion: "2.49",
        availableVersion: "2.50",
        updateAvailable: true,
        updateCheck: "current",
      },
    ],
  });
  await screen.findByRole("heading", { name: "Install updates" });
  expect(screen.getByRole("button", { name: "Open VSCodium" })).toBe(editor);
  fireEvent.click(editor);
  await screen.findByText(
    "The findings changed. Review your current next step before continuing.",
  );
  expect(vi.mocked(open).mock.calls.length).toBe(before);
  expect(screen.getByRole("button", { name: "Review updates" })).toBeTruthy();
  spy.mockRestore();
});

function lifecycleReport(
  mutation_outcome: Report["mutation_outcome"],
  good = false,
): Report {
  return {
    mutation_outcome,
    code: good ? 0 : 1,
    success: good,
    validation_collected_at: good ? 1793990000 : null,
    lines: good
      ? [
          "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
          "SKYVIEW_EVENT|summary|0|Done",
        ]
      : ["SKYVIEW_EVENT|error|operation|Synthetic reported failure"],
    log_path: "fixture.log",
    platform: { supported: true, label: "Fixture" },
  };
}
async function openSetupReview() {
  openDisclosure("Other actions");
  fireEvent.click(
    screen.getByRole("button", { name: "Install development tools" }),
  );
  const button = await screen.findByRole("button", {
    name: "Continue with Install",
  });
  await waitFor(() =>
    expect((button as HTMLButtonElement).disabled).toBe(false),
  );
  return button;
}

it("shows a proven native non-start without inventing an incident or re-prompting", async () => {
  vi.mocked(operate).mockResolvedValueOnce(lifecycleReport("not_started"));
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(await openSetupReview());
  await screen.findByRole("heading", { name: "No changes were started" });
  expect(
    screen.queryByRole("heading", { name: "Review an interruption" }),
  ).toBeNull();
  expect(vi.mocked(operate).mock.calls.length).toBe(before + 1);
  const back = screen.getByRole("button", { name: "Back to Overview" });
  await waitFor(() => expect((back as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(back);
  await screen.findByRole("heading", { name: "Try checking again" });
  expect(vi.mocked(operate).mock.calls.length).toBe(before + 1);
});

it("cancelled error text without native non-start evidence stays uncertain", async () => {
  vi.mocked(operate).mockRejectedValueOnce(
    new Error("Administrator authentication was cancelled"),
  );
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(await openSetupReview());
  await screen.findByRole("heading", { name: "Setup outcome is unconfirmed" });
  expect(
    screen.queryByRole("heading", { name: "No changes were started" }),
  ).toBeNull();
  expect(screen.queryByRole("heading", { name: "Ready!" })).toBeNull();
  expect(
    screen.getByText(/not a confirmed cancellation or rollback/),
  ).toBeTruthy();
});

it("keeps passed checks separate from an uncertain native mutation outcome", async () => {
  vi.mocked(operate).mockResolvedValueOnce(lifecycleReport("uncertain", true));
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(await openSetupReview());
  await screen.findByRole("heading", { name: "Setup outcome is unconfirmed" });
  expect(screen.queryByRole("heading", { name: "Ready!" })).toBeNull();
  expect(screen.queryByRole("button", { name: "Retry install" })).toBeNull();
});

it("checks incomplete verification explicitly after reported completion without reinstalling", async () => {
  vi.mocked(operate).mockResolvedValueOnce(lifecycleReport("completed"));
  vi.mocked(operate).mockResolvedValueOnce(
    lifecycleReport("not_requested", true),
  );
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(await openSetupReview());
  await screen.findByRole("heading", {
    name: "Setup finished, but checking did not finish",
  });
  expect(vi.mocked(operate).mock.calls.length).toBe(before + 1);
  const check = screen.getByRole("button", { name: "Check my setup" });
  await waitFor(() =>
    expect((check as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(check);
  await screen.findByRole("heading", { name: "Ready!" });
  expect(
    vi
      .mocked(operate)
      .mock.calls.slice(before)
      .map((c) => c[0]),
  ).toEqual(["install", "validate"]);
});

it("Back from an unstarted review submits no operation", async () => {
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  await openSetupReview();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  await screen.findByRole("heading", { name: "Start building" });
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
});

it("requires review again when options change before confirmation", async () => {
  vi.mocked(operate).mockResolvedValueOnce(lifecycleReport("completed", true));
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  await openSetupReview();
  fireEvent.click(screen.getByRole("button", { name: /^Validation/ }));
  fireEvent.click(screen.getByText("Advanced", { exact: true }));
  fireEvent.click(
    screen.getByLabelText(
      "Check for managed package updates during validation",
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Overview" }));
  let proceed = await screen.findByRole("button", {
    name: "Continue with Install",
  });
  await waitFor(() =>
    expect((proceed as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(proceed);
  await screen.findByText(/The reviewed findings or scope changed/);
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  proceed = await screen.findByRole("button", {
    name: "Continue with Install",
  });
  await waitFor(() =>
    expect((proceed as HTMLButtonElement).disabled).toBe(false),
  );
  fireEvent.click(proceed);
  await waitFor(() =>
    expect(vi.mocked(operate).mock.calls.length).toBe(before + 1),
  );
  expect(vi.mocked(operate).mock.calls.at(-1)?.[2]).toBe(true);
});

it("navigation during a delayed review inspection does not submit or redirect later", async () => {
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  let finish!: (s: RecoveryState) => void;
  vi.mocked(inspectRecovery).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  openDisclosure("Other actions");
  fireEvent.click(
    screen.getByRole("button", { name: "Install development tools" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "About" }));
  finish(previewRecovery());
  await screen.findByText(/The pending request was not submitted/);
  expect(
    screen.getByRole("button", { name: "About" }).getAttribute("aria-current"),
  ).toBe("page");
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(
    screen.queryByRole("heading", { name: "Before Install begins" }),
  ).toBeNull();
});

it("rapid confirmation and navigation preserve one actual operation and its verification", async () => {
  let finish!: (r: Report) => void;
  let emit!: (line: string) => void;
  vi.mocked(operate).mockImplementationOnce(async (_m, _id, _u, _a, onLine) => {
    emit = onLine;
    return new Promise((resolve) => {
      finish = resolve;
    });
  });
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  const proceed = await openSetupReview();
  fireEvent.click(proceed);
  fireEvent.click(proceed);
  await waitFor(() =>
    expect(vi.mocked(operate).mock.calls.length).toBe(before + 1),
  );
  emit("SKYVIEW_EVENT|progress|95|Validating your development environment");
  await screen.findByRole("heading", { name: "Checking the result…" });
  fireEvent.click(screen.getByRole("button", { name: "About" }));
  expect(
    screen.getByRole("button", { name: "Return to current task" }),
  ).toBeTruthy();
  finish(lifecycleReport("completed", true));
  await waitFor(() =>
    expect(
      screen.queryByRole("button", { name: "Return to current task" }),
    ).toBeNull(),
  );
  expect(
    screen.getByRole("button", { name: "About" }).getAttribute("aria-current"),
  ).toBe("page");
  fireEvent.click(screen.getByRole("button", { name: "Overview" }));
  await screen.findByRole("heading", { name: "Ready!" });
  expect(vi.mocked(operate).mock.calls.length).toBe(before + 1);
});

it("reopen forgets an unstarted review and queries current observations", async () => {
  const before = vi.mocked(operate).mock.calls.length,
    inspections = vi.mocked(inspect).mock.calls.length;
  const first = render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  await openSetupReview();
  first.unmount();
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  expect(
    screen.queryByRole("heading", { name: "Before Install begins" }),
  ).toBeNull();
  expect(vi.mocked(inspect).mock.calls.length).toBe(inspections + 2);
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
});

it("reopen reconstructs active work honestly without saved progress or replay", async () => {
  let finish!: (r: Report) => void;
  vi.mocked(operate).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const before = vi.mocked(operate).mock.calls.length;
  const first = render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(await openSetupReview());
  await waitFor(() =>
    expect(vi.mocked(operate).mock.calls.length).toBe(before + 1),
  );
  first.unmount();
  const active = previewRecovery();
  active.effectiveActivity = "active";
  active.readiness = "blocked";
  active.decision = "block_active";
  vi.mocked(inspectRecovery).mockResolvedValue(active);
  render(<App />);
  await screen.findByRole("heading", { name: "Let setup finish" });
  finish(lifecycleReport("completed", true));
  expect(screen.queryByRole("progressbar")).toBeNull();
  expect(screen.queryByRole("button", { name: "Stop" })).toBeNull();
  expect(vi.mocked(operate).mock.calls.length).toBe(before + 1);
});

it("retains an unresolved repair and download diagnostics without an automatic repair loop", async () => {
  const failed = {
    ...lifecycleReport("uncertain"),
    validation_collected_at: 1793990000,
    lines: [
      "SKYVIEW_EVENT|validation|FAIL|Python 3.14 not found",
      "SKYVIEW_EVENT|error|provisioning|Download failed; network unavailable",
      "SKYVIEW_EVENT|summary|1|Failed",
    ],
  };
  vi.mocked(inspect).mockResolvedValueOnce(failed);
  vi.mocked(operate).mockResolvedValueOnce(failed);
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Setup needed" });
  openDisclosure("Other actions");
  fireEvent.click(screen.getByRole("button", { name: "Repair setup" }));
  await screen.findByRole("heading", { name: "Review your fixes" });
  fireEvent.click(screen.getByRole("button", { name: "Repair setup" }));
  await screen.findByRole("heading", {
    name: "The repair has not confirmed a resolution",
  });
  expect(
    screen.getByText(/Reported error: Download failed; network unavailable/),
  ).toBeTruthy();
  expect(vi.mocked(operate).mock.calls.length).toBe(before + 1);
  expect(screen.queryByRole("button", { name: "Retry repair" })).toBeNull();
  openDisclosure("Details");
  expect(
    screen.getByRole("button", { name: "Create support report" }),
  ).toBeTruthy();
});

it("finishing acknowledgment after navigation retains the receipt without replay or redirection", async () => {
  const state = interrupted("user");
  vi.mocked(inspectRecovery).mockResolvedValue(state);
  let finish!: (value: Awaited<ReturnType<typeof acknowledgeUser>>) => void;
  vi.mocked(acknowledgeUser).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Review an interruption" });
  fireEvent.click(screen.getByRole("button", { name: "Review interruption" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Acknowledge interruption" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "About" }));
  vi.mocked(inspectRecovery).mockResolvedValue(previewRecovery());
  finish({
    incidentId: state.user.incident!.id,
    reportId: "receipt",
    reportWarning: null,
    acknowledgment: {
      incidentId: state.user.incident!.id,
      acknowledgedAt: 22,
      reportId: "receipt",
    },
  });
  await screen.findByText(/Recovery summary saved: receipt/);
  expect(
    screen.getByRole("button", { name: "About" }).getAttribute("aria-current"),
  ).toBe("page");
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(acknowledgeUser).toHaveBeenCalledTimes(1);
});

it("drops late stream output after completion and while a newer request is active", async () => {
  let oldEmit!: (line: string) => void;
  let finish!: (report: Report) => void;
  vi.mocked(operate).mockImplementationOnce(async (_m, _id, _u, _a, emit) => {
    oldEmit = emit;
    return lifecycleReport("completed", true);
  });
  vi.mocked(operate).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  fireEvent.click(await openSetupReview());
  await screen.findByRole("heading", { name: "Ready!" });
  oldEmit("SKYVIEW_EVENT|validation|FAIL|Late completed-request finding");
  openDisclosure("Details");
  expect(
    screen.getByRole("region", { name: "Provisioning log" }).textContent,
  ).not.toContain("Late completed-request");
  openDisclosure("Other actions");
  fireEvent.click(screen.getByRole("button", { name: "Check my setup" }));
  await waitFor(() =>
    expect(vi.mocked(operate).mock.calls.length).toBe(before + 2),
  );
  oldEmit("SKYVIEW_EVENT|validation|FAIL|Late superseded-request finding");
  expect(
    screen.getByRole("region", { name: "Provisioning log" }).textContent,
  ).not.toContain("Late superseded-request");
  finish(lifecycleReport("not_requested", true));
  await screen.findByRole("heading", { name: "Ready!" });
});

it("Cancel during fresh confirmation inspection abandons the request without reopening review", async () => {
  const before = vi.mocked(operate).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  const proceed = await openSetupReview();
  let finish!: (state: RecoveryState) => void;
  vi.mocked(inspectRecovery).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  fireEvent.click(proceed);
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  finish(previewRecovery());
  await screen.findByText(/The pending request was not submitted/);
  expect(
    screen.queryByRole("heading", { name: "Before Install begins" }),
  ).toBeNull();
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  expect(
    screen
      .getByRole("button", { name: "Overview" })
      .getAttribute("aria-current"),
  ).toBe("page");
});

it("unmount during admission discards even a pending read-only operation request", async () => {
  const before = vi.mocked(operate).mock.calls.length;
  const first = render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  let finish!: (state: RecoveryState) => void;
  vi.mocked(inspectRecovery).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  openDisclosure("Other actions");
  fireEvent.click(screen.getByRole("button", { name: "Check my setup" }));
  first.unmount();
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  await act(async () => {
    finish(previewRecovery());
    await Promise.resolve();
  });
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
});

it("waits for startup safety before validation and stays checking between phases", async () => {
  let settleSafety!: (state: RecoveryState) => void;
  let settleValidation!: (report: Report) => void;
  vi.mocked(inspectRecovery).mockReturnValueOnce(
    new Promise((resolve) => {
      settleSafety = resolve;
    }),
  );
  vi.mocked(inspect).mockReturnValueOnce(
    new Promise((resolve) => {
      settleValidation = resolve;
    }),
  );
  const before = vi.mocked(inspect).mock.calls.length;
  render(<App />);
  expect(vi.mocked(inspect).mock.calls.length).toBe(before);
  expect(
    screen.getByRole("heading", { name: "Checking your setup…" }),
  ).toBeTruthy();
  await act(async () => {
    settleSafety(previewRecovery());
  });
  await waitFor(() =>
    expect(vi.mocked(inspect).mock.calls.length).toBe(before + 1),
  );
  expect(
    screen.getByRole("heading", { name: "Checking your setup…" }),
  ).toBeTruthy();
  expect(
    screen.queryByRole("heading", { name: "Check not finished" }),
  ).toBeNull();
  await act(async () => {
    settleValidation({
      validation_collected_at: 1793990000,
      code: 0,
      success: true,
      lines: [
        "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
        "SKYVIEW_EVENT|summary|0|Done",
      ],
      log_path: "test.log",
      platform: { label: "Windows 11 x64", supported: true },
    });
  });
  expect(await screen.findByRole("heading", { name: "Ready!" })).toBeTruthy();
});

function startupReport(): Report {
  return {
    validation_collected_at: 1793990000,
    code: 0,
    success: true,
    lines: [
      "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
      "SKYVIEW_EVENT|summary|0|Done",
    ],
    log_path: "test.log",
    platform: { label: "Windows 11 x64", supported: true },
  };
}

it("submits only one startup sequence during StrictMode effect replay", async () => {
  const safetyBefore = vi.mocked(inspectRecovery).mock.calls.length;
  const validationBefore = vi.mocked(inspect).mock.calls.length;
  const mutationBefore = vi.mocked(operate).mock.calls.length;
  render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
  await screen.findByRole("heading", { name: "Ready!" });
  expect(vi.mocked(inspectRecovery).mock.calls.length).toBe(safetyBefore + 1);
  expect(vi.mocked(inspect).mock.calls.length).toBe(validationBefore + 1);
  expect(vi.mocked(operate).mock.calls.length).toBe(mutationBefore);
});

it("defers startup validation for known active work without inventing a failed check", async () => {
  const active = previewRecovery();
  active.effectiveActivity = "active";
  active.readiness = "blocked";
  vi.mocked(inspectRecovery).mockResolvedValue(active);
  const before = vi.mocked(inspect).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Changes are paused" });
  expect(vi.mocked(inspect).mock.calls.length).toBe(before);
  expect(
    screen.queryByText(/This workstation could not be checked/),
  ).toBeNull();
  expect(
    screen
      .getByRole("button", { name: "Check again" })
      .hasAttribute("disabled"),
  ).toBe(false);
});

it("keeps unavailable startup safety separate from tool verification", async () => {
  vi.mocked(inspectRecovery).mockRejectedValue(new Error("Unavailable"));
  const before = vi.mocked(inspect).mock.calls.length;
  render(<App />);
  await screen.findByRole("heading", { name: "Safety check unavailable" });
  expect(vi.mocked(inspect).mock.calls.length).toBe(before);
  expect(screen.queryByRole("heading", { name: "Ready!" })).toBeNull();
});

it("does not redirect navigation when delayed startup validation finishes", async () => {
  let complete!: (report: Report) => void;
  vi.mocked(inspect).mockReturnValueOnce(
    new Promise((resolve) => {
      complete = resolve;
    }),
  );
  render(<App />);
  await waitFor(() => expect(complete).toBeTypeOf("function"));
  fireEvent.click(screen.getByRole("button", { name: "About" }));
  await act(async () => {
    complete(startupReport());
  });
  expect(
    screen.getByRole("heading", { name: "About Skyview Dev Setup" }),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Overview" }));
  expect(screen.getByRole("heading", { name: "Ready!" })).toBeTruthy();
});

it("does not submit startup validation after unmount while safety was pending", async () => {
  let complete!: (state: RecoveryState) => void;
  vi.mocked(inspectRecovery).mockReturnValueOnce(
    new Promise((resolve) => {
      complete = resolve;
    }),
  );
  const before = vi.mocked(inspect).mock.calls.length;
  const app = render(<App />);
  app.unmount();
  await act(async () => {
    complete(previewRecovery());
  });
  expect(vi.mocked(inspect).mock.calls.length).toBe(before);
});

it("keeps a queued explicit check busy and rejects duplicate clicks before admission", async () => {
  render(<App />);
  await screen.findByRole("heading", { name: "Ready!" });
  let admit!: () => void;
  const gate = new Promise<void>((resolve) => {
    admit = resolve;
  });
  const sequence = vi
    .spyOn(readQueue, "withNativeReadSequence")
    .mockImplementationOnce(async (task) => {
      await gate;
      return task();
    });
  const before = vi.mocked(operate).mock.calls.length;
  const disclosure = screen.getByText("Other actions").closest("details")!;
  disclosure.open = true;
  const check = screen.getByRole("button", { name: "Check my setup" });
  fireEvent.click(check);
  fireEvent.click(check);
  expect(
    screen.getByRole("heading", { name: "Checking your setup…" }),
  ).toBeTruthy();
  expect(vi.mocked(operate).mock.calls.length).toBe(before);
  await act(async () => {
    admit();
  });
  await waitFor(() =>
    expect(vi.mocked(operate).mock.calls.length).toBe(before + 1),
  );
  sequence.mockRestore();
});
