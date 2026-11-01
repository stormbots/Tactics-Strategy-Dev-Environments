import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { RecoveryPage } from "./RecoveryPage";
import { previewRecovery, type RecoveryState } from "./recovery";

const id = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
function unknownActivity() {
  const state = previewRecovery();
  state.machine.incidentId = id;
  state.machine.intentSubmitted = true;
  state.effectiveActivity = state.nativeSafety.activity = "unknown";
  state.nativeSafety.interrupted = true;
  state.decision = "block_activity_unknown";
  state.readiness = "blocked";
  return state;
}
function props(state: RecoveryState | null = unknownActivity()) {
  return {
    state,
    loading: false,
    error: "",
    pending: null,
    outcomes: [],
    platformLabel: "Windows 11 · x64",
    onCheck: vi.fn(),
    onAcknowledge: vi.fn(),
    onContinue: vi.fn(),
    onCancel: vi.fn(),
    onValidate: vi.fn(),
    onLogs: vi.fn(),
    onSupport: vi.fn(),
  };
}
afterEach(cleanup);

it("leads the submitted Windows interruption with one next action and keeps precise evidence collapsed", () => {
  const callbacks = props();
  const { container } = render(<RecoveryPage {...callbacks} />);
  expect(
    screen.getByRole("heading", { name: "Let’s get setup working again" }),
  ).toBeTruthy();
  expect(screen.getByText("Save your work.")).toBeTruthy();
  expect(screen.getByText(/Start → Power → Restart/)).toBeTruthy();
  expect(
    screen.getByText(/doesn’t automatically fix an unfinished installation/),
  ).toBeTruthy();
  expect(
    screen.getByText(/You don’t need to submit that acknowledgment again/),
  ).toBeTruthy();
  const primary = container.querySelectorAll("button.primary");
  expect(primary).toHaveLength(1);
  expect(primary[0].textContent).toBe("Check again");
  expect(screen.queryByRole("button", { name: "Run validation" })).toBeNull();
  expect(
    screen.queryByRole("button", { name: /Acknowledge|Continue with/ }),
  ).toBeNull();
  const details = container.querySelector("details") as HTMLDetailsElement;
  expect(details.open).toBe(false);
  expect(details.textContent).toContain(id);
  expect(details.textContent).toContain("Acknowledgment submitted");
  expect(details.textContent).toContain("does not give permission");
  fireEvent.click(primary[0]);
  expect(callbacks.onCheck).toHaveBeenCalledTimes(1);
  expect(callbacks.onAcknowledge).not.toHaveBeenCalled();
  expect(callbacks.onContinue).not.toHaveBeenCalled();
  expect(callbacks.onValidate).not.toHaveBeenCalled();
});

it.each(["missing", "unavailable", "different-source"])(
  "does not claim saved machine consent when %s",
  (kind) => {
    const state = unknownActivity();
    if (kind === "missing") state.machine.intentSubmitted = false;
    if (kind === "unavailable") state.machine.available = false;
    if (kind === "different-source") state.machine.incidentId = null;
    render(<RecoveryPage {...props(state)} />);
    expect(screen.queryByText(/You don’t need to submit/)).toBeNull();
  },
);

it("does not let the computer acknowledgment claim consent for a separate account incident", () => {
  const state = unknownActivity();
  state.user.incident = {
    id: "b564efb0-e4b1-42b4-8c17-e794011bd734",
    operation: "repair",
    stage: "system",
    startedAt: 1,
    observedAt: 2,
  };
  state.canAcknowledgeUser = true;
  const { container } = render(<RecoveryPage {...props(state)} />);
  expect(
    screen.getByText(/SDE has your acknowledgment for this computer/),
  ).toBeTruthy();
  expect(
    screen.queryByText(/acknowledgment for this account is saved/),
  ).toBeNull();
  expect(
    screen.getByText(/account’s interruption has not been acknowledged/),
  ).toBeTruthy();
  expect(
    screen.getByRole("button", { name: "Acknowledge interruption" }).className,
  ).toBe("secondary");
  expect(container.querySelector("button.primary")?.textContent).toBe(
    "Check again",
  );
});

