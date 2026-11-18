import { AssertionError } from "node:assert";
import { createRequire } from "node:module";
import type { Locator } from "playwright-core";
import { expect as valueExpect } from "./assertions";
import type { Assertion } from "@vitest/expect";
const require = createRequire(import.meta.url);
if (require("playwright-core/package.json").version !== "1.63.0")
  throw new Error(
    "Review browser assertion protocol before updating Playwright core",
  );
type Text = string | RegExp;
type Options = {
  timeout?: number;
  ignoreCase?: boolean;
  useInnerText?: boolean;
  ratio?: number;
  checked?: boolean;
  indeterminate?: boolean;
  pseudo?: string;
  visible?: boolean;
  enabled?: boolean;
};
type Result = {
  matches: boolean;
  received?: unknown;
  log?: string[];
  timedOut?: boolean;
  errorMessage?: string;
};
// Pinned Playwright core protocol. Preserve its native retry, strict locator,
// visibility, whitespace, regex and cancellation semantics; do not approximate DOM checks.
interface ExpectingLocator extends Locator {
  _expect(
    expression: string,
    options: Record<string, unknown>,
  ): Promise<Result>;
}
let signal: AbortSignal | undefined;
export function assertionSignal(value: AbortSignal | undefined) {
  const previous = signal;
  signal = value;
  return previous;
}
function text(values: Text[], options: Record<string, unknown> = {}) {
  return values.map((value) => ({
    string: typeof value === "string" ? value : undefined,
    regexSource: value instanceof RegExp ? value.source : undefined,
    regexFlags: value instanceof RegExp ? value.flags : undefined,
    ...options,
  }));
}
class BrowserAssertion {
  constructor(
    private locator: Locator,
    private negative = false,
  ) {}
  get not() {
    return new BrowserAssertion(this.locator, !this.negative);
  }
  private async check(
    expression: string,
    data: Record<string, unknown> = {},
    options: Options = {},
  ) {
    const locator = this.locator as ExpectingLocator;
    if (typeof locator._expect !== "function")
      throw new Error("Pinned browser expectation method is unavailable");
    const result = await locator._expect(expression, {
      ...data,
      isNot: this.negative,
      timeout: options.timeout ?? 5000,
      signal,
    });
    if (!result || typeof result.matches !== "boolean")
      throw new Error("Browser core returned an incomplete assertion result");
    if (
      result.matches === this.negative ||
      result.errorMessage ||
      result.timedOut
    )
      throw new AssertionError({
        message: `${this.negative ? "not " : ""}${expression}: ${result.errorMessage ?? result.log?.join("\n") ?? "expectation did not match"}`,
        actual: result.received,
        expected: data,
      });
  }
  toBeVisible(options: Options = {}) {
    return this.check(
      options.visible === false ? "to.be.hidden" : "to.be.visible",
      {},
      options,
    );
  }
  toBeHidden(options: Options = {}) {
    return this.check("to.be.hidden", {}, options);
  }
  toBeFocused(options: Options = {}) {
    return this.check("to.be.focused", {}, options);
  }
  toBeDisabled(options: Options = {}) {
    return this.check("to.be.disabled", {}, options);
  }
  toBeEnabled(options: Options = {}) {
    return this.check(
      options.enabled === false ? "to.be.disabled" : "to.be.enabled",
      {},
      options,
    );
  }
  toBeChecked(options: Options = {}) {
    return this.check(
      "to.be.checked",
      {
        expectedValue: {
          checked: options.checked,
          indeterminate: options.indeterminate,
        },
      },
      options,
    );
  }
  toBeInViewport(options: Options = {}) {
    return this.check(
      "to.be.in.viewport",
      { expectedNumber: options.ratio },
      options,
    );
  }
  toHaveCount(value: number, options: Options = {}) {
    return this.check("to.have.count", { expectedNumber: value }, options);
  }
  toHaveAttribute(name: string, expected?: Text, options: Options = {}) {
    return this.check(
      expected === undefined ? "to.have.attribute" : "to.have.attribute.value",
      {
        expressionArg: name,
        ...(expected === undefined
          ? {}
          : {
              expectedText: text([expected], {
                ignoreCase: options.ignoreCase,
              }),
            }),
      },
      options,
    );
  }
  toHaveCSS(name: string, expected: Text, options: Options = {}) {
    return this.check(
      "to.have.css",
      {
        expressionArg: name,
        expectedText: text([expected]),
        pseudo: options.pseudo,
      },
      options,
    );
  }
  toHaveClass(expected: Text | Text[], options: Options = {}) {
    return this.check(
      Array.isArray(expected) ? "to.have.class.array" : "to.have.class",
      { expectedText: text(Array.isArray(expected) ? expected : [expected]) },
      options,
    );
  }
  toHaveText(expected: Text | Text[], options: Options = {}) {
    return this.check(
      Array.isArray(expected) ? "to.have.text.array" : "to.have.text",
      {
        expectedText: text(Array.isArray(expected) ? expected : [expected], {
          normalizeWhiteSpace: true,
          ignoreCase: options.ignoreCase,
        }),
        useInnerText: options.useInnerText,
      },
      options,
    );
  }
  toContainText(expected: Text | Text[], options: Options = {}) {
    return this.check(
      Array.isArray(expected) ? "to.contain.text.array" : "to.have.text",
      {
        expectedText: text(Array.isArray(expected) ? expected : [expected], {
          matchSubstring: true,
          normalizeWhiteSpace: true,
          ignoreCase: options.ignoreCase,
        }),
        useInnerText: options.useInnerText,
      },
      options,
    );
  }
}
export function expect(value: Locator, message?: string): BrowserAssertion;
export function expect(value: unknown, message?: string): Assertion;
export function expect(value: unknown, message?: string) {
  return value &&
    typeof value === "object" &&
    typeof (value as { _expect?: unknown })._expect === "function" &&
    "count" in value
    ? new BrowserAssertion(value as unknown as Locator)
    : valueExpect(value, message);
}

