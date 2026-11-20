import { test, expect } from "../testing/browserApi";
import axe from "axe-core";
for (const width of [390, 1140]) {
  test(`Overview safety finding stays specific and review-only at ${width}px`, async ({
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
    globalThis.__overviewSafety=${JSON.stringify(state)};globalThis.__safetyAcks=0;
    export async function inspectRecovery(){return structuredClone(globalThis.__overviewSafety);}
    export async function acknowledgeMachine(){globalThis.__safetyAcks++;throw new Error('No acknowledgment permitted');}
    export async function acknowledgeUser(){globalThis.__safetyAcks++;throw new Error('No acknowledgment permitted');}
   `,
      });
    });
    await page.route("**/src/bridge.ts*", async (route) => {
      if (
        new URL(route.request().url()).searchParams.has("safetyBridgeBaseline")
      )
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
    export * from '/src/bridge.ts?safetyBridgeBaseline';globalThis.__safetyOperations=0;
    export async function inspect(){return {validation_collected_at:Math.floor(Date.now()/1000),code:1,success:true,lines:['SKYVIEW_EVENT|validation|FAIL|Python: expected 3.14; detected 3.15','SKYVIEW_EVENT|summary|1|Done'],log_path:'Browser simulation',platform:{label:'Windows 11',supported:true}};}
    export async function operate(){globalThis.__safetyOperations++;throw new Error('No operation permitted');}
   `,
      });
    });
    await page.goto("/");
    const card = page.getByRole("region", {
      name: "Change safety needs review",
    });
    await expect(card).toBeVisible();
    await expect(
      card.getByText("Development-tool Update", { exact: true }),
    ).toBeVisible();
    await expect(
      card.getByText("Operation name unavailable", { exact: true }),
    ).toBeVisible();
    await expect(
      card.getByText(
        /cannot yet confirm that the earlier system operation ended/,
      ),
    ).toBeVisible();
    await expect(card).not.toContainText("Python");
    await expect(card).not.toContainText("Separate finding");
    await page.addScriptTag({ content: axe.source });
    expect(
      await page.evaluate(
        async () =>
          (
            await (window as any).axe.run(
              document.querySelector(
                '[aria-labelledby="change-safety-overview-heading"]',
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
    const address = card.getByRole("button", {
      name: "Address safety finding",
    });
    await expect(address).toBeEnabled();
    await address.focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("button", { name: "Check again", exact: true }),
    ).toBeVisible();
    expect(await page.evaluate(() => (window as any).__safetyAcks)).toBe(0);
    expect(await page.evaluate(() => (window as any).__safetyOperations)).toBe(
      0,
    );
    await page.evaluate(() => {
      const s = (window as any).__overviewSafety;
      s.nativeSafety.activity = "inactive";
      s.nativeSafety.activityReason = "no_package_activity";
      s.nativeSafety.interrupted = false;
      s.nativeSafety.restart = "confirmed";
      s.machine.incidentId = null;
      s.user.incident = null;
      s.user.gate = "inactive";
      s.user.restart = "confirmed";
      s.effectiveActivity = "inactive";
      s.readiness = "ready_for_native_recheck";
      s.decision = "allow_with_health_warning";
    });
    await page
      .getByRole("button", { name: "Check again", exact: true })
      .click();
    await expect(
      page.getByRole("region", {
        name: "There is nothing to recover from right now",
      }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    await expect(card).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__safetyAcks)).toBe(0);
    expect(await page.evaluate(() => (window as any).__safetyOperations)).toBe(
      0,
    );
  });
}
