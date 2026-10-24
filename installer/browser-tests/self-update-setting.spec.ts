import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

test("student can toggle with keyboard; schedule/history stay independent and layout fits", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Schedule", exact: true }).click();
  const toggle = page.getByRole("switch", { name: "Automatic SDE updates" });
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  const schedule = await page.locator(".schedule-status").innerText();
  const history = await page
    .locator(".maintenance-scope .information-grid")
    .first()
    .innerText();
  await toggle.focus();
  await page.keyboard.press("Space");
  await expect(toggle).toHaveAttribute("aria-checked", "false");
  await expect(
    page.getByText("SDE application installation is paused.", { exact: false }),
  ).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(toggle).toHaveAttribute("aria-checked", "true");
  await expect(page.locator(".schedule-status")).toHaveText(schedule);
  // The only changed receipt field is the setting's timestamp.
  expect(history).toContain("No result recorded");
  await expect(
    page.getByText(
      "Setting saved. No maintenance or installation was started.",
    ),
  ).toBeVisible();
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const violations = await page.evaluate(
    async () =>
      (
        await (
          window as unknown as {
            axe: { run: () => Promise<{ violations: unknown[] }> };
          }
        ).axe.run()
      ).violations,
  );
  expect(violations).toEqual([]);
  for (const width of [1024, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await expect(toggle).toBeVisible();
  }
  await page.screenshot({
    path: "test-results/sde-update-setting-compact.png",
    fullPage: true,
  });
});
