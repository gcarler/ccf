import { readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const TRACKED = ['tsconfig.json', 'next-env.d.ts'];

export async function snapshotNextConfig(cwd) {
    const snap = new Map();
    for (const name of TRACKED) {
        try {
            snap.set(name, await readFile(join(cwd, name), 'utf8'));
        } catch {
            // El archivo puede no existir en instalaciones parciales.
        }
    }
    return snap;
}

export async function restoreNextConfig(cwd, snap) {
    for (const name of TRACKED) {
        const path = join(cwd, name);
        if (snap.has(name)) {
            await writeFile(path, snap.get(name), 'utf8');
        } else {
            await rm(path, { force: true });
        }
    }
}
