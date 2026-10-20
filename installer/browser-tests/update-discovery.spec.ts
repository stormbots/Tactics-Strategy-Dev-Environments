import { expect, test } from "@playwright/test";
import axe from "axe-core";
import { chooseTheme, chooseZoom, closeAppearance } from "./appearance-helpers";
for (const theme of ["Light", "Dark"]) {
  test(`tool preview is read-only, accessible and cancellable in ${theme}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1040, height: 820 });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Partially installed", exact: true }),
    ).toBeVisible();
    await chooseTheme(page, theme);
    await chooseZoom(page, 4);
    await closeAppearance(page);
    await page.getByRole("button", { name: "Update", exact: true }).click();
    await page
      .getByRole("button", { name: "Update Development Tools", exact: true })
      .click();
    const preview = page.getByRole("heading", {
      name: "Preview development-tool update",
    });
    await expect(preview).toBeFocused();
    await expect(
      page.getByRole("button", { name: "Refresh preview" }),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Continue with Update" }),
    ).toBeEnabled();
    await expect(page.getByRole("progressbar")).toHaveCount(0);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth + 2,
    );
    expect(overflow).toBe(false);
    await page.addScriptTag({ content: axe.source });
    const violations = await page.evaluate(
      async () => (await (window as any).axe.run(document)).violations,
    );
    expect(violations).toEqual([]);
    await page.screenshot({
      path: `test-results/update-preview-${theme.toLowerCase()}.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(preview).toHaveCount(0);
    await expect(page.getByRole("progressbar")).toHaveCount(0);
    await page.getByRole("button", { name: "About", exact: true }).click();
    await page.getByRole("button", { name: "Check for SDE updates" }).click();
    await expect(
      page.getByText(/No newer stable SDE release found/),
    ).toBeVisible();
  });
}
