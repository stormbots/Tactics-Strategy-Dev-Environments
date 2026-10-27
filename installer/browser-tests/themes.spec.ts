import {
  openAppearance,
  chooseTheme,
  closeAppearance,
} from "./appearance-helpers";
import { test, expect, type Page } from "@playwright/test";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
async function audit(page: Page) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(async () => {
    return (
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
    ).violations;
  });
  expect(violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
}
for (const theme of ["Light", "Dark"] as const) {
  for (const width of [390, 900, 1140]) {
    test(`${theme} theme, all pages, focus and reflow at ${width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: "Partially installed", exact: true }),
      ).toBeVisible();
      await chooseTheme(page, theme);
      await expect(page.locator("html")).toHaveAttribute(
        "data-theme",
        theme.toLowerCase(),
      );
      await openAppearance(page);
      await page.getByRole("button", { name: theme, exact: true }).focus();
      await page.keyboard.press("Space");
      await expect(
        page.locator(".theme-control button:focus-visible"),
      ).toHaveCSS("outline-style", "solid");
      await page.keyboard.press("Enter");
      await expect(
        page.getByRole("button", { name: theme, exact: true }),
      ).toHaveAttribute("aria-pressed", "true");
      await audit(page);
      await page.screenshot({
        path: `test-results/theme-${theme}-${width}-overview.png`,
        fullPage: true,
      });
      await page.getByRole("button", { name: "Update", exact: true }).click();
      await page.getByText("Advanced", { exact: true }).click();
      const option = page.getByLabel(
        "Check for managed package updates during validation",
      );
      await option.click();
      await chooseTheme(page, theme === "Light" ? "Dark" : "Light");
      await expect(
        page.getByRole("button", { name: "Update", exact: true }),
      ).toHaveAttribute("aria-pressed", "true");
      await expect(option).toBeChecked();
      await chooseTheme(page, theme);
      for (const name of ["Validation", "Schedule", "About"]) {
        await closeAppearance(page);
        await page
          .getByRole("button", { name: new RegExp(`^${name}`) })
          .click();
        if (name === "Schedule")
          await expect(page.locator(".schedule-status")).toContainText(
            "Enabled",
          );
        const heading = page.getByRole("heading", { level: 1 });
        const title = await heading.textContent();
        await chooseTheme(page, theme === "Light" ? "Dark" : "Light");
        await expect(heading).toHaveText(title!);
        await chooseTheme(page, theme);
        await expect(heading).toHaveText(title!);
        await audit(page);
      }
      await page.reload();
      await openAppearance(page);
      await expect(
        page.getByRole("button", { name: theme, exact: true }),
      ).toHaveAttribute("aria-pressed", "true");
      await expect(page.locator("html")).toHaveAttribute(
        "data-theme",
        theme.toLowerCase(),
      );
    });
  }
}
test("System follows live changes, manual override and returning to System", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await openAppearance(page);
  await expect(page.getByRole("button", { name: "System" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await chooseTheme(page, "Light");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await chooseTheme(page, "System");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
test("switching theme preserves an active operation and expanded log", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Partially installed", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Install Development Environment" })
    .click();
  await page.getByRole("button", { name: "Continue with Install" }).click();
  const log = page.getByRole("region", { name: "Provisioning log" });
  await expect(log).toContainText("Checking system");
  await chooseTheme(page, "Dark");
  await expect(log).toContainText("Checking system");
  await expect(
    page.getByRole("heading", { name: "Live details" }),
  ).toBeVisible();
  await audit(page);
  await expect(
    page.getByRole("heading", { name: "Development environment ready." }),
  ).toBeVisible();
  await audit(page);
});

for (const theme of ["Light", "Dark"] as const) {
  test(`${theme} text, controls and focus meet contrast requirements`, async ({
    page,
  }) => {
    await page.goto("/");
    await chooseTheme(page, theme);
    const ratios = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      function luminance(role: string) {
        const hex = style.getPropertyValue(`--${role}`).trim().slice(1);
        const [r, g, b] = [0, 2, 4].map((i) => {
          const channel = parseInt(hex.slice(i, i + 2), 16) / 255;
          return channel <= 0.04045
            ? channel / 12.92
            : ((channel + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
      }
      const pairs: [string, string, number][] = [
        ["text", "surface", 4.5],
        ["muted", "canvas", 4.5],
        ["muted", "subtle", 4.5],
        ["link", "surface", 4.5],
        ["success", "surface", 4.5],
        ["warning", "surface", 4.5],
        ["danger", "surface", 4.5],
        ["info", "surface", 4.5],
        ["success", "success-surface", 4.5],
        ["warning", "warning-surface", 4.5],
        ["notice-text", "notice-surface", 4.5],
        ["log-text", "log-surface", 4.5],
        ["primary-text", "primary", 4.5],
        ["primary-text", "primary-hover", 4.5],
        ["focus", "surface", 3],
        ["focus", "subtle", 3],
        ["focus", "canvas", 3],
        ["control-line", "surface", 3],
        ["control-line", "subtle", 3],
        ["progress", "track", 3],
      ];
      return pairs.map(([foreground, background, min]) => {
        const a = luminance(foreground),
          b = luminance(background);
        return {
          foreground,
          background,
          min,
          ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05),
        };
      });
    });
    for (const pair of ratios)
      expect(pair.ratio, JSON.stringify(pair)).toBeGreaterThanOrEqual(pair.min);
  });
}

test("unavailable system detection keeps System selected with Light fallback", async ({
  page,
}) => {
  await page.addInitScript(() =>
    Object.defineProperty(window, "matchMedia", { value: undefined }),
  );
  await page.goto("/");
  await openAppearance(page);
  await expect(page.getByRole("button", { name: "System" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await chooseTheme(page, "Dark");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
});
