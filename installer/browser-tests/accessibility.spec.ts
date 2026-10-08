import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
async function audit(page: import("@playwright/test").Page) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(async () => {
    const a = (
      window as unknown as {
        axe: { run: (options: unknown) => Promise<{ violations: unknown[] }> };
      }
    ).axe;
    return (
      await a.run({
        runOnly: {
          type: "tag",
          values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
        },
      })
    ).violations;
  });
  expect(violations).toEqual([]);
}
test("desktop contrast, keyboard access, progress and completion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1140, height: 1000 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Partially installed", exact: true }),
  ).toBeVisible();
  await audit(page);
  await page.screenshot({
    path: "test-results/overview-desktop.png",
    fullPage: true,
  });
  await page.keyboard.press("Tab");
  await expect(page.getByText("Skip to main content")).toBeFocused();
  await page
    .getByRole("button", { name: "Install Development Environment" })
    .click();
  await expect(page.getByRole("progressbar")).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Provisioning log" }),
  ).toBeInViewport();
  await expect(
    page.getByRole("heading", { name: "Live details" }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", { name: "Provisioning log" }),
  ).toContainText("Checking system");
  await audit(page);
  await page.screenshot({ path: "test-results/installation-desktop.png" });
  await expect(
    page.getByRole("heading", { name: "Development environment ready." }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Development environment ready." }),
  ).toBeFocused();
  await audit(page);
  await page.getByRole("button", { name: "View validation results" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await audit(page);
  await page.screenshot({
    path: "test-results/validation-desktop.png",
    fullPage: true,
  });
});
test("mobile layout and labels", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Partially installed", exact: true }),
  ).toBeVisible();
  await audit(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/overview-mobile.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Install Development Environment" })
    .click();
  await expect(
    page.getByRole("region", { name: "Provisioning log" }),
  ).toBeInViewport();
  expect(
    await page
      .locator(".progress-panel .spinner")
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe("none");
  await audit(page);
  await page.screenshot({ path: "test-results/installation-mobile.png" });
});
for (const width of [1140, 520]) {
  test(`Schedule and About keyboard, contrast and reflow at ${width}px`, async ({
    page,
  }) => {
    // 520 CSS pixels also models a 1040px application window at 200% scale.
    await page.setViewportSize({ width, height: 1000 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.goto("/");
    const schedule = page.getByRole("button", {
      name: "Schedule",
      exact: true,
    });
    await schedule.focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: "Maintenance schedule" }),
    ).toBeFocused();
    await expect(
      page.getByText("skyview-student-dev-update.timer", { exact: true }),
    ).toBeVisible();
    await audit(page);
    await page.getByRole("button", { name: "Refresh", exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(".schedule-status")).toContainText(
      "Enabled · Last result: Succeeded",
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/schedule-${width}.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "About", exact: true }).focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: "About Skyview Dev Setup" }),
    ).toBeFocused();
    await expect(page.getByText("1.2.1", { exact: true })).toBeVisible();
    const github = page.getByRole("link", {
      name: /View the project on GitHub/,
    });
    await expect(github).toHaveAttribute(
      "href",
      "https://github.com/stormbots/Tactics-Strategy-Dev-Environments",
    );
    await expect(
      page.getByRole("link", { name: /Visit Skyview Robotics/ }),
    ).toHaveAttribute("href", "https://skyviewrobotics.com");
    await github.focus();
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("link", { name: /Visit Skyview Robotics/ }),
    ).toBeFocused();
    await audit(page);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `test-results/about-${width}.png`,
      fullPage: true,
    });
  });
}
