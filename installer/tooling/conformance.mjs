import { spawn } from "node:child_process";
import { writeFile, readFile } from "node:fs/promises";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import assert from "node:assert/strict";
import { root, output } from "./compile.mjs";
import { inspectDependencies } from "./dependencies.mjs";
export async function conformance() {
  await writeFile(
    join(output, "testing/mock-fixture.js"),
    'export function read(){return "actual";}',
  );
  await writeFile(
    join(output, "testing/spy-fixture.js"),
    'export function read(){return "actual";}',
  );
  async function run(file, receipt) {
    return await new Promise((done, reject) => {
      const child = spawn(
        process.execPath,
        [
          "--experimental-test-module-mocks",
          "--import",
          pathToFileURL(join(root, "testing/dom.mjs")).href,
          file,
        ],
        {
          cwd: root,
          env: { ...process.env, SDE_TEST_RECEIPT: receipt },
          stdio: ["ignore", "pipe", "pipe"],
        },
      );
      let text = "";
      child.stdout.on("data", (b) => (text += b));
      child.stderr.on("data", (b) => (text += b));
      const deadline = setTimeout(() => child.kill("SIGTERM"), 20000);
      child.on("error", reject);
      child.on("exit", (code, signal) => {
        clearTimeout(deadline);
        done({ code: signal ? 1 : code, text });
      });
    });
  }
  const receipt = join(output, "conformance.json");
  const positive = await run(
    join(root, "testing/runner.conformance.mjs"),
    receipt,
  );
  if (positive.code !== 0) {
    console.error(positive.text);
    throw new Error("Runner conformance failed");
  }
  const result = JSON.parse(await readFile(receipt, "utf8"));
  assert.equal(result.registered.length, 5);
  assert.deepEqual(result.registered, result.completed);
  const bundleFixture = join(output, "testing/bundle-fixture");
  await (
    await import("node:fs/promises")
  ).mkdir(bundleFixture, { recursive: true });
  await writeFile(
    join(bundleFixture, "bundle.js"),
    "// node_modules/picomatch/lib/parse.js\nexport const ordinary=true;",
  );
  await assert.rejects(
    () => inspectDependencies(bundleFixture),
    /Removed matcher signature/,
  );
  const cases = {
    equality: `it('negative',()=>expect('SDE_RECEIVED').toBe('SDE_EXPECTED'));`,
    negation: `it('negative',()=>expect('SDE_EXPECTED').not.toBe('SDE_EXPECTED'));`,
    promise: `it('negative',async()=>{await expect(Promise.resolve('SDE_RECEIVED')).resolves.toBe('SDE_EXPECTED');});`,
    unawaited: `it('negative',()=>{expect(Promise.resolve('SDE_RECEIVED')).resolves.toBe('SDE_EXPECTED');});`,
    calls: `it('negative',()=>expect(vi.fn()).toHaveBeenCalledTimes(99));`,
    absent: ``,
    unfinished: `it('negative',async()=>{await new Promise(()=>{});});`,
  };
  for (const [name, body] of Object.entries(cases)) {
    const path = join(output, "testing", `negative-${name}.mjs`),
      receipt = path + ".json";
    await writeFile(
      path,
      `import {it,vi,expect} from './unitApi.js';\n${body}\n`,
    );
    const failed = await run(path, receipt);
    assert.notEqual(failed.code, 0, `False green for ${name}`);
    const record = JSON.parse(await readFile(receipt, "utf8"));
    assert.equal(
      record.registered.length,
      name === "absent" ? 0 : 1,
      `Negative control did not register: ${name}`,
    );
    assert.equal(
      record.completed.length,
      ["absent", "unfinished"].includes(name) ? 0 : 1,
      `Negative control did not reach its assertion: ${name}`,
    );
    if (["equality", "negation", "promise", "unawaited"].includes(name))
      assert.match(failed.text, /SDE_EXPECTED/);
    if (name === "calls") assert.match(failed.text, /99/);
  }
  console.log(
    "RUNNER_CONFORMANCE_OK (5 positive cases, 7 required failure/cancellation controls; bundled-code control)",
  );
}
