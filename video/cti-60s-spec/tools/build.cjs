// build.cjs - bundle the Remotion project without esbuild.
//
// Remotion's bundle() builds with webpack, but its module rules use an esbuild
// loader and esbuild starts a service process over pipes, which this host
// refuses (spawn EPERM). The override below swaps that loader for the in-process
// TypeScript transpiler, so bundling needs no child process at all.

const path = require("node:path");
const { bundle } = require("@remotion/bundler");

const root = path.resolve(__dirname, "..");

async function main() {
  const serveUrl = await bundle({
    entryPoint: path.join(root, "src", "index.ts"),
    outDir: path.join(root, "build"),
    publicDir: path.join(root, "public"),
    onProgress: (p) => { if (p % 20 < 1) console.log("bundling " + p + "%"); },
    webpackOverride: (config) => {
      const usesEsbuild = (rule) => {
        const uses = Array.isArray(rule.use) ? rule.use : rule.loader ? [rule] : [];
        return uses.some((u) => u && typeof u.loader === "string" && u.loader.includes("esbuild-loader"));
      };
      const rules = (config.module.rules || []).filter((rule) => !usesEsbuild(rule));
      rules.push({
        test: /\.[jt]sx?$/,
        exclude: /node_modules/,
        use: [{ loader: path.join(root, "tools", "tsx-loader.cjs") }],
      });
      config.module.rules = rules;
      return config;
    },
  });
  console.log("BUNDLE OK " + serveUrl);
}

main().catch((e) => { console.error("BUNDLE FAILED:", e && e.stack ? e.stack : e); process.exit(1); });