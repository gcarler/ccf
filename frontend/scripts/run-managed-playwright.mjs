import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { restoreNextConfig, snapshotNextConfig } from './preserve-next-config.mjs';

const rawArgs = process.argv.slice(2);
const authEnabled = rawArgs.includes('--auth');
const academyRolesEnabled = rawArgs.includes('--academy-roles');
const reuseBuild = rawArgs.includes('--reuse-build');
const hasWorkersFlag = rawArgs.includes('--workers');

// Filter out managed-runner flags so they are not forwarded to playwright test.
const args = rawArgs.filter(
  (arg) => arg !== '--auth' && arg !== '--academy-roles' && arg !== '--reuse-build',
);

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

const cwd = process.cwd();
const managedBuildName = reuseBuild ? '.next' : `.next-playwright-${process.pid}`;
const managedBuildDir = path.join(cwd, managedBuildName);
let ownsManagedBuildDir = false;

process.on('exit', () => {
  if (ownsManagedBuildDir) {
    fs.rmSync(managedBuildDir, { recursive: true, force: true });
  }
});

if (!reuseBuild) {
  // Keep E2E builds isolated: `npm run build` swaps the shared .next directory,
  // which can strand an already-running Next server with stale manifests.
  // Reserve a per-process directory and only ever clean up the one this runner
  // owns; a collision is an error, never permission to delete another run's data.
  fs.mkdirSync(managedBuildDir);
  ownsManagedBuildDir = true;
  const configSnapshot = await snapshotNextConfig(cwd);
  let buildStatus = 0;

  try {
    const buildResult = spawnSync(
      process.execPath,
      [path.join(cwd, 'scripts', 'with-next-lock.mjs'), 'next', 'build'],
      {
        stdio: 'inherit',
        env: { ...env, NEXT_DIST_DIR: managedBuildName },
      },
    );

    if (buildResult.error) {
      throw buildResult.error;
    }
    buildStatus = buildResult.status ?? 1;

    if (buildStatus === 0) {
      const aliasesResult = spawnSync(
        process.execPath,
        [path.join(cwd, 'scripts', 'fix-next-static-aliases.mjs')],
        {
          stdio: 'inherit',
          env: { ...env, NEXT_DIST_DIR: managedBuildName },
        },
      );
      if (aliasesResult.error) throw aliasesResult.error;
      buildStatus = aliasesResult.status ?? 1;
    }
  } finally {
    await restoreNextConfig(cwd, configSnapshot);
  }

  if (buildStatus !== 0) {
    fs.rmSync(managedBuildDir, { recursive: true, force: true });
    ownsManagedBuildDir = false;
    process.exit(buildStatus);
  }
}

env.NEXT_DIST_DIR = managedBuildName;

// Stabilise E2E suites by defaulting to a single Playwright worker unless the
// caller explicitly requested a different value. Auth tests share login state
// and public-contract tests hit the backend heavily, so serial execution keeps
// both groups reliable.
if (!hasWorkersFlag) {
  args.unshift('1');
  args.unshift('--workers');
}

if (authEnabled || academyRolesEnabled) {
  env.E2E_AUTH_ENABLED = process.env.E2E_AUTH_ENABLED || '1';
  env.E2E_API_URL = process.env.E2E_API_URL || apiBaseUrl;
  env.E2E_EMAIL = process.env.E2E_EMAIL || 'e2e.admin@ccf.local';
  env.E2E_PASSWORD = process.env.E2E_PASSWORD || 'E2E-admin-ccf-2026!';
}

const isSeededProjectsE2E = args.some((arg) =>
  /(?:^|\/)tests\/e2e\/projects\/(?:detail|projects-demo)\.spec\.ts$/.test(arg),
);
if (authEnabled && isSeededProjectsE2E) {
  const preferredPython = process.env.PYTHON_BIN || path.resolve(cwd, '../venv/bin/python');
  const pythonBin = fs.existsSync(preferredPython) ? preferredPython : 'python3';
  const targetCheck = spawnSync(
    pythonBin,
    ['scripts/seeding/seed_projects_demo.py', '--check-target'],
    { cwd: path.resolve(cwd, '..'), stdio: 'inherit', env },
  );
  if (targetCheck.error) throw targetCheck.error;
  if ((targetCheck.status ?? 1) !== 0) process.exit(targetCheck.status ?? 1);
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
  // npm launches `next start` as a child. On Unix, a detached process group
  // lets cleanup terminate both the npm wrapper and its Next descendant when
  // Playwright or this runner is interrupted. Windows uses taskkill /T below.
  detached: process.platform !== 'win32',
  stdio: 'inherit',
  env,
});

let serverStopRequested = false;

const stopServer = () => {
  if (serverStopRequested || !startServer.pid) {
    return;
  }
  serverStopRequested = true;

  if (process.platform === 'win32') {
    // npm.cmd may have spawned several descendants; /T terminates the full
    // tree and /F prevents a stuck Next child from surviving the runner.
    spawnSync('taskkill', ['/pid', String(startServer.pid), '/T', '/F'], {
      stdio: 'ignore',
    });
    return;
  }

  try {
    // Negative PIDs address the detached process group, not an unrelated
    // service that happens to use another port.
    process.kill(-startServer.pid, 'SIGTERM');
  } catch (error) {
    // The group may already have exited. Preserve the runner's original
    // result for that expected case, while surfacing unexpected failures.
    if (error?.code !== 'ESRCH') {
      throw error;
    }
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
