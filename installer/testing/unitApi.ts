import {
  test as nodeTest,
  describe as nodeDescribe,
  beforeEach,
  afterEach,
  after,
  mock as nodeMock,
} from "node:test";
import { format } from "node:util";
import { writeFileSync } from "node:fs";
import {
  fn,
  spyOn as maintainedSpyOn,
  clearAllMocks,
  resetAllMocks,
  restoreAllMocks,
  isMockFunction,
  type MockedFunction,
} from "@vitest/spy";
import { waitFor } from "@testing-library/dom";
import * as fakeTimers from "@sinonjs/fake-timers";
export { beforeEach, afterEach };
export { expect } from "./assertions";

// Preserve Vitest 5's clearMocks default: histories reset before hooks/cases,
// while mock implementations and queued responses remain intact.
beforeEach(() => clearAllMocks());

const registered: string[] = [],
  completed: string[] = [],
  groups: string[] = [];
let currentURL = "";
const facades = new Map<
  string,
  { backing: Record<string, any>; values: Record<string, any> }
>();
export function configureTest(url: string) {
  currentURL = url;
}
function resolveModule(specifier: string): string {
  return specifier.startsWith(".")
    ? new URL(
        /\.[a-z]+$/.test(specifier) ? specifier : `${specifier}.js`,
        currentURL,
      ).href
    : import.meta.resolve(specifier);
}
function registerFacade(url: string, backing: Record<string, any>) {
  const values: Record<string, any> = {};
  for (const [name, value] of Object.entries(backing)) {
    values[name] =
      typeof value === "function" &&
      !isMockFunction(value) &&
      !/^class\s/.test(Function.prototype.toString.call(value))
        ? function (this: unknown, ...args: unknown[]) {
            return Reflect.apply(backing[name], this, args);
          }
        : value;
  }
  nodeMock.module(url, { cache: true, exports: values });
  facades.set(url, { backing, values });
}
export async function namespaceFacade(specifier: string) {
  const url = resolveModule(specifier);
  if (!facades.has(url)) registerFacade(url, { ...(await import(url)) });
}
function register(name: string, body: (...args: any[]) => any) {
  const full = [...groups, name].join(" ");
  registered.push(full);
  return nodeTest(name, { timeout: 5000 }, async () => {
    try {
      await body();
    } finally {
      completed.push(full);
    }
  });
}
type Row<T> = T extends readonly unknown[] ? [...T] : [T];
export const it = Object.assign(register, {
  each<T>(rows: readonly T[]) {
    return (name: string, body: (...args: Row<T>) => unknown) => {
      for (const row of rows) {
        const args = Array.isArray(row) ? row : [row];
        let index = 0;
        const title = name.replace(/%([sdifjoO%])/g, (token, type) =>
          type === "%" ? "%" : format(token, args[index++]),
        );
        register(title, () => body(...(args as Row<T>)));
      }
    };
  },
});
export const test = it;
export function describe(name: string, body: () => unknown) {
  return nodeDescribe(name, () => {
    groups.push(name);
    try {
      body();
    } finally {
      groups.pop();
    }
  });
}
const globals = new Map<
  string,
  {
    host: PropertyDescriptor | undefined;
    window: PropertyDescriptor | undefined;
  }
>();
let clock: ReturnType<typeof fakeTimers.install> | null = null;
export const vi = {
  fn,
  mocked<T extends (...args: any[]) => any>(value: T): MockedFunction<T> {
    return value as MockedFunction<T>;
  },
  async mock(
    specifier: string,
    factory: (original: <T>() => Promise<T>) => unknown,
  ) {
    if (registered.length)
      throw new Error("Declare module mocks before registering tests");
    const url = resolveModule(specifier);
    const original = <T>() => import(url) as Promise<T>;
    registerFacade(url, (await factory(original)) as Record<string, any>);
  },
  importActual<T>(specifier: string): Promise<T> {
    return import(resolveModule(specifier));
  },
  spyOn: ((target: any, key: string, access?: "get" | "set") => {
    for (const facade of facades.values()) {
      if (
        target?.[key] === facade.values[key] &&
        Object.hasOwn(facade.backing, key)
      )
        return maintainedSpyOn(facade.backing, key, access as any);
    }
    return maintainedSpyOn(target, key, access as any);
  }) as typeof maintainedSpyOn,
  resetAllMocks,
  restoreAllMocks,
  stubGlobal(name: string, value: unknown) {
    if (!globals.has(name))
      globals.set(name, {
        host: Object.getOwnPropertyDescriptor(globalThis, name),
        window: Object.getOwnPropertyDescriptor(window, name),
      });
    Object.defineProperty(globalThis, name, {
      value,
      writable: true,
      configurable: true,
    });
    Object.defineProperty(window, name, {
      value,
      writable: true,
      configurable: true,
    });
  },
  unstubAllGlobals() {
    for (const [name, descriptor] of globals) {
      if (descriptor.host)
        Object.defineProperty(globalThis, name, descriptor.host);
      else Reflect.deleteProperty(globalThis, name);
      if (descriptor.window)
        Object.defineProperty(window, name, descriptor.window);
      else Reflect.deleteProperty(window, name);
    }
    globals.clear();
  },
  useFakeTimers() {
    if (clock) throw new Error("Timers already mocked");
    clock = fakeTimers.install();
  },
  useRealTimers() {
    clock?.uninstall();
    clock = null;
  },
  setSystemTime(value: Date) {
    if (!clock) throw new Error("Mock timers before setting time");
    clock.setSystemTime(value);
  },
  waitFor,
};
function receipt() {
  if (!process.env.SDE_TEST_RECEIPT)
    throw new Error("A case receipt is required");
  writeFileSync(
    process.env.SDE_TEST_RECEIPT,
    JSON.stringify({ registered, completed }),
  );
  if (!registered.length || registered.length !== completed.length)
    process.exitCode = 1;
}
after(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
process.on("exit", receipt);
