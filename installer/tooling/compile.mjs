import { build } from "esbuild";
import ts from "typescript";
import {
  readdir,
  readFile,
  writeFile,
  mkdir,
  rm,
  copyFile,
} from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";
export const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
export const output = join(root, ".test-output/unit");
export const browserOutput = join(root, ".test-output/browser");
const extension = (value) =>
  value.startsWith(".") && !/\.[a-z]+$/.test(value) ? value + ".js" : value;
export async function compileTests(kind = "unit") {
  const target = kind === "browser" ? browserOutput : output;
  await rm(target, { recursive: true, force: true });
  await mkdir(target, { recursive: true });
  const source = (await readdir(join(root, "src")))
    .filter((name) => /\.tsx?$/.test(name) && name !== "main.tsx")
    .map((name) => "src/" + name);
  const testing = (await readdir(join(root, "testing")))
    .filter((name) => name.endsWith(".ts"))
    .map((name) => "testing/" + name);
  const browser = (await readdir(join(root, "browser-tests")))
    .filter((name) => name.endsWith(".ts"))
    .map((name) => "browser-tests/" + name);
  await build({
    absWorkingDir: root,
    entryPoints: [...source, ...testing, ...browser],
    outdir: target,
    outbase: ".",
    bundle: false,
    format: "esm",
    platform: "node",
    target: "node24",
    jsx: "automatic",
  });
  await copyFile(join(root, "package.json"), join(target, "package.json"));
  for (const directory of ["src", "testing", "browser-tests"]) {
    for (const file of await readdir(join(target, directory))) {
      const path = join(target, directory, file);
      let text = await readFile(path, "utf8");
      const tree = ts.createSourceFile(
        path,
        text,
        ts.ScriptTarget.Latest,
        true,
        ts.ScriptKind.JS,
      );
      const api = [],
        imports = [],
        mocks = [],
        rest = [],
        namespaces = [];
      for (const statement of tree.statements) {
        if (ts.isImportDeclaration(statement)) {
          const specifier = extension(statement.moduleSpecifier.text);
          const clause = statement.importClause;
          if (!clause) {
            imports.push(`await import(${JSON.stringify(specifier)});`);
            continue;
          }
          if (specifier.endsWith("unitApi.js")) {
            api.push(
              statement
                .getText(tree)
                .replace(
                  statement.moduleSpecifier.getText(tree),
                  JSON.stringify(specifier),
                ),
            );
            continue;
          }
          if (specifier.endsWith(".json")) {
            const bindings = clause.namedBindings?.elements
              .map(
                (e) => `${e.propertyName?.text ?? e.name.text}: ${e.name.text}`,
              )
              .join(", ");
            imports.push(
              `const __json = (await import(${JSON.stringify(specifier)}, {with:{type:'json'}})).default; const {${bindings}}=__json;`,
            );
            continue;
          }
          const names = [];
          if (clause.name) names.push(`default: ${clause.name.text}`);
          if (
            clause.namedBindings &&
            ts.isNamespaceImport(clause.namedBindings)
          ) {
            imports.push(
              `const ${clause.namedBindings.name.text}=await import(${JSON.stringify(specifier)});`,
            );
            if (file.endsWith(".test.js")) namespaces.push(specifier);
          } else {
            if (clause.namedBindings)
              names.push(
                ...clause.namedBindings.elements.map(
                  (e) =>
                    `${e.propertyName?.text ?? e.name.text}: ${e.name.text}`,
                ),
              );
            imports.push(
              `const {${names.join(",")}}=await import(${JSON.stringify(specifier)});`,
            );
          }
        } else if (
          file.endsWith(".test.js") &&
          ts.isExpressionStatement(statement) &&
          ts.isCallExpression(statement.expression) &&
          statement.expression.expression.getText(tree) === "vi.mock"
        ) {
          mocks.push(`await ${statement.getText(tree)}`);
        } else rest.push(statement.getText(tree));
      }
      if (file.endsWith(".test.js")) {
        text = `import { configureTest as __configure, namespaceFacade as __namespace } from '../testing/unitApi.js';\n${api.join("\n")}\n__configure(import.meta.url);\n${mocks.join("\n")}\n${namespaces.map((s) => `await __namespace(${JSON.stringify(s)});`).join("\n")}\n${imports.join("\n")}\n${rest.join("\n")}`;
      } else {
        // Preserve normal static ESM linkage outside test modules, including browser source mocks.
        text = text.replace(
          /(from\s+['"])(\.\.?\/[^'"]+)(['"])/g,
          (all, a, s, b) => `${a}${extension(s)}${b}`,
        );
        text = text.replace(
          /import\s*\{\s*version\s*\}\s*from\s*(['"])\.\.\/package\.json\1;/g,
          `import __package from '../package.json' with {type:'json'}; const {version}=__package;`,
        );
      }
      await writeFile(path, text);
    }
  }
}
