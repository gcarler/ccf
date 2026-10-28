import { rm } from 'node:fs/promises';
import { join } from 'node:path';
import process from 'node:process';
import { spawn } from 'node:child_process';
import { snapshotNextConfig, restoreNextConfig } from './preserve-next-config.mjs';

const cwd = process.cwd();
const verifyDir = join(cwd, '.next-verify');

await rm(verifyDir, { recursive: true, force: true });
// next build muta tsconfig.json / next-env.d.ts (apuntan al distDir); los
// restauramos para no ensuciar el working tree del gate.
const configSnap = await snapshotNextConfig(cwd);

async function cleanup() {
    await restoreNextConfig(cwd, configSnap);
    await rm(verifyDir, { recursive: true, force: true });
}

let child = null;
let closed = Promise.resolve(1);
let interruptedBy = null;

// El gate del pre-push corre este script bajo `timeout`, que envía SIGTERM al
// vencer. Sin un handler, Node muere sin ejecutar el `finally` y deja
// tsconfig.json / next-env.d.ts mutados (el push se niega con worktree sucio)
// y .next-verify huérfano. Con el handler: se detiene el build hijo, se espera
// su cierre y se restaura el working tree antes de salir.
for (const [signal, exitCode] of [['SIGTERM', 143], ['SIGINT', 130]]) {
    process.on(signal, async () => {
        if (interruptedBy) return;
        interruptedBy = signal;
        try {
            child?.kill('SIGTERM');
            await closed;
        } finally {
            await cleanup();
            process.exit(exitCode);
        }
    });
}

let exitCode = 0;
try {
    child = spawn(
        process.execPath,
        [join(cwd, 'scripts', 'with-next-lock.mjs'), 'next', 'build'],
        {
            stdio: 'inherit',
            shell: false,
            env: { ...process.env, NEXT_DIST_DIR: '.next-verify' },
        },
    );
    closed = new Promise((resolve) => {
        child.on('error', () => resolve(1));
        child.on('close', (code) => resolve(code ?? 1));
    });
    exitCode = await closed;
} catch (error) {
    console.error('Unexpected error during verify-build:', error);
    exitCode = 1;
} finally {
    if (!interruptedBy) {
        await cleanup();
    }
}

// Si una señal llegó durante el build, su handler finaliza el proceso con el
// código de señal una vez restaurado el árbol; no se compite con él aquí.
if (!interruptedBy) {
    process.exit(exitCode);
}
