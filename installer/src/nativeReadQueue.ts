import { isTauri } from "@tauri-apps/api/core";

// A same-window scheduling identity, never native permission or cached safety.
const identity = Symbol("read-sequence");
export type ReadSequence = { readonly [identity]: true };

export class NativeReadQueue {
  private tail: Promise<void> = Promise.resolve();
  private active: ReadSequence | undefined;

  sequence<T>(task: (lease: ReadSequence) => Promise<T>): Promise<T> {
    const result = this.tail.then(async () => {
      const lease: ReadSequence = { [identity]: true };
      this.active = lease;
      try {
        return await task(lease);
      } finally {
        this.active = undefined;
      }
    });
    // Failed reads are still failures to their caller; they cannot poison the queue.
    this.tail = result.then(
      () => {},
      () => {},
    );
    return result;
  }

  read<T>(task: () => Promise<T>, lease?: ReadSequence): Promise<T> {
    if (!lease) return this.sequence(task);
    if (lease !== this.active)
      return Promise.reject(
        new Error("The read sequence is no longer current."),
      );
    // The outer sequence already owns scheduling: do not enqueue recursively.
    return Promise.resolve().then(task);
  }
}

const queue = new NativeReadQueue();

export function withNativeReadSequence<T>(
  task: (lease?: ReadSequence) => Promise<T>,
  enabled = true,
): Promise<T> {
  // Preview has no native gate. Mutations never enter this read-only queue.
  return enabled && isTauri() ? queue.sequence(task) : task();
}

export function nativeRead<T>(
  task: () => Promise<T>,
  lease?: ReadSequence,
): Promise<T> {
  return queue.read(task, lease);
}
