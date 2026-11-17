import ts from "typescript";
import { createHash } from "node:crypto";
import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import assert from "node:assert/strict";
import { root } from "./compile.mjs";
export async function checkBaseline() {
  const data = JSON.parse(
    await readFile(join(root, "testing/baseline.json"), "utf8"),
  );
  const printer = ts.createPrinter({
    removeComments: true,
    newLine: ts.NewLineKind.LineFeed,
  });
  for (const [file, expected] of Object.entries(data.assertions)) {
    const source = await readFile(join(root, file), "utf8");
    const tree = ts.createSourceFile(
      file,
      source,
      ts.ScriptTarget.Latest,
      true,
      file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
    );
    const calls = [];
    function visit(node) {
      if (
        ts.isCallExpression(node) &&
        /^expect\s*[.(]/.test(node.getText(tree))
      )
        calls.push(printer.printNode(ts.EmitHint.Expression, node, tree));
      ts.forEachChild(node, visit);
    }
    visit(tree);
    assert.equal(
      calls.length,
      expected.count,
      `Original assertion count changed: ${file}`,
    );
    assert.equal(
      createHash("sha256").update(JSON.stringify(calls)).digest("hex"),
      expected.sha256,
      `Original assertion source changed: ${file}`,
    );
  }
  const sourceTests = (await readdir(join(root, "src")))
    .filter((f) => /\.test\.tsx?$/.test(f))
    .map((f) => "src/" + f)
    .sort();
  assert.deepEqual(
    sourceTests,
    Object.keys(data.unit).sort(),
    "Every unit file must be registered",
  );
  const browserTests = (await readdir(join(root, "browser-tests")))
    .filter((f) => f.endsWith(".spec.ts"))
    .sort();
  assert.deepEqual(
    browserTests,
    [...new Set(data.browser.map((c) => c.file))].sort(),
    "Every browser file must be registered",
  );
  return data;
}
