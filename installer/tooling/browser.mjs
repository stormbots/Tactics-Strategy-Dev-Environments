import { checkBaseline } from "./baseline.mjs";
import { compileTests, root, browserOutput as output } from "./compile.mjs";
import { readFile, mkdir } from "node:fs/promises";
import { spawn } from "node:child_process";
import { join } from "node:path";
import assert from "node:assert/strict";
await checkBaseline();
await compileTests("browser");
const baseline = JSON.parse(
  await readFile(join(root, "testing/baseline.json"), "utf8"),
).browser;
const args = process.argv.slice(2);
const projectArg = args.find((a) => a.startsWith("--project="));
const selectors = args.filter((a) => !a.startsWith("--project="));
if (selectors.some((s) => s.startsWith("-")))
  throw new Error("Unsupported browser flag");
const cases = baseline.filter(
  (c) =>
    (!projectArg || c.project === projectArg.slice(10)) &&
    (!selectors.length || selectors.some((s) => c.file === s)),
);
if (!cases.length) throw new Error("No preserved browser cases selected");
const server = spawn(process.execPath, [join(root, "tooling/dev.mjs")], {
  cwd: root,
  stdio: ["ignore", "inherit", "inherit", "ipc"],
});
let serverFailure = null;
server.once("error", (e) => (serverFailure = e));
server.once(
  "exit",
  (code) => (serverFailure = new Error(`Development server exited: ${code}`)),
);
try {
  // Require readiness from our own child, never an unrelated server on port 1420.
  await new Promise((done, reject) => {
    const deadline = setTimeout(
      () => reject(new Error("Development server did not start")),
      30000,
    );
    server.once("error", (error) => {
      clearTimeout(deadline);
      reject(error);
    });
    server.once("exit", (code) => {
      clearTimeout(deadline);
      reject(new Error(`Development server exited before readiness: ${code}`));
    });
    server.once("message", (message) => {
      clearTimeout(deadline);
      if (message?.type !== "sde-development-ready")
        reject(new Error("Unexpected development-server readiness message"));
      else done();
    });
  });
  await mkdir(join(output, "browser-receipts"), { recursive: true });
  let count = 0;
  const files = [...new Set(cases.map((c) => `${c.project}|${c.file}`))];
  for (const key of files) {
    if (serverFailure) throw serverFailure;
    const [project, file] = key.split("|");
    const receipt = join(output, "browser-receipts", `${project}-${file}.json`);
    const status = await new Promise((done, reject) => {
      const child = spawn(
        process.execPath,
        [join(output, "browser-tests", file.replace(/\.ts$/, ".js"))],
        {
          cwd: root,
          stdio: "inherit",
          env: {
            ...process.env,
            SDE_BROWSER_PROJECT: project,
            SDE_BROWSER_RECEIPT: receipt,
          },
        },
      );
      const deadline = setTimeout(
        () => child.kill("SIGTERM"),
        30000 +
          cases.filter((c) => c.file === file && c.project === project).length *
            180000,
      );
      child.once("error", reject);
      child.once("exit", (code, signal) => {
        clearTimeout(deadline);
        done(signal ? 1 : code);
      });
    });
    if (status !== 0)
      throw new Error(`Browser file failed: ${key} (${status})`);
    const result = JSON.parse(await readFile(receipt, "utf8"));
    const expected = cases
      .filter((c) => c.file === file && c.project === project)
      .map((c) => c.title);
    assert.deepEqual(
      [...result.registered].sort(),
      expected.sort(),
      `Browser registration changed: ${key}`,
    );
    assert.deepEqual(
      [...result.completed].sort(),
      expected.sort(),
      `Browser completion changed: ${key}`,
    );
    count += result.completed.length;
  }
  if (serverFailure) throw serverFailure;
  console.log(
    `BROWSER_PARITY_OK (${count} cases, ${files.length} isolated files/projects)`,
  );
} finally {
  server.kill("SIGTERM");
}
