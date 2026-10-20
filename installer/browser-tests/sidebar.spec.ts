import { expect, test, type Page } from "@playwright/test";
import { chooseZoom, closeAppearance } from "./appearance-helpers";

async function expectFullHeightSidebar(page: Page) {
  const sidebar = page.locator(".sidebar");
  await expect(sidebar).toHaveCSS("position", "fixed");
  const bounds = await sidebar.boundingBox();
  expect(bounds).not.toBeNull();
  expect(Math.abs(bounds!.y)).toBeLessThanOrEqual(1);
  expect(
    Math.abs(bounds!.y + bounds!.height - page.viewportSize()!.height),
  ).toBeLessThanOrEqual(1);
}

for (const [position, zoom] of [90, 100, 115, 130, 150].entries()) {
  test(`desktop sidebar fills the viewport at ${zoom}% through scroll and resize`, async ({
    page,
    browserName,
  }) => {
    await page.setViewportSize({ width: 1920, height: 1128 });
    await page.goto("/");
    await chooseZoom(page, position);
    await closeAppearance(page);
    await expectFullHeightSidebar(page);
    await expect(page.locator(".sidebar-bottom")).toBeInViewport();
    if (zoom === 130)
      await page.screenshot({
        path: `test-results/sidebar-${browserName}-130.png`,
      });

    await page.setViewportSize({ width: 1920, height: 600 });
    const scroll = await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight);
      return window.scrollY;
    });
    expect(scroll).toBeGreaterThan(0);
    await expectFullHeightSidebar(page);
    await expect(
      page.getByRole("navigation", { name: "Application" }),
    ).toBeInViewport();

    // At this height the sidebar must scroll instead of losing its footer or
    // growing beyond the window. It stays a sidebar at every supported zoom.
    await page.setViewportSize({ width: 1920, height: 400 });
    await expectFullHeightSidebar(page);
    await page.locator(".sidebar-bottom").scrollIntoViewIfNeeded();
    await expect(page.locator(".sidebar-bottom")).toBeInViewport();
    const about = page.getByRole("button", { name: "About", exact: true });
    await about.focus();
    await about.press("Enter");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "About Skyview Dev Setup",
    );
    await expectFullHeightSidebar(page);

    await page.setViewportSize({ width: 1920, height: 1128 });
    await page.locator(".sidebar").evaluate((el) => (el.scrollTop = 0));
    await expectFullHeightSidebar(page);
    await expect(page.locator(".sidebar-bottom")).toBeInViewport();

    await page.setViewportSize({ width: 640, height: 600 });
    await expect(page.locator(".sidebar")).toHaveCSS("position", "static");
    await expect(
      page.getByRole("navigation", { name: "Application" }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Are you ready to build?",
    );
  });
}
