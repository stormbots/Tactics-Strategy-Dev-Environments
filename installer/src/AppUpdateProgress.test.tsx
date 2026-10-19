import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { AppUpdateProgress } from "./AppUpdateProgress";
import { AppReleaseCheck } from "./AppReleaseCheck";
import {
  discoverAppUpdate,
  inspectAppUpdateProgress,
  closeForAppUpdate,
  requestAppUpdate,
} from "./bridge";
import {
  acceptProgress,
  parseUpdateProgress,
  parseReleaseCheck,
  type UpdateProgress,
} from "./appUpdate";
vi.mock("./bridge", () => ({
  discoverAppUpdate: vi.fn(),
  inspectAppUpdateProgress: vi.fn(),
  closeForAppUpdate: vi.fn(),
  requestAppUpdate: vi.fn(),
}));
const id = "00000000-0000-4000-8000-000000000001";
const boot = "00000000-0000-4000-8000-000000000002";
function fixture(p: Partial<UpdateProgress> = {}): UpdateProgress {
  return {
    requestId: id,
    bootId: boot,
    sequence: 4,
    state: "ready",
    observedMs: 20_000,
    ageMs: 0,
    remainingMs: 120_000,
    fresh: true,
    candidateVersion: "1.2.2",
    candidateSha256: "a".repeat(64),
    closeAllowed: false,
    ...p,
  };
}
beforeEach(() => {
  vi.useFakeTimers({
    toFake: [
      "setTimeout",
      "clearTimeout",
      "setInterval",
      "clearInterval",
      "performance",
    ],
  });
  vi.mocked(inspectAppUpdateProgress).mockReset();
  vi.mocked(discoverAppUpdate).mockReset();
  vi.mocked(closeForAppUpdate).mockReset();
  vi.mocked(requestAppUpdate).mockReset();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
const flush = async () => {
  await act(async () => {
    await Promise.resolve();
  });
};
it("fresh ready is advisory, never close/installation authority", async () => {
  vi.mocked(inspectAppUpdateProgress).mockResolvedValue(fixture());
  render(<AppUpdateProgress requestId={id} />);
  await flush();
  expect(
    screen.getByText(/Last protected report: Ready to install/),
  ).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Close SDE & install",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(closeForAppUpdate).not.toHaveBeenCalled();
  expect(requestAppUpdate).not.toHaveBeenCalled();
});
it("local aging and repeated same-publication polls cannot manufacture fresh progress", async () => {
  vi.mocked(inspectAppUpdateProgress).mockImplementation(async () =>
    fixture({ ageMs: performance.now() }),
  );
  render(<AppUpdateProgress requestId={id} />);
  await flush();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(11_000);
  });
  expect(screen.getByText(/observation is stale or expired/)).toBeTruthy();
  expect(closeForAppUpdate).not.toHaveBeenCalled();
});
it.each(["rejected", "hung"])(
  "%s read clears ready rather than implying cancellation and stops polling",
  async (kind) => {
    vi.mocked(inspectAppUpdateProgress).mockResolvedValueOnce(fixture());
    if (kind === "rejected")
      vi.mocked(inspectAppUpdateProgress).mockRejectedValue(
        new Error("private paths"),
      );
    else
      vi.mocked(inspectAppUpdateProgress).mockReturnValue(
        new Promise(() => {}),
      );
    render(<AppUpdateProgress requestId={id} />);
    await flush();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(8000);
    });
    expect(screen.getByText(/Protected progress is unavailable/)).toBeTruthy();
    expect(screen.queryByRole("button")).toBeNull();
    const calls = vi.mocked(inspectAppUpdateProgress).mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(20_000);
    });
    expect(inspectAppUpdateProgress).toHaveBeenCalledTimes(calls);
    expect(screen.queryByText(/private paths/)).toBeNull();
  },
);
it.each([
  "current",
  "paused",
  "deferred",
  "updated",
  "recoveryRequired",
] as const)(
  "%s is an observed outcome and never clears a barrier",
  async (state) => {
    vi.mocked(inspectAppUpdateProgress).mockResolvedValue(fixture({ state }));
    render(<AppUpdateProgress requestId={id} />);
    await flush();
    expect(
      screen.getByText(/not clearance of a startup or recovery barrier/),
    ).toBeTruthy();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4000);
    });
    expect(inspectAppUpdateProgress).toHaveBeenCalledTimes(1);
  },
);
it("bounded 15-minute polling does not start another attempt", async () => {
  let seq = 0;
  vi.mocked(inspectAppUpdateProgress).mockImplementation(async () => {
    seq++;
    return fixture({
      sequence: 1,
      state: "preparing",
      candidateVersion: null,
      candidateSha256: null,
      ageMs: performance.now(),
      fresh: performance.now() <= 10000,
    });
  });
  render(<AppUpdateProgress requestId={id} />);
  await flush();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(905_000);
  });
  expect(seq).toBeLessThanOrEqual(450);
  expect(screen.getByText(/Protected progress is unavailable/)).toBeTruthy();
  expect(requestAppUpdate).not.toHaveBeenCalled();
});
it("request switch and unmount discard late old replies and timers", async () => {
  let resolve!: (p: UpdateProgress) => void;
  vi.mocked(inspectAppUpdateProgress)
    .mockReturnValueOnce(
      new Promise((r) => {
        resolve = r;
      }),
    )
    .mockResolvedValue(fixture({ requestId: boot, state: "updated" }));
  const view = render(<AppUpdateProgress requestId={id} />);
  view.rerender(<AppUpdateProgress requestId={boot} />);
  await flush();
  await act(async () => resolve(fixture()));
  expect(
    screen.queryByRole("button", { name: "Close SDE & install" }),
  ).toBeNull();
  view.unmount();
  const calls = vi.mocked(inspectAppUpdateProgress).mock.calls.length;
  await act(async () => {
    await vi.advanceTimersByTimeAsync(20_000);
  });
  expect(inspectAppUpdateProgress).toHaveBeenCalledTimes(calls);
});
it("rejects malformed, foreign, permission-bearing and inconsistent progress", () => {
  for (const change of [
    { requestId: boot },
    { bootId: "bad" },
    { sequence: 0 },
    { sequence: 33 },
    { state: "cancel" },
    { ageMs: -1 },
    { ageMs: 10001 },
    { remainingMs: 900001 },
    { closeAllowed: true },
    { candidateSha256: "bad" },
    { candidateVersion: null },
    { remainingMs: 0 },
    { extra: true },
  ]) {
    expect(() =>
      parseUpdateProgress({ ...fixture(), ...change }, id),
    ).toThrow();
  }
});
it("rejects replay mutation, sequence/phase regression, candidate changes and terminal resurrection", () => {
  const old = fixture();
  for (const next of [
    fixture({ sequence: 3 }),
    fixture({ state: "installing" }),
    fixture({ sequence: 5, state: "downloading" }),
    fixture({ candidateSha256: "b".repeat(64), sequence: 5 }),
    fixture({ remainingMs: 120001 }),
    fixture({ observedMs: 19999, sequence: 5 }),
  ])
    expect(() => acceptProgress(old, next)).toThrow();
  expect(() =>
    acceptProgress(
      fixture({ state: "updated" }),
      fixture({ sequence: 5, state: "ready" }),
    ),
  ).toThrow();
  expect(
    acceptProgress(old, fixture({ ageMs: 1000, remainingMs: 119000 })).ageMs,
  ).toBe(1000);
});
it("release validation requires exact typed metadata and never yields execution authority", () => {
  for (const v of [
    { status: "available", candidate: null },
    {
      status: "available",
      candidate: { version: "1.2.2", tag: "v1.2.3", sha256: "a".repeat(64) },
    },
    { status: "current", candidate: null },
    { status: "no_newer_listing", candidate: null, enabled: true },
  ])
    expect(() => parseReleaseCheck(v)).toThrow();
  expect(
    parseReleaseCheck({ status: "no_newer_listing", candidate: null }).status,
  ).toBe("no_newer_listing");
});
it("release checking is explicit and a metadata result never submits an update", async () => {
  vi.mocked(discoverAppUpdate).mockResolvedValue({
    status: "available",
    candidate: { version: "1.2.2", tag: "v1.2.2", sha256: "a".repeat(64) },
  });
  render(<AppReleaseCheck />);
  expect(discoverAppUpdate).not.toHaveBeenCalled();
  const { fireEvent } = await import("@testing-library/react");
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "Check SDE release" })),
  );
  expect(
    screen.getByText(/Signed metadata verified for SDE 1.2.2/),
  ).toBeTruthy();
  expect(requestAppUpdate).not.toHaveBeenCalled();
});
it("late discovery after the watchdog cannot replace an unavailable result", async () => {
  let resolve!: (v: Awaited<ReturnType<typeof discoverAppUpdate>>) => void;
  vi.mocked(discoverAppUpdate).mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  render(<AppReleaseCheck />);
  const { fireEvent } = await import("@testing-library/react");
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "Check SDE release" })),
  );
  await act(async () => {
    await vi.advanceTimersByTimeAsync(20_001);
  });
  await act(async () =>
    resolve({ status: "no_newer_listing", candidate: null }),
  );
  expect(screen.getByText(/could not be verified/)).toBeTruthy();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(20_000);
  });
  expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(true);
});

