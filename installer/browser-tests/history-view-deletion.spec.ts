import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
import { chooseTheme, closeAppearance } from "./appearance-helpers";
const require = createRequire(import.meta.url);
const id = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
for (const theme of ["Light", "Dark"])
  for (const width of [640, 1140]) {
    test(`History view confirmation in ${theme} at ${width}px preserves other-source observations`, async ({
      page,
    }) => {
      const machine = {
        entries: [
          {
            incidentId: id,
            status: "archive_observed_acknowledgment_unknown",
            continuation: "not_recorded",
          },
        ],
        nextCursor: null,
      };
      const entry = {
        incidentId: id,
        status: "acknowledgment_observed",
        continuation: "not_recorded",
        acknowledgment: { acknowledgedAt: 50, reportId: null },
        viewToken: "opaque-user-view",
      };
      await page.route("**/src/recoveryIncidents.ts*", (route) =>
        route.fulfill({
          contentType: "application/javascript",
          body: `let deleted=false; export async function listRecoveryIncidents(source){return {observedAt:100,hiddenViews:source==='user'&&deleted?1:0,machine:source==='machine'?${JSON.stringify(machine)}:null,user:source==='user'?{entries:deleted?[]:[${JSON.stringify(entry)}],nextCursor:null}:null};} export async function deleteRecoveryHistoryView(token){if(token!=='opaque-user-view')throw new Error('Wrong view');deleted=true;}`,
        }),
      );
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await chooseTheme(page, theme);
      await closeAppearance(page);
      await page.getByRole("button", { name: "Recovery", exact: true }).click();
      await page.getByText("Earlier recovery events", { exact: true }).click();
      const history = page.getByRole("region", {
        name: "Recovery event history",
      });
      const remove = history.getByRole("button", {
        name: `Delete user history view ${id}`,
        exact: true,
      });
      await remove.click();
      await expect(
        history.getByRole("group", {
          name: "Confirm user history view deletion",
        }),
      ).toBeVisible();
      await history
        .getByRole("button", { name: "Keep user history view" })
        .click();
      await expect(remove).toBeFocused();
      await remove.click();
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
        path: `test-results/history-view-deletion-${theme}-${width}.png`,
        fullPage: true,
      });
      await history
        .getByRole("button", { name: "Confirm delete user history view" })
        .click();
      await expect(
        history.getByText(/Selected history view deleted/),
      ).toBeVisible();
      await expect(
        history.getByText(`Incident ${id}`, { exact: true }),
      ).toHaveCount(1);
      await expect(page.getByRole("progressbar")).toHaveCount(0);
      await history
        .getByRole("button", { name: "Refresh user incident history" })
        .click();
      await expect(
        history.getByText(/1 deleted history view is excluded/),
      ).toBeVisible();
    });
  }
