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
