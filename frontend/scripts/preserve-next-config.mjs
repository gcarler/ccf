import { readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const TRACKED = ['tsconfig.json', 'next-env.d.ts'];

export async function snapshotNextConfig(cwd) {
    const snap = new Map();
    for (const name of TRACKED) {
        try {
            snap.set(name, await readFile(join(cwd, name), 'utf8'));
        } catch {
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
