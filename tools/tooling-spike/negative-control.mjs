// Prove the prototype fails for a wrong App assertion rather than silently skipping cases.
import { readFile, writeFile, unlink } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";
const source = new URL("./app.test.mjs", import.meta.url);
const temporary = new URL(
  `./.negative-app-${process.pid}.mjs`,
  import.meta.url,
);
const original = await readFile(source, "utf8");
const target = "assert.equal(inspect.mock.callCount(), before + 1)";
assert.ok(original.includes(target));
await writeFile(
  temporary,
  original.replace(
    target,
    "assert.fail('SPIKE_INTENTIONAL_ASSERTION_FAILURE')",
  ),
);
try {
  const result = spawnSync(
    process.execPath,
    ["--experimental-test-module-mocks", fileURLToPath(temporary)],
    { encoding: "utf8", timeout: 20000 },
  );
  assert.equal(result.error, undefined);
  assert.notEqual(result.status, 0);
  assert.match(
    result.stdout + result.stderr,
    /SPIKE_INTENTIONAL_ASSERTION_FAILURE/,
  );
  console.log(
    `SPIKE_NEGATIVE_CONTROL_OK (intentional App assertion exited ${result.status})`,
  );
} finally {
  await unlink(temporary);
}