it("does not give restart or repair instructions while an installation is active", () => {
  const state = unknownActivity();
  state.effectiveActivity = "active";
  state.nativeSafety.packageHealth = "incomplete";
  render(<RecoveryPage {...props(state)} />);
  expect(
    screen.getByText("Let the current setup or update finish."),
  ).toBeTruthy();
  expect(screen.queryByText(/Restart your computer using/)).toBeNull();
  expect(
    screen.queryByText(/Open Technical details for the repair/),
  ).toBeNull();
  expect(screen.queryByRole("button", { name: "Run validation" })).toBeNull();
});

it("unavailable records lead to support rather than pretending a restart repairs them", () => {
  const state = unknownActivity();
  state.user.available = false;
  const callbacks = props(state);
  render(<RecoveryPage {...callbacks} />);
  expect(
    screen.getByText(/SDE couldn’t read or verify its safety records/),
  ).toBeTruthy();
  expect(screen.queryByText(/Restart your computer using/)).toBeNull();
  expect(screen.getByText(/Do not delete them to unlock changes/)).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Create support report" }),
  );
  expect(callbacks.onSupport).toHaveBeenCalledTimes(1);
  expect(callbacks.onContinue).not.toHaveBeenCalled();
});

it("unknown activity takes priority over repair guidance for incomplete packages", () => {
  const state = unknownActivity();
  state.nativeSafety.packageHealth = "incomplete";
  render(<RecoveryPage {...props(state)} />);
  expect(screen.getByText("Save your work.")).toBeTruthy();
  expect(
    screen.queryByText(/Open Technical details for the repair/),
  ).toBeNull();
});

it("uses the computer power menu rather than Windows instructions on Mint", () => {
  render(<RecoveryPage {...props()} platformLabel="Linux Mint 22.3" />);
  expect(
    screen.getByText(/normal Restart option in its power menu/),
  ).toBeTruthy();
  expect(screen.queryByText(/Start → Power/)).toBeNull();
});

it("offers the existing single acknowledgment action with automatic summary explanation", () => {
  const state = previewRecovery();
  state.machine.incidentId = id;
  state.canAcknowledgeMachine = true;
  state.readiness = "needs_acknowledgment";
  const callbacks = props(state);
  const { container } = render(
    <RecoveryPage {...callbacks} pending="install" />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Acknowledge and continue" }),
  );
  expect(callbacks.onAcknowledge).toHaveBeenCalledTimes(1);
  expect(screen.getByText(/tries to save a report automatically/)).toBeTruthy();
  expect(container.querySelectorAll("button.primary")).toHaveLength(1);
});

it("retains continue and cancellation callbacks without starting a request automatically", () => {
  const callbacks = props(previewRecovery());
  render(<RecoveryPage {...callbacks} pending="repair" />);
  expect(callbacks.onContinue).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Continue with repair" }));
  expect(callbacks.onContinue).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole("button", { name: "Back to Overview" }));
  expect(callbacks.onCancel).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole("button", { name: "Cancel" })).toBeNull();
});

it("keeps report-save warnings visible without putting reference IDs in the main reading path", () => {
  const { container } = render(
    <RecoveryPage
      {...props()}
      outcomes={[
        { incidentId: id, reportId: "saved-reference", reportWarning: null },
        {
          incidentId: id,
          reportId: null,
          reportWarning: "Summary save failed; original record remains.",
        },
      ]}
    />,
  );
  expect(screen.getByText(/Summary save failed/).closest("details")).toBeNull();
  expect(
    screen.getByText(/Local summary saved: saved-reference/).closest("details"),
  ).toBe(container.querySelector("details"));
});

it("keeps unavailable state blocked and disables all actions while a check is running", () => {
  const callbacks = props(null);
  const { container } = render(<RecoveryPage {...callbacks} loading />);
  expect(screen.queryByRole("button", { name: "Run validation" })).toBeNull();
  expect(
    screen.queryByRole("button", { name: /Acknowledge|Continue with/ }),
  ).toBeNull();
  for (const button of container.querySelectorAll("button"))
    expect(button.disabled).toBe(true);
});
