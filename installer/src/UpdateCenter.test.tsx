import { beforeEach, afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
} from "@testing-library/react";
import {
  ApplicationUpdates,
  ToolUpdatePreview,
  useUpdateDiscovery,
} from "./UpdateCenter";
import {
  checkApplication,
  checkTools,
  checkPreflight,
  openRelease,
  type AppDiscovery,
  type ToolPreview,
} from "./updateDiscovery";
import type { ToolRecord } from "./model";
vi.mock("./updateDiscovery", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./updateDiscovery")>()),
  checkApplication: vi.fn(),
  checkTools: vi.fn(),
  checkPreflight: vi.fn(),
  openRelease: vi.fn(),
}));
const tool: ToolRecord = {
  tool: "Git",
  installedVersion: "2.43.0",
  availableVersion: null,
  updateAvailable: false,
  updateCheck: "notChecked",
};
const available = (version = "1.2.14"): AppDiscovery => ({
  version: "1.2.13",
  checkedAt: 100,
  candidate: {
    tag: `v${version}`,
    version,
    platform: "windows-x86_64",
    installer: "Skyview-Dev-Setup-Windows-x64.exe",
  },
  failure: null,
});
beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  vi.mocked(checkApplication).mockResolvedValue(available());
  vi.mocked(checkTools).mockResolvedValue({
    tools: [{ ...tool, updateCheck: "current" }],
    checkedAt: 100,
  });
  vi.mocked(checkPreflight).mockResolvedValue([
    { name: "Disk", status: "pass", detail: "Enough space" },
  ]);
});
afterEach(cleanup);
it("deduplicates checks and rejects a late pre-operation tool result", async () => {
  let complete!: (p: ToolPreview) => void;
  vi.mocked(checkTools).mockReturnValueOnce(
    new Promise((resolve) => {
      complete = resolve;
    }),
  );
  const { result, rerender } = renderHook(
    ({ generation, enabled }) =>
      useUpdateDiscovery([tool], generation, enabled),
    { initialProps: { generation: 0, enabled: true } },
  );
  await waitFor(() => expect(checkTools).toHaveBeenCalledTimes(1));
  act(() => {
    void result.current.refreshTools();
    void result.current.refreshTools();
  });
  expect(checkTools).toHaveBeenCalledTimes(1);
  rerender({ generation: 1, enabled: false });
  await act(async () =>
    complete({
      tools: [
        {
          ...tool,
          availableVersion: "9.0.0",
          updateAvailable: true,
          updateCheck: "current",
        },
      ],
      checkedAt: 100,
    }),
  );
  expect(result.current.preview).toBeNull();
  rerender({ generation: 1, enabled: true });
  await waitFor(() =>
    expect(result.current.preview?.tools[0].updateAvailable).toBe(false),
  );
});
it("dismissal belongs to one version and a later version is announced", async () => {
  function Harness() {
    const data = useUpdateDiscovery([], 0, false);
    return <ApplicationUpdates data={data} about />;
  }
  render(<Harness />);
  await screen.findByText(/SDE 1.2.14 is available/);
  fireEvent.click(screen.getByRole("button", { name: "Dismiss this version" }));
  expect(localStorage.getItem("sde-dismissed-release")).toBe("v1.2.14");
  expect(
    screen.queryByRole("button", { name: "Dismiss this version" }),
  ).toBeNull();
  vi.mocked(checkApplication).mockResolvedValueOnce(available("1.2.15"));
  fireEvent.click(
    screen.getByRole("button", { name: "Check for SDE updates" }),
  );
  await screen.findByText(/SDE 1.2.15 is available/);
  expect(
    screen.getByRole("button", { name: "Dismiss this version" }),
  ).toBeTruthy();
  fireEvent.click(
    screen.getByRole("button", { name: "Download SDE installer" }),
  );
  expect(openRelease).toHaveBeenCalledWith("v1.2.15", true);
});
it("failed refresh retains successful check time and never says current", async () => {
  function Harness() {
    const data = useUpdateDiscovery([], 0, false);
    return <ApplicationUpdates data={data} about />;
  }
  render(<Harness />);
  await screen.findByText(/SDE 1.2.14 is available/);
  const previous = screen.getByText(/Last successful SDE check/).textContent;
  vi.mocked(checkApplication).mockResolvedValueOnce({
    ...available(),
    candidate: null,
    checkedAt: 200,
    failure: "rateLimited",
  });
  fireEvent.click(
    screen.getByRole("button", { name: "Check for SDE updates" }),
  );
  await screen.findByText(/GitHub temporarily limited/);
  expect(screen.getByText(/Last successful SDE check/).textContent).toBe(
    previous,
  );
  expect(
    screen.queryByRole("button", { name: "Download SDE installer" }),
  ).toBeNull();
});
it("preflight blockers prevent confirmation, and cancellation starts no operation", async () => {
  vi.mocked(checkPreflight).mockResolvedValueOnce([
    {
      name: "Package manager",
      status: "blocking",
      detail: "Another operation holds a lock",
    },
  ]);
  const onContinue = vi.fn(),
    onCancel = vi.fn();
  function Harness() {
    const data = useUpdateDiscovery([tool], 0, true);
    return (
      <ToolUpdatePreview
        data={data}
        snapshot={[tool]}
        platformSupported
        onContinue={onContinue}
        onCancel={onCancel}
      />
    );
  }
  render(<Harness />);
  await screen.findByText(/Another operation holds a lock/);
  expect(
    (
      screen.getByRole("button", {
        name: "Continue with Update",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Continue with Update" }));
  expect(onContinue).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(onCancel).toHaveBeenCalledOnce();
});
it("unavailable preflight checks need explicit acknowledgement", async () => {
  vi.mocked(checkPreflight).mockResolvedValueOnce([
    {
      name: "Package source",
      status: "unavailable",
      detail: "Source unavailable",
    },
  ]);
  const onContinue = vi.fn();
  function Harness() {
    const data = useUpdateDiscovery([tool], 0, true);
    return (
      <ToolUpdatePreview
        data={data}
        snapshot={[tool]}
        platformSupported
        onContinue={onContinue}
        onCancel={() => {}}
      />
    );
  }
  render(<Harness />);
  await screen.findByText(/Source unavailable/);
  const button = screen.getByRole("button", {
    name: "Continue with Update",
  }) as HTMLButtonElement;
  expect(button.disabled).toBe(true);
  fireEvent.click(screen.getByRole("checkbox"));
  expect(button.disabled).toBe(false);
  fireEvent.click(button);
  expect(onContinue).toHaveBeenCalledOnce();
});
it("a failed request clears an old download offer without claiming current", async () => {
  function Harness() {
    const data = useUpdateDiscovery([], 0, false);
    return <ApplicationUpdates data={data} about />;
  }
  render(<Harness />);
  await screen.findByRole("button", { name: "Download SDE installer" });
  vi.mocked(checkApplication).mockRejectedValueOnce(
    new Error("raw server detail"),
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Check for SDE updates" }),
  );
  await screen.findByText(/SDE discovery could not finish/);
  expect(
    screen.queryByRole("button", { name: "Download SDE installer" }),
  ).toBeNull();
  expect(screen.queryByText(/raw server detail/)).toBeNull();
});
it("honors a server supplied retry time", async () => {
  vi.mocked(checkApplication).mockResolvedValueOnce({
    ...available(),
    candidate: null,
    failure: "rateLimited",
    retryAt: Date.now() / 1000 + 600,
  });
  function Harness() {
    const data = useUpdateDiscovery([], 0, false);
    return <ApplicationUpdates data={data} about />;
  }
  render(<Harness />);
  await screen.findByText(/GitHub requested another check after/);
  expect(
    (
      screen.getByRole("button", {
        name: "Check for SDE updates",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
});
