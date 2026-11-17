// Direct Node equivalents of demanding existing App tests. No Vitest compatibility shim.
import { test, afterEach, after, mock } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";
let completed = 0;
process.on("exit", () => {
  if (completed !== 6) {
    console.error(`Expected 6 completed cases, got ${completed}`);
    process.exitCode = 1;
  }
});
const dom = new JSDOM("<!doctype html><html><body></body></html>", {
  url: "http://localhost/",
  pretendToBeVisual: true,
});
for (const key of [
  "window",
  "document",
  "navigator",
  "localStorage",
  "HTMLElement",
  "Element",
  "SVGElement",
  "Node",
  "MutationObserver",
  "Event",
  "KeyboardEvent",
  "MouseEvent",
  "FocusEvent",
  "DOMException",
]) {
  Object.defineProperty(globalThis, key, {
    configurable: true,
    value: dom.window[key],
    writable: true,
  });
}
for (const key of [
  "getComputedStyle",
  "requestAnimationFrame",
  "cancelAnimationFrame",
])
  globalThis[key] = dom.window[key].bind(dom.window);
globalThis.ResizeObserver = class {
  observe() {}
  disconnect() {}
};
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const React = await import("react");
const { render, screen, fireEvent, waitFor, cleanup, act } =
  await import("@testing-library/react");