class PollAssertion {
  constructor(
    private read: () => unknown | Promise<unknown>,
    private options: { timeout?: number; intervals?: number[] },
    private negative = false,
  ) {}
  get not() {
    return new PollAssertion(this.read, this.options, !this.negative);
  }
  private async check(
    method: "toBe" | "toEqual" | "toBeLessThanOrEqual",
    expected: unknown,
  ) {
    const deadline = performance.now() + (this.options.timeout ?? 5000);
    const intervals = this.options.intervals ?? [100, 250, 500, 1000];
    let index = 0;
    if (
      !intervals.length ||
      intervals.some((value) => !Number.isFinite(value) || value <= 0)
    )
      throw new Error("Polling intervals must be positive");
    for (;;) {
      if (signal?.aborted) throw new Error("Browser assertion was canceled");
      try {
        const assertion = valueExpect(await this.read());
        (this.negative ? assertion.not : assertion)[method](expected as never);
        return;
      } catch (error) {
        if (performance.now() >= deadline) throw error;
      }
      await new Promise((done) =>
        setTimeout(
          done,
          Math.min(
            intervals[Math.min(index++, intervals.length - 1)],
            Math.max(1, deadline - performance.now()),
          ),
        ),
      );
    }
  }
  toBe(expected: unknown) {
    return this.check("toBe", expected);
  }
  toEqual(expected: unknown) {
    return this.check("toEqual", expected);
  }
  toBeLessThanOrEqual(expected: number) {
    return this.check("toBeLessThanOrEqual", expected);
  }
}
export namespace expect {
  export function poll(
    read: () => unknown | Promise<unknown>,
    options: { timeout?: number; intervals?: number[] } = {},
  ) {
    return new PollAssertion(read, options);
  }
}
