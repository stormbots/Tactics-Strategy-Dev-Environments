import { test, expect, type Page } from "@playwright/test";
import axe from "axe-core";
import { chooseTheme, closeAppearance } from "./appearance-helpers";
import { otherAction, disclosure } from "./guided-helpers";
const good = {
  code: 0,
  success: true,
  validation_collected_at: 1793990000,
  mutation_outcome: "completed",
  lines: [
    "SKYVIEW_EVENT|validation|PASS|Git: 2.49",
    "SKYVIEW_EVENT|summary|0|Done",
  ],
  log_path: "Synthetic lifecycle fixture",
  platform: { label: "Fixture — no native operations", supported: true },
};
async function fixture(page: Page, outcome: string) {
  const report =
    outcome === "not-started"
      ? {
          ...good,
          mutation_outcome: "not_started",
          code: 1,
          success: false,
          lines: [
            "SKYVIEW_EVENT|error|operation|Administrator approval was cancelled",
          ],
          validation_collected_at: null,
        }
      : outcome === "incomplete"
        ? {
            ...good,
            code: 1,
            success: false,
            lines: [],
            validation_collected_at: null,
          }
        : { ...good, mutation_outcome: "uncertain" };
  await page.route("**/src/bridge.ts*", async (route) => {
    if (new URL(route.request().url()).searchParams.has("lifecycleBaseline")) {
      await route.continue();
      return;
    }
    await route.fulfill({
      contentType: "application/javascript",
      body: `
      export * from '/src/bridge.ts?lifecycleBaseline';
      window.lifecycleCalls=[];
      export async function inspect(){return ${JSON.stringify({ ...good, mutation_outcome: "not_requested" })};}
      export async function operate(mode,id,updates,ack,emit){
        window.lifecycleCalls.push({mode,updates});
        if(mode==='validate')return ${JSON.stringify({ ...good, mutation_outcome: "not_requested" })};
        emit('SKYVIEW_EVENT|progress|95|Validating your development environment');
        if(${JSON.stringify(outcome)}==='pending')return new Promise(resolve=>{window.finishLifecycle=()=>resolve(${JSON.stringify(good)})});
        return ${JSON.stringify(report)};
      }`,
    });
  });
}
async function proceed(page: Page) {
  await otherAction(page, "Install development tools");
  await page
    .getByRole("button", { name: "Continue with Install", exact: true })
    .click();
}
for (const theme of ["Light", "Dark"])
  for (const width of [390, 1140]) {
    test(`${theme} lifecycle results at ${width}px retain safe next steps`, async ({
      page,
    }) => {
      test.setTimeout(60000);
      await page.setViewportSize({ width, height: 900 });
      for (const [outcome, heading] of [
        ["not-started", "No changes were started"],
        ["uncertain", "Setup outcome is unconfirmed"],
        ["incomplete", "Setup finished, but checking did not finish"],
      ]) {
        await page.unrouteAll();
        await fixture(page, outcome);
        await page.goto("/");
        await expect(
          page.getByRole("heading", { name: "Ready!", exact: true }),
        ).toBeVisible();
        await chooseTheme(page, theme);
        await closeAppearance(page);
        await proceed(page);
        await expect(
          page.getByRole("heading", { name: heading, exact: true }),
        ).toBeVisible();
        await expect(
          page.getByRole("heading", { name: "Ready!", exact: true }),
        ).toHaveCount(0);
        await expect(page.locator(".guided-task button.primary")).toHaveCount(
          1,
        );
        expect(
          await page.evaluate(() =>
            (window as any).lifecycleCalls.map((c: any) => c.mode),
          ),
        ).toEqual(["install"]);
        await page.addScriptTag({ content: axe.source });
        expect(
          await page.evaluate(
            async () => (await (window as any).axe.run(document)).violations,
          ),
        ).toEqual([]);
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth > innerWidth + 1,
          ),
        ).toBe(false);
        await page.screenshot({
          path: `test-results/lifecycle-${outcome}-${theme}-${width}.png`,
          fullPage: true,
        });
        if (outcome === "not-started")
          await page
            .getByRole("button", { name: "Back to Overview", exact: true })
            .click();
        await page
          .getByRole("button", { name: /^Check (my setup|again)$/ })
          .click();
        await expect(
          page.getByRole("heading", { name: "Ready!", exact: true }),
        ).toBeVisible();
        expect(
          await page.evaluate(() =>
            (window as any).lifecycleCalls.map((c: any) => c.mode),
          ),
        ).toEqual(["install", "validate"]);
      }
    });
  }
test("one confirmed operation keeps verification and result through navigation", async ({
  page,
}) => {
  await fixture(page, "pending");
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Ready!", exact: true }),
  ).toBeVisible();
  await otherAction(page, "Install development tools");
  await page
    .getByRole("button", { name: "Continue with Install", exact: true })
    .evaluate((button: HTMLButtonElement) => {
      button.click();
      button.click();
    });
  await expect(
    page.getByRole("heading", { name: "Checking the result…", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "About", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Return to current task", exact: true }),
  ).toBeVisible();
  await page.evaluate(() => (window as any).finishLifecycle());
  await expect(
    page.getByRole("button", { name: "Return to current task", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "About", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Ready!", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(() => (window as any).lifecycleCalls),
  ).toHaveLength(1);
});
test("changed review options require another review before execution", async ({
  page,
}) => {
  await fixture(page, "not-started");
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Ready!", exact: true }),
  ).toBeVisible();
  await otherAction(page, "Install development tools");
  await page.getByRole("button", { name: /^Validation/ }).click();
  await page.getByText("Advanced", { exact: true }).click();
  await page
    .getByLabel("Check for managed package updates during validation")
    .check();
  await page.getByRole("button", { name: "Overview", exact: true }).click();
  await page
    .getByRole("button", { name: "Continue with Install", exact: true })
    .click();
  await expect(
    page.getByText(/The reviewed findings or scope changed/),
  ).toBeVisible();
  expect(
    await page.evaluate(() => (window as any).lifecycleCalls),
  ).toHaveLength(0);
  await page
    .getByRole("button", { name: "Continue with Install", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "No changes were started", exact: true }),
  ).toBeVisible();
  expect(await page.evaluate(() => (window as any).lifecycleCalls)).toEqual([
    { mode: "install", updates: true },
  ]);
});
test("reopen discards an unstarted review and makes no operation request", async ({
  page,
}) => {
  await fixture(page, "pending");
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Ready!", exact: true }),
  ).toBeVisible();
  await otherAction(page, "Install development tools");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Start building", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Before Install begins", exact: true }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(() => (window as any).lifecycleCalls),
  ).toHaveLength(0);
  await disclosure(page, "Details");
  await expect(
    page.getByRole("button", { name: "Create support report", exact: true }),
  ).toBeVisible();
});
