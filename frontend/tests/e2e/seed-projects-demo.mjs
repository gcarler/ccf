import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');

function seedViaPython() {
  const result = spawnSync('python3', ['scripts/seeding/seed_projects_demo.py'], {
    cwd: repoRoot,
    env: {
      ...process.env,
      PROJECTS_DEMO_EMAIL: process.env.E2E_EMAIL || process.env.PROJECTS_DEMO_EMAIL || '',
    },
    encoding: 'utf8',
  });
  if (result.status !== 0) {
    throw new Error(`[seed-projects-demo] Python seed failed: ${result.stderr || result.stdout || 'unknown error'}`);
  }
  return result.stdout.trim();
}

try {
  const output = seedViaPython();
  console.log(output || '[seed-projects-demo] seeded');
} catch (error) {
  console.error(error);
  process.exit(1);
}
