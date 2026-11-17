import { build } from "esbuild";
import { createServer } from "node:http";
import { readFile, readdir, stat } from "node:fs/promises";
import { dirname, resolve, join, basename } from "node:path";
import { fileURLToPath } from "node:url";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
// Stable module endpoints preserve existing browser test interception and the
// real same-window native queue identity. Production builds bundle normally.
const boundaries = new Set([
  "bridge",
  "recovery",
  "recoveryReports",
  "recoveryIncidents",
  "nativeReadQueue",
]);
const plugin = {
  name: "read-adapter-boundaries",
  setup(builder) {
    builder.onResolve({ filter: /^\.\.?\// }, (args) => {
      if (args.kind === "entry-point") return;
      const path = resolve(args.resolveDir, args.path).replace(
        /\.(ts|tsx|js)$/,
        "",
      );
      if (dirname(path) === join(root, "src") && boundaries.has(basename(path)))
        return { path: `/src/${basename(path)}.ts`, external: true };
    });
  },
};
let stamp = "",
  cache = new Map();
async function compiled(name) {
  const files = await readdir(join(root, "src"));
  const next = (
    await Promise.all(
      files.map(
        async (file) =>
          `${file}:${(await stat(join(root, "src", file))).mtimeMs}`,
      ),
    )
  ).join("|");
  if (next !== stamp) {
    stamp = next;
    cache.clear();
  }
  if (!cache.has(name))
    cache.set(
      name,
      build({
        absWorkingDir: root,
        entryPoints: [name === "main" ? "src/main.tsx" : `src/${name}.ts`],
        outfile: `.dev/${name}.js`,
        bundle: true,
        write: false,
        format: "esm",
        platform: "browser",
        target: "es2022",
        jsx: "automatic",
        plugins: [plugin],
        define: { "process.env.NODE_ENV": '"development"' },
      }),
    );
  return cache.get(name);
}
const server = createServer(async (req, res) => {
  try {
    const path = new URL(req.url, "http://localhost").pathname;
    if (path === "/") {
      let html = await readFile(join(root, "index.html"), "utf8");
      html = html
        .replace('src="/src/main.tsx"', 'src="/assets/main.js"')
        .replace(
          "</head>",
          '<link rel="stylesheet" href="/assets/main.css"/></head>',
        );
      res.writeHead(200, { "Content-Type": "text/html" });
      res.end(html);
      return;
    }
    if (path === "/assets/main.js" || path === "/assets/main.css") {
      const bundle = await compiled("main");
      const css = path.endsWith(".css");
      const file = bundle.outputFiles.find((file) =>
        file.path.endsWith(css ? ".css" : ".js"),
      );
      if (!file) throw new Error("Build output missing");
      res.writeHead(200, {
        "Content-Type": css ? "text/css" : "text/javascript",
      });
      res.end(file.contents);
      return;
    }
    const match =
      /^\/src\/(bridge|recovery|recoveryReports|recoveryIncidents|nativeReadQueue)\.ts$/.exec(
        path,
      );
    if (match) {
      const bundle = await compiled(match[1]);
      res.writeHead(200, { "Content-Type": "text/javascript" });
      res.end(
        bundle.outputFiles.find((file) => file.path.endsWith(".js")).contents,
      );
      return;
    }
    if (path === "/skyview-logo.png") {
      res.writeHead(200, { "Content-Type": "image/png" });
      res.end(await readFile(join(root, "public/skyview-logo.png")));
      return;
    }
    res.writeHead(404);
    res.end("Not found");
  } catch (error) {
    console.error(error);
    res.writeHead(500);
    res.end("Development build failed");
  }
});
server.on("error", (error) => {
  console.error(error);
  process.exitCode = 1;
});
server.listen(1420, "127.0.0.1", () => {
  console.log(
    "SDE development server: http://127.0.0.1:1420 (refresh after source changes)",
  );
  process.send?.({ type: "sde-development-ready" });
});
for (const signal of ["SIGINT", "SIGTERM"])
  process.on(signal, () => server.close(() => process.exit()));
