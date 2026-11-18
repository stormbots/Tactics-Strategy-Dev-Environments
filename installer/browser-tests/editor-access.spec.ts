import { test, expect } from "../testing/browserApi";
import axe from "axe-core";
import { chooseTheme, closeAppearance } from "./appearance-helpers";

for (const width of [390, 1140]) {
  test(`VSCodium access review stays in place at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const path = `/home/student/${"project preferences ".repeat(8)}/.config/VSCodium/User/settings.json`;
    const message =
      "SDE could not open the file that stores your VSCodium preferences because it did not have permission to read it. Your settings have not been changed, and VSCodium may still work normally.";
    const record = {
      schema: 1,
      component: "VSCodium",
      scope: "standardUserFile",
      path,
      status: "unreadable",
      reason: "accessDenied",
      recommendations: [],
    };
    const report = {
      validation_collected_at: 1793990000,
      code: 0,
      success: true,
      lines: [
        `SKYVIEW_EVENT|preferences|VSCodium|${JSON.stringify(record)}`,
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
        `SKYVIEW_EVENT|preferences|VSCodium|${JSON.stringify({ ...record, status: "missing", reason: "defaults" })}`,
        "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
        "SKYVIEW_EVENT|validation|INFO|VSCodium has no user preferences file here. It can use its defaults.",
        "SKYVIEW_EVENT|summary|0|Done",
      ],
    };
    await page.route("**/src/bridge.ts*", async (route) => {
      if (new URL(route.request().url()).searchParams.has("accessBaseline"))
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
        export * from '/src/bridge.ts?accessBaseline';
        export async function inspect(){return ${JSON.stringify(report)}}
        let attempts=0;
        export async function operate(mode){
          if(mode!=='validate')throw new Error('No changes permitted in this browser simulation');
          attempts++;
          if(attempts===1)return {...${JSON.stringify(report)},code:1,success:false,lines:['SKYVIEW_EVENT|error|collection|The check did not finish']};
          return ${JSON.stringify(resolved)};
        }
      `,
      });
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Ready!", exact: true }),
    ).toBeVisible();
    await chooseTheme(page, "Dark");
    await closeAppearance(page);
    await page.getByRole("button", { name: "Validation", exact: true }).click();
    const review = page.getByRole("button", {
      name: "Review access problem",
      exact: true,
    });
    await review.focus();
    await page.keyboard.press("Enter");
    const region = page.getByRole("region", { name: "VSCodium access review" });
    await expect(region).toBeVisible();
    await expect(region.getByText(path, { exact: true })).toBeVisible();
    await page.addScriptTag({ content: axe.source });
    const violations = await page.evaluate(
      async () =>
        (
          await (window as any).axe.run(
            document.querySelector(".validation-card"),
            { rules: { "color-contrast": { enabled: false } } },
          )
        ).violations,
    );
    expect(violations).toEqual([]);
    await region.getByRole("button", { name: "Check VSCodium again" }).click();
    await expect(
      page.getByText(/The earlier results are still shown below/),
    ).toBeVisible();
    await expect(region).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Validation results" }),
    ).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await region.getByRole("button", { name: "Check VSCodium again" }).click();
    await expect(review).toHaveCount(0);
    await expect(
      page.getByText(
        "VSCodium has no user preferences file here. It can use its defaults.",
        { exact: true },
      ),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Validation results" }),
    ).toBeVisible();
  });
}