const originalRecovery = await import("./.output/source/recovery.js");
const originalQueue = await import("./.output/source/nativeReadQueue.js");
const startupReport = () => ({
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
let inspectImplementation = async () => startupReport();
let safetyImplementation = async () => originalRecovery.previewRecovery();
let queueGate = null;
const inspect = mock.fn((...args) => inspectImplementation(...args));
const operate = mock.fn(async (mode) => {
  assert.equal(
    mode,
    "validate",
    "These read-only tests must never start a change",
  );
  return startupReport();
});
const inspectRecovery = mock.fn((...args) => safetyImplementation(...args));
const withNativeReadSequence = mock.fn(async (task, enabled) => {
  if (queueGate) {
    const gate = queueGate;
    queueGate = null;
    await gate;
    return task();
  }
  return originalQueue.withNativeReadSequence(task, enabled);
});
const neverAcknowledge = mock.fn(async () => {
  throw new Error("No acknowledgment authorized");
});
mock.module(new URL("./.output/source/nativeReadQueue.js", import.meta.url), {
  cache: true,
  exports: { ...originalQueue, withNativeReadSequence },
});
mock.module(new URL("./.output/source/recovery.js", import.meta.url), {
  cache: true,
  exports: {
    ...originalRecovery,
    inspectRecovery,
    acknowledgeMachine: neverAcknowledge,
    acknowledgeUser: neverAcknowledge,
  },
});
mock.module(new URL("./.output/source/bridge.js", import.meta.url), {
  cache: true,
  exports: {
    native: false,
    appVersion: "1.2.1",
    inspect,
    operate,
    inspectSchedule: async () => ({
      status: "enabled",
      active: true,
      identifier: "Test timer",
      frequency: "Weekly",
      nextRun: null,
      lastRun: null,
      lastResult: "never",
      resultDetail: "No history",
      catchUp: true,
      logFolder: "/logs",
      logsAvailable: false,
      note: "",
      observedAt: "2026-11-17T00:00:00Z",
      createdAt: null,
      lastSuccess: null,
    }),
    inspectSelfUpdate: async () => ({
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
    }),
    inspectOperationIncident: async () => ({
      incident: null,
      backendActive: false,
    }),
    acknowledgeOperationIncident: neverAcknowledge,
    supportContext: async () => ({ deviceName: "TEST", logs: null }),
    saveSupportReport: async () => null,
    open: async () => {},
    setSelfUpdatePaused: async () => {
      throw new Error("No policy change authorized");
    },
  },
});
// Mock modules before importing App. Node does not retroactively replace ESM imports.
const importDeadline = setTimeout(() => {
  throw new Error("App module initialization timed out");
}, 10000);
let App;
try {
  ({ default: App } = await import("./.output/source/App.js"));
} finally {
  clearTimeout(importDeadline);
}
afterEach(() => {
  completed++;
  cleanup();
  assert.equal(neverAcknowledge.mock.callCount(), 0);
  assert.ok(
    operate.mock.calls.every((call) => call.arguments[0] === "validate"),
  );
  inspectImplementation = async () => startupReport();
  safetyImplementation = async () => originalRecovery.previewRecovery();
  queueGate = null;
});
after(() => {
  dom.window.close();
  assert.equal(completed, 6, "Every named parity case must execute");
});

test(
  "startup waits for safety, then validation, without a false failure",
  { timeout: 10000 },
  async () => {
    let settleSafety, settleValidation;
    safetyImplementation = () =>
      new Promise((resolve) => {
        settleSafety = resolve;
      });
    inspectImplementation = () =>
      new Promise((resolve) => {
        settleValidation = resolve;
      });
    const before = inspect.mock.callCount();
    render(React.createElement(App));
    assert.equal(inspect.mock.callCount(), before);
    assert.ok(screen.getByRole("heading", { name: "Checking your setup…" }));
    await act(async () => settleSafety(originalRecovery.previewRecovery()));
    await waitFor(() => assert.equal(inspect.mock.callCount(), before + 1));
    assert.ok(screen.getByRole("heading", { name: "Checking your setup…" }));
    assert.equal(
      screen.queryByRole("heading", { name: "Check not finished" }),
      null,
    );
    await act(async () => settleValidation(startupReport()));
    assert.ok(await screen.findByRole("heading", { name: "Ready!" }));
  },
);

test(
  "queued explicit check stays busy and rejects duplicate clicks before admission",
  { timeout: 10000 },
  async () => {
    render(React.createElement(App));
    await screen.findByRole("heading", { name: "Ready!" });
    let admit;
    queueGate = new Promise((resolve) => {
      admit = resolve;
    });
    const before = operate.mock.callCount();
    screen.getByText("Other actions").closest("details").open = true;
    const check = screen.getByRole("button", { name: "Check my setup" });
    fireEvent.click(check);
    fireEvent.click(check);
    assert.ok(screen.getByRole("heading", { name: "Checking your setup…" }));
    assert.equal(operate.mock.callCount(), before);
    await act(async () => admit());
    await waitFor(() => assert.equal(operate.mock.callCount(), before + 1));
    assert.equal(operate.mock.calls.at(-1).arguments[0], "validate");
    assert.equal(neverAcknowledge.mock.callCount(), 0);
  },
);

test(
  "StrictMode effect replay submits one startup sequence and no mutation",
  { timeout: 10000 },
  async () => {
    const safetyBefore = inspectRecovery.mock.callCount();
    const validationBefore = inspect.mock.callCount();
    const operationsBefore = operate.mock.callCount();
    render(
      React.createElement(React.StrictMode, null, React.createElement(App)),
    );
    await screen.findByRole("heading", { name: "Ready!" });
    assert.equal(inspectRecovery.mock.callCount(), safetyBefore + 1);
    assert.equal(inspect.mock.callCount(), validationBefore + 1);
    assert.equal(operate.mock.callCount(), operationsBefore);
  },
);

test(
  "late startup validation cannot redirect navigation",
  { timeout: 10000 },
  async () => {
    let complete;
    inspectImplementation = () =>
      new Promise((resolve) => {
        complete = resolve;
      });
    render(React.createElement(App));
    await waitFor(() => assert.equal(typeof complete, "function"));
    fireEvent.click(screen.getByRole("button", { name: "About" }));
    await act(async () => complete(startupReport()));
    assert.ok(screen.getByRole("heading", { name: "About Skyview Dev Setup" }));
    fireEvent.click(screen.getByRole("button", { name: "Overview" }));
    assert.ok(screen.getByRole("heading", { name: "Ready!" }));
  },
);

test(
  "unmount during pending safety prevents startup validation",
  { timeout: 10000 },
  async () => {
    let complete;
    safetyImplementation = () =>
      new Promise((resolve) => {
        complete = resolve;
      });
    const before = inspect.mock.callCount();
    const app = render(React.createElement(App));
    app.unmount();
    await act(async () => complete(originalRecovery.previewRecovery()));
    assert.equal(inspect.mock.callCount(), before);
  },
);

test(
  "known active work still blocks startup tool inspection",
  { timeout: 10000 },
  async () => {
    const active = originalRecovery.previewRecovery();
    active.effectiveActivity = "active";
    active.readiness = "blocked";
    safetyImplementation = async () => active;
    const before = inspect.mock.callCount();
    render(React.createElement(App));
    await screen.findByRole("heading", { name: "Changes are paused" });
    assert.equal(inspect.mock.callCount(), before);
    assert.equal(
      screen.queryByText(/This workstation could not be checked/),
      null,
    );
    assert.equal(
      screen
        .getByRole("button", { name: "Check again" })
        .hasAttribute("disabled"),
      false,
    );
  },
);
