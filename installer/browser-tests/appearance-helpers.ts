import { expect, type Page } from "@playwright/test";
export async function openAppearance(page: Page) {
  await page.waitForFunction(() => {
    const slot = document.getElementById("compact-appearance-slot");
    if (!slot) return false;
    const compact = getComputedStyle(slot).display !== "none";
    return compact
      ? !!document.querySelector(".settings-trigger")
      : !!document.querySelector(".appearance-toolbar");
  });
  const trigger = page.getByRole("button", {
    name: "Appearance settings",
    exact: true,
  });
  if (
    (await trigger.isVisible()) &&
    (await trigger.getAttribute("aria-expanded")) === "false"
  )
    await trigger.click();
}
export async function chooseTheme(page: Page, theme: string) {
  await openAppearance(page);
  await page.getByRole("button", { name: theme, exact: true }).click();
}
export async function chooseZoom(page: Page, position: number) {
  const levels = [90, 100, 115, 130, 150];
  for (let steps = 0; steps < 5; steps++) {
    await openAppearance(page);
    const current = Number(
      (await page.locator(".zoom-value:visible").textContent())!.replace(
        "%",
        "",
      ),
    );
    if (current === levels[position]) break;
    await page
      .getByRole("button", {
        name: current < levels[position] ? "Increase zoom" : "Decrease zoom",
      })
      .click();
  }
  await openAppearance(page);
  await expect(page.locator(".zoom-value:visible")).toHaveText(
    `${levels[position]}%`,
  );
}
export async function closeAppearance(page: Page) {
  const trigger = page.getByRole("button", {
    name: "Appearance settings",
    exact: true,
  });
  if (
    (await trigger.isVisible()) &&
    (await trigger.getAttribute("aria-expanded")) === "true"
  )
    await trigger.click();
}
