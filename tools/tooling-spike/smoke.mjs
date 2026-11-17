// Load the esbuild production output under the repository's current Tauri CSP.
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve, extname, sep } from "node:path";
import assert from "node:assert/strict";
import { chromium } from "playwright-core";
const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, ".output/frontend");
const config = JSON.parse(
  await readFile(
    resolve(here, "../../installer/src-tauri/tauri.conf.json"),
    "utf8",
  ),
);
const errors = [];
const types = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".png": "image/png",
};
const server = createServer(async (request, response) => {
  try {
    const name = decodeURIComponent(
      new URL(request.url, "http://localhost").pathname,
    );
    const path = resolve(root, "." + (name === "/" ? "/index.html" : name));
    if (!path.startsWith(root + sep) || !(await stat(path)).isFile())
      throw new Error("Not found");
    response.writeHead(200, {
      "Content-Type": types[extname(path)] || "application/octet-stream",
      "Content-Security-Policy": config.app.security.csp,
    });
    response.end(await readFile(path));
  } catch {
    response.writeHead(404);
    response.end("Not found");
  }
});
await new Promise((done) => server.listen(0, "127.0.0.1", done));
let browser;
try {
  browser = await chromium.launch({
    executablePath: process.env.SDE_SPIKE_CHROMIUM || "/usr/bin/chromium",
    headless: true,
    args: ["--no-sandbox"],
  });
  for (const width of [390, 1140]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    page.setDefaultTimeout(10000);
    page.on("pageerror", (error) => errors.push(String(error)));
    page.on("console", (message) => {
      if (
        message.type() === "error" &&
        /Content Security Policy|Refused to/.test(message.text())
      )
        errors.push(message.text());
    });
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.getByRole("heading", { level: 1 }).waitFor();
    await page.getByRole("button", { name: /^Validation(?:\s|$)/ }).click();
    await page.getByRole("heading", { name: "Validation results" }).waitFor();
    await page.getByRole("table").waitFor();
    assert.equal(
      await page
        .locator(".brand img")
        .evaluate((img) => img.complete && img.naturalWidth > 0),
      true,
      "Logo asset must load",
    );
    assert.equal(
      await page
        .locator(".app-shell")
        .evaluate((element) => getComputedStyle(element).display),
      width === 390 ? "block" : "flex",
      "Production CSS must load",
    );
    await page.getByRole("button", { name: "About", exact: true }).click();
    await page
      .getByRole("heading", { name: "About Skyview Dev Setup" })
      .waitFor();
    await page.close();
  }
  assert.deepEqual(errors, [], "No runtime or CSP violations");
  console.log(
    "SPIKE_PRODUCTION_BROWSER_OK (390px, 1140px; real bundle, CSS, logo and Tauri CSP)",
  );
} finally {
  if (browser) await browser.close();
  await new Promise((done) => server.close(done));
}
