import { afterEach, expect, it, vi } from "../testing/unitApi";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ChangeSafetyOverviewCard } from "./ChangeSafetyOverviewCard";
import { previewRecovery, type RecoveryState } from "./recovery";
function blocked(): RecoveryState {
  const value = previewRecovery();
  value.nativeSafety.interrupted = true;
  value.nativeSafety.activity = "unknown";
  value.nativeSafety.activityReason = "earlier_process_lifetime_unknown";
  value.machine.incidentId = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
  value.effectiveActivity = "unknown";
  value.readiness = "blocked";
  return value;
}
function props(state: RecoveryState | null = blocked()) {
  return {
    state,
    pending: false,
    error: "",
    busy: false,
    onReview: vi.fn(),
    onSupport: vi.fn(),
  };
}
afterEach(cleanup);
it("review and support are explicit callbacks and cannot change the safety observation", () => {
  const options = props(),
    before = JSON.stringify(options.state);
  render(<ChangeSafetyOverviewCard {...options} />);
  expect(
    screen.getByText(
      /cannot yet confirm that the earlier system operation ended/,
    ),
  ).toBeTruthy();
  expect(options.onReview).not.toHaveBeenCalled();
  expect(options.onSupport).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Address safety finding" }),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Create safety support report" }),
  );
  expect(options.onReview).toHaveBeenCalledTimes(1);
  expect(options.onSupport).toHaveBeenCalledTimes(1);
  expect(JSON.stringify(options.state)).toBe(before);
  expect(
    screen.queryByRole("button", {
      name: /Acknowledge|Restart|Start|Continue/,
    }),
  ).toBeNull();
});
it("account name and times cannot be substituted for an unknown system operation", () => {
  const state = blocked();
  state.user.incident = {
    id: "account",
    operation: "repair",
    stage: "profile",
    startedAt: 1700000000,
    observedAt: 1700000100,
  };
  render(<ChangeSafetyOverviewCard {...props(state)} />);
  expect(screen.getByText("Repair")).toBeTruthy();
  expect(screen.getByText("System operation")).toBeTruthy();
  expect(screen.getByText("Operation name unavailable")).toBeTruthy();
  expect(screen.getByText("Time unavailable")).toBeTruthy();
  expect(screen.getByText("System safety last checked")).toBeTruthy();
});
it("missing names and invalid times stay unknown without an invented failure", () => {
  const state = blocked();
  state.machine.incidentId = null;
  state.nativeSafety.interrupted = false;
  state.user.incident = {
    id: "account",
    operation: "toString" as "update",
    stage: "unknown",
    startedAt: 0,
    observedAt: NaN,
  };
  render(<ChangeSafetyOverviewCard {...props(state)} />);
  expect(screen.getByText("Operation name unavailable")).toBeTruthy();
  expect(screen.getAllByText("Time unavailable")).toHaveLength(2);
  expect(
    screen.getByText(/current evidence does not establish the cause/),
  ).toBeTruthy();
  expect(screen.queryByText(/operation failed/)).toBeNull();
});
it("running work warns against force-closing and does not suggest restart", () => {
  const state = blocked();
  state.effectiveActivity = "active";
  render(<ChangeSafetyOverviewCard {...props(state)} />);
  expect(
    screen.getByText(/Let it finish before starting another change/),
  ).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: /Restart|Acknowledge/ }),
  ).toBeNull();
});
it("unreadable sources stay distinct from a missing operation or confirmed failure", () => {
  const state = blocked();
  state.machine.available = false;
  state.user.available = false;
  state.user.incident = {
    id: "unreadable",
    operation: "install",
    stage: "system",
    startedAt: 1700000000,
    observedAt: 1700000100,
  };
  render(<ChangeSafetyOverviewCard {...props(state)} />);
  expect(
    screen.getByText(/could not read or verify all of its safety information/),
  ).toBeTruthy();
  expect(screen.getByText(/Operation name unavailable/)).toBeTruthy();
  expect(screen.queryByText("Install")).toBeNull();
  expect(screen.queryByText("System safety last checked")).toBeNull();
});
it("confirmed restart evidence failures use a bounded explanation and unknown codes remain unknown", () => {
  const state = blocked();
  state.nativeSafety.activityReason = "restart_evidence_unavailable";
  const view = render(<ChangeSafetyOverviewCard {...props(state)} />);
  expect(
    screen.getByText(/could not read enough restart information/),
  ).toBeTruthy();
  state.nativeSafety.activityReason = "unrecognized-private-diagnostic";
  view.rerender(<ChangeSafetyOverviewCard {...props(state)} />);
  expect(
    screen.getByText(/current evidence does not establish the cause/),
  ).toBeTruthy();
  expect(screen.queryByText(/unrecognized-private-diagnostic/)).toBeNull();
});
it("ready safety removes the card while health-only uncertainty does not become a blocker", () => {
  const view = render(
    <ChangeSafetyOverviewCard {...props(previewRecovery())} />,
  );
  expect(screen.queryByRole("region")).toBeNull();
  const state = previewRecovery();
  state.readiness = "needs_acknowledgment";
  state.canAcknowledgeMachine = true;
  view.rerender(<ChangeSafetyOverviewCard {...props(state)} />);
  expect(
    screen.getByText(/Its retained interruption still needs your review/),
  ).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: "Acknowledge interruption" }),
  ).toBeNull();
  state.nativeSafety.packageHealth = "incomplete";
  view.rerender(<ChangeSafetyOverviewCard {...props(state)} />);
  expect(screen.getByText(/An installation needs attention/)).toBeTruthy();
});
it("pending and failed reads cannot display a cleared finding or stale operation details", () => {
  const options = props();
  options.pending = true;
  render(<ChangeSafetyOverviewCard {...options} />);
  expect(
    screen.getByRole("heading", { name: "Checking change safety…" }),
  ).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Address safety finding",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(screen.queryByText("System operation")).toBeNull();
  cleanup();
  render(
    <ChangeSafetyOverviewCard
      {...props(previewRecovery())}
      error="read failed"
    />,
  );
  expect(
    screen.getByRole("heading", { name: "Change safety needs review" }),
  ).toBeTruthy();
});
