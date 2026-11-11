import { test, expect } from "@playwright/test";
import axe from "axe-core";
import { chooseTheme, chooseZoom, closeAppearance } from "./appearance-helpers";
import { disclosure } from "./guided-helpers";

test.use({ actionTimeout: 10000 });

// WF15–WF17/WF20–WF22/WF28/WF30, production App with synthetic observations.
// Browser evidence only: no native operation or OS approval is simulated as real.
const blockers = [
  ["active", "Let setup finish"],
  ["unknown", "Check whether setup has finished"],
  ["untrusted", "SDE couldn’t verify that changes are safe"],
  ["incident", "Review what happened"],
  ["native-incomplete", "An installation needs attention"],
] as const;
for (const theme of ["Light", "Dark"])
  for (const width of [390, 1140])
    test(`${theme} combined safety findings at ${width}px retain diagnostics at every zoom`, async ({
      page,
    }) => {
      test.setTimeout(180000);
      await page.setViewportSize({ width, height: 900 });
      for (const [state, heading] of blockers) {
        await page.unrouteAll();
        await page.route("**/src/bridge.ts*", async (route) => {
          if (
            new URL(route.request().url()).searchParams.has("combinedBaseline")
          ) {
            await route.continue();
            return;
          }
          await route.fulfill({
            contentType: "application/javascript",
            body: `
            export * from '/src/bridge.ts?combinedBaseline';
            window.combinedMutations=[];
            export async function inspect(){return {
              code:1,success:false,validation_collected_at:1793990000,
              platform:{supported:true,label:'Synthetic combined fixture'},
              log_path:'Synthetic fixture — no native execution',
              lines:['SKYVIEW_EVENT|validation|FAIL|Git not found',
                'SKYVIEW_EVENT|validation|PASS|Python: 3.14',
                'SKYVIEW_EVENT|summary|1|Complete fixture',
                'SKYVIEW_EVENT|tool|Python|'+JSON.stringify({tool:'Python',installedVersion:'3.14',availableVersion:'3.15',updateAvailable:true,updateCheck:'current'})]
            };}
            export async function operate(...args){window.combinedMutations.push(args);throw new Error('Unexpected operation in read-only test');}
          `,
          });
        });
        await page.route("**/src/recovery.ts*", async (route) => {
          if (
            new URL(route.request().url()).searchParams.has("combinedBaseline")
          ) {
            await route.continue();
            return;
          }
          await route.fulfill({
            contentType: "application/javascript",
            body: `
            export * from '/src/recovery.ts?combinedBaseline';
            import {previewRecovery} from '/src/recovery.ts?combinedBaseline';
            export async function inspectRecovery(){
              const s=previewRecovery(), state=${JSON.stringify(state)};
              s.readiness=state==='incident'?'needs_acknowledgment':'blocked';
              s.decision=state==='native-incomplete'?'block_incomplete':state==='incident'?'needs_acknowledgment':'block_'+state;
              if(state==='active'||state==='unknown')s.effectiveActivity=state;
              if(state==='untrusted')s.nativeSafety.trust='untrusted';
              if(state==='native-incomplete')s.nativeSafety.packageHealth='incomplete';
              s.guidance={code:'combined-fixture',title:'Synthetic safety blocker',steps:['Retain the other findings. No change is authorized.']};
              return s;
            }
          `,
          });
        });
        await page.goto("/");
        await expect(
          page.getByRole("heading", { name: heading, exact: true }),
        ).toBeVisible();
        await chooseTheme(page, theme);
        for (const position of [0, 1, 2, 3, 4]) {
          await chooseZoom(page, position);
          await closeAppearance(page);
          await expect(page.locator(".guided-task button.primary")).toHaveCount(
            1,
          );
          await expect(
            page.getByRole("heading", { name: "Ready!", exact: true }),
          ).toHaveCount(0);
          await disclosure(page, "Other actions");
          for (const name of [
            "Install development tools",
            "Repair setup",
            "Review tool updates",
          ])
            await expect(
              page.getByRole("button", { name, exact: true }),
            ).toHaveCount(0);
          await page.addScriptTag({ content: axe.source });
          expect(
            await page.evaluate(
              async () => (await (window as any).axe.run(document)).violations,
            ),
          ).toEqual([]);
          const layout = await page.evaluate(() => ({
            overflow: document.documentElement.scrollWidth > innerWidth + 1,
            wide: [...document.querySelectorAll("main *")]
              .filter((el) => el.getBoundingClientRect().right > innerWidth + 1)
              .map((el) => ({
                tag: el.tagName,
                class: el.className,
                text: el.textContent?.slice(0, 60),
              })),
          }));
          expect(
            layout.overflow,
            JSON.stringify({ state, position, ...layout }),
          ).toBe(false);
        }
        if (["active", "unknown", "untrusted"].includes(state)) {
          await page.locator(".guided-task button.primary").click();
          await expect(
            page.getByRole("heading", { name: heading, exact: true }),
          ).toBeVisible();
        }
        await disclosure(page, "Details");
        await expect(
          page.getByRole("button", {
            name: "Create support report",
            exact: true,
          }),
        ).toBeVisible();
        await page.getByRole("button", { name: /^Validation/ }).click();
        await expect(
          page.getByText("Git could not be found", { exact: true }),
        ).toBeVisible();
        await page
          .getByRole("button", { name: "Overview", exact: true })
          .click();
        await expect(
          page.getByRole("heading", { name: heading, exact: true }),
        ).toBeVisible();
        expect(
          await page.evaluate(() => (window as any).combinedMutations),
        ).toEqual([]);
        await page.screenshot({
          path: `test-results/combined-${state}-${theme}-${width}-150.png`,
          fullPage: true,
        });
      }
    });
