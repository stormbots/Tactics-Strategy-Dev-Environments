import { test, expect } from "../testing/browserApi";
import axe from "axe-core";
for (const width of [390, 1140]) {
  test(`Python finding uses structured evidence and read-only follow-up at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.route("**/src/bridge.ts*", async (route) => {
      if (new URL(route.request().url()).searchParams.has("pythonCardBaseline"))
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
    export * from '/src/bridge.ts?pythonCardBaseline';globalThis.__pythonPhase='missing';globalThis.__pythonChanges=0;globalThis.__pythonChecks=0;
    function result(){const phase=globalThis.__pythonPhase;const ok=phase==='passed';const runtime={schema:1,component:'Python',requiredFamily:'3.14',status:ok?'passed':phase==='timeout'?'incomplete':'notFound',reason:ok?'verified':phase==='timeout'?'interpreterTimeout':'notDiscovered',version:ok?'3.14.9':null,executable:ok?'C:\\\\Python314\\\\python.exe':null,pipVersion:ok?'25.3':null};return {code:ok?0:1,success:ok,validation_collected_at:Math.floor(Date.now()/1000),lines:['SKYVIEW_EVENT|runtime|Python|'+JSON.stringify(runtime),'SKYVIEW_EVENT|validation|'+(ok?'PASS':'FAIL')+'|Python: observed result; another Python 3.15 can remain installed','SKYVIEW_EVENT|summary|'+(ok?'0':'1')+'|Done'],log_path:'Browser simulation',platform:{label:'Windows 11',supported:true}};}
    export async function inspect(){return result();}
    export async function operate(mode){if(mode!=='validate'){globalThis.__pythonChanges++;throw new Error('No modifications allowed');}globalThis.__pythonChecks++;globalThis.__pythonPhase=globalThis.__pythonChecks===1?'timeout':'passed';await new Promise(resolve=>setTimeout(resolve,120));return result();}
   `,
      });
    });
    await page.goto("/");
    const missing = page.getByRole("region", {
      name: "Python 3.14 wasn’t found by this check",
    });
    await expect(missing).toBeVisible();
    await expect(
      missing.getByText(/Other Python versions can stay installed/),
    ).toBeVisible();
    await expect(missing).not.toContainText("Restart");
    await missing.getByRole("button", { name: "Review Python check" }).focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: "Validation results", exact: true }),
    ).toBeVisible();
    expect(await page.evaluate(() => (window as any).__pythonChanges)).toBe(0);
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    const check = page.getByRole("button", {
      name: "Check setup again",
      exact: true,
    });
    await expect(check).toBeEnabled();
    await check.click();
    await expect(
      page.getByText(/earlier Python result stays below/),
    ).toBeVisible();
    const timeout = page.getByRole("region", {
      name: "The Python check took too long",
    });
    await expect(timeout).toBeVisible();
    await expect(
      timeout.getByText(/does not mean Python is missing/),
    ).toBeVisible();
    await expect(missing).toHaveCount(0);
    await page.addScriptTag({ content: axe.source });
    expect(
      await page.evaluate(
        async () =>
          (
            await (window as any).axe.run(
              document.querySelector(
                '[aria-labelledby="python-readiness-heading"]',
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
    await expect(check).toBeEnabled();
    await check.click();
    await expect(
      page.locator('[aria-labelledby="python-readiness-heading"]'),
    ).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__pythonChecks)).toBe(2);
    expect(await page.evaluate(() => (window as any).__pythonChanges)).toBe(0);
  });
}
