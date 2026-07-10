import { spawn } from 'node:child_process';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import process from 'node:process';

const args = process.argv.slice(2);

if (args.length === 0) {
    console.error('Usage: node scripts/with-next-lock.mjs <command> [...args]');
    process.exit(1);
}

const lockDir = join(process.cwd(), '.next-command.lock');
const lockInfoPath = join(lockDir, 'owner.json');
const staleAfterMs = 10 * 60 * 1000;
const retryDelayMs = 250;

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

async function readLockInfo() {
    try {
        return JSON.parse(await readFile(lockInfoPath, 'utf8'));
    } catch {
        return null;
    }
}

async function acquireLock() {
    while (true) {
        try {
            await mkdir(lockDir);
            await writeFile(
                lockInfoPath,
                JSON.stringify({
                    pid: process.pid,
                    command: args.join(' '),
                    createdAt: new Date().toISOString(),
                }, null, 2),
                'utf8',
            );
            return;
        } catch (error) {
            if (error?.code !== 'EEXIST') {
                throw error;
            }

            const info = await readLockInfo();
            const createdAt = info?.createdAt ? Date.parse(info.createdAt) : Number.NaN;
            const isStale = Number.isNaN(createdAt) || Date.now() - createdAt > staleAfterMs;

            if (isStale) {
                await rm(lockDir, { recursive: true, force: true });
                continue;
            }

            await sleep(retryDelayMs);
        }
    }
}

async function releaseLock() {
    await rm(lockDir, { recursive: true, force: true });
}

function resolveCommand(command, commandArgs) {
    if (command === 'next') {
        return {
            executable: process.execPath,
            args: [join(process.cwd(), 'node_modules', 'next', 'dist', 'bin', 'next'), ...commandArgs],
        };
    }

    return {
        executable: command,
        args: commandArgs,
    };
}

await acquireLock();

// Aumentar memoria disponible para evitar OOM en builds grandes
if (!process.env.NODE_OPTIONS || !process.env.NODE_OPTIONS.includes('max-old-space-size')) {
    process.env.NODE_OPTIONS = `${process.env.NODE_OPTIONS || ''} --max-old-space-size=8192`.trim();
}

const command = resolveCommand(args[0], args.slice(1));
const child = spawn(command.executable, command.args, {
    stdio: 'inherit',
    shell: false,
});

try {
    const exitCode = await new Promise((resolve) => {
        child.on('error', () => resolve(1));
        child.on('close', resolve);
    });

    process.exitCode = exitCode ?? 1;
} finally {
    await releaseLock();
}
