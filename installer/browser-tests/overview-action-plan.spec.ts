import { test, expect } from "../testing/browserApi";
import axe from "axe-core";
for (const width of [390, 1140]) {
  test(`Procedural plan links current findings and preserves safety at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    const now = Math.floor(Date.now() / 1000);
    const state = {
      nativeSafety: {
        observedAt: now,
        trust: "trusted",
        activity: "unknown",
        packageHealth: "unknown",
        activityReason: "earlier_process_lifetime_unknown",
        restart: "same_session",
        interrupted: true,
        acknowledged: false,
        decision: "block_activity_unknown",
      },
      machine: {
        available: true,
        incidentId: "256f7aea-bf4d-4d0f-a73a-68c2b74e258b",
        intentSubmitted: false,
        acknowledgedAt: null,
      },
      user: {
        observedAt: now,
        available: true,
        incident: {
          id: "9bdf869a-2750-4fe3-811b-7572906bbc08",
          operation: "update",
          stage: "profile",
          startedAt: now - 3600,
          observedAt: now - 1800,
        },
        acknowledgment: null,
        restart: "same_session",
        gate: "unknown",
        viewToken: null,
      },
      effectiveActivity: "unknown",
      decision: "block_activity_unknown",
      readiness: "blocked",
      canAcknowledgeMachine: false,
      canAcknowledgeUser: false,
      guidance: {
        code: "activity_unknown",
        title: "Earlier operation remains unconfirmed",
        steps: ["Review the current safety findings."],
      },
    };
    await page.route("**/src/recovery.ts*", async (route) => {
      if (new URL(route.request().url()).searchParams.has("safetyBaseline"))
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
    export * from '/src/recovery.ts?safetyBaseline';
    globalThis.__overviewSafety=${JSON.stringify(state)};globalThis.__planAcks=0;
    export async function inspectRecovery(){return structuredClone(globalThis.__overviewSafety);}
    export async function acknowledgeMachine(){globalThis.__planAcks++;throw new Error('No acknowledgment permitted');}
    export async function acknowledgeUser(){globalThis.__planAcks++;throw new Error('No acknowledgment permitted');}
   `,
      });
    });
    await page.route("**/src/bridge.ts*", async (route) => {
      if (new URL(route.request().url()).searchParams.has("planBaseline"))
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
      export * from '/src/bridge.ts?planBaseline';globalThis.__planPassed=false;globalThis.__planChanges=0;
      function result(){const ok=globalThis.__planPassed;return {validation_collected_at:Math.floor(Date.now()/1000),code:ok?0:1,success:ok,lines:['SKYVIEW_EVENT|runtime|Python|'+JSON.stringify({schema:1,component:'Python',requiredFamily:'3.14',status:ok?'passed':'notFound',reason:ok?'verified':'notDiscovered',version:ok?'3.14.9':null,executable:ok?'C:\\\\Python314\\\\python.exe':null,pipVersion:ok?'25.3':null}),'SKYVIEW_EVENT|validation|'+(ok?'PASS':'FAIL')+'|Python: checked','SKYVIEW_EVENT|summary|'+(ok?0:1)+'|Done'],log_path:'Browser simulation',platform:{label:'Windows 11',supported:true}};}
      export async function inspect(){return result();}
      export async function operate(mode){if(mode!=='validate'){globalThis.__planChanges++;throw new Error('No changes allowed');}globalThis.__planPassed=true;return result();}
      `,
      });
    });
    await page.goto("/");
    const plan = page.getByRole("region", { name: "Review the 2 items below" });
    await expect(plan).toBeVisible();
    const items = plan.getByRole("list", { name: "Items to review" });
    await expect(items.getByRole("listitem")).toHaveCount(2);
    const python = plan.getByRole("button", {
      name: "Review the Python requirement",
    });
    await python.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator("#python-readiness-heading")).toBeFocused();
    await plan.getByRole("button", { name: "Review change safety" }).click();
    await expect(page.locator("#change-safety-overview-heading")).toBeFocused();
    await expect(
      page.locator('[aria-labelledby="change-safety-overview-heading"]'),
    ).not.toContainText("Python");
    await page.addScriptTag({ content: axe.source });
    expect(
      await page.evaluate(
        async () =>
          (
            await (window as any).axe.run(
              document.querySelector(".guided-task"),
            )
          ).violations,
      ),
    ).toEqual([]);
    const card = page.locator('[aria-labelledby="python-readiness-heading"]');
    await card.getByRole("button", { name: "Check setup again" }).click();
    const remaining = page.getByRole("region", {
      name: "Review the item below",
    });
    await expect(remaining).toBeVisible();
    await expect(remaining.getByRole("listitem")).toHaveCount(1);
    await expect(
      remaining.getByRole("button", { name: "Review change safety" }),
    ).toBeVisible();
    await expect(card).toHaveCount(0);
    await expect(
      page.locator('[aria-labelledby="change-safety-overview-heading"]'),
    ).toBeVisible();
    expect(await page.evaluate(() => (window as any).__planChanges)).toBe(0);
    expect(await page.evaluate(() => (window as any).__planAcks)).toBe(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}