it.each(["ready", "downloading"] as const)(
  "%s view has accessible names and no automatic action",
  async (state) => {
    vi.useRealTimers();
    vi.mocked(inspectAppUpdateProgress).mockResolvedValue(fixture({ state }));
    const { container } = render(<AppUpdateProgress requestId={id} />);
    await flush();
    const axe = (await import("axe-core")).default;
    expect(
      (
        await axe.run(container, {
          rules: { "color-contrast": { enabled: false } },
        })
      ).violations,
    ).toEqual([]);
    expect(requestAppUpdate).not.toHaveBeenCalled();
    expect(closeForAppUpdate).not.toHaveBeenCalled();
  },
);

it("cached same-age replies cannot restart the freshness clock", async () => {
  vi.mocked(inspectAppUpdateProgress).mockResolvedValue(fixture());
  render(<AppUpdateProgress requestId={id} />);
  await flush();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(11_000);
  });
  expect(screen.getByText(/observation is stale or expired/)).toBeTruthy();
  expect(closeForAppUpdate).not.toHaveBeenCalled();
});

it("discovery cooldown never retries automatically", async () => {
  vi.mocked(discoverAppUpdate).mockResolvedValue({
    status: "no_newer_listing",
    candidate: null,
  });
  render(<AppReleaseCheck />);
  const { fireEvent } = await import("@testing-library/react");
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "Check SDE release" })),
  );
  expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(true);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(30_001);
  });
  expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(
    false,
  );
  expect(discoverAppUpdate).toHaveBeenCalledTimes(1);
});
