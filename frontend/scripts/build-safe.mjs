import { rename, rm } from 'node:fs/promises';
import { join } from 'node:path';
import process from 'node:process';
import { spawn } from 'node:child_process';

const cwd = process.cwd();
const distDir = join(cwd, '.next');
const backupDir = join(cwd, `.next.backup-${Date.now()}-${process.pid}`);

async function moveCurrentBuildToBackup() {
    try {
        await rename(distDir, backupDir);
        return true;
    } catch (error) {
        if (error?.code === 'ENOENT') {
            return false;
        }
        throw error;
    }
}

async function restoreBackup() {
    try {
        await rm(distDir, { recursive: true, force: true });
        await rename(backupDir, distDir);
        console.error('Restored previous frontend build after failed compilation.');
    } catch (error) {
        console.error('Failed to restore previous frontend build:', error);
    }
}

const hadPreviousBuild = await moveCurrentBuildToBackup();

const child = spawn(
    process.execPath,
    [join(cwd, 'scripts', 'with-next-lock.mjs'), 'next', 'build'],
    {
        stdio: 'inherit',
        shell: false,
    },
);

const exitCode = await new Promise((resolve) => {
    child.on('error', () => resolve(1));
    child.on('close', resolve);
});

if ((exitCode ?? 1) === 0) {
    const aliasChild = spawn(
        process.execPath,
        [join(cwd, 'scripts', 'fix-next-static-aliases.mjs')],
        {
            stdio: 'inherit',
            shell: false,
        },
    );

    const aliasExitCode = await new Promise((resolve) => {
        aliasChild.on('error', () => resolve(1));
        aliasChild.on('close', resolve);
    });

    if ((aliasExitCode ?? 1) !== 0) {
        if (hadPreviousBuild) {
            await restoreBackup();
        }
        process.exit(aliasExitCode ?? 1);
    }

    if (hadPreviousBuild) {
        await rm(backupDir, { recursive: true, force: true });
    }
    process.exit(0);
}

if (hadPreviousBuild) {
    await restoreBackup();
}

process.exit(exitCode ?? 1);
