import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "browser-tests",
  use: { baseURL: "http://127.0.0.1:1420", headless: true },
  projects: [
    { name: "chromium", use: { browserName: "chromium" } },
    {
      name: "webkit-sidebar",
      testMatch: ["sidebar.spec.ts", "self-update-setting.spec.ts"],
      use: { browserName: "webkit" },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:1420",
    reuseExistingServer: !process.env.CI,
  },
  reporter: "list",
});
