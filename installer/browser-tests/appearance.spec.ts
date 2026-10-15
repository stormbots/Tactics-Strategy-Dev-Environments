import { test, expect } from "@playwright/test";
import {
  chooseTheme,
  chooseZoom,
  openAppearance,
  closeAppearance,
} from "./appearance-helpers";

for (const theme of ["Light", "Dark"]) {
  for (const width of [320, 640, 1100, 1101, 1440, 1920]) {
    test(`${theme} appearance placement and bounds at ${width}px across all zoom levels`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 820 });
      await page.goto("/");
      await chooseTheme(page, theme);
      for (const position of [0, 1, 2, 3, 4]) {
        await chooseZoom(page, position);
        const compact = await page
          .getByRole("button", { name: "Appearance settings", exact: true })
          .isVisible();
        expect(
          await page
            .locator(".sidebar")
            .evaluate((el) => getComputedStyle(el).position === "static"),
        ).toBe(compact);
        await expect(
          page.getByRole("button", { name: "System", exact: true }),
        ).toHaveCount(1);
        await expect(page.getByRole("slider")).toHaveCount(0);
        const overflow = await page.evaluate(() => ({
          right: document.body.getBoundingClientRect().right,
          width: innerWidth,
        }));
        expect(overflow.right).toBeLessThanOrEqual(overflow.width + 1);
        if (compact) {
          const box = (await page
            .locator(".appearance-popover")
            .boundingBox())!;
          expect(box.x).toBeGreaterThanOrEqual(0);
          expect(box.x + box.width).toBeLessThanOrEqual(width + 1);
          expect(box.y + box.height).toBeLessThanOrEqual(821);
          const fits = await page
            .locator(".appearance-popover")
            .evaluate((el) => el.scrollWidth <= el.clientWidth);
          expect(fits).toBe(true);
        } else {
          const title = (await page
            .getByRole("heading", { level: 1 })
            .boundingBox())!;
          const controls = (await page
            .locator(".appearance-toolbar .theme-control")
            .boundingBox())!;
          expect(title.x + title.width).toBeLessThanOrEqual(controls.x);
          expect(
            Math.abs(
              title.y + title.height / 2 - (controls.y + controls.height / 2),
            ),
          ).toBeLessThan(15);
        }
        await closeAppearance(page);
      }
    });
  }
}

