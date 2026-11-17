import { build } from "esbuild";
import { readFile, writeFile, mkdir, rm, cp } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const target = join(root, "dist");
await rm(target, { recursive: true, force: true });
await mkdir(target, { recursive: true });
const result = await build({
  absWorkingDir: root,
  entryPoints: ["src/main.tsx"],
  outfile: join(target, "assets/app.js"),
  bundle: true,
  format: "esm",
  platform: "browser",
  target: "es2022",
  jsx: "automatic",
  minify: true,
  metafile: true,
  define: { "process.env.NODE_ENV": '"production"' },
});
let html = await readFile(join(root, "index.html"), "utf8");
if (!html.includes('src="/src/main.tsx"'))
  throw new Error("Review the frontend entry before building");
html = html
  .replace('src="/src/main.tsx"', 'src="./assets/app.js"')
  .replace(
    "</head>",
    '<link rel="stylesheet" href="./assets/app.css"/></head>',
  );
await writeFile(join(target, "index.html"), html);
await cp(join(root, "public"), target, { recursive: true });
if (
  Object.keys(result.metafile.inputs).some((name) =>
    /picomatch|tinyglobby|node_modules\/(?:vite|vitest|@vitest|@sinonjs)\/|\.test\.|testing\//.test(
      name,
    ),
  )
)
  throw new Error("Removed tooling found in production graph");
console.log(
  `FRONTEND_BUILD_OK (${Object.keys(result.metafile.inputs).length} inputs)`,
);
