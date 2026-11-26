// tsx-loader.cjs - a webpack loader that transpiles TS/TSX in-process.
//
// Remotion's stock loader hands the work to esbuild, which starts a service
// process over pipes; this host refuses piped stdio for any child process, so
// that service cannot start. typescript.transpileModule runs in-process and is
// enough here: Remotion only needs the JSX/TS transform, not type checking
// (that is what `npm run typecheck` is for).

const ts = require("typescript");

module.exports = function tsxLoader(source, inputMap) {
  if (this.cacheable) this.cacheable();
  const fileName = this.resourcePath;
  const result = ts.transpileModule(source, {
    fileName,
    reportDiagnostics: false,
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      target: ts.ScriptTarget.ES2020,
      module: ts.ModuleKind.ESNext,
      moduleResolution: ts.ModuleResolutionKind.Bundler,
      esModuleInterop: true,
      allowSyntheticDefaultImports: true,
      isolatedModules: true,
      sourceMap: false,
      inlineSourceMap: false,
      importHelpers: false,
    },
  });
  this.callback(null, result.outputText, inputMap);
};