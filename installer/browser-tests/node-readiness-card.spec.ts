import { test, expect } from "../testing/browserApi";
import axe from "axe-core";
for (const width of [390, 1140]) {
  test(`Node.js/npm finding keeps failed and incomplete checks distinct at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.route("**/src/bridge.ts*", async (route) => {
      if (new URL(route.request().url()).searchParams.has("nodeCardBaseline"))
        return route.continue();
      await route.fulfill({
        contentType: "application/javascript",
        body: `
    export * from '/src/bridge.ts?nodeCardBaseline';globalThis.__nodePhase='missing';globalThis.__nodeChanges=0;globalThis.__nodeChecks=0;
    function result(){const phase=globalThis.__nodePhase;const ok=phase==='passed';const found=ok||phase==='npmFailed'||phase==='timeout';const runtime={schema:1,component:'Node.js',requiredFamily:'24',status:ok?'passed':phase==='timeout'?'incomplete':phase==='npmFailed'?'unusable':'notFound',reason:ok?'verified':phase==='timeout'?'npmTimeout':phase==='npmFailed'?'npmFailed':'notDiscovered',version:found?'24.19.0':null,executable:found?'C:\\\\Node24\\\\node.exe':null,npmVersion:ok?'11.9.0':null,npmCli:ok?'C:\\\\Node24\\\\node_modules\\\\npm\\\\bin\\\\npm-cli.js':null,maintenanceEligibility:'notEvaluated'};return {code:ok?0:1,success:ok,validation_collected_at:Math.floor(Date.now()/1000),lines:['SKYVIEW_EVENT|runtime|Node.js|'+JSON.stringify(runtime),'SKYVIEW_EVENT|validation|'+(ok?'PASS':'FAIL')+'|Node.js: observed result; another Node.js version can remain installed','SKYVIEW_EVENT|summary|'+(ok?'0':'1')+'|Done'],log_path:'Browser simulation',platform:{label:'Windows 11',supported:true}};}
    export async function inspect(){return result();}
    export async function operate(mode){if(mode!=='validate'){globalThis.__nodeChanges++;throw new Error('No modifications allowed');}globalThis.__nodeChecks++;globalThis.__nodePhase=globalThis.__nodeChecks===1?'timeout':globalThis.__nodeChecks===2?'npmFailed':'passed';await new Promise(resolve=>setTimeout(resolve,120));return result();}
   `,
      });
    });
    await page.goto("/");
    const missing = page.getByRole("region", {
      name: "Node.js 24 wasn’t found by this check",
    });
    await expect(missing).toBeVisible();
    await expect(
      missing.getByText(/Other versions can stay installed/),
    ).toBeVisible();
    await expect(missing).not.toContainText("Restart");
    await missing
      .getByRole("button", { name: "Review Node.js/npm check" })
      .focus();
    await page.keyboard.press("Enter");
    await expect(
      page.getByRole("heading", { name: "Validation results", exact: true }),
    ).toBeVisible();
    expect(await page.evaluate(() => (window as any).__nodeChanges)).toBe(0);
    await page.getByRole("button", { name: "Overview", exact: true }).click();
    const check = page
      .locator('[aria-labelledby="node-readiness-heading"]')
      .getByRole("button", {
        name: "Check setup again",
        exact: true,
      });
    await expect(check).toBeEnabled();
    await check.click();
    await expect(
      page.getByText(/earlier Node.js\/npm result stays below/),
    ).toBeVisible();
    const timeout = page.getByRole("region", {
      name: "The npm check took too long",
    });
    await expect(timeout).toBeVisible();
    await expect(
      timeout.getByText(/does not mean either tool is missing/),
    ).toBeVisible();
    await expect(missing).toHaveCount(0);
    await page.addScriptTag({ content: axe.source });
    expect(
      await page.evaluate(
        async () =>
          (
            await (window as any).axe.run(
              document.querySelector(
                '[aria-labelledby="node-readiness-heading"]',
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
    const npmFailure = page.getByRole("region", {
      name: "Node.js 24 was found, but its npm check failed",
    });
    await expect(npmFailure).toBeVisible();
    await expect(
      npmFailure.getByText(
        /does not show that another installed Node.js version caused/,
      ),
    ).toBeVisible();
    await expect(timeout).toHaveCount(0);
    await expect(check).toBeEnabled();
    await check.click();
    await expect(
      page.locator('[aria-labelledby="node-readiness-heading"]'),
    ).toHaveCount(0);
    expect(await page.evaluate(() => (window as any).__nodeChecks)).toBe(3);
    expect(await page.evaluate(() => (window as any).__nodeChanges)).toBe(0);
  });
}
