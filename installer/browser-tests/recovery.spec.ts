import { test, expect, type Page } from "@playwright/test";
import { createRequire } from "node:module";
import { chooseTheme, closeAppearance } from "./appearance-helpers";
const require = createRequire(import.meta.url);
async function checkPrimaryStyles(page: Page) {
  const primary = page
    .getByRole("region", {
      name: "Let’s get setup working again",
    })
    .locator(".result-actions button.primary");
  const colors = await page.evaluate(() => {
    const theme = getComputedStyle(document.documentElement);
    const style = document.createElement("span").style;
    const color = (token: string) => {
      style.color = theme.getPropertyValue(token).trim();
      return style.color;
    };
    return {
      text: color("--primary-text"),
      normal: color("--primary"),
      hover: color("--primary-hover"),
    };
  });
  // Check actual cascaded styles, not just the palette's contrast ratios.
  await page.mouse.move(0, 0);
  await expect(primary).toHaveCSS("color", colors.text);
  await expect(primary).toHaveCSS("background-color", colors.normal);
  await primary.focus();
  await expect(primary).toBeFocused();
  await expect(primary).toHaveCSS("color", colors.text);
  await primary.hover();
  await expect(primary).toHaveCSS("background-color", colors.hover);
  await expect(primary).toHaveCSS("color", colors.text);
}
async function audit(page: Page) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(
    async () =>
      (
        await (
          window as unknown as {
            axe: {
              run: (options: unknown) => Promise<{ violations: unknown[] }>;
            };
          }
        ).axe.run({
          runOnly: {
            type: "tag",
            values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
          },
        })
      ).violations,
  );
  expect(violations).toEqual([]);
}
for (const theme of ["Light", "Dark"])
  for (const width of [640, 1140]) {
    test(`Recovery findings remain accessible in ${theme} at ${width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: "Partially installed", exact: true }),
      ).toBeVisible();
      await chooseTheme(page, theme);
      await closeAppearance(page);
      const card = page.getByRole("region", { name: "Workstation status" });
      await expect(card).toHaveCount(1);
      // The default preview has real FAIL rows: their red severity must outrank
      // the independent nonblocking package-health warning.
      await expect(card).toHaveClass(/tone-red/);
      await card
        .getByRole("button", {
          name: /Package health remains unverified.*Review Recovery/,
        })
        .click();
      await expect(
        page.getByRole("heading", { name: "Let’s get setup working again" }),
      ).toBeVisible();
      await expect(
        page.getByText("Open logs", { exact: true }),
      ).not.toBeVisible();
      await page.getByText("Technical details", { exact: true }).click();
      await expect(
        page.getByText("Package health remains unverified", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Acknowledge/ }),
      ).toHaveCount(0);
      await page
        .getByRole("button", { name: "Check again", exact: true })
        .click();
      await expect(
        page.getByText("No current machine incident recorded."),
      ).toBeVisible();
      await expect(page.getByRole("progressbar")).toHaveCount(0);
      await checkPrimaryStyles(page);
      await audit(page);
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth + 1,
        ),
      ).toBe(true);
      await page.screenshot({
        path: `test-results/recovery-${theme}-${width}.png`,
        fullPage: true,
      });
    });

    test(`Unknown health alone keeps Ready yellow in ${theme} at ${width}px`, async ({
      page,
    }) => {
      // Browser-only module override: retain every other preview export and
      // replace only Validation's result. No production flags or native state.
      await page.route("**/src/bridge.ts*", async (route) => {
        if (
          new URL(route.request().url()).searchParams.has("recoveryBaseline")
        ) {
          await route.continue();
          return;
        }
        await route.fulfill({
          contentType: "application/javascript",
          body: `export * from "/src/bridge.ts?recoveryBaseline";
            export async function inspect() { return ${JSON.stringify({
              code: 0,
              success: true,
              lines: [
                "SKYVIEW_EVENT|validation|PASS|Git: 2.49.0",
                "SKYVIEW_EVENT|summary|0|Validation passed",
              ],
              log_path: "Synthetic browser fixture — no files read",
              platform: { label: "Linux Mint 22.3", supported: true },
            })}; }`,
        });
      });
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      const card = page.getByRole("region", { name: "Workstation status" });
      await expect(card.getByRole("heading", { name: "Ready!" })).toBeVisible();
      await chooseTheme(page, theme);
      await closeAppearance(page);
      await expect(card).toHaveCount(1);
      await expect(card).toHaveClass(/tone-yellow/);
      const reason = card.getByRole("button", {
        name: /Package health remains unverified.*Review Recovery/,
      });
      await expect(reason).toBeVisible();
      await reason.focus();
      await reason.press("Enter");
      await expect(
        page.getByRole("heading", { name: "Let’s get setup working again" }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Acknowledge/ }),
      ).toHaveCount(0);
      await expect(page.getByRole("progressbar")).toHaveCount(0);
    });

    test(`Student recovery shows one next step before details in ${theme} at ${width}px`, async ({
      page,
    }) => {
      const id = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
      // Synthetic browser modules only. No privileged command or real journal.
      await page.route("**/src/recovery.ts*", async (route) => {
        if (
          new URL(route.request().url()).searchParams.has("studentBaseline")
        ) {
          await route.continue();
          return;
        }
        await route.fulfill({
          contentType: "application/javascript",
          body: `
          import {previewRecovery} from "/src/recovery.ts?studentBaseline";
          export * from "/src/recovery.ts?studentBaseline";
          export async function inspectRecovery() {
            const state = previewRecovery();
            state.machine.incidentId = "${id}";
            state.machine.intentSubmitted = true;
            state.effectiveActivity = state.nativeSafety.activity = "unknown";
            state.nativeSafety.interrupted = true;
            state.readiness = "blocked";
            state.decision = "block_activity_unknown";
            state.nativeSafety.decision = "block_activity_unknown";
            state.guidance = {code:"recheck_activity", title:"Activity could not be established", steps:["Save work and use normal Restart, then check again. Restart does not repair packages or acknowledge an interruption."]};
            return state;
          }`,
        });
      });
      await page.route("**/src/bridge.ts*", async (route) => {
        if (
          new URL(route.request().url()).searchParams.has("studentBaseline")
        ) {
          await route.continue();
          return;
        }
        await route.fulfill({
          contentType: "application/javascript",
          body: `
          import {inspect as inspectOriginal} from "/src/bridge.ts?studentBaseline";
          export * from "/src/bridge.ts?studentBaseline";
          export async function inspect() { return {...(await inspectOriginal()), platform:{label:"Windows 11 x64", supported:true}}; }`,
        });
      });
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: "Let’s get setup working again" }),
      ).toBeVisible();
      await chooseTheme(page, theme);
      await closeAppearance(page);
      await expect(page.getByText(/Start → Power → Restart/)).toBeVisible();
      await expect(
        page.getByText(/You don’t need to submit that acknowledgment again/),
      ).toBeVisible();
      const recovery = page.getByRole("region", {
        name: "Let’s get setup working again",
      });
      await expect(recovery.locator("button.primary")).toHaveText(
        "Check again",
      );
      await expect(
        recovery.getByRole("button", {
          name: /Run validation|Acknowledge|Continue with/,
        }),
      ).toHaveCount(0);
      await expect(page.locator(".recovery-disclosure[open]")).toHaveCount(0);
      await expect(
        page.getByText(`Incident reference: ${id}`, { exact: true }),
      ).not.toBeVisible();
      await expect(
        page.getByText("Earlier recovery events", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText("Saved reports", { exact: true }),
      ).toBeVisible();
      await checkPrimaryStyles(page);
      await audit(page);
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth + 1,
        ),
      ).toBe(true);
      await page.screenshot({
        path: `test-results/student-recovery-${theme}-${width}.png`,
        fullPage: true,
      });
      const technical = page.getByText("Technical details", { exact: true });
      await technical.focus();
      await technical.press("Enter");
      await expect(
        page.getByText(`Incident reference: ${id}`, { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: "Open logs", exact: true }),
      ).toBeVisible();
      await expect(page.getByRole("progressbar")).toHaveCount(0);
    });
  }
