import { test, expect } from "../testing/browserApi";
import axe from "axe-core";
for (const width of [390, 1140]) {
  test(`Overview VSCodium access review remains in place at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const message =
      "SDE could not open the file that stores your VSCodium preferences because it did not have permission to read it. Your settings have not been changed, and VSCodium may still work normally.";
    const metadata = {
      schema: 1,
      component: "VSCodium",
      scope: "standardUserFile",
      path: "/home/student/.config/VSCodium/User/settings.json",
      status: "unreadable",
      reason: "accessDenied",
      recommendations: [],
    };
    const report = {
      code: 0,
      success: true,
      validation_collected_at: Math.floor(Date.now() / 1000),
      lines: [
        `SKYVIEW_EVENT|preferences|VSCodium|${JSON.stringify(metadata)}`,
        "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
        `SKYVIEW_EVENT|validation|WARNING|${message}`,
        "SKYVIEW_EVENT|summary|0|Done",
      ],
      log_path: "Browser simulation",
      platform: { label: "Linux Mint 22.3", supported: true },
    };
    const resolved = {
      ...report,
      lines: [
        `SKYVIEW_EVENT|preferences|VSCodium|${JSON.stringify({ ...metadata, status: "missing", reason: "defaults" })}`,
        "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
        "SKYVIEW_EVENT|validation|INFO|VSCodium can use its defaults",
        "SKYVIEW_EVENT|summary|0|Done",
      ],
    };
    await page.route("**/src/bridge.ts*", async (route) => {
      if (
        new URL(route.request().url()).searchParams.has(
          "editorOverviewBaseline",
        )
      )
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
    export * from '/src/bridge.ts?editorOverviewBaseline';globalThis.__editorOverviewChecks=0;globalThis.__editorOverviewChanges=0;
    export async function inspect(){return ${JSON.stringify(report)};}
    export async function operate(mode){if(mode!=='validate'){globalThis.__editorOverviewChanges++;throw new Error('No changes allowed');}globalThis.__editorOverviewChecks++;const n=globalThis.__editorOverviewChecks;await new Promise(resolve=>setTimeout(resolve,n===4?350:80));if(n===1)return {...${JSON.stringify(report)},code:1,success:false,lines:['SKYVIEW_EVENT|error|collection|The check did not finish']};if(n===2)return {...${JSON.stringify(report)},lines:['SKYVIEW_EVENT|preferences|VSCodium|'+JSON.stringify({...${JSON.stringify(metadata)},reason:'readFailed'}),'SKYVIEW_EVENT|validation|PASS|Git: 2.49','SKYVIEW_EVENT|validation|WARNING|VSCodium preferences read failed','SKYVIEW_EVENT|summary|0|Done']};return n===3?${JSON.stringify(report)}:${JSON.stringify(resolved)};}
   `,
      });
    });
    await page.goto("/");
    const card = page.getByRole("region", {
      name: "We couldn’t finish checking VSCodium",
      exact: true,
    });
    await expect(card).toBeVisible();
    await expect(card.getByText(message, { exact: true })).toBeVisible();
    const review = card.getByRole("button", { name: "Review access problem" });
    await expect(review).toBeEnabled();
    await review.focus();
    await page.keyboard.press("Enter");
    const panel = card.getByRole("region", { name: "VSCodium access review" });
    await expect(panel).toBeVisible();
    expect(
      await page.evaluate(() => (window as any).__editorOverviewChecks),
    ).toBe(0);
    const check = panel.getByRole("button", { name: "Check VSCodium again" });
    await check.click();
    await expect(card.getByText(/These are earlier findings/)).toBeVisible();
    await expect(panel).toBeVisible();
    await expect(
      card.getByRole("heading", {
        name: "We couldn’t finish checking VSCodium",
      }),
    ).toBeFocused();
    await expect(check).toBeEnabled();
    await check.click();
    await expect(check).toBeEnabled();
    expect(
      await page.evaluate(() => (window as any).__editorOverviewChecks),
    ).toBe(2);
    await expect(panel).toBeVisible();
    await expect(card.getByText(/These are earlier findings/)).toBeVisible();
    await check.click();
    await expect(check).toBeEnabled();
    expect(
      await page.evaluate(() => (window as any).__editorOverviewChecks),
    ).toBe(3);
    await expect(card.getByText(/These are earlier findings/)).toHaveCount(0);
    await page.addScriptTag({ content: axe.source });
    expect(
      await page.evaluate(
        async () =>
          (
            await (window as any).axe.run(
              document.querySelector(
                '[aria-labelledby="editor-access-overview-heading"]',
              ),
            )
          ).violations,
      ),
    ).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await check.click();
    await expect
      .poll(() => page.evaluate(() => (window as any).__editorOverviewChecks))
      .toBe(4);
    await page.getByRole("button", { name: "About", exact: true }).click();
    await expect(
      page.getByRole("heading", {
        name: "About Skyview Dev Setup",
        exact: true,
      }),
    ).toBeVisible();
    await page.waitForTimeout(450);
    await expect(
      page.getByRole("heading", {
        name: "About Skyview Dev Setup",
        exact: true,
      }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    await expect(card).toHaveCount(0);
    expect(
      await page.evaluate(() => (window as any).__editorOverviewChanges),
    ).toBe(0);
  });
}
