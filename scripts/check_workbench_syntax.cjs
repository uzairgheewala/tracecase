const fs = require("fs");
const path = require("path");
const childProcess = require("child_process");

let ts;
try {
  ts = require("typescript");
} catch (_) {
  const globalRoot = childProcess.execFileSync("npm", ["root", "-g"], { encoding: "utf8" }).trim();
  ts = require(path.join(globalRoot, "typescript"));
}

const root = path.resolve(__dirname, "..", "apps", "workbench", "src");
const files = [];
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const target = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(target);
    else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith(".d.ts")) files.push(target);
  }
}
walk(root);
let failed = false;
for (const file of files.sort()) {
  const source = fs.readFileSync(file, "utf8");
  const result = ts.transpileModule(source, {
    fileName: file,
    reportDiagnostics: true,
    compilerOptions: {
      target: ts.ScriptTarget.ES2022,
      module: ts.ModuleKind.ESNext,
      jsx: ts.JsxEmit.ReactJSX,
      strict: true,
    },
  });
  const errors = (result.diagnostics || []).filter((item) => item.category === ts.DiagnosticCategory.Error);
  if (errors.length) {
    failed = true;
    console.error(file);
    for (const error of errors) console.error(ts.flattenDiagnosticMessageText(error.messageText, "\n"));
  }
}
if (failed) process.exit(1);
console.log(`Workbench TypeScript syntax transpilation passed for ${files.length} files.`);
