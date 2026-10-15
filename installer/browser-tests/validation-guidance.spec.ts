import { test, expect, type Page } from "@playwright/test";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
async function audit(page: Page) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(
    async () =>
      (
        await (
          window as unknown as {
            axe: { run: (opts: unknown) => Promise<{ violations: unknown[] }> };
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
}
for (const theme of ["Light", "Dark"])
  for (const width of [640, 1040]) {
    test(`${theme} guidance at ${width}px preserves status and requires explicit action`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 820 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: "Partially installed", exact: true }),
      ).toBeVisible();
      await page.getByRole("radio", { name: theme, exact: true }).check();
      if (width === 640) {
        const zoom = page.getByRole("slider", { name: "UI zoom", exact: true });
        await zoom.focus();
        await zoom.press("End");
      }
      await page.getByRole("button", { name: /^Validation/ }).click();
      const row = page
        .getByRole("row")
        .filter({ hasText: "Python 3.14 could not be found" });
      await expect(row).toContainText("FAIL");
      await expect(page.getByRole("row").nth(1)).toContainText("FAIL");
      await expect(
        row.getByText("Python 3.14: not installed", { exact: true }),
      ).toBeHidden();
      await row.getByText("Technical details", { exact: true }).click();
      await expect(
        row.getByText("Python 3.14: not installed", { exact: true }),
      ).toBeVisible();
      await expect(
        page.getByText("Git identity: not configured (optional)", {
          exact: true,
        }),
      ).toBeVisible();
      await expect(page.getByText("INFORMATION", { exact: true })).toHaveCount(
        2,
      );
      await audit(page);
      await page.screenshot({
        path: `test-results/guidance-${theme}-${width}.png`,
        fullPage: false,
      });
      await page
        .getByRole("button", { name: "View Schedule", exact: true })
        .click();
      await expect(
        page.getByRole("heading", { name: "Maintenance schedule" }),
      ).toBeFocused();
      await expect(page.locator(".schedule-status")).toContainText("Enabled");
      await page.getByRole("button", { name: /^Validation/ }).click();
      await page
        .getByRole("button", {
          name: /Review Update for Managed update available for Git/,
        })
        .click();
      await expect(
        page.getByRole("button", {
          name: "Update Development Tools",
          exact: true,
        }),
      ).toBeVisible();
      await expect(page.getByRole("progressbar")).toHaveCount(0);
      await page.getByRole("button", { name: /^Validation/ }).click();
      await row.getByRole("button", { name: /Review Repair/ }).click();
      await expect(
        page.getByRole("button", { name: "Repair", exact: true }),
      ).toHaveAttribute("aria-pressed", "true");
      await expect(page.getByRole("status")).toContainText("full workflow");
      await expect(page.getByRole("progressbar")).toHaveCount(0);
      await page
        .getByRole("button", { name: "Repair Development Environment" })
        .click();
      await expect(page.getByRole("progressbar")).toBeVisible();
      await expect(
        page.getByRole("heading", { name: "Development environment ready." }),
      ).toBeVisible();
      await audit(page);
    });
  }
