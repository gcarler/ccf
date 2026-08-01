const fs = require('fs');
const path = require('path');

const rootDir = '/root/ccf/frontend';

const layoutPath = path.join(rootDir, 'src/app/layout.tsx');
const tailwindPath = path.join(rootDir, 'tailwind.config.ts');
const globalsCssPath = path.join(rootDir, 'src/app/globals.css');
const publicCssPath = path.join(rootDir, 'src/app/(public)/public.css');
const builderPuckPath = path.join(rootDir, 'src/app/plataforma/cms/builder-puck/page.tsx');

console.log("=== EMPIRICAL VERIFICATION FOR MILESTONE 1 ===");

// 1. Verify layout.tsx font imports and html variable binding
const layoutContent = fs.readFileSync(layoutPath, 'utf8');
const fontImports = ['Roboto', 'Inter', 'Open_Sans', 'Outfit'];
fontImports.forEach(font => {
  if (!layoutContent.includes(font)) {
    console.error(`[FAIL] layout.tsx missing import for ${font}`);
  } else {
    console.log(`[PASS] layout.tsx imports ${font}`);
  }
});

const requiredFontVarsInLayout = ['--font-roboto', '--font-open-sans', '--font-inter', '--font-outfit'];
requiredFontVarsInLayout.forEach(v => {
  if (!layoutContent.includes(v)) {
    console.error(`[FAIL] layout.tsx missing definition of font variable ${v}`);
  } else {
    console.log(`[PASS] layout.tsx defines font variable ${v}`);
  }
});

const htmlClassCheck = ['roboto.variable', 'openSans.variable', 'inter.variable', 'outfit.variable'];
htmlClassCheck.forEach(c => {
  if (!layoutContent.includes(c)) {
    console.error(`[FAIL] layout.tsx html tag missing ${c}`);
  } else {
    console.log(`[PASS] layout.tsx html tag includes ${c}`);
  }
});

// 2. Extract site variables defined in public.css across all themes
const publicCssContent = fs.readFileSync(publicCssPath, 'utf8');

function extractThemeVars(cssContent, themeSelector) {
  const themeStartIndex = cssContent.indexOf(themeSelector);
  if (themeStartIndex === -1) {
    console.error(`[FAIL] Theme selector ${themeSelector} not found in public.css`);
    return new Set();
  }
  const blockStart = cssContent.indexOf('{', themeStartIndex);
  const blockEnd = cssContent.indexOf('}', blockStart);
  const blockContent = cssContent.slice(blockStart + 1, blockEnd);

  const varMatches = blockContent.matchAll(/--site-[a-zA-Z0-9-]+(?=\s*:)/g);
  const vars = new Set();
  for (const match of varMatches) {
    vars.add(match[0]);
  }
  return vars;
}

const lightVars = extractThemeVars(publicCssContent, '.theme-light');
const instVars = extractThemeVars(publicCssContent, '.theme-institutional');
const darkVars = extractThemeVars(publicCssContent, '.theme-dark');

console.log(`\nFound --site-* variables count:`);
console.log(`  .theme-light: ${lightVars.size}`);
console.log(`  .theme-institutional: ${instVars.size}`);
console.log(`  .theme-dark: ${darkVars.size}`);

// Check if set of variables match across themes
const allThemes = [
  { name: '.theme-light', set: lightVars },
  { name: '.theme-institutional', set: instVars },
  { name: '.theme-dark', set: darkVars }
];

let themesMatch = true;
for (const varName of lightVars) {
  if (!instVars.has(varName)) {
    console.error(`[FAIL] Variable ${varName} in .theme-light is missing from .theme-institutional`);
    themesMatch = false;
  }
  if (!darkVars.has(varName)) {
    console.error(`[FAIL] Variable ${varName} in .theme-light is missing from .theme-dark`);
    themesMatch = false;
  }
}
for (const varName of instVars) {
  if (!lightVars.has(varName)) {
    console.error(`[FAIL] Variable ${varName} in .theme-institutional is missing from .theme-light`);
    themesMatch = false;
  }
}
for (const varName of darkVars) {
  if (!lightVars.has(varName)) {
    console.error(`[FAIL] Variable ${varName} in .theme-dark is missing from .theme-light`);
    themesMatch = false;
  }
}

if (themesMatch) {
  console.log(`[PASS] All 3 public themes define identical set of ${lightVars.size} --site-* variables.`);
}

// 3. Verify tailwind.config.ts site-* color mappings
const tailwindContent = fs.readFileSync(tailwindPath, 'utf8');

const tailwindSiteMatches = [...tailwindContent.matchAll(/"site-([a-zA-Z0-9-]+)"\s*:\s*"var\((--site-[a-zA-Z0-9-]+)\)"/g)];
console.log(`\nFound ${tailwindSiteMatches.length} site-* color mappings in tailwind.config.ts`);

let missingInCss = 0;
for (const match of tailwindSiteMatches) {
  const [, key, cssVar] = match;
  if (!lightVars.has(cssVar)) {
    console.error(`[FAIL] tailwind.config.ts maps site-${key} to ${cssVar}, which is NOT defined in public.css`);
    missingInCss++;
  }
}
if (missingInCss === 0) {
  console.log(`[PASS] All site-* colors in tailwind.config.ts map to valid --site-* variables in public.css.`);
}

// 4. Verify font fallbacks in globals.css and tailwind.config.ts
const globalsCssContent = fs.readFileSync(globalsCssPath, 'utf8');

console.log(`\nChecking globals.css font declarations...`);
const fontVarsInGlobals = ['--font-outfit', '--font-display', '--font-headline', '--font-body', '--font-label', '--font-mono'];
fontVarsInGlobals.forEach(v => {
  if (globalsCssContent.includes(v)) {
    console.log(`[PASS] globals.css contains ${v}`);
  } else {
    console.error(`[FAIL] globals.css missing ${v}`);
  }
});

// Check fallbacks in globals.css font vars
if (globalsCssContent.includes("--font-outfit:    var(--font-outfit, 'Outfit'), sans-serif;")) {
  console.log(`[PASS] --font-outfit in globals.css has proper fallback chain ('Outfit', sans-serif)`);
} else {
  console.warn(`[WARN] Check --font-outfit in globals.css for fallbacks`);
}

// Check puck builder fallbacks
const builderPuckContent = fs.readFileSync(builderPuckPath, 'utf8');
console.log(`\nChecking builder-puck/page.tsx CSS variable fallbacks...`);
const puckSiteVarUsages = [...builderPuckContent.matchAll(/var\((--site-[a-zA-Z0-9-]+)(?:,\s*([^)]+))?\)/g)];
console.log(`Found ${puckSiteVarUsages.length} var(--site-*) usages in builder-puck/page.tsx`);

let puckMissingFallbackCount = 0;
for (const usage of puckSiteVarUsages) {
  const [fullMatch, cssVar, fallback] = usage;
  if (!fallback) {
    console.warn(`[INFO] puck builder usage ${fullMatch} has no inline fallback`);
  } else {
    // console.log(`  ${cssVar} -> fallback: ${fallback}`);
  }
}

console.log("\n=== VERIFICATION COMPLETE ===");
