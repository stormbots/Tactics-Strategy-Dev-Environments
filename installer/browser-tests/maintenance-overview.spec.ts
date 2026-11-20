import { test, expect } from "../testing/browserApi";
import axe from "axe-core";
for (const width of [390, 1140]) {
  test(`Overview keeps the saved maintenance choice separate from findings at ${width}px`, async ({
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
      if (
        new URL(route.request().url()).searchParams.has(
          "overviewMaintenanceBaseline",
        )
      )
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
    export * from '/src/bridge.ts?overviewMaintenanceBaseline';
    globalThis.__maintenanceChanges=0;globalThis.__maintenanceDefinition='${"b".repeat(64)}';globalThis.__maintenanceUnavailable=false;
    export async function inspect(){return {validation_collected_at:Math.floor(Date.now()/1000),code:0,success:true,lines:['SKYVIEW_EVENT|validation|PASS|Git: 2.49','SKYVIEW_EVENT|summary|0|Done'],log_path:'Browser simulation',platform:{label:'Linux Mint 22.3',supported:true}};}
    export async function inspectSchedule(){if(globalThis.__maintenanceUnavailable)throw new Error('Unavailable');return {...${JSON.stringify(sample)},observedAt:new Date().toISOString(),choiceContext:{...${JSON.stringify(sample.choiceContext)},definitionId:globalThis.__maintenanceDefinition}};}
    export async function operate(){globalThis.__maintenanceChanges++;throw new Error('No operation permitted');}
    export async function setSelfUpdatePaused(){globalThis.__maintenanceChanges++;throw new Error('No policy change permitted');}
   `,
      });
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Ready!", exact: true }),
    ).toBeVisible();
    const card = page.getByRole("region", {
      name: "Weekly maintenance is disabled",
      exact: true,
    });
    await expect(card).toBeVisible();
    expect(
      await page.evaluate(() =>
        localStorage.getItem("sde.maintenance.disabled-choice.v1"),
      ),
    ).toBe(null);
    await card
      .getByRole("button", { name: "Review weekly maintenance" })
      .focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: "Maintenance schedule", exact: true }),
    ).toBeFocused();
    await page
      .getByRole("button", { name: "Leave maintenance disabled" })
      .click();
    await expect(
      page.getByText(/Your choice to leave maintenance disabled is saved/),
    ).toBeVisible();
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    const saved = page.getByRole("region", {
      name: "You chose to leave weekly maintenance disabled",
    });
    await expect(saved).toBeVisible();
    await expect(
      saved.getByText(/timer is still active in this session/),
    ).toBeVisible();
    await expect(
      saved.getByText(/An earlier maintenance attempt failed/),
    ).toBeVisible();
    await expect(
      saved.getByRole("button", { name: "View maintenance details" }),
    ).toBeVisible();
    await page.addScriptTag({ content: axe.source });
    expect(
      await page.evaluate(
        async () =>
          (
            await (window as any).axe.run(
              document.querySelector(
                '[aria-labelledby="maintenance-overview-heading"]',
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
    await saved
      .getByRole("button", { name: "View maintenance details" })
      .click();
    await page.evaluate(() => {
      (window as any).__maintenanceDefinition = "c".repeat(64);
    });
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(
      page.getByRole("button", { name: "Leave maintenance disabled" }),
    ).toBeEnabled();
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    await expect(card).toBeVisible();
    await expect(saved).toHaveCount(0);
    await card
      .getByRole("button", { name: "Review weekly maintenance" })
      .click();
    await page.evaluate(() => {
      (window as any).__maintenanceUnavailable = true;
    });
    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(page.getByText(/Schedule unavailable/)).toBeVisible();
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    await expect(
      page.getByRole("region", {
        name: "We couldn’t finish checking weekly maintenance",
      }),
    ).toBeVisible();
    await expect(saved).toHaveCount(0);
    expect(
      await page.evaluate(() => (window as any).__maintenanceChanges),
    ).toBe(0);
  });
}
