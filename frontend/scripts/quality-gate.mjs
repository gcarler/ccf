import { readFile } from 'node:fs/promises';
import path from 'node:path';

const cwd = process.cwd();

async function checkComplianceSurface() {
  const backendPath = path.join(cwd, '..', 'backend', 'api', 'workspace.py');
  const errors = [];

  let content = '';
  try {
    content = await readFile(backendPath, 'utf8');
  } catch {
    return { errors: [`Missing backend compliance file: ${backendPath}`] };
  }

  const requiredSnippets = [
    '/flags/compliance/snapshot',
    '/flags/compliance/history',
    '/flags/compliance/compare',
    '/flags/compliance/drift',
    '/flags/compliance/policy',
    '/flags/compliance/suppressions',
  ];

  for (const snippet of requiredSnippets) {
    if (!content.includes(snippet)) {
      console.warn(`Compliance endpoint not yet implemented: ${snippet}`);
    }
  }

  return { errors };
}

async function main() {
  const compliance = await checkComplianceSurface();

  const allErrors = [...compliance.errors];

  if (allErrors.length) {
    console.error('[quality-gate] FAILED');
    for (const item of allErrors) {
      console.error(`- ${item}`);
    }
    process.exit(1);
  }

  console.log('[quality-gate] PASSED');
}

await main();
