import { test, expect } from "@playwright/test";
import { createRequire } from "node:module";
import { chooseTheme, closeAppearance } from "./appearance-helpers";
const require = createRequire(import.meta.url);
const id = "256f7aea-bf4d-4d0f-a73a-68c2b74e258b";
for (const theme of ["Light", "Dark"])
  for (const width of [640, 1140]) {
    test(`Report-independent observations in ${theme} at ${width}px remain read-only`, async ({
      page,
    }) => {
      // Test-only source fixtures, never native commands or real storage.
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
      const user = {
        entries: [
          {
            incidentId: id,
            status: "acknowledgment_observed",
            continuation: "not_recorded",
            acknowledgment: { acknowledgedAt: 50, reportId: null },
          },
          {
            incidentId: "b564efb0-e4b1-42b4-8c17-e794011bd734",
            status: "ambiguous_generations",
            continuation: "not_recorded",
          },
        ],
        nextCursor: null,
        unexpectedEntries: false,
      };
      await page.route("**/src/recoveryIncidents.ts*", (route) =>
        route.fulfill({
          contentType: "application/javascript",
          body: `export async function listRecoveryIncidents(source){return {observedAt:100,machine:source==='machine'?${JSON.stringify(machine)}:null,user:source==='user'?${JSON.stringify(user)}:null};}`,
        }),
      );
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/");
      await chooseTheme(page, theme);
      await closeAppearance(page);
      await page.getByRole("button", { name: "Recovery", exact: true }).click();
      const history = page.getByRole("region", {
        name: "Retained incident observations",
      });
      await expect(
        history.getByText(
          /Private contents were not read; acknowledgment status is unknown/,
        ),
      ).toBeVisible();
      await expect(
        history.getByText(/No saved report reference/),
      ).toBeVisible();
      await expect(
        history.getByText(/Multiple retained generations/),
      ).toBeVisible();
      await history
        .getByRole("button", { name: "Refresh user incident history" })
        .click();
      await expect(
        history.getByText("Continuation/completion: not recorded."),
      ).toHaveCount(3);
      await expect(
        history.getByRole("button", {
          name: /Acknowledge|Delete|Repair|Continue/,
        }),
      ).toHaveCount(0);
      await expect(page.getByRole("progressbar")).toHaveCount(0);
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
        path: `test-results/recovery-incidents-${theme}-${width}.png`,
        fullPage: true,
      });
    });
  }
