import { readdir, readFile } from "node:fs/promises";
import { join, extname } from "node:path";
import { root } from "./compile.mjs";
// npm audit cannot see a matcher copied into a distributed bundle. Keep the
// known removed code signatures out of this installed development tree too.
export async function inspectDependencies(
  directory = join(root, "node_modules"),
) {
  let inspected = 0;
  async function walk(path) {
    for (const entry of await readdir(path, { withFileTypes: true })) {
      const file = join(path, entry.name);
      if (entry.isDirectory()) await walk(file);
      else if (
        entry.isFile() &&
        [".js", ".mjs", ".cjs"].includes(extname(entry.name))
      ) {
        const source = await readFile(file, "utf8");
        inspected++;
        if (
          source.includes("picomatch") ||
          source.includes("analyzeRepeatedExtglob")
        )
          throw new Error(
            `Removed matcher signature found in installed code: ${file}`,
          );
      }
    }
  }
  await walk(directory);
  return inspected;
}
export async function checkDependencies() {
  const lock = JSON.parse(
    await readFile(join(root, "package-lock.json"), "utf8"),
  );
  if (
    Object.keys(lock.packages).some((name) =>
      /(?:^|\/)node_modules\/(picomatch|tinyglobby|vite|vitest|playwright|prettier)$/.test(
        name,
      ),
    )
  )
    throw new Error(
      "Removed build/test bundle returned to the lockfile; review dependency remediation",
    );
  console.log(
    `DEPENDENCY_DISTRIBUTION_OK (${await inspectDependencies()} JavaScript files; full npm audit remains separate)`,
  );
}
