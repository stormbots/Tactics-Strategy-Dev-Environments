import { test, expect } from "../testing/browserApi";
import axe from "axe-core";

for (const width of [390, 1140]) {
  test(`Maintenance inspection stays in place at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const record = {
      status: "unavailable",
      active: false,
      identifier: "skyview-student-dev-update.timer",
      inspectionScope: "schedule",
      inspectionReason: "accessDenied",
      frequency: "Unavailable",
      nextRun: null,
      lastRun: null,
      lastResult: "unavailable",
      resultDetail: "Unavailable",
      catchUp: null,
      logFolder: "/logs",
      logsAvailable: false,
      note: "Confirmed native read-access failure",
      observedAt: "2026-11-18T00:00:00Z",
      createdAt: null,
      lastSuccess: null,
    };
    await page.route("**/src/bridge.ts*", async (route) => {
      if (
        new URL(route.request().url()).searchParams.has("maintenanceBaseline")
      )
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
        export * from '/src/bridge.ts?maintenanceBaseline';
        export async function inspect(){return {validation_collected_at:1793990000,code:0,success:true,
          lines:['SKYVIEW_EVENT|validation|PASS|Git: 2.49','SKYVIEW_EVENT|summary|0|Done'],
          log_path:'Browser simulation',platform:{label:'Linux Mint 22.3',supported:true}};}
        globalThis.__schedulePhase='denied';globalThis.__scheduleChanges=0;
        export async function inspectSchedule(){
          if(globalThis.__schedulePhase==='transport')throw new Error('The status check did not finish');
          if(globalThis.__schedulePhase==='disabled')return {...${JSON.stringify(record)},status:'disabled',inspectionReason:'verified',lastResult:'failure',resultDetail:'Earlier failed attempt'};
          if(globalThis.__schedulePhase==='history')return {...${JSON.stringify(record)},status:'enabled',active:true,inspectionScope:'history'};
          if(globalThis.__schedulePhase==='inactive')return {...${JSON.stringify(record)},status:'enabled',active:false,inspectionReason:'verified'};
          if(globalThis.__schedulePhase==='enabled')return {...${JSON.stringify(record)},status:'enabled',active:true,inspectionReason:'verified'};
          return ${JSON.stringify(record)};
        }
        export async function operate(){globalThis.__scheduleChanges++;throw new Error('No operation is permitted in this simulation');}
        export async function setSelfUpdatePaused(){globalThis.__scheduleChanges++;throw new Error('No policy change is permitted in this simulation');}
      `,
      });
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Ready!", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Schedule", exact: true }).click();
    const review = page.getByRole("region", {
      name: "Maintenance status review",
    });
    await expect(
      review.getByRole("heading", {
        name: "We couldn’t check weekly maintenance",
      }),
    ).toBeVisible();
    await expect(review.getByText(/SDE did not have permission/)).toBeVisible();
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
    await page.evaluate(() => {
      (window as any).__schedulePhase = "transport";
    });
    const retry = review.getByRole("button", {
      name: "Check maintenance status again",
    });
    await retry.focus();
    await page.keyboard.press("Enter");
    await expect(
      review.getByRole("heading", {
        name: "We couldn’t finish checking weekly maintenance",
      }),
    ).toBeVisible();
    await page.evaluate(() => {
      (window as any).__schedulePhase = "disabled";
    });
    await retry.click();
    await expect(
      review.getByRole("heading", { name: "Weekly maintenance is disabled" }),
    ).toBeVisible();
    await expect(page.locator(".schedule-status")).toContainText("Disabled");
    await expect(
      page.getByRole("heading", { name: "Scheduled maintenance", exact: true }),
    ).toBeFocused();
    await page.evaluate(() => {
      (window as any).__schedulePhase = "denied";
    });
    await retry.click();
    await expect(
      review.getByRole("heading", {
        name: "We couldn’t check weekly maintenance",
      }),
    ).toBeVisible();
    await page
      .getByText("Earlier maintenance observation", { exact: true })
      .click();
    await expect(page.getByText(/Earlier failed attempt/)).toBeVisible();
    await expect(page.locator(".schedule-status")).toContainText("Unavailable");
    await page.evaluate(() => {
      (window as any).__schedulePhase = "history";
    });
    await retry.click();
    await expect(
      review.getByRole("heading", {
        name: "We couldn’t check the maintenance history",
      }),
    ).toBeVisible();
    await expect(page.locator(".schedule-status")).toContainText("Enabled");
    await page.evaluate(() => {
      (window as any).__schedulePhase = "inactive";
    });
    await retry.click();
    await expect(
      review.getByRole("heading", {
        name: "Weekly maintenance is enabled but not waiting",
      }),
    ).toBeVisible();
    await expect(page.locator(".schedule-status")).toContainText(
      "Enabled · Inactive",
    );
    await page.evaluate(() => {
      (window as any).__schedulePhase = "enabled";
    });
    await retry.click();
    await expect(review).toHaveCount(0);
    await expect(
      page.getByText("Earlier maintenance observation", { exact: true }),
    ).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__scheduleChanges)).toBe(
      0,
    );
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}
