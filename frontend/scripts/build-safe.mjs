import { access, rename, rm } from 'node:fs/promises';
import { join } from 'node:path';
import process from 'node:process';
import { spawn } from 'node:child_process';
import { snapshotNextConfig, restoreNextConfig } from './preserve-next-config.mjs';

const cwd = process.cwd();
const liveDir = join(cwd, '.next');
const stagingDir = join(cwd, '.next-build');
const oldDir = join(cwd, '.next-old');

async function exists(filePath) {
    try {
        await access(filePath);
        return true;
    } catch {
        return false;
    }
}

async function runChild(executable, args, env) {
    const child = spawn(executable, args, {
        stdio: 'inherit',
        shell: false,
        env: { ...process.env, ...(env || {}) },
    });
    return new Promise((resolve) => {
        child.on('error', () => resolve(1));
        child.on('close', resolve);
    });
}

// En un crash intermedio puede existir .next-old sin .next; lo restauramos
// para no dejar al servidor sin build que servir.
async function restoreLastGood() {
    if (!(await exists(liveDir)) && (await exists(oldDir))) {
        await rename(oldDir, liveDir);
        console.error('Restored last good build from .next-old.');
    }
}

// ─── 1. Limpieza de residuos ─────────────────────────────────────────────────
// Solo se borra el staging: .next-old no se toca aquí (puede contener el último
// build bueno y el swap lo reemplaza de forma atómica al final).
await rm(stagingDir, { recursive: true, force: true });

// next build muta tsconfig.json / next-env.d.ts (apuntan al distDir). Los
// preservamos para que el working tree quede limpio tras el build.
const configSnap = await snapshotNextConfig(cwd);

let exitCode = 0;

try {
    // ─── 2. Build hacia el directorio staging ───────────────────────────────
    // Con NEXT_DIST_DIR=.next-build el build escribe fuera del .next que está
    // sirviendo el proceso en producción: durante todo el build, el servidor
    // vivo sigue atendiendo con su build completo (cero 400 por .next a medias).
    const buildExit = await runChild(
        process.execPath,
        [join(cwd, 'scripts', 'with-next-lock.mjs'), 'next', 'build'],
        { NEXT_DIST_DIR: '.next-build' },
    );

    if ((buildExit ?? 1) !== 0) {
        await rm(stagingDir, { recursive: true, force: true });
        await restoreLastGood();
        console.error('Build failed — the live build in .next was left untouched.');
        exitCode = buildExit ?? 1;
    } else {
        // ─── 3. Materializar aliases de assets dentro del build staging ────
        const aliasExit = await runChild(
            process.execPath,
            [join(cwd, 'scripts', 'fix-next-static-aliases.mjs')],
            { NEXT_DIST_DIR: '.next-build' },
        );
        if ((aliasExit ?? 1) !== 0) {
            await rm(stagingDir, { recursive: true, force: true });
            await restoreLastGood();
            console.error('Static alias fix failed — live build untouched.');
            exitCode = aliasExit ?? 1;
        } else {
            // ─── 4. Swap atómico: .next → .next-old, .next-build → .next ───
            // Ventana mínima y sin estado "a medias": o el servidor sirve el
            // build viejo (renombrado como .next-old) o el nuevo (.next). El
            // proceso que sirve debe reiniciarse después (deploy_frontend.sh).
            await rm(oldDir, { recursive: true, force: true });
            if (await exists(liveDir)) {
                await rename(liveDir, oldDir);
            }
            await rename(stagingDir, liveDir);
            // Con KEEP_OLD_BUILD=1 (deploy_frontend.sh) se conserva .next-old
            // (último build bueno) hasta que el smoke del deploy confirme el
            // build nuevo — permite rollback real si restart/smoke fallan.
            if (process.env.KEEP_OLD_BUILD !== '1') {
                await rm(oldDir, { recursive: true, force: true });
            }
            console.error('[build] new build swapped into .next — restart the server to serve it.');
        }
    }
} catch (error) {
    console.error('Unexpected error during build-safe:', error);
    await restoreLastGood();
    exitCode = 1;
} finally {
    await restoreNextConfig(cwd, configSnap);
}

process.exit(exitCode);
