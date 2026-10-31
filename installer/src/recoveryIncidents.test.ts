import { beforeEach, expect, it, vi } from "vitest";
import { invoke, isTauri } from "@tauri-apps/api/core";
import { listRecoveryIncidents } from "./recoveryIncidents";
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(),
  isTauri: vi.fn(() => true),
}));
beforeEach(() => {
  vi.mocked(invoke).mockReset();
  vi.mocked(isTauri).mockReturnValue(true);
});
it("uses fixed source and bounded opaque-ID pagination, not a private path or mutation argument", async () => {
  await listRecoveryIncidents("user", "opaque-id");
  expect(invoke).toHaveBeenCalledExactlyOnceWith("list_recovery_incidents", {
    source: "user",
    cursor: "opaque-id",
    limit: 25,
  });
});
it("preview has no workstation incident records and performs no native call", async () => {
  vi.mocked(isTauri).mockReturnValue(false);
  expect((await listRecoveryIncidents("machine")).machine?.entries).toEqual([]);
  expect((await listRecoveryIncidents("user")).user?.entries).toEqual([]);
  expect(invoke).not.toHaveBeenCalled();
});
