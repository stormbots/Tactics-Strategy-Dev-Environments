// Research only: compile the current production source without changing installer scripts.
import { build } from "esbuild";
import { readdir, readFile, writeFile, mkdir, rm, cp } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve, join } from "node:path";
const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "../..");
const source = join(root, "installer/src");
const output = join(here, ".output");
await rm(output, { recursive: true, force: true });
await mkdir(join(output, "source"), { recursive: true });
const files = (await readdir(source)).filter(
  (name) =>
    /\.tsx?$/.test(name) && !name.includes(".test.") && name !== "main.tsx",
);
await build({
  entryPoints: files.map((name) => join(source, name)),
  outdir: join(output, "source"),
  bundle: false,
  format: "esm",
  platform: "node",
  target: "node24",
  jsx: "automatic",
});
for (const name of await readdir(join(output, "source"))) {
  const path = join(output, "source", name);
  let text = await readFile(path, "utf8");
  // Node ESM requires explicit extensions; do not bundle away mock boundaries.
  text = text.replace(
    /(from\s+['"])(\.\.?\/[^'"]+)(['"])/g,
    (all, before, specifier, after) =>
      /\.[a-z]+$/i.test(specifier) ? all : `${before}${specifier}.js${after}`,
  );
  await writeFile(path, text);
}
const artifact = join(output, "frontend");
await mkdir(artifact, { recursive: true });
const result = await build({
  entryPoints: [join(source, "main.tsx")],
  outfile: join(artifact, "assets/app.js"),
  bundle: true,
  format: "esm",
  platform: "browser",
  target: "es2022",
  jsx: "automatic",
  minify: true,
  metafile: true,
  nodePaths: [join(here, "node_modules")],
  define: { "process.env.NODE_ENV": '"production"' },
});
let html = await readFile(join(root, "installer/index.html"), "utf8");
if (!html.includes('src="/src/main.tsx"'))
  throw new Error("Frontend entry changed; review this prototype");
html = html
  .replace('src="/src/main.tsx"', 'src="./assets/app.js"')
  .replace(
    "</head>",
    '<link rel="stylesheet" href="./assets/app.css"/></head>',
  );
await writeFile(join(artifact, "index.html"), html);
await cp(join(root, "installer/public"), artifact, { recursive: true });
await writeFile(
  join(output, "metafile.json"),
  JSON.stringify(result.metafile, null, 2),
);
if (
  Object.keys(result.metafile.inputs).some((name) =>
    /picomatch|tinyglobby|vitest|vite\//i.test(name),
  )
)
  throw new Error("Unexpected affected tooling in frontend graph");
console.log(
  `SPIKE_FRONTEND_BUILD_OK (${Object.keys(result.metafile.inputs).length} inputs)`,
);
