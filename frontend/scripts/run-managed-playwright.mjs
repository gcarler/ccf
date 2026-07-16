import { spawnSync } from 'node:child_process';

const args = [...process.argv.slice(2)];
const authFlagIndex = args.indexOf('--auth');
const authEnabled = authFlagIndex >= 0;

if (authEnabled) {
  args.splice(authFlagIndex, 1);
}

const port = process.env.PLAYWRIGHT_PORT || '4173';
const apiBaseUrl = (
  process.env.E2E_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_BASE_URL ||
  'http://127.0.0.1:8000/api'
).replace(/\/$/, '');

const env = {
  ...process.env,
  PLAYWRIGHT_MANAGED_WEBSERVER: '1',
  PLAYWRIGHT_PORT: port,
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '/api',
  API_BASE_URL: process.env.API_BASE_URL || apiBaseUrl,
};

if (authEnabled) {
  env.E2E_AUTH_ENABLED = process.env.E2E_AUTH_ENABLED || '1';
  env.E2E_API_URL = process.env.E2E_API_URL || apiBaseUrl;
}

const npxBin = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const result = spawnSync(npxBin, ['playwright', 'test', ...args], {
  stdio: 'inherit',
  env,
});

if (result.error) {
  throw result.error;
}

process.exit(result.status ?? 1);
