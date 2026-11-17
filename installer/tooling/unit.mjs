import { checkDependencies } from "./dependencies.mjs";
import { conformance } from "./conformance.mjs";
import { checkBaseline } from "./baseline.mjs";
import { compileTests, root, output } from "./compile.mjs";
import { readFile, mkdir } from "node:fs/promises";
import { spawn } from "node:child_process";
import { join, basename } from "node:path";
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
await checkBaseline();
await checkDependencies();
await compileTests();
await conformance();
const baseline = JSON.parse(
  await readFile(join(root, "testing/baseline.json"), "utf8"),
).unit;
const selectors = process.argv.slice(2);
if (selectors.some((s) => s.startsWith("-")))
  throw new Error("Use source test filenames as selectors; no unchecked flags");
const files = Object.keys(baseline).filter(
  (file) =>
    !selectors.length ||
    selectors.some((s) => file.endsWith(s) || basename(file) === s),
);
if (!files.length) throw new Error("No registered test files selected");
await mkdir(join(output, "receipts"), { recursive: true });
let count = 0;
for (const file of files) {
  const receipt = join(output, "receipts", basename(file) + ".json");
  const compiled = join(output, file.replace(/\.tsx?$/, ".js"));
  const status = await new Promise((done, reject) => {
    const child = spawn(
      process.execPath,
      [
        "--experimental-test-module-mocks",
        "--import",
        pathToFileURL(join(root, "testing/dom.mjs")).href,
        compiled,
      ],
      {
        cwd: root,
        stdio: "inherit",
        env: { ...process.env, SDE_TEST_RECEIPT: receipt },
      },
    );
    const deadline = setTimeout(
      () => child.kill("SIGTERM"),
      20000 + baseline[file].length * 25000,
    );
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      clearTimeout(deadline);
      done(signal ? 1 : code);
    });
  });
  if (status !== 0) throw new Error(`Unit file failed: ${file} (${status})`);
  const result = JSON.parse(await readFile(receipt, "utf8"));
  assert.deepEqual(
    [...result.registered].sort(),
    [...baseline[file]].sort(),
    `Registration differs from preserved baseline: ${file}`,
  );
  assert.deepEqual(
    [...result.completed].sort(),
    [...baseline[file]].sort(),
    `Completion differs from preserved baseline: ${file}`,
  );
  count += result.completed.length;
}
console.log(`UNIT_PARITY_OK (${count} cases, ${files.length} isolated files)`);
