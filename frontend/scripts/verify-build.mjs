import { rm } from 'node:fs/promises';
import { join } from 'node:path';
import process from 'node:process';
import { spawn } from 'node:child_process';
import { snapshotNextConfig, restoreNextConfig } from './preserve-next-config.mjs';

const cwd = process.cwd();
const verifyDir = join(cwd, '.next-verify');

await rm(verifyDir, { recursive: true, force: true });
const configSnapshot = await snapshotNextConfig(cwd);
let exitCode = 0;

try {
    const child = spawn(
        process.execPath,
        [join(cwd, 'scripts', 'with-next-lock.mjs'), 'next', 'build'],
        {
            stdio: 'inherit',
            shell: false,
            env: { ...process.env, NEXT_DIST_DIR: '.next-verify' },
        },
    );
    exitCode = (await new Promise((resolve) => {
        child.on('error', () => resolve(1));
        child.on('close', resolve);
    })) ?? 1;
} catch (error) {
    console.error('Unexpected error during verify-build:', error);
    exitCode = 1;
} finally {
    await restoreNextConfig(cwd, configSnapshot);
    await rm(verifyDir, { recursive: true, force: true });
}

process.exit(exitCode);
