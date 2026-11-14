import { expect, it, vi } from "vitest";
import { NativeReadQueue, type ReadSequence } from "./nativeReadQueue";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

it("keeps diagnostics behind both phases of the owner's read sequence", async () => {
  const queue = new NativeReadQueue();
  const safety = deferred<void>();
  const validation = deferred<void>();
  const calls: string[] = [];
  const startup = queue.sequence(async (lease) => {
    await queue.read(async () => {
      calls.push("safety");
      await safety.promise;
    }, lease);
    await queue.read(async () => {
      calls.push("validation");
      await validation.promise;
    }, lease);
  });
  const diagnostic = queue.read(async () => {
    calls.push("diagnostic");
  });
  await vi.waitFor(() => expect(calls).toEqual(["safety"]));
  safety.resolve();
  await vi.waitFor(() => expect(calls).toEqual(["safety", "validation"]));
  validation.resolve();
  await Promise.all([startup, diagnostic]);
  expect(calls).toEqual(["safety", "validation", "diagnostic"]);
});

it("does not retry a failed read and lets the next request run", async () => {
  const queue = new NativeReadQueue();
  const failed = vi.fn(async () => {
    throw new Error("Unavailable");
  });
  const next = vi.fn(async () => "current");
  const first = queue.read(failed);
  const second = queue.read(next);
  await expect(first).rejects.toThrow("Unavailable");
  await expect(second).resolves.toBe("current");
  expect(failed).toHaveBeenCalledTimes(1);
  expect(next).toHaveBeenCalledTimes(1);
});

it("rejects a stale scheduling identity rather than entering a different sequence", async () => {
  const queue = new NativeReadQueue();
  let old!: ReadSequence;
  await queue.sequence(async (lease) => {
    old = lease;
  });
  const read = vi.fn(async () => "not run");
  await expect(queue.read(read, old)).rejects.toThrow("no longer current");
  expect(read).not.toHaveBeenCalled();
  await expect(queue.read(async () => "fresh")).resolves.toBe("fresh");
});
