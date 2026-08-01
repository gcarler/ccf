const fs = require('fs');
const path = require('path');

console.log('=== EMPIRICAL STRESS & CHALLENGE HARNESS v2 (M1 R3 Challenger 2) ===\n');

let totalFailures = 0;

function reportResult(testName, passed, details = '') {
  if (passed) {
    console.log(`[PASS] ${testName}`);
  } else {
    console.log(`[FAIL] ${testName}`);
    if (details) console.log(`       ${details}`);
    totalFailures++;
  }
}

const srcDir = path.resolve(__dirname, '../../src');

function getAllFiles(dir, exts = ['.ts', '.tsx', '.css', '.js', '.jsx']) {
  let results = [];
  if (!fs.existsSync(dir)) return results;
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat && stat.isDirectory()) {
      results = results.concat(getAllFiles(filePath, exts));
    } else {
      if (exts.includes(path.extname(filePath))) {
        results.push(filePath);
      }
    }
  });
  return results;
}

const sourceFiles = getAllFiles(srcDir);

// ---------------------------------------------------------------------------
// TEST 1: Exhaustive Check for Malformed HSL Strings (255 255% 255% / etc.)
// ---------------------------------------------------------------------------
console.log('--- TEST 1: Malformed HSL String Audit ---');

let invalidHslMatches = [];
// Target malformed HSL patterns like "255 255%" or "255 255% 255%"
const malformedHslPattern = /255\s+255%/g;

sourceFiles.forEach(file => {
  const content = fs.readFileSync(file, 'utf8');
  if (malformedHslPattern.test(content)) {
    invalidHslMatches.push(file);
  }
});

// Also explicitly check tokens-semantic.ts and ThemeContext.tsx for border-glass values
const tokensSemanticPath = path.resolve(srcDir, 'design/tokens-semantic.ts');
const themeContextPath = path.resolve(srcDir, 'app/plataforma/theme/ThemeContext.tsx');
const globalsCssPath = path.resolve(srcDir, 'app/globals.css');

const tokensContent = fs.readFileSync(tokensSemanticPath, 'utf8');
const themeContextContent = fs.readFileSync(themeContextPath, 'utf8');
const globalsContent = fs.readFileSync(globalsCssPath, 'utf8');

const isBorderGlassFixedInTokens = !tokensContent.includes('255 255%');
const isBorderGlassFixedInTheme = !themeContextContent.includes('255 255%');
const isBorderGlassFixedInGlobals = !globalsContent.includes('255 255%');

reportResult(
  'Zero occurrences of "255 255%" across all src/ files',
  invalidHslMatches.length === 0,
  invalidHslMatches.join('\n')
);

reportResult(
  'border-glass token in tokens-semantic.ts uses valid HSL (0 0% 100% / ...)',
  isBorderGlassFixedInTokens,
  'tokens-semantic.ts still contains 255 255%'
);

reportResult(
  'border-glass token in ThemeContext.tsx uses valid HSL (0 0% 100% / ...)',
  isBorderGlassFixedInTheme,
  'ThemeContext.tsx still contains 255 255%'
);

reportResult(
  '--border-glass in globals.css uses valid HSL (0 0% 100% / ...)',
  isBorderGlassFixedInGlobals,
  'globals.css still contains 255 255%'
);


// ---------------------------------------------------------------------------
// TEST 2: Cyclic CSS Custom Variable Definitions Audit
// ---------------------------------------------------------------------------
console.log('\n--- TEST 2: Cyclic CSS Custom Variable Property Audit ---');

let cyclicMatches = [];
const cssVarDefRegex = /(--[\w-]+)\s*:\s*var\(\s*\1[,\s\)]/g;

sourceFiles.forEach(file => {
  const content = fs.readFileSync(file, 'utf8');
  let match;
  while ((match = cssVarDefRegex.exec(content)) !== null) {
    cyclicMatches.push({ file, varName: match[1], line: match[0] });
  }
});

reportResult(
  'Zero cyclic custom property definitions (--var: var(--var...)) in src/',
  cyclicMatches.length === 0,
  cyclicMatches.map(m => `${m.file}: ${m.line}`).join('\n')
);

const isFontOutfitCyclicInGlobals = /--font-outfit\s*:\s*var\(--font-outfit/.test(globalsContent);
reportResult(
  '--font-outfit in globals.css is non-cyclic',
  !isFontOutfitCyclicInGlobals,
  'globals.css still has self-referential --font-outfit'
);


// ---------------------------------------------------------------------------
// TEST 3: Heading Specificity and Font Squashing Audit
// ---------------------------------------------------------------------------
console.log('\n--- TEST 3: Heading Specificity & Puck Canvas Font Squashing Audit ---');

const platformH1Not = /\.workspace-platform\s+h1:not\(\[class\*="text-"\]\)/.test(globalsContent);
const platformH6Not = /\.workspace-platform\s+h6:not\(\[class\*="text-"\]\)/.test(globalsContent);
const puckEditorH1Not = /\.puck-editor\s+h1:not\(\[class\*="text-"\]\)/.test(globalsContent);
const puckH1Not = /\.Puck\s+h1:not\(\[class\*="text-"\]\)/.test(globalsContent);
const platformPuckH1Not = /\.workspace-platform\s+\.puck-editor\s+h1:not\(\[class\*="text-"\]\)/.test(globalsContent);

reportResult(
  'globals.css .workspace-platform heading selectors use :not([class*="text-"])',
  platformH1Not && platformH6Not,
  'Missing :not([class*="text-"]) on .workspace-platform headings'
);

reportResult(
  'globals.css Puck editor heading rules use :not([class*="text-"]) to preserve utility font-sizes',
  puckEditorH1Not && puckH1Not && platformPuckH1Not,
  'Missing :not([class*="text-"]) on Puck canvas heading override rules'
);


// ---------------------------------------------------------------------------
// TEST 4: Theme Variable Cascading & Puck Setup Audit
// ---------------------------------------------------------------------------
console.log('\n--- TEST 4: Theme Variable Cascading & Puck Setup Audit ---');

const puckPagePath = path.resolve(srcDir, 'app/plataforma/cms/builder-puck/page.tsx');
const puckPageContent = fs.readFileSync(puckPagePath, 'utf8');

const hasIframeDisabled = /iframe=\{\{\s*enabled:\s*false\s*\}\}/.test(puckPageContent);
const hasThemeStylesApplied = /<main[^>]*style=\{themeStyles\}/.test(puckPageContent);
const fetchesThemeApi = /\/cms\/v2\/public\/sites\/\$\{siteKey\}\/theme/.test(puckPageContent);

reportResult(
  'builder-puck/page.tsx sets iframe={{ enabled: false }} on <Puck>',
  hasIframeDisabled,
  'Puck iframe is not disabled!'
);

reportResult(
  'builder-puck/page.tsx passes style={themeStyles} to container <main>',
  hasThemeStylesApplied,
  '<main> container does not apply themeStyles!'
);

reportResult(
  'builder-puck/page.tsx fetches site theme dynamically from CMS API',
  fetchesThemeApi,
  'Theme API fetch missing in builder-puck/page.tsx'
);


console.log(`\n=== FINAL EMPIRICAL VERIFICATION SUMMARY ===`);
console.log(`Total Failures: ${totalFailures}`);
process.exit(totalFailures === 0 ? 0 : 1);
