import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
import { chooseTheme, closeAppearance } from "./appearance-helpers";
const require = createRequire(import.meta.url);
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
        page.getByRole("heading", { name: "Recovery findings" }),
      ).toBeVisible();
      await expect(
        page.getByText("Package health remains unverified", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Acknowledge/ }),
      ).toHaveCount(0);
      await page
        .getByRole("button", { name: "Check Again", exact: true })
        .click();
      await expect(
        page.getByText("No current machine incident recorded."),
      ).toBeVisible();
      await expect(page.getByRole("progressbar")).toHaveCount(0);
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
        page.getByRole("heading", { name: "Recovery findings" }),
      ).toBeVisible();
      await expect(
        page.getByRole("button", { name: /Acknowledge/ }),
      ).toHaveCount(0);
      await expect(page.getByRole("progressbar")).toHaveCount(0);
    });
  }
