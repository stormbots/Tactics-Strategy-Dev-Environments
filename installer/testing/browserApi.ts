import { test as nodeTest, after } from "node:test";
import { writeFileSync } from "node:fs";
import { chromium, webkit, type Browser, type Page } from "playwright-core";
import { assertionSignal } from "./browserAssertions";
export { expect } from "./browserAssertions";
export type { Page, Locator, Browser, BrowserContext } from "playwright-core";
if (
  !["chromium", "webkit-sidebar"].includes(
    process.env.SDE_BROWSER_PROJECT ?? "",
  )
)
  throw new Error("A supported browser project is required");
const browserName =
  process.env.SDE_BROWSER_PROJECT === "webkit-sidebar" ? "webkit" : "chromium";
const registered: string[] = [],
  completed: string[] = [];
let browser: Browser | undefined;
let activeTimeout: number | null = null;
let options: { actionTimeout?: number } = {};
type Body = (fixture: {
  page: Page;
  browserName: "chromium" | "webkit";
}) => unknown;
function register(name: string, body: Body) {
  const literal =
    /test\.setTimeout\(\s*(\d+(?:\.\d+)?(?:e[+-]?\d+)?)\s*\)/i.exec(
      body.toString(),
    );
  const timeout = literal ? Number(literal[1]) : 30000;
  registered.push(name);
  return nodeTest(name, { timeout }, async (context) => {
    if (!browser)
      browser = await (browserName === "webkit" ? webkit : chromium).launch({
        headless: true,
        ...(browserName === "chromium" && process.env.SDE_BROWSER_EXECUTABLE
          ? { executablePath: process.env.SDE_BROWSER_EXECUTABLE }
          : {}),
      });
    const session = await browser.newContext({
      baseURL: "http://127.0.0.1:1420",
      viewport: { width: 1280, height: 720 },
    });
    const page = await session.newPage();
    page.setDefaultTimeout(options.actionTimeout ?? 0);
    activeTimeout = timeout;
    assertionSignal(context.signal);
    context.after(async () => {
      assertionSignal(undefined);
      activeTimeout = null;
      await session.close();
    });
    try {
      await body({ page, browserName });
    } finally {
      completed.push(name);
    }
  });
}
export const test = Object.assign(register, {
  use(value: { actionTimeout?: number }) {
    options = { ...options, ...value };
  },
  setTimeout(value: number) {
    if (activeTimeout !== value)
      throw new Error(
        "Test timeout must be a statically declared literal preserved by the runner",
      );
  },
});
after(async () => {
  await browser?.close();
});
process.on("exit", () => {
  if (!process.env.SDE_BROWSER_RECEIPT)
    throw new Error("A browser case receipt is required");
  writeFileSync(
    process.env.SDE_BROWSER_RECEIPT,
    JSON.stringify({ registered, completed }),
  );
  if (!registered.length || registered.length !== completed.length)
    process.exitCode = 1;
});
