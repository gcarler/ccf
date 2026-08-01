import fs from 'fs';
import path from 'path';

console.log("=== EMPIRICAL CSS STRESS-TEST SUITE ===");

// 1. Test cyclic variable reference in globals.css
const globalsCssPath = '/root/ccf/frontend/src/app/globals.css';
const globalsCss = fs.readFileSync(globalsCssPath, 'utf8');

const cyclicFontRegex = /--font-outfit:\s*var\(--font-outfit/;
const isCyclicFont = cyclicFontRegex.test(globalsCss);
console.log(`[Test 1] Cyclic variable --font-outfit self-reference: ${isCyclicFont ? 'FAILED (Cyclic loop detected!)' : 'PASSED'}`);

// 2. Test invalid HSL in dark mode in globals.css
const invalidHslRegex = /--border-glass:\s*255\s+255%/;
const isInvalidHsl = invalidHslRegex.test(globalsCss);
console.log(`[Test 2] Invalid HSL syntax 255% in [data-theme="night"]: ${isInvalidHsl ? 'FAILED (Invalid HSL percentage 255% detected!)' : 'PASSED'}`);

// 3. Test layout.tsx dark mode body text color asymmetry
const layoutPath = '/root/ccf/frontend/src/app/layout.tsx';
const layoutContent = fs.readFileSync(layoutPath, 'utf8');
const darkBodyAsymmetryRegex = /dark:text-\[hsl\(var\(--text-secondary\)\)\]/;
const isDarkAsymmetric = darkBodyAsymmetryRegex.test(layoutContent);
console.log(`[Test 3] layout.tsx body dark mode text color: ${isDarkAsymmetric ? 'FAILED (Body uses text-secondary instead of text-primary in dark mode!)' : 'PASSED'}`);

// 4. Test Puck iframe disabled specificity collision with .workspace-platform
const puckPagePath = '/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx';
const puckContent = fs.readFileSync(puckPagePath, 'utf8');
const hasIframeDisabled = /iframe=\{\{\s*enabled:\s*false\s*\}\}/.test(puckContent);
const workspacePlatformH1 = /\.workspace-platform\s+h1\s*\{/.test(globalsCss);
console.log(`[Test 4] Puck iframe disabled (${hasIframeDisabled}) vs .workspace-platform h1 rule (${workspacePlatformH1}): ${hasIframeDisabled && workspacePlatformH1 ? 'FAILED (Puck canvas h1/h2/h3 will be overridden by .workspace-platform rule with higher specificity!)' : 'PASSED'}`);
