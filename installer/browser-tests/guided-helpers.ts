import { type Page } from "@playwright/test";
export async function disclosure(page: Page, name: string) {
  const summary = page.getByText(name, { exact: true });
  if (!((await summary.locator("..").getAttribute("open")) !== null))
    await summary.click();
}
export async function otherAction(page: Page, name: string) {
  await disclosure(page, "Other actions");
  await page.getByRole("button", { name, exact: true }).click();
}
