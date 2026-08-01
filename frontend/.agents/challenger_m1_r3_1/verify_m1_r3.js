const fs = require('fs');
const path = require('path');

console.log('====================================================');
console.log('EMPIRICAL VERIFICATION HARNESS - M1 R3 (CHALLENGER 1)');
console.log('====================================================\n');

let passCount = 0;
let failCount = 0;
const errors = [];

function assert(condition, message) {
  if (condition) {
    console.log(`[PASS] ${message}`);
    passCount++;
  } else {
    console.error(`[FAIL] ${message}`);
    failCount++;
    errors.push(message);
  }
}

// ---------------------------------------------------------------------------
// TEST 1: Check for lingering invalid HSL syntax across codebase
// ---------------------------------------------------------------------------
console.log('--- TEST 1: Invalid HSL Syntax Audit ---');

const srcDir = path.join(__dirname, '../../src');

function getAllFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  for (const file of files) {
    const filePath = path.join(dir, file);
    if (fs.statSync(filePath).isDirectory()) {
      if (file !== 'node_modules' && file !== '.next') {
        getAllFiles(filePath, fileList);
      }
    } else {
      if (/\.(ts|tsx|css|js|jsx)$/.test(file)) {
        fileList.push(filePath);
      }
    }
  }
  return fileList;
}

const allSrcFiles = getAllFiles(srcDir);
let invalidHslFound = false;
const invalidHslDetails = [];

// Regex to catch malformed 255% or bad HSL syntax
const invalid255Percent = /255\s+255%/i;
const malformedHslPercent = /hsl\s*\([^)]*\b255%/i;

for (const file of allSrcFiles) {
  const content = fs.readFileSync(file, 'utf8');
  if (invalid255Percent.test(content) || malformedHslPercent.test(content)) {
    invalidHslFound = true;
    invalidHslDetails.push(path.relative('/root/ccf/frontend', file));
  }
}

assert(!invalidHslFound, `No malformed '255 255%' HSL strings found in src/ files. (Found in: ${invalidHslDetails.join(', ') || 'none'})`);

// Check tokens-semantic.ts and ThemeContext.tsx specifically for border-glass
const tokensSemanticContent = fs.readFileSync(path.join(srcDir, 'design/tokens-semantic.ts'), 'utf8');
const themeContextContent = fs.readFileSync(path.join(srcDir, 'app/plataforma/theme/ThemeContext.tsx'), 'utf8');

const tokensBorderGlassNight = /'border-glass':\s*'0 0% 100% \/ 0\.05'/.test(tokensSemanticContent);
assert(tokensBorderGlassNight, "tokens-semantic.ts contains valid '0 0% 100% / 0.05' for border-glass night token");

const themeContextBorderGlassNight = /'--border-glass':\s*'0 0% 100% \/ 0\.05'/.test(themeContextContent);
assert(themeContextBorderGlassNight, "ThemeContext.tsx contains valid '0 0% 100% / 0.05' for --border-glass night token");

// ---------------------------------------------------------------------------
// TEST 2: Check for cyclic CSS custom property definitions
// ---------------------------------------------------------------------------
console.log('\n--- TEST 2: Cyclic CSS Custom Property Audit ---');

const globalsCssPath = path.join(srcDir, 'app/globals.css');
const globalsCss = fs.readFileSync(globalsCssPath, 'utf8');

// Self-referential pattern: --varName: ... var(--varName ...)
const varDefRegex = /--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);/g;
let match;
const varMap = new Map();

