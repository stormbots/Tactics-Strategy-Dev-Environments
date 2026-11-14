import { beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import {
  inspect,
  inspectSchedule,
  inspectSelfUpdate,
  supportContext,
  inspectOperationIncident,
  operate,
} from "./bridge";
import { inspectRecovery } from "./recovery";
import { listRecoveryIncidents } from "./recoveryIncidents";
import { readRecoveryReport } from "./recoveryReports";
import { checkApplication } from "./updateDiscovery";
import { withNativeReadSequence } from "./nativeReadQueue";

vi.mock("@tauri-apps/api/core", () => ({
  isTauri: () => true,
  invoke: vi.fn(),
}));
beforeEach(() => {
  vi.mocked(invoke).mockReset().mockResolvedValue({});
});

it("serializes real gate-taking adapters behind startup while gate-free queries proceed", async () => {
  let release!: () => void;
  const calls: string[] = [];
  vi.mocked(invoke).mockImplementation(async (command) => {
    calls.push(command);
    if (command === "inspect_system")
      await new Promise<void>((resolve) => {
        release = resolve;
      });
    return {};
  });
  const startup = withNativeReadSequence(async (lease) => {
    await inspectRecovery(lease);
    await inspect(lease);
  });
  await vi.waitFor(() =>
    expect(calls).toEqual(["inspect_recovery_state", "inspect_system"]),
  );
  const reads = [
    inspectSelfUpdate(),
    supportContext(false),
    inspectOperationIncident(),
    listRecoveryIncidents("machine"),
    readRecoveryReport("report-id"),
  ];
  await inspectSchedule();
  await checkApplication();
  expect(calls).toEqual([
    "inspect_recovery_state",
    "inspect_system",
    "inspect_schedule",
    "check_application",
  ]);
  release();
  await Promise.all([startup, ...reads]);
  expect(calls.slice(4)).toEqual([
    "inspect_self_update",
    "support_context",
    "inspect_operation_incident",
    "list_recovery_incidents",
    "read_recovery_report_details",
  ]);
});

it("uses one owned sequence for explicit read-only validation without recursive enqueue", async () => {
  await withNativeReadSequence(async (lease) => {
    await inspectRecovery(lease);
    await operate("validate", "read-id", false, false, () => {}, lease);
    await inspectRecovery(lease);
  });
  expect(vi.mocked(invoke).mock.calls.map(([command]) => command)).toEqual([
    "inspect_recovery_state",
    "run_operation",
    "inspect_recovery_state",
  ]);
});

it("does not turn the read sequence into mutation permission or a mutation queue", async () => {
  let release!: () => void;
  const running = withNativeReadSequence(async () => {
    await new Promise<void>((resolve) => {
      release = resolve;
    });
  });
  await vi.waitFor(() => expect(release).toBeTypeOf("function"));
  // Only the explicit normal operation call submits these unchanged RPC fields.
  await operate("repair", "explicit-id", false, false, () => {});
  expect(invoke).toHaveBeenCalledExactlyOnceWith("run_operation", {
    operation: "repair",
    runId: "explicit-id",
    checkUpdates: false,
    acknowledgedUncertainty: false,
  });
  release();
  await running;
});
