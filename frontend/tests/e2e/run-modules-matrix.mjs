import { spawnSync } from 'node:child_process';

const rawProfiles = process.env.E2E_MATRIX_PROFILES || 'admin,editor,manager';
const profiles = rawProfiles
  .split(',')
  .map((value) => value.trim().toLowerCase())
  .filter(Boolean);

const baseEnv = {
  ...process.env,
  E2E_AUTH_ENABLED: process.env.E2E_AUTH_ENABLED || '1',
};

const resolvedApiUrl =
  process.env.E2E_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_BASE_URL ||
  '';

if (!resolvedApiUrl) {
  console.log('[e2e:modules:matrix] Missing E2E_API_URL/NEXT_PUBLIC_API_URL/API_BASE_URL. Skipping matrix.');
  process.exit(0);
}

let ranAtLeastOneProfile = false;

for (const profile of profiles) {
  const upper = profile.toUpperCase().replace(/[^A-Z0-9]+/g, '_');
  const email = process.env[`E2E_${upper}_EMAIL`] || '';
  const password = process.env[`E2E_${upper}_PASSWORD`] || '';

  if (!email || !password) {
    console.log(`[e2e:modules:matrix] Skipping profile "${profile}" — missing E2E_${upper}_EMAIL/E2E_${upper}_PASSWORD.`);
    continue;
  }

  ranAtLeastOneProfile = true;
  console.log(`[e2e:modules:matrix] Running module smoke matrix for profile "${profile}" (${email}).`);

  const result = spawnSync('npm', ['run', 'test:e2e:modules', '--', '--reporter=line'], {
    cwd: process.cwd(),
    stdio: 'inherit',
    env: {
      ...baseEnv,
      E2E_EMAIL: email,
      E2E_PASSWORD: password,
      E2E_API_URL: resolvedApiUrl,
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || resolvedApiUrl,
      E2E_AUTH_PROFILE: profile,
    },
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

if (!ranAtLeastOneProfile) {
  console.log('[e2e:modules:matrix] No runnable profiles found. Nothing executed.');
}
