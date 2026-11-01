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
      await expect(card).toHaveClass(/tone-yellow/);
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
  }
