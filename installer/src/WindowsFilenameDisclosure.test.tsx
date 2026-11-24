import { beforeEach, afterEach, expect, it, vi } from "../testing/unitApi";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { PreflightReview } from "./PreflightReview";
import { ToolUpdatePreview, useUpdateDiscovery } from "./UpdateCenter";
import { WindowsFilenameDisclosure } from "./WindowsFilenameDisclosure";
import {
  checkPreflight,
  checkTools,
  checkApplication,
} from "./updateDiscovery";
vi.mock("./updateDiscovery", async (original) => ({
  ...(await original<typeof import("./updateDiscovery")>()),
  checkPreflight: vi.fn(),
  checkTools: vi.fn(),
  checkApplication: vi.fn(),
}));
beforeEach(() => {
  vi.resetAllMocks();
  localStorage.clear();
  vi.mocked(checkPreflight).mockResolvedValue([
    { name: "Disk", status: "pass", detail: "Enough space" },
  ]);
  vi.mocked(checkTools).mockResolvedValue({ tools: [], checkedAt: 1 });
  vi.mocked(checkApplication).mockResolvedValue({
    version: "1.2.1",
    checkedAt: 1,
    candidate: null,
    failure: null,
  });
});
afterEach(cleanup);
it("Windows Install discloses the required change before explicit approval", async () => {
  const approve = vi.fn(),
    cancel = vi.fn();
  render(
    <PreflightReview
      operation="install"
      platformSupported
      platformLabel="Windows 11 · x64"
      onContinue={approve}
      onCancel={cancel}
    />,
  );
  await screen.findByText(/prerequisite checks passed/);
  const note = screen.getByRole("complementary", {
    name: "Required Windows setting",
  });
  const button = screen.getByRole("button", { name: "Continue with Install" });
  expect(note.textContent).toContain("replace your current preference");
  expect(
    note.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  expect(approve).not.toHaveBeenCalled();
  fireEvent.click(button);
  expect(approve).toHaveBeenCalledWith(false);
  expect(cancel).not.toHaveBeenCalled();
});
it("Windows Update keeps its disclosure while blockers prevent approval and Cancel stays read-only", async () => {
  vi.mocked(checkPreflight).mockResolvedValue([
    { name: "Package manager", status: "blocking", detail: "Setup is running" },
  ]);
  const approve = vi.fn(),
    cancel = vi.fn();
  function Harness() {
    const data = useUpdateDiscovery([], 0, true);
    return (
      <ToolUpdatePreview
        data={data}
        snapshot={[]}
        platformSupported
        platformLabel="Windows 11"
        onContinue={approve}
        onCancel={cancel}
      />
    );
  }
  render(<Harness />);
  await screen.findByText("Setup is running");
  expect(
    screen.getByRole("complementary", { name: "Required Windows setting" })
      .textContent,
  ).toContain("Update includes a profile setup step");
  expect(
    (
      screen.getByRole("button", {
        name: "Continue with Update",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Continue with Update" }));
  expect(approve).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(cancel).toHaveBeenCalledOnce();
});
it("Mint and unknown platforms receive no Windows claim and the disclosure offers no setting controls", async () => {
  const view = render(
    <WindowsFilenameDisclosure
      platformLabel="Linux Mint 22.3"
      operation="repair"
    />,
  );
  expect(screen.queryByRole("complementary")).toBeNull();
  view.rerender(
    <WindowsFilenameDisclosure
      platformLabel="System check pending"
      operation="repair"
    />,
  );
  expect(screen.queryByRole("complementary")).toBeNull();
  view.rerender(
    <WindowsFilenameDisclosure platformLabel="Windows 11" operation="repair" />,
  );
  expect(screen.getByRole("complementary").textContent).toContain(
    "Repair includes a profile setup step",
  );
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.queryByRole("checkbox")).toBeNull();
});
it("the required-setting explanation cannot acknowledge unavailable preflight information", async () => {
  vi.mocked(checkPreflight).mockRejectedValue(new Error("No preflight result"));
  const approve = vi.fn();
  render(
    <PreflightReview
      operation="install"
      platformSupported
      platformLabel="Windows 11"
      onContinue={approve}
      onCancel={vi.fn()}
    />,
  );
  await screen.findByText(/Preflight could not produce a complete result/);
  expect(screen.getByRole("complementary")).toBeTruthy();
  const check = screen.getByRole("checkbox") as HTMLInputElement;
  const button = screen.getByRole("button", {
    name: "Continue with Install",
  }) as HTMLButtonElement;
  expect(check.checked).toBe(false);
  expect(button.disabled).toBe(true);
  expect(approve).not.toHaveBeenCalled();
  fireEvent.click(check);
  fireEvent.click(button);
  expect(approve).toHaveBeenCalledWith(true);
});
