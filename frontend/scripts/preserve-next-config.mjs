import { readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

// next build muta tsconfig.json (añade el distDir al include) y next-env.d.ts
// (apunta el reference de tipos al distDir) cuando NEXT_DIST_DIR != '.next'.
// Esos dos archivos están trackeados en git y deben quedar intactos después de
// cualquier build del deploy seguro (build-safe / verify-build), o el working
// tree se ensucia y tsc apunta a directorios que ya no existen.
const TRACKED = ['tsconfig.json', 'next-env.d.ts'];

export async function snapshotNextConfig(cwd) {
    const snap = new Map();
    for (const name of TRACKED) {
        try {
            snap.set(name, await readFile(join(cwd, name), 'utf8'));
        } catch {
            // No existía antes del build; en el restore se elimina.
        }
    }
    return snap;
}

export async function restoreNextConfig(cwd, snap) {
    for (const name of TRACKED) {
        const p = join(cwd, name);
        if (snap.has(name)) {
            await writeFile(p, snap.get(name), 'utf8');
        } else {
            await rm(p, { force: true });
        }
    }
}
