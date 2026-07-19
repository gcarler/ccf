import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';

const args = [...process.argv.slice(2)];
const authFlagIndex = args.indexOf('--auth');
const authEnabled = authFlagIndex >= 0;
const academyRolesFlagIndex = args.indexOf('--academy-roles');
const academyRolesEnabled = academyRolesFlagIndex >= 0;
const hasWorkersFlag = args.includes('--workers');

if (authEnabled) {
  args.splice(authFlagIndex, 1);
}
if (academyRolesEnabled) {
  args.splice(academyRolesFlagIndex, 1);
}

async function resolveManagedPort() {
  if (process.env.PLAYWRIGHT_PORT) {
    return process.env.PLAYWRIGHT_PORT;
  }

  return await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      const port =
        address && typeof address === 'object'
          ? String(address.port)
          : '4173';
      server.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve(port);
      });
    });
  });
}

const port = await resolveManagedPort();
const apiBaseUrl = (
  process.env.E2E_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.API_BASE_URL ||
  'http://127.0.0.1:8000/api'
).replace(/\/$/, '');

const env = {
  ...process.env,
  PLAYWRIGHT_PORT: port,
  PLAYWRIGHT_BASE_URL: process.env.PLAYWRIGHT_BASE_URL || `http://localhost:${port}`,
  NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '/api',
  API_BASE_URL: process.env.API_BASE_URL || apiBaseUrl,
};

const managedBuildDir = path.join(process.cwd(), '.next');
fs.rmSync(managedBuildDir, { recursive: true, force: true });

const buildResult = spawnSync('npm', ['run', 'build'], {
  stdio: 'inherit',
  env,
});

if (buildResult.error) {
  throw buildResult.error;
}

if ((buildResult.status ?? 1) !== 0) {
  process.exit(buildResult.status ?? 1);
}

if (authEnabled || academyRolesEnabled) {
  env.E2E_AUTH_ENABLED = process.env.E2E_AUTH_ENABLED || '1';
  env.E2E_API_URL = process.env.E2E_API_URL || apiBaseUrl;
  env.E2E_EMAIL = process.env.E2E_EMAIL || 'e2e.admin@ccf.local';
  env.E2E_PASSWORD = process.env.E2E_PASSWORD || 'E2E-admin-ccf-2026!';

  if (!hasWorkersFlag) {
    args.unshift('1');
    args.unshift('--workers');
  }
}

if (academyRolesEnabled) {
  // TKT-202: seed 4 distinct role users (Lector/Estudiante/Editor/Admin)
  // so the multi-role Academy suite can log in as each persona.
  env.ACADEMY_SEED_PASSWORD =
    process.env.ACADEMY_SEED_PASSWORD || 'E2E-Academy-2026!';
  const academySeed = spawnSync(
    'node',
    ['tests/e2e/academy/seed-academy-roles.mjs'],
    { stdio: 'inherit', env },
  );
  if (academySeed.error) throw academySeed.error;
  if ((academySeed.status ?? 1) !== 0) {
    process.exit(academySeed.status ?? 1);
  }
}

if (authEnabled) {
  const seedResult = spawnSync('node', ['tests/e2e/seed-auth-user.mjs'], {
    stdio: 'inherit',
    env,
  });

  if (seedResult.error) {
    throw seedResult.error;
  }

  if ((seedResult.status ?? 1) !== 0) {
    process.exit(seedResult.status ?? 1);
  }
}

const startBin = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const startServer = spawn(startBin, ['run', 'start', '--', '-p', port], {
  stdio: 'inherit',
  env,
});

const stopServer = () => {
  if (!startServer.killed) {
    startServer.kill('SIGTERM');
  }
};

process.on('exit', stopServer);
process.on('SIGINT', () => {
  stopServer();
  process.exit(130);
});
process.on('SIGTERM', () => {
  stopServer();
  process.exit(143);
});

if (startServer.error) {
  throw startServer.error;
}

async function waitForServerReady(baseUrl, timeoutMs = 120_000) {
  const deadline = Date.now() + timeoutMs;
  const target = `${baseUrl.replace(/\/$/, '')}/login`;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(target, { redirect: 'manual' });
      if (response.status >= 200 && response.status < 500) {
        return;
      }
    } catch {
      // Server still booting.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  throw new Error(`Managed server did not become ready at ${target} within ${timeoutMs}ms`);
}

await waitForServerReady(env.PLAYWRIGHT_BASE_URL);

const npxBin = process.platform === 'win32' ? 'npx.cmd' : 'npx';
const result = spawnSync(npxBin, ['playwright', 'test', ...args], {
  stdio: 'inherit',
  env,
});

stopServer();

if (result.error) {
  throw result.error;
}

process.exit(result.status ?? 1);
