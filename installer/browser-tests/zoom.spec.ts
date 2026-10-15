import { test, expect, type Page } from "@playwright/test";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const levels = [90, 100, 115, 130, 150];
async function chooseZoom(page: Page, position: number) {
  const slider = page.getByRole("slider", { name: "UI zoom", exact: true });
  await slider.focus();
  await slider.press("Home");
  for (let i = 0; i < position; i++) await slider.press("ArrowRight");
  await expect(slider).toHaveAttribute(
    "aria-valuetext",
    `${levels[position]}%`,
  );
}
async function audit(page: Page) {
  await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
  const result = await page.evaluate(async () => {
    const axe = (
      window as unknown as {
        axe: { run: (options: unknown) => Promise<{ violations: unknown[] }> };
      }
    ).axe;
    return (
      await axe.run({
        runOnly: {
          type: "tag",
          values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
        },
      })
    ).violations;
  });
  expect(result).toEqual([]);
  const sizes = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    client: document.documentElement.clientWidth,
    right: document.body.getBoundingClientRect().right,
    viewport: innerWidth,
  }));
  expect(sizes.scroll).toBeLessThanOrEqual(sizes.client + 1);
  expect(sizes.right).toBeLessThanOrEqual(sizes.viewport + 1);
}
for (const theme of ["Light", "Dark"]) {
  for (const width of [640, 1040]) {
    for (const [position, zoom] of levels.entries()) {
      test(`${theme} ${zoom}% at ${width}px: scales and reflows every page`, async ({
        page,
      }) => {
        await page.setViewportSize({ width, height: 600 });
        await page.goto("/");
        await expect(
          page.getByRole("heading", {
            name: "Partially installed",
            exact: true,
          }),
        ).toBeVisible();
        await page.getByRole("radio", { name: theme, exact: true }).check();
        await chooseZoom(page, position);
        await expect(
          page.locator(".zoom-slider input:focus-visible"),
        ).toHaveCSS("outline-style", "solid");
        const sizes = await page.evaluate(() => {
          const el = document.querySelector(".operation-description")!;
          const svg = document.querySelector(".mode-tabs button svg")!;
          return {
            font:
              parseFloat(getComputedStyle(el).fontSize) *
              parseFloat(getComputedStyle(document.documentElement).zoom),
            icon: svg.getBoundingClientRect().width,
            sideHeight: document
              .querySelector(".sidebar")!
              .getBoundingClientRect().height,
            sidePosition: getComputedStyle(document.querySelector(".sidebar")!)
              .position,
          };
        });
        expect(sizes.font).toBeCloseTo((12 * zoom) / 100, 2);
        expect(sizes.icon).toBeCloseTo((17 * zoom) / 100, 1);
        if (sizes.sidePosition === "fixed")
          expect(sizes.sideHeight).toBeLessThanOrEqual(601);
        await audit(page);
        if (zoom === 150)
          await page.screenshot({
            path: `test-results/zoom-${theme}-${width}-150.png`,
            fullPage: true,
          });
        await page.getByRole("button", { name: "Update", exact: true }).click();
        await page.getByText("Advanced", { exact: true }).click();
        const option = page.getByLabel(
          "Check for managed package updates during validation",
        );
        await option.check();
        await chooseZoom(page, (position + 1) % 5);
        await expect(option).toBeChecked();
        await expect(
          page.getByRole("button", { name: "Update", exact: true }),
        ).toHaveAttribute("aria-pressed", "true");
        await chooseZoom(page, position);
        for (const name of ["Validation", "Schedule", "About"]) {
          await page
            .getByRole("button", { name: new RegExp(`^${name}`) })
            .click();
          if (name === "Schedule")
            await expect(page.locator(".schedule-status")).toContainText(
              "Enabled",
            );
          const title = await page
            .getByRole("heading", { level: 1 })
            .textContent();
          await chooseZoom(page, (position + 1) % 5);
          await expect(page.getByRole("heading", { level: 1 })).toHaveText(
            title!,
          );
          await chooseZoom(page, position);
          await audit(page);
        }
        await page.reload();
        await expect(
          page.getByRole("slider", { name: "UI zoom", exact: true }),
        ).toHaveAttribute("aria-valuetext", `${zoom}%`);
      });
    }
  }
}
test("zoom control defaults to 100% and bounds keyboard choices to the five positions", async ({
  page,
}) => {
  await page.goto("/");
  const slider = page.getByRole("slider", { name: "UI zoom", exact: true });
  await expect(slider).toHaveAttribute("aria-valuetext", "100%");
  await slider.focus();
  await slider.press("End");
  await expect(slider).toHaveAttribute("aria-valuetext", "150%");
  await slider.press("ArrowRight");
  await expect(slider).toHaveAttribute("aria-valuetext", "150%");
  await slider.press("Home");
  await slider.press("ArrowLeft");
  await expect(slider).toHaveAttribute("aria-valuetext", "90%");
});
test("zoom and theme changes preserve an active operation and log", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Partially installed", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Install Development Environment" })
    .click();
  const log = page.getByRole("region", { name: "Provisioning log" });
  await expect(log).toContainText("Checking system");
  await chooseZoom(page, 4);
  await page.getByRole("radio", { name: "Dark", exact: true }).check();
  await expect(log).toContainText("Checking system");
  await expect(
    page.getByRole("heading", { name: "Live details" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Development environment ready." }),
  ).toBeVisible();
  await audit(page);
});

test("pointer selection reaches every zoom position after the control scales", async ({
  page,
}) => {
  await page.setViewportSize({ width: 640, height: 600 });
  await page.goto("/");
  const slider = page.getByRole("slider", { name: "UI zoom", exact: true });
  for (const position of [4, 0, 2, 3, 1]) {
    await slider.scrollIntoViewIfNeeded();
    const box = (await slider.boundingBox())!;
    const scale = await page.evaluate(() =>
      parseFloat(getComputedStyle(document.documentElement).zoom),
    );
    const inset = 9 * scale;
    await page.mouse.click(
      box.x + inset + ((box.width - 2 * inset) * position) / 4,
      box.y + box.height / 2,
    );
    await expect(slider).toHaveAttribute(
      "aria-valuetext",
      `${levels[position]}%`,
    );
  }
});
