import { test, expect } from "@playwright/test";
import axe from "axe-core";
import { chooseTheme, closeAppearance } from "./appearance-helpers";
import { disclosure } from "./guided-helpers";

const scenarios = [
  ["checking", "Checking your setup…", "Finding your next step"],
  ["unavailable", "Check not finished", "Try checking again"],
  ["ready", "Ready!", "Start building"],
  ["updates", "Ready!", "Install updates"],
  ["setup", "Setup needed", "Set up this computer"],
  ["repair", "Setup needs a fix", "Fix your setup"],
  ["attention", "Setup needs attention", "Follow the recommended fix"],
  ["incomplete", "Check not finished", "Try checking again"],
  ["active", "Changes are paused", "Let setup finish"],
  ["unknown", "Changes are paused", "Check whether setup has finished"],
  [
    "untrusted",
    "Safety check unavailable",
    "SDE couldn’t verify that changes are safe",
  ],
  ["incident", "Review an interruption", "Review what happened"],
  [
    "native-incomplete",
    "Changes are paused",
    "An installation needs attention",
  ],
] as const;
for (const theme of ["Light", "Dark"])
  for (const width of [390, 1140]) {
    test(`${theme} guided states at ${width}px use one action and preserve diagnostic routes`, async ({
      page,
    }) => {
      test.setTimeout(90000);
      await page.setViewportSize({ width, height: 900 });
      for (const [state, headline, heading] of scenarios) {
        await page.unrouteAll();
        const fail =
          state === "setup"
            ? "Git not found"
            : state === "repair"
              ? "Python 3.14 could not create a venv with pip"
              : state === "attention"
                ? "Unrecognized fixture finding"
                : null;
        const report = {
          validation_collected_at: 1793990000,
          code: fail || state === "incomplete" ? 1 : 0,
          success: !fail && state !== "incomplete",
          lines: [
            `SKYVIEW_EVENT|validation|${fail ? "FAIL" : "PASS"}|${fail ?? "Git: 2.49"}`,
            ...(state === "incomplete"
              ? []
              : [`SKYVIEW_EVENT|summary|${fail ? 1 : 0}|Complete fixture`]),
            ...(state === "updates"
              ? [
                  `SKYVIEW_EVENT|tool|Git|${JSON.stringify({ tool: "Git", installedVersion: "2.49", availableVersion: "2.50", updateAvailable: true, updateCheck: "current" })}`,
                ]
              : []),
          ],
          log_path: "Synthetic browser fixture",
          platform: {
            supported: true,
            label: "Fixture — no native operations",
          },
        };
        await page.route("**/src/bridge.ts*", async (route) => {
          if (
            new URL(route.request().url()).searchParams.has("guidedBaseline")
          ) {
            await route.continue();
            return;
          }
          await route.fulfill({
            contentType: "application/javascript",
            body: `export * from '/src/bridge.ts?guidedBaseline'; export async function inspect(){${state === "checking" ? "return new Promise(()=>{})" : state === "unavailable" ? "throw new Error('Synthetic collection failure')" : `return ${JSON.stringify(report)}`}}`,
          });
        });
        await page.route("**/src/recovery.ts*", async (route) => {
          if (
            new URL(route.request().url()).searchParams.has("guidedBaseline")
          ) {
            await route.continue();
            return;
          }
          await route.fulfill({
            contentType: "application/javascript",
            body: `
          export * from '/src/recovery.ts?guidedBaseline';
          import {previewRecovery} from '/src/recovery.ts?guidedBaseline';
          export async function inspectRecovery(){
            const s=previewRecovery();const state=${JSON.stringify(state)};
            if(['active','unknown','untrusted','incident','native-incomplete'].includes(state)){
              s.readiness=state==='incident'?'needs_acknowledgment':'blocked';
              s.decision=state==='native-incomplete'?'block_incomplete':state==='incident'?'needs_acknowledgment':'block_'+state;
              if(state==='active'||state==='unknown')s.effectiveActivity=state;
              if(state==='untrusted')s.nativeSafety.trust='untrusted';
              if(state==='native-incomplete')s.nativeSafety.packageHealth='incomplete';
              s.guidance={code:'fixture',title:'Synthetic safety finding',steps:['Read-only fixture. Review current observations before making changes.']};
            } return s;
          }`,
          });
        });
        await page.goto("/");
        await expect(
          page
            .getByRole("region", { name: "Workstation status" })
            .getByRole("heading", { name: headline, exact: true }),
        ).toBeVisible();
        await expect(
          page.getByRole("heading", { name: heading, exact: true }),
        ).toBeVisible();
        await chooseTheme(page, theme);
        await closeAppearance(page);
        await expect(page.locator(".guided-task button.primary")).toHaveCount(
          state === "checking" ? 0 : 1,
        );
        await expect(
          page.getByRole("group", { name: "Choose an operation" }),
        ).toHaveCount(0);
        await expect(
          page.getByText("Development tools", { exact: true }),
        ).toBeVisible();
        if (state === "updates") {
          await expect(
            page.getByRole("button", { name: "Review updates", exact: true }),
          ).toHaveCount(1);
          await expect(
            page.getByRole("button", { name: "Open VSCodium", exact: true }),
          ).toBeHidden();
        }
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
          path: `test-results/guided-${state}-${theme}-${width}.png`,
          fullPage: true,
        });
        await disclosure(page, "Details");
        await expect(
          page.getByRole("button", {
            name: "Create support report",
            exact: true,
          }),
        ).toBeVisible();
        await expect(
          page.getByRole("button", { name: "View schedule", exact: true }),
        ).toBeVisible();
      }
    });
  }
