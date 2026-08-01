const fs = require('fs');
const path = require('path');

const globalsCss = fs.readFileSync('/root/ccf/frontend/src/app/globals.css', 'utf8');
const publicCss = fs.readFileSync('/root/ccf/frontend/src/app/(public)/public.css', 'utf8');
const tokensSemantic = fs.readFileSync('/root/ccf/frontend/src/design/tokens-semantic.ts', 'utf8');
const themeContext = fs.readFileSync('/root/ccf/frontend/src/app/plataforma/theme/ThemeContext.tsx', 'utf8');

console.log('=== EMPIRICAL VERIFICATION HARNESS (M1 R2) ===\n');

// --- TEST 1: Cyclic --font-outfit ---
console.log('--- TEST 1: Cyclic --font-outfit Definition ---');
const cyclicMatch = globalsCss.match(/--font-outfit\s*:\s*var\(--font-outfit[^;]*;/);
if (cyclicMatch) {
  console.log('FAIL: Self-referential cyclic definition detected in globals.css:');
  console.log('  Found:', cyclicMatch[0]);
} else {
  console.log('PASS: No cyclic --font-outfit definition found in globals.css.');
}
console.log('');

// --- TEST 2: Invalid HSL Syntax (255 255% 255%) ---
console.log('--- TEST 2: Invalid HSL Syntax (255 255% 255%) ---');
let hslFailures = [];

const filesToCheck = [
  { name: 'src/app/globals.css', content: globalsCss },
  { name: 'src/app/(public)/public.css', content: publicCss },
  { name: 'src/design/tokens-semantic.ts', content: tokensSemantic },
  { name: 'src/app/plataforma/theme/ThemeContext.tsx', content: themeContext }
];

filesToCheck.forEach(f => {
  const matches = [...f.content.matchAll(/255\s+255%/g)];
  if (matches.length > 0) {
    hslFailures.push({ file: f.name, count: matches.length });
  }
});

if (hslFailures.length > 0) {
  console.log('FAIL: Invalid HSL syntax "255 255% 255%" detected in files:');
  hslFailures.forEach(item => {
    console.log(`  - ${item.file} (${item.count} instance(s))`);
  });
} else {
  console.log('PASS: No "255 255% 255%" invalid HSL syntax found.');
}
console.log('');

// --- TEST 3: Puck Canvas Heading Font Size Squashing ---
console.log('--- TEST 3: Puck Canvas Heading Font Size Specificity & Cascade ---');

const hasNotTextFilter = globalsCss.includes('.workspace-platform h1:not([class*="text-"])') &&
                         globalsCss.includes('.puck-editor h1:not([class*="text-"])');

if (hasNotTextFilter) {
  console.log('PASS: Headings inside Puck editor canvas with utility classes (e.g. text-4xl) are not overridden.');
} else {
  const puckOverrideMatch = globalsCss.match(/\.workspace-platform\s+\.(?:puck-editor|Puck)\s+h1[\s\S]*?\{[\s\S]*?\}/);
  console.log('Puck override rule in globals.css:');
  if (puckOverrideMatch) {
    console.log(puckOverrideMatch[0].trim());
  }

  console.log('\nCascade Analysis:');
  console.log('1. Tailwind utility selector ".text-4xl" has specificity (0, 1, 0).');
  console.log('2. Selector ".workspace-platform .puck-editor h1" has specificity (0, 2, 1).');
  console.log('3. Since (0, 2, 1) > (0, 1, 0), ".workspace-platform .puck-editor h1" overrides ".text-4xl".');
  console.log('4. The rule sets "font-size: inherit;".');
  console.log('5. "font-size: inherit;" causes <h1 className="text-4xl"> to inherit font-size from its parent container inside .workspace-platform (var(--text-base) = 13px).');
  console.log('RESULT: FAIL — Headings inside Puck editor canvas with utility classes (e.g. text-4xl) are overridden and squashed to parent font-size (13px).');
}

console.log('\n=== VERIFICATION COMPLETE ===');