test("popover keyboard entry, dismissal, outside focus, navigation and resize", async ({
  page,
}) => {
  await page.setViewportSize({ width: 640, height: 600 });
  await page.goto("/");
  const trigger = page.getByRole("button", {
    name: "Appearance settings",
    exact: true,
  });
  await trigger.focus();
  await trigger.press("Enter");
  await expect(
    page.getByRole("button", { name: "System", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("button", { name: "Light", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await trigger.click();
  await page.getByRole("button", { name: "About", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await trigger.click();
  await page.getByRole("button", { name: "Light", exact: true }).focus();
  await page.setViewportSize({ width: 1440, height: 820 });
  await expect(trigger).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Light", exact: true }),
  ).toBeFocused();
  await page.setViewportSize({ width: 640, height: 600 });
  await expect(trigger).toBeFocused();
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await trigger.click();
  const validation = page.getByRole("button", { name: /^Validation/ });
  await validation.focus();
  await page.keyboard.press("Space");
  await expect(trigger).toHaveAttribute("aria-expanded", "false");
  await trigger.click();
  // Clicking a focusable target outside the panel preserves the clicked focus.
  const overview = page.getByRole("button", { name: "Overview", exact: true });
  await overview.click();
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await trigger.click();
  await overview.click();
  await expect(overview).toBeFocused();
});

test("preferences survive panel dismissal and layout transitions with storage blocked", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => {
      throw Error("blocked");
    };
    Storage.prototype.setItem = () => {
      throw Error("blocked");
    };
  });
  await page.setViewportSize({ width: 640, height: 820 });
  await page.goto("/");
  await chooseTheme(page, "Dark");
  await chooseZoom(page, 2);
  await closeAppearance(page);
  await openAppearance(page);
  await expect(
    page.getByRole("button", { name: "Dark", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".zoom-value:visible")).toHaveText("115%");
  await page.setViewportSize({ width: 1920, height: 1080 });
  await expect(page.locator(".zoom-value:visible")).toHaveText("115%");
  await expect(
    page.getByRole("button", { name: "Dark", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});

for (const theme of ["Light", "Dark"])
  for (const width of [640, 1440]) {
    test(`${theme} ${width}px implementation screenshot`, async ({ page }) => {
      await page.setViewportSize({ width, height: 820 });
      await page.goto("/");
      await expect(
        page.getByRole("heading", { name: "Partially installed", exact: true }),
      ).toBeVisible();
      await chooseTheme(page, theme);
      await openAppearance(page);
      await page.mouse.move(0, 0);
      await page.getByRole("heading", { level: 1 }).focus();
      await page.screenshot({
        path: `test-results/appearance-${theme}-${width}.png`,
        fullPage: true,
      });
    });
  }

test("short compact viewport scrolls the panel without clipping controls", async ({
  page,
}) => {
  await page.setViewportSize({ width: 640, height: 220 });
  await page.goto("/");
  await chooseZoom(page, 4);
  const panel = page.locator(".appearance-popover");
  const bounds = (await panel.boundingBox())!;
  expect(bounds.y + bounds.height).toBeLessThanOrEqual(221);
  await page.getByRole("button", { name: "Decrease zoom" }).click();
  await expect(page.locator(".zoom-value:visible")).toHaveText("130%");
});

test("theme tooltips work on keyboard focus and dismiss with Escape in wide layout", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 820 });
  await page.goto("/");
  const system = page.getByRole("button", { name: "System", exact: true });
  await system.focus();
  const tip = page
    .locator(".theme-option")
    .filter({ has: system })
    .locator(".appearance-tooltip");
  await expect(tip).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(tip).toBeHidden();
  await expect(system).toBeFocused();
});

test("appearance changes preserve an active validation and its completed log", async ({
  page,
}) => {
  await page.setViewportSize({ width: 640, height: 820 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Partially installed", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Validate", exact: true }).click();
  await page
    .getByRole("button", {
      name: "Validate Development Environment",
      exact: true,
    })
    .click();
  const log = page.getByRole("region", { name: "Provisioning log" });
  await expect(log).toContainText("Checking system");
  await chooseTheme(page, "Dark");
  await chooseZoom(page, 2);
  await expect(log).toContainText("Checking system");
  await expect(page.getByRole("progressbar")).toHaveCount(0);
  await expect(log).toContainText("Validating environment");
  await expect(
    page.getByRole("button", { name: "Validate", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("compact popover stays above navigation and page content", async ({
  page,
}) => {
  await page.setViewportSize({ width: 640, height: 820 });
  await page.goto("/");
  await chooseZoom(page, 4);
  const unobscured = await page
    .locator(".appearance-popover button")
    .evaluateAll((buttons) =>
      buttons.every((button) => {
        const r = button.getBoundingClientRect();
        return (
          document
            .elementFromPoint(r.x + r.width / 2, r.y + r.height / 2)
            ?.closest("button") === button
        );
      }),
    );
  expect(unobscured).toBe(true);
});

test("zoom limits retain keyboard focus on the enabled opposite button", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1920, height: 900 });
  await page.goto("/");
  await chooseZoom(page, 3);
  const plus = page.getByRole("button", { name: "Increase zoom" });
  const minus = page.getByRole("button", { name: "Decrease zoom" });
  await plus.focus();
  await plus.press("Enter");
  await expect(plus).toBeDisabled();
  await expect(minus).toBeFocused();
  await chooseZoom(page, 1);
  await minus.focus();
  await minus.press("Space");
  await expect(minus).toBeDisabled();
  await expect(plus).toBeFocused();
});

test("popover refits when an already open window becomes very short", async ({
  page,
}) => {
  await page.setViewportSize({ width: 640, height: 820 });
  await page.goto("/");
  await chooseZoom(page, 4);
  await page.setViewportSize({ width: 640, height: 150 });
  await expect
    .poll(async () => {
      const box = (await page.locator(".appearance-popover").boundingBox())!;
      return box.y + box.height;
    })
    .toBeLessThanOrEqual(150);
  await page.getByRole("button", { name: "Decrease zoom" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".zoom-value:visible")).toHaveText("130%");
});

test("Escape dismisses hovered theme tooltips when keyboard focus is elsewhere", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 820 });
  await page.goto("/");
  await page.getByRole("button", { name: "Overview", exact: true }).focus();
  const system = page.getByRole("button", { name: "System", exact: true });
  await system.hover();
  const tip = page
    .locator(".theme-option")
    .filter({ has: system })
    .locator(".appearance-tooltip");
  await expect(tip).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(tip).toBeHidden();
  await expect(
    page.getByRole("button", { name: "Overview", exact: true }),
  ).toBeFocused();
});

test("Escape outside the appearance controls does not suppress the next focus tooltip", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 820 });
  await page.goto("/");
  await page.getByRole("button", { name: "Overview", exact: true }).focus();
  await page.keyboard.press("Escape");
  const system = page.getByRole("button", { name: "System", exact: true });
  await system.focus();
  await expect(
    page
      .locator(".theme-option")
      .filter({ has: system })
      .locator(".appearance-tooltip"),
  ).toBeVisible();
});
