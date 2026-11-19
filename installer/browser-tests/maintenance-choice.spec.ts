import { test, expect } from "../testing/browserApi";
import axe from "axe-core";
for (const width of [390, 1140]) {
  test(`Maintenance choice stays explicit and in place at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const sample = {
      status: "disabled",
      active: true,
      identifier: "skyview-student-dev-update.timer",
      inspectionScope: "schedule",
      inspectionReason: "verified",
      choiceContext: {
        machineId: "a".repeat(64),
        identifier: "skyview-student-dev-update.timer",
        definitionId: "b".repeat(64),
      },
      frequency: "Weekly",
      nextRun: null,
      lastRun: null,
      lastResult: "failure",
      resultDetail: "Earlier failed attempt",
      catchUp: true,
      logFolder: "/logs",
      logsAvailable: false,
      note: "",
      createdAt: null,
      lastSuccess: null,
    };
    await page.route("**/src/bridge.ts*", async (route) => {
      if (new URL(route.request().url()).searchParams.has("choiceBaseline"))
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
        export * from '/src/bridge.ts?choiceBaseline';
        globalThis.__choiceReads=0;globalThis.__choiceChanges=0;globalThis.__choiceDefinition='${"b".repeat(64)}';
        export async function inspect(){return {validation_collected_at:Math.floor(Date.now()/1000),code:0,success:true,lines:['SKYVIEW_EVENT|validation|PASS|Git: 2.49','SKYVIEW_EVENT|summary|0|Done'],log_path:'Browser simulation',platform:{label:'Linux Mint 22.3',supported:true}};}
        export async function inspectSchedule(){globalThis.__choiceReads++;return {...${JSON.stringify(sample)},observedAt:new Date().toISOString(),choiceContext:{...${JSON.stringify(sample.choiceContext)},definitionId:globalThis.__choiceDefinition}};}
        export async function operate(){globalThis.__choiceChanges++;throw new Error('No operation allowed');}
        export async function setSelfUpdatePaused(){globalThis.__choiceChanges++;throw new Error('No policy change allowed');}
      `,
      });
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Ready!", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Schedule", exact: true }).click();
    const save = page.getByRole("button", {
      name: "Leave maintenance disabled",
    });
    await expect(save).toBeEnabled();
    expect(
      await page.evaluate(() =>
        localStorage.getItem("sde.maintenance.disabled-choice.v1"),
      ),
    ).toBe(null);
    const readsBefore = await page.evaluate(
      () => (window as any).__choiceReads,
    );
    await save.focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByText(/Your choice to leave maintenance disabled is saved/),
    ).toBeVisible();
    await expect(page.locator(".schedule-status")).toContainText("Disabled");
    await expect(
      page.getByText(/timer is still active in this session/),
    ).toBeVisible();
    await expect(
      page.getByText("Earlier failed attempt", { exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Scheduled maintenance", exact: true }),
    ).toBeFocused();
    expect(await page.evaluate(() => (window as any).__choiceReads)).toBe(
      readsBefore + 1,
    );
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    await page.getByRole("button", { name: "Schedule", exact: true }).click();
    await expect(
      page.getByText(/Your choice to leave maintenance disabled is saved/),
    ).toBeVisible();
    await expect(save).toHaveCount(0);
    await page.evaluate(() => {
      (window as any).__choiceDefinition = "c".repeat(64);
    });
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(save).toBeEnabled();
    await page.evaluate(() => {
      (window as any).__choiceOriginalSet = Storage.prototype.setItem;
      Storage.prototype.setItem = function () {
        throw new Error("storage denied");
      };
    });
    await save.click();
    await expect(page.getByText(/SDE couldn’t save your choice/)).toBeVisible();
    await expect(save).toBeEnabled();
    await page.evaluate(() => {
      Storage.prototype.setItem = (window as any).__choiceOriginalSet;
    });
    await save.click();
    await expect(
      page.getByText(/Your choice to leave maintenance disabled is saved/),
    ).toBeVisible();
    expect(await page.evaluate(() => (window as any).__choiceChanges)).toBe(0);
    await page.addScriptTag({ content: axe.source });
    const violations = await page.evaluate(
      async () =>
        (
          await (window as any).axe.run(
            document.querySelector(".information-card"),
          )
        ).violations,
    );
    expect(violations).toEqual([]);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  });
}