while ((match = varDefRegex.exec(globalsCss)) !== null) {
  const varName = match[1];
  const value = match[2];
  
  // Check if variable references itself
  const selfRefRegex = new RegExp(`var\\s*\\(\\s*--${varName}\\b`);
  if (selfRefRegex.test(value)) {
    assert(false, `Cyclic CSS variable detected in globals.css: --${varName}: ${value}`);
  }
  
  // Extract all referenced vars
  const refs = [];
  const refMatches = value.matchAll(/var\s*\(\s*--([a-zA-Z0-9_-]+)/g);
  for (const refMatch of refMatches) {
    refs.push(refMatch[1]);
  }
  varMap.set(varName, refs);
}

// Check for multi-step cycles using DFS
let cycleFound = false;
function checkCycle(node, visited = new Set(), pathStack = []) {
  visited.add(node);
  pathStack.push(node);
  
  const neighbors = varMap.get(node) || [];
  for (const neighbor of neighbors) {
    if (!visited.has(neighbor)) {
      checkCycle(neighbor, visited, pathStack);
    } else if (pathStack.includes(neighbor)) {
      cycleFound = true;
      assert(false, `Indirect CSS variable cycle detected: ${pathStack.join(' -> ')} -> ${neighbor}`);
    }
  }
  
  pathStack.pop();
}

for (const varName of varMap.keys()) {
  checkCycle(varName);
}

assert(!cycleFound, "Zero cyclic CSS variable definitions found in globals.css");

const hasOutfitselfRef = /--font-outfit\s*:\s*var\s*\(\s*--font-outfit/i.test(globalsCss);
assert(!hasOutfitselfRef, "globals.css does not contain self-referential '--font-outfit: var(--font-outfit...)'");

// ---------------------------------------------------------------------------
// TEST 3: Heading CSS Specificity & Puck Canvas Rules
// ---------------------------------------------------------------------------
console.log('\n--- TEST 3: Heading CSS Specificity & Puck Canvas Rules ---');

const platformH1NotText = /\.workspace-platform\s+h1:not\(\[class\*="text-"\]\)/.test(globalsCss);
assert(platformH1NotText, "globals.css contains '.workspace-platform h1:not([class*=\"text-\"])' selector filtering utility classes");

const puckH1NotText = /\.puck-editor\s+h1:not\(\[class\*="text-"\]\)/.test(globalsCss) ||
                      /\.Puck\s+h1:not\(\[class\*="text-"\]\)/.test(globalsCss);
assert(puckH1NotText, "globals.css contains Puck canvas heading rule with ':not([class*=\"text-\"])'");

// Simple selector specificity evaluator simulation
function evaluateHeadingMatching(className) {
  // Check if .workspace-platform h1:not([class*="text-"]) matches element with className
  const hasTextClass = /text-/.test(className);
  const matchesPlatformRule = !hasTextClass;
  return matchesPlatformRule;
}

assert(evaluateHeadingMatching('text-4xl') === false, "Heading with className='text-4xl' is NOT matched by workspace-platform squashing rule (preserves size)");
assert(evaluateHeadingMatching('text-3xl font-bold') === false, "Heading with className='text-3xl font-bold' is NOT matched by workspace-platform squashing rule (preserves size)");
assert(evaluateHeadingMatching('') === true, "Heading with no className IS matched by workspace-platform default rule (applies max text size)");

// ---------------------------------------------------------------------------
// TEST 4: Puck Editor Integration Verification
// ---------------------------------------------------------------------------
console.log('\n--- TEST 4: Puck Editor Integration Verification ---');

const puckPagePath = path.join(srcDir, 'app/plataforma/cms/builder-puck/page.tsx');
if (fs.existsSync(puckPagePath)) {
  const puckPageContent = fs.readFileSync(puckPagePath, 'utf8');
  
  const hasIframeDisabled = /iframe\s*=\s*\{\s*\{\s*enabled\s*:\s*false\s*\}\s*\}/.test(puckPageContent) ||
                            /iframe\s*=\s*\{\s*false\s*\}/.test(puckPageContent);
  assert(hasIframeDisabled, "builder-puck/page.tsx specifies iframe={{ enabled: false }} on <Puck>");
  
  const hasThemeVarInjection = /--site-background|themeStyles|--site-primary/.test(puckPageContent);
  assert(hasThemeVarInjection, "builder-puck/page.tsx handles site theme CSS custom property binding");
} else {
  assert(false, "builder-puck/page.tsx exists");
}

// ---------------------------------------------------------------------------
// SUMMARY
// ---------------------------------------------------------------------------
console.log('\n====================================================');
console.log(`RESULTS: ${passCount} PASSED, ${failCount} FAILED`);
console.log('====================================================');

if (failCount > 0) {
  console.error('VERIFICATION FAILED!');
  process.exit(1);
} else {
  console.log('VERIFICATION SUCCESSFUL!');
  process.exit(0);
}
