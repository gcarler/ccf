/* Auditoría de imports huérfanos hacia lib/cms.
 *
 * Para cada import nombrado (import { x } / import type { x }) cuyo módulo
 * apunte a src/lib/cms/*, verifica que `x` esté exportado por ese módulo.
 * Usa la API del compilador de TypeScript para resolver símbolos reales
 * (no regex), así que respeta re-exports, export type, etc.
 */
const ts = require("typescript");
const path = require("path");
const fs = require("fs");

const FRONTEND = path.resolve(__dirname, "..");
const SRC = path.join(FRONTEND, "src");

const rootNames = [];
function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === ".next") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full);
    else if (/\.(ts|tsx)$/.test(entry.name)) rootNames.push(full);
  }
}
walk(SRC); // todo src/ (módulos cms + todos sus consumidores)
walk(path.join(FRONTEND, "tests"));

const options = {
  target: ts.ScriptTarget.ES2020,
  module: ts.ModuleKind.ESNext,
  moduleResolution: ts.ModuleResolutionKind.Bundler,
  baseUrl: FRONTEND,
  paths: { "@/*": ["src/*"] },
  strict: true,
  skipLibCheck: true,
  allowJs: true,
  esModuleInterop: true,
  jsx: ts.JsxEmit.Preserve,
  noEmit: true,
  resolveJsonModule: true,
};

const program = ts.createProgram(rootNames, options);
const checker = program.getTypeChecker();

// Construye el mapa de símbolos exportados por cada módulo de lib/cms.
const cmsExports = new Map(); // ruta resuelta -> Set<nombres exportados>
function collectExports(sourceFile, modulePath) {
  if (cmsExports.has(modulePath)) return cmsExports.get(modulePath);
  const set = new Set();
  cmsExports.set(modulePath, set);
  const sf = program.getSourceFile(modulePath);
  if (!sf) return set;
  // El símbolo del módulo expone TODOS los exports reales (value + type,
  // re-exports, export type, export default, etc.) vía getExportsOfModule.
  const moduleSymbol = sf.symbol || checker.getSymbolAtLocation(sf);
  if (moduleSymbol) {
    const exports = checker.getExportsOfModule(moduleSymbol);
    exports.forEach((e) => set.add(e.name));
  }
  // Los re-exports via export { x } from "..." también aparecen en el
  // símbolo del módulo; para re-exports directos de otros módulos cms,
  // propagamos manualmente por si el checker no los resolvió (defensivo).
  for (const stmt of sf.statements) {
    if (ts.isExportDeclaration(stmt) && stmt.moduleSpecifier && ts.isStringLiteral(stmt.moduleSpecifier)) {
      const resolved = resolveToCms(stmt.moduleSpecifier.text, modulePath);
      if (resolved) {
        const inner = collectExports(sf, resolved);
        inner.forEach((n) => set.add(n));
      }
    }
  }
  return set;
}

function resolveToCms(spec, fromFile) {
  if (!spec.startsWith("@/lib/cms") && !spec.startsWith("../") && !spec.startsWith("./")) return null;
  let target;
  if (spec.startsWith("@/")) {
    target = path.join(SRC, spec.slice(2));
  } else {
    target = path.resolve(path.dirname(fromFile), spec);
  }
  const candidates = [
    target,
    target + ".ts",
    target + ".tsx",
    target + ".d.ts",
    path.join(target, "index.ts"),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) {
      const real = fs.realpathSync(c);
      if (real.startsWith(path.join(SRC, "lib/cms"))) return real;
    }
  }
  return null;
}

const problems = [];
const seen = new Set();

for (const rootName of rootNames) {
  const sf = program.getSourceFile(rootName);
  if (!sf) continue;
  for (const stmt of sf.statements) {
    if (!ts.isImportDeclaration(stmt)) continue;
    const spec = stmt.moduleSpecifier;
    if (!ts.isStringLiteral(spec)) continue;
    const modulePath = resolveToCms(spec.text, rootName);
    if (!modulePath) continue;
    const exports = collectExports(sf, modulePath);
    const clause = stmt.importClause;
    if (!clause) continue;
    const named = clause.namedBindings;
    if (named && ts.isNamedImports(named)) {
      for (const el of named.elements) {
        const importedName = el.propertyName ? el.propertyName.text : el.name.text;
        if (!exports.has(importedName)) {
          const key = `${rootName}::${spec.text}::${importedName}`;
          if (!seen.has(key)) {
            seen.add(key);
            problems.push({
              file: path.relative(FRONTEND, rootName),
              module: spec.text,
              imported: importedName,
            });
          }
        }
      }
    }
  }
}

if (problems.length === 0) {
  console.log("✅ 0 imports huérfanos hacia lib/cms (verificados con el compilador TS)");
} else {
  console.log(`⚠️  ${problems.length} imports huérfanos:\n`);
  for (const p of problems) {
    console.log(`  ${p.file}\n      import { ${p.imported} } from "${p.module}"  <- NO exportado`);
  }
  // process.exitCode (no process.exit): permite que stdout se flushee en CI
  // antes de salir, y el `|| fail` de run_ci.sh ve el exit 1.
  process.exitCode = 1;
}
