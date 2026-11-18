import assert from "node:assert/strict";
import {
  it,
  vi,
  expect,
  configureTest,
  namespaceFacade,
} from "../.test-output/unit/testing/unitApi.js";
const directory = new URL("../.test-output/unit/testing/", import.meta.url);
configureTest(new URL("runner.conformance.mjs", directory).href);
const actual = await vi.importActual("./mock-fixture.js");
await vi.mock("./mock-fixture.js", async (original) => ({
  ...(await original()),
  read: vi.fn(() => "mocked"),
}));
const mocked = await import(new URL("mock-fixture.js", directory).href);
await namespaceFacade("./spy-fixture.js");
const spyNamespace = await import(new URL("spy-fixture.js", directory).href);
it("module mocks preserve original imports and change later imports", () => {
  assert.equal(actual.read(), "actual");
  assert.equal(mocked.read(), "mocked");
  expect(mocked.read).toHaveBeenCalledExactlyOnceWith();
});
it("maintained mock queues, reset, call matching and asymmetric assertions stay exact", () => {
  const fn = vi
    .fn(() => 3)
    .mockReturnValueOnce(1)
    .mockReturnValueOnce(2);
  assert.deepEqual([fn(), fn(), fn()], [1, 2, 3]);
  expect(fn).toHaveBeenCalledTimes(3);
  fn.mockReset();
  expect(fn).not.toHaveBeenCalled();
  fn({ required: "value", extra: 7 });
  expect(fn).toHaveBeenCalledExactlyOnceWith(
    expect.objectContaining({ required: expect.any(String) }),
  );
  assert.throws(() => expect(fn).toHaveBeenCalledTimes(9));
});
it("namespace spies affect shared bindings and restore the original function", () => {
  const spy = vi.spyOn(spyNamespace, "read").mockReturnValueOnce("overridden");
  assert.equal(spyNamespace.read(), "overridden");
  expect(spy).toHaveBeenCalledOnce();
  spy.mockRestore();
  assert.equal(spyNamespace.read(), "actual");
});
it("global stubs cover the DOM and host and restore both descriptors", () => {
  const host = Object.getOwnPropertyDescriptor(globalThis, "matchMedia");
  const dom = Object.getOwnPropertyDescriptor(window, "matchMedia");
  const replacement = vi.fn();
  vi.stubGlobal("matchMedia", replacement);
  assert.equal(globalThis.matchMedia, replacement);
  assert.equal(window.matchMedia, replacement);
  vi.unstubAllGlobals();
  assert.deepEqual(
    Object.getOwnPropertyDescriptor(globalThis, "matchMedia"),
    host,
  );
  assert.deepEqual(Object.getOwnPropertyDescriptor(window, "matchMedia"), dom);
});
it("fake time and awaited rejection assertions retain failure semantics", async () => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-26T12:00:00Z"));
  assert.equal(new Date().toISOString(), "2026-10-26T12:00:00.000Z");
  vi.useRealTimers();
  await expect(Promise.resolve(7)).resolves.toBe(7);
  await expect(Promise.reject(new Error("expected"))).rejects.toThrow(
    "expected",
  );
  await assert.rejects(async () => {
    await expect(Promise.resolve(7)).resolves.toBe(8);
  });
  assert.throws(() => expect("same").not.toBe("same"));
});

const crossCaseMock = vi
  .fn(() => "retained implementation")
  .mockReturnValueOnce("first queued response")
  .mockReturnValueOnce("second queued response");
it("a case records its own mock calls", () => {
  expect(crossCaseMock).not.toHaveBeenCalled();
  expect(crossCaseMock()).toBe("first queued response");
  expect(crossCaseMock).toHaveBeenCalledOnce();
});
it("the next case has clean call history and retained response queues", () => {
  expect(crossCaseMock).not.toHaveBeenCalled();
  expect(crossCaseMock()).toBe("second queued response");
  expect(crossCaseMock()).toBe("retained implementation");
  expect(crossCaseMock).toHaveBeenCalledTimes(2);
});
