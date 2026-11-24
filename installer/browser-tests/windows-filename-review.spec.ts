import { test, expect } from "../testing/browserApi";
import { otherAction } from "./guided-helpers";
import axe from "axe-core";
for (const width of [390, 1140]) {
  test(`Windows required filename setting is disclosed before every approval at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    let platformLabel = "Windows 11 · x64";
    await page.route("**/src/bridge.ts*", async (route) => {
      if (
        new URL(route.request().url()).searchParams.has(
          "filenameReviewBaseline",
        )
      )
        return route.continue();
      const report = {
        code: 0,
        success: true,
        validation_collected_at: Math.floor(Date.now() / 1000),
        lines: [
          "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
          "SKYVIEW_EVENT|summary|0|Done",
        ],
        log_path: "Browser simulation",
        platform: { label: platformLabel, supported: true },
      };
      await route.fulfill({
        contentType: "application/javascript",
        body: `export * from '/src/bridge.ts?filenameReviewBaseline';globalThis.__filenameChanges=0;export async function inspect(){return ${JSON.stringify(report)};}export async function operate(){globalThis.__filenameChanges++;throw new Error('No changes permitted');}`,
      });
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Ready!", exact: true }),
    ).toBeVisible();
    for (const [action, approve, cancel] of [
      ["Install development tools", "Continue with Install", "Cancel"],
      ["Repair setup", "Repair setup", "Back"],
      ["Review tool updates", "Continue with Update", "Cancel"],
    ]) {
      await otherAction(page, action);
      const note = page.getByRole("complementary", {
        name: "Required Windows setting",
      });
      await expect(note).toBeVisible();
      await expect(note).toContainText("replace your current preference");
      const button = page.getByRole("button", { name: approve, exact: true });
      await expect(button).toBeEnabled();
      expect(
        await page.evaluate((name) => {
          const note = document.querySelector(
            '[aria-label="Required Windows setting"]',
          )!;
          const button = Array.from(document.querySelectorAll("button")).find(
            (b) => b.textContent?.trim() === name,
          )!;
          return !!(
            note.compareDocumentPosition(button) &
            Node.DOCUMENT_POSITION_FOLLOWING
          );
        }, approve),
      ).toBe(true);
      await page.addScriptTag({ content: axe.source });
      expect(
        await page.evaluate(
          async () =>
            (
              await (window as any).axe.run(
                document.querySelector(
                  '[aria-label="Required Windows setting"]',
                ),
              )
            ).violations,
        ),
      ).toEqual([]);
      await button.focus();
      await page.keyboard.press("Tab");
      expect(await page.evaluate(() => (window as any).__filenameChanges)).toBe(
        0,
      );
      await page.getByRole("button", { name: cancel, exact: true }).click();
      await expect(note).toHaveCount(0);
    }
    expect(await page.evaluate(() => (window as any).__filenameChanges)).toBe(
      0,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    platformLabel = "Linux Mint 22.3";
    await page.reload();
    await expect(
      page.getByRole("heading", { name: "Ready!", exact: true }),
    ).toBeVisible();
    await otherAction(page, "Install development tools");
    await expect(
      page.getByRole("heading", { name: "Before Install begins" }),
    ).toBeVisible();
    await expect(
      page.getByRole("complementary", { name: "Required Windows setting" }),
    ).toHaveCount(0);
    await page.getByRole("button", { name: "Cancel", exact: true }).click();
    expect(await page.evaluate(() => (window as any).__filenameChanges)).toBe(
      0,
    );
  });
}
