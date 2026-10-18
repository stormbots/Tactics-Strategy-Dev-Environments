import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { AppUpdateControl } from "./AppUpdateControl";
import {
  inspectAppUpdate,
  requestAppUpdate,
  inspectAppUpdateProgress,
} from "./bridge";
import { parseAppUpdate } from "./appUpdate";
vi.mock("./bridge", () => ({
  inspectAppUpdate: vi.fn(),
  requestAppUpdate: vi.fn(),
  inspectAppUpdateProgress: vi.fn(),
}));
beforeEach(() => {
  vi.mocked(inspectAppUpdate).mockReset();
  vi.mocked(requestAppUpdate).mockReset();
  vi.mocked(inspectAppUpdateProgress).mockReset();
});
afterEach(cleanup);
it("real backend contract and every unknown/forged eligibility reply fail closed", () => {
  for (const value of [
    null,
    {},
    { enabled: true, reason: "native_validation_pending" },
    { enabled: false, reason: "future" },
    "enabled",
  ]) {
    expect(parseAppUpdate(value).enabled).toBe(false);
  }
  expect(
    parseAppUpdate({ enabled: false, reason: "native_validation_pending" }),
  ).toEqual({ enabled: false, reason: "native_validation_pending" });
});
it("stays disabled while loading and after native validation-pending discovery", async () => {
  let resolve!: (value: Awaited<ReturnType<typeof inspectAppUpdate>>) => void;
  vi.mocked(inspectAppUpdate).mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  render(<AppUpdateControl />);
  expect(
    (screen.getByRole("button", { name: "Update Now" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  await act(async () =>
    resolve({ enabled: false, reason: "native_validation_pending" }),
  );
  expect(screen.getByText(/not enabled on this installation/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Update Now" }));
  expect(requestAppUpdate).not.toHaveBeenCalled();
});
it("read failure is unavailable, never a claim that SDE is current", async () => {
  vi.mocked(inspectAppUpdate).mockRejectedValue(
    new Error("secret backend details"),
  );
  render(<AppUpdateControl />);
  await screen.findByText(/availability could not be confirmed/);
  expect(screen.queryByText(/secret backend details/)).toBeNull();
  expect(requestAppUpdate).not.toHaveBeenCalled();
});
async function consentFixture() {
  // Test-only eligibility. Neither real bridge nor native backend can enable it.
  vi.mocked(inspectAppUpdate).mockResolvedValue({
    enabled: true,
    reason: "unavailable",
  });
  render(<AppUpdateControl />);
  await waitFor(() =>
    expect(
      (screen.getByRole("button", { name: "Update Now" }) as HTMLButtonElement)
        .disabled,
    ).toBe(false),
  );
  fireEvent.click(screen.getByRole("button", { name: "Update Now" }));
}
it("requires explicit upfront consent and supports backing out before authorization", async () => {
  await consentFixture();
  expect(document.activeElement).toBe(
    screen.getByRole("heading", { name: "Authorize an SDE update" }),
  );
  expect(screen.getByText(/crash may allow installation/)).toBeTruthy();
  expect(screen.getByText(/15 minutes/)).toBeTruthy();
  expect(screen.getByText(/final policy check/)).toBeTruthy();
  const authorize = screen.getByRole("button", {
    name: "Authorize update",
  }) as HTMLButtonElement;
  expect(authorize.disabled).toBe(true);
  fireEvent.click(authorize);
  expect(requestAppUpdate).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Back" }));
  await waitFor(() =>
    expect(document.activeElement).toBe(
      screen.getByRole("button", { name: "Update Now" }),
    ),
  );
  fireEvent.click(screen.getByRole("button", { name: "Update Now" }));
  expect((screen.getByRole("checkbox") as HTMLInputElement).checked).toBe(
    false,
  );
});
it.each(["reject", "unexpected success"])(
  "%s never claims preparation, cancellation, completion or allows retry",
  async (outcome) => {
    let settle!: () => void;
    vi.mocked(requestAppUpdate).mockReturnValue(
      new Promise<never>((resolve, reject) => {
        settle = () =>
          outcome === "reject"
            ? reject(new Error("private authorization detail"))
            : resolve(undefined as never);
      }),
    );
    await consentFixture();
    fireEvent.click(screen.getByRole("checkbox"));
    const submit = screen.getByRole("button", { name: "Authorize update" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    expect(requestAppUpdate).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Back" })).toBeNull();
    expect(screen.getByText(/Waiting for system authorization/)).toBeTruthy();
    await act(async () => settle());
    expect(
      screen.getByText(/No installation request was confirmed/),
    ).toBeTruthy();
    expect(screen.queryByText(/private authorization detail/)).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  },
);
it("late discovery after unmount cannot submit anything", async () => {
  let resolve!: (value: Awaited<ReturnType<typeof inspectAppUpdate>>) => void;
  vi.mocked(inspectAppUpdate).mockReturnValue(
    new Promise((r) => {
      resolve = r;
    }),
  );
  const view = render(<AppUpdateControl />);
  view.unmount();
  await act(async () => resolve({ enabled: true, reason: "unavailable" }));
  expect(requestAppUpdate).not.toHaveBeenCalled();
});

it("does not attach progress from URL or local storage without a correlated request", async () => {
  const id = "00000000-0000-4000-8000-000000000001";
  const previous = location.href;
  history.replaceState({}, "", `?requestId=${id}`);
  localStorage.setItem("sde-update-request", id);
  try {
    vi.mocked(inspectAppUpdate).mockResolvedValue({
      enabled: false,
      reason: "native_validation_pending",
    });
    render(<AppUpdateControl />);
    await screen.findByText(/not enabled on this installation/);
    expect(inspectAppUpdateProgress).not.toHaveBeenCalled();
    expect(requestAppUpdate).not.toHaveBeenCalled();
  } finally {
    history.replaceState({}, "", previous);
    localStorage.removeItem("sde-update-request");
  }
});
