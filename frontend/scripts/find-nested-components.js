const fs = require("fs");
const path = require("path");
const ts = require("typescript");

const ROOTS = [
  path.resolve(__dirname, "..", "src"),
];

function isPascalCase(name) {
  return /^[A-Z][a-zA-Z0-9]*$/.test(name);
}

function returnsJSX(body) {
  let hasJSX = false;
  function visit(node) {
    if (hasJSX) return;
    if (ts.isJsxElement(node) || ts.isJsxSelfClosingElement(node) || ts.isJsxFragment(node)) {
      hasJSX = true;
      return;
    }
    ts.forEachChild(node, visit);
  }
  visit(body);
  return hasJSX;
}

function isComponent(node) {
  if (ts.isFunctionDeclaration(node) && node.name && isPascalCase(node.name.text)) {
    return node.body && returnsJSX(node.body);
  }
  return false;
}

function isArrowConstComponent(decl) {
  if (!ts.isIdentifier(decl.name) || !isPascalCase(decl.name.text)) return false;
  const initializer = decl.initializer;
  if (!initializer || !(ts.isArrowFunction(initializer) || ts.isFunctionExpression(initializer))) {
    return false;
  }
  const body = initializer.body;
  if (!body) return false;
  if (ts.isBlock(body)) {
    return returnsJSX(body);
  }
  return ts.isJsxElement(body) || ts.isJsxSelfClosingElement(body) || ts.isJsxFragment(body);
}

function findNestedComponents(sourceFile) {
  const nested = [];
  function visit(node, insideComponent) {
    if (isComponent(node)) {
      if (insideComponent) {
        nested.push({
          name: node.name.text,
          line: sourceFile.getLineAndCharacterOfPosition(node.getStart()).line + 1,
          kind: "function",
        });
      }
      ts.forEachChild(node, (child) => visit(child, true));
    } else if (ts.isVariableStatement(node)) {
      for (const decl of node.declarationList.declarations) {
        if (isArrowConstComponent(decl)) {
          if (insideComponent) {
            nested.push({
              name: decl.name.text,
              line: sourceFile.getLineAndCharacterOfPosition(decl.getStart()).line + 1,
              kind: "arrow/const",
            });
          }
          if (decl.initializer) {
            visit(decl.initializer, true);
          }
        } else {
          visit(decl, insideComponent);
        }
      }
    } else {
      ts.forEachChild(node, (child) => visit(child, insideComponent));
    }
  }
  visit(sourceFile, false);
  return nested;
}

const EXCLUDED_PATTERNS = [
  /\.test\.tsx?$/,
  /\.spec\.tsx?$/,
  /\.stories\.tsx?$/,
];

function shouldExclude(file) {
  return EXCLUDED_PATTERNS.some(pattern => pattern.test(file));
}

function walk(dir, files = []) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(fullPath, files);
    } else if (entry.isFile() && (fullPath.endsWith(".ts") || fullPath.endsWith(".tsx")) && !fullPath.endsWith(".d.ts") && !shouldExclude(fullPath)) {
      files.push(fullPath);
    }
  }
  return files;
}

const PROJECT_ROOT = path.resolve(__dirname, "..");

const files = [];
for (const root of ROOTS) walk(root, files);
const results = [];
for (const file of files) {
  const source = fs.readFileSync(file, "utf8");
  const sourceFile = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true);
  const nested = findNestedComponents(sourceFile);
  if (nested.length > 0) {
    results.push({ file: path.relative(PROJECT_ROOT, file), nested });
  }
}

if (results.length === 0) {
  console.log("No nested React components found in frontend/src.");
  process.exit(0);
} else {
  let total = 0;
  for (const { file, nested } of results) {
    console.log(`\n${file}:`);
    for (const n of nested) {
      console.log(`  - ${n.name} (${n.kind}) at line ${n.line}`);
      total++;
    }
  }
  console.log(`\nTotal: ${total} nested components in ${results.length} files`);
  process.exit(1);
}
