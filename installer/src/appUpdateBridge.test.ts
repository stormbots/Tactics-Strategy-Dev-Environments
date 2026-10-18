import { beforeEach, expect, it, vi } from "vitest";
import { invoke } from "@tauri-apps/api/core";
import { inspectAppUpdate, requestAppUpdate } from "./bridge";
vi.mock("@tauri-apps/api/core", () => ({
  isTauri: () => true,
  invoke: vi.fn(),
}));
beforeEach(() => {
  vi.mocked(invoke).mockReset();
});
it("inspection uses the fixed read-only command without caller arguments", async () => {
  vi.mocked(invoke).mockResolvedValue({
    enabled: false,
    reason: "native_validation_pending",
  });
  expect(await inspectAppUpdate()).toEqual({
    enabled: false,
    reason: "native_validation_pending",
  });
  expect(invoke).toHaveBeenCalledExactlyOnceWith("inspect_app_update");
});
it("an unexpected enabled reply cannot activate the UI", async () => {
  vi.mocked(invoke).mockResolvedValue({
    enabled: true,
    reason: "native_validation_pending",
  });
  expect((await inspectAppUpdate()).enabled).toBe(false);
});
it("a direct request has no command/path/candidate parameters and never treats success as acceptance", async () => {
  vi.mocked(invoke).mockResolvedValue(undefined);
  await expect(requestAppUpdate()).rejects.toThrow(
    "No app-only update request was confirmed",
  );
  expect(invoke).toHaveBeenCalledExactlyOnceWith("request_app_update");
});
it("backend refusal is not retried", async () => {
  vi.mocked(invoke).mockRejectedValue(new Error("Disabled"));
  await expect(requestAppUpdate()).rejects.toThrow("Disabled");
  expect(invoke).toHaveBeenCalledTimes(1);
});

it("fixed discovery command cannot submit requests or take caller-selected URLs", async () => {
  const { discoverAppUpdate } = await import("./bridge");
  vi.mocked(invoke).mockResolvedValue({
    status: "no_newer_listing",
    candidate: null,
  });
  expect((await discoverAppUpdate()).status).toBe("no_newer_listing");
  expect(invoke).toHaveBeenCalledExactlyOnceWith("discover_app_update");
});
it("invalid progress/close IDs are rejected before IPC", async () => {
  const { inspectAppUpdateProgress, closeForAppUpdate } =
    await import("./bridge");
  await expect(inspectAppUpdateProgress("../../policy.json")).rejects.toThrow();
  await expect(closeForAppUpdate("../../policy.json")).rejects.toThrow();
  expect(invoke).not.toHaveBeenCalled();
});
it("even a successful close reply cannot cause GUI exit", async () => {
  const { closeForAppUpdate } = await import("./bridge");
  vi.mocked(invoke).mockResolvedValue(undefined);
  await expect(
    closeForAppUpdate("00000000-0000-4000-8000-000000000001"),
  ).rejects.toThrow(/disabled/);
  expect(invoke).toHaveBeenCalledExactlyOnceWith("close_for_app_update", {
    requestId: "00000000-0000-4000-8000-000000000001",
  });
});
