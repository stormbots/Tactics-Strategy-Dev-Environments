import { expect, it, vi, beforeEach } from "vitest";
import { invoke, isTauri } from "@tauri-apps/api/core";
import {
  acknowledgeMachine,
  acknowledgeUser,
  inspectRecovery,
  previewRecovery,
  recoveryNeedsAttention,
} from "./recovery";
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
  isTauri: vi.fn(() => true),
}));
beforeEach(() => {
  vi.mocked(invoke).mockReset();
  vi.mocked(isTauri).mockReturnValue(true);
});
it("uses a fixed input-free native observation and never persists preview state", async () => {
  vi.mocked(invoke).mockResolvedValue(previewRecovery());
  await inspectRecovery();
  expect(invoke).toHaveBeenCalledExactlyOnceWith("inspect_recovery_state");
  vi.mocked(invoke).mockClear();
  vi.mocked(isTauri).mockReturnValue(false);
  expect((await inspectRecovery()).readiness).toBe("ready_for_native_recheck");
  expect(invoke).not.toHaveBeenCalled();
});
it("acknowledges only the displayed user generation nonce, with automatic native report input", async () => {
  const state = previewRecovery();
  state.canAcknowledgeUser = true;
  state.user.incident = {
    id: "user-id",
    operation: "repair",
    stage: "system",
    startedAt: 1,
    observedAt: 2,
  };
  state.user.viewToken = "opaque-view";
  const validation = {
    collectedAt: 21,
    checks: [{ status: "PASS" as const, message: "Git" }],
  };
  await acknowledgeUser(state, validation);
  expect(invoke).toHaveBeenCalledExactlyOnceWith(
    "acknowledge_user_recovery_incident",
    {
      incidentId: "user-id",
      viewToken: "opaque-view",
      confirmed: true,
      validation,
    },
  );
  state.user.viewToken = null;
  await expect(acknowledgeUser(state, validation)).rejects.toThrow(
    "Check Again",
  );
  expect(invoke).toHaveBeenCalledTimes(1);
});
it("machine acknowledgment is not a separate save dialog or a mutation permit", async () => {
  const state = previewRecovery();
  state.canAcknowledgeMachine = true;
  state.machine.incidentId = "machine-id";
  await acknowledgeMachine(state, null);
  expect(invoke).toHaveBeenCalledExactlyOnceWith(
    "acknowledge_recovery_incident",
    { incidentId: "machine-id", confirmed: true, validation: null },
  );
  state.canAcknowledgeMachine = false;
  await expect(acknowledgeMachine(state, null)).rejects.toThrow("Check Again");
  expect(invoke).toHaveBeenCalledTimes(1);
});
it("unavailable and blocked observations never become request readiness", () => {
  expect(recoveryNeedsAttention(null)).toBe(true);
  const state = previewRecovery();
  expect(recoveryNeedsAttention(state)).toBe(false);
  state.readiness = "blocked";
  expect(recoveryNeedsAttention(state)).toBe(true);
  state.readiness = "needs_acknowledgment";
  expect(recoveryNeedsAttention(state)).toBe(true);
});
