import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
import { chooseTheme, closeAppearance } from "./appearance-helpers";
const require = createRequire(import.meta.url);
const id = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
for (const theme of ["Light", "Dark"])
  for (const width of [640, 1140]) {
    test(`Saved Recovery report review and explicit deletion in ${theme} at ${width}px`, async ({
      page,
    }) => {
      // Test-only module fixture: no native commands, files, journals or production
      // preview flags. Native storage/export correctness is a separate CI gate.
      const entry = {
        reportId: id,
        incidentId: id,
        capturedAt: 100,
        status: "saved",
      };
      const details = {
        reportId: id,
        html: "<!doctype html><html lang='en'><head><title>Synthetic report</title></head><body><h1>SDE recovery summary</h1><p>Synthetic diagnostic snapshot, not completion evidence.</p></body></html>",
        acknowledgment: {
          source: "user",
          status: "unknown",
          observedAt: 200,
          acknowledgedAt: null,
          note: "No matching acknowledgment was established. This does not prove completion.",
          continuation: "not_recorded",
        },
      };
      await page.route("**/src/recoveryReports.ts*", (route) =>
        route.fulfill({
          contentType: "application/javascript",
          body: `let present=true; export async function listRecoveryReports(){return {entries:present?[${JSON.stringify(entry)}]:[],nextCursor:null};} export async function readRecoveryReport(){return ${JSON.stringify(details)};} export async function exportRecoveryReport(){return null;} export async function deleteRecoveryReport(){present=false;}`,
        }),
      );
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await chooseTheme(page, theme);
      await closeAppearance(page);
      await page.getByRole("button", { name: "Recovery", exact: true }).click();
      await page
        .getByRole("button", { name: `View report ${id}`, exact: true })
        .click();
      await expect(
        page.getByRole("heading", { name: "Selected recovery summary" }),
      ).toBeFocused();
      await expect(
        page.getByTitle("Retained recovery summary preview"),
      ).toHaveAttribute("sandbox", "");
      await expect(
        page.getByText(/Acknowledgment observation: unknown/),
      ).toBeVisible();
      await page.getByRole("button", { name: "Export report copy" }).click();
      await expect(page.getByText(/Export canceled/)).toBeVisible();
      await page
        .getByRole("button", { name: "Delete selected local report" })
        .click();
      await page.getByRole("button", { name: "Keep local report" }).click();
      await expect(
        page.getByTitle("Retained recovery summary preview"),
      ).toBeVisible();
      await page.addScriptTag({ path: require.resolve("axe-core/axe.min.js") });
      const violations = await page.evaluate(
        async () =>
          (
            await (
              window as unknown as {
                axe: {
                  run: (options: unknown) => Promise<{ violations: unknown[] }>;
                };
              }
            ).axe.run({
              runOnly: {
                type: "tag",
                values: ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"],
              },
            })
          ).violations,
      );
      expect(violations).toEqual([]);
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth + 1,
        ),
      ).toBe(true);
      await page.screenshot({
        path: `test-results/recovery-history-${theme}-${width}.png`,
        fullPage: true,
      });
      await page
        .getByRole("button", { name: "Delete selected local report" })
        .click();
      await page
        .getByRole("button", { name: "Confirm delete local report" })
        .click();
      await expect(
        page.getByText(/Selected local report deleted/),
      ).toBeVisible();
      await expect(page.getByRole("progressbar")).toHaveCount(0);
      await page
        .getByRole("button", { name: "Refresh report history" })
        .click();
      await expect(
        page.getByText(/No retained reports were found/),
      ).toBeVisible();
    });
  }
