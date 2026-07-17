import { access, mkdir, readdir, readFile, symlink, unlink } from 'node:fs/promises';
import { join, dirname, basename } from 'node:path';
import process from 'node:process';

const cwd = process.cwd();
const serverAppDir = join(cwd, '.next/server/app');
const nextStaticDir = join(cwd, '.next/static');

async function exists(filePath) {
    try {
        await access(filePath);
        return true;
    } catch {
        return false;
    }
}

async function collectHtmlFiles(dir) {
    const entries = await readdir(dir, { withFileTypes: true });
    const files = [];

    for (const entry of entries) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) {
            files.push(...await collectHtmlFiles(path));
        } else if (entry.isFile() && entry.name.endsWith('.html')) {
            files.push(path);
        }
    }

    return files;
}

function candidateForAsset(assetPath, cssFallback) {
    if (assetPath.includes('/_next/static/css/')) {
        return cssFallback;
    }

    const fileName = basename(assetPath);
    const aliasedName = fileName.replace(/-[a-f0-9]{6,}(?=\.(?:js|css)$)/i, '');
    if (aliasedName === fileName) return null;

    return assetPath.replace(fileName, aliasedName);
}

async function linkAlias(targetPath, sourcePath) {
    if (await exists(targetPath)) return false;
    await mkdir(dirname(targetPath), { recursive: true });
    try {
        await symlink(sourcePath, targetPath);
    } catch (error) {
        if (error?.code === 'EEXIST') return false;
        throw error;
    }
    return true;
}

async function main() {
    if (!(await exists(serverAppDir))) {
        return;
    }

    const cssFiles = [];
    const cssDir = join(nextStaticDir, 'css');
    if (await exists(cssDir)) {
        for (const entry of await readdir(cssDir, { withFileTypes: true })) {
            const path = join(cssDir, entry.name);
            if (entry.isFile() && entry.name.endsWith('.css')) cssFiles.push(path);
            if (entry.isDirectory()) {
                for (const nested of await readdir(path, { withFileTypes: true })) {
                    const nestedPath = join(path, nested.name);
                    if (nested.isFile() && nested.name.endsWith('.css')) cssFiles.push(nestedPath);
                }
            }
        }
    }
    const cssFallback = cssFiles.length === 1 ? cssFiles[0] : null;

    const htmlFiles = await collectHtmlFiles(serverAppDir);
    const assetUrls = new Set();

    for (const htmlFile of htmlFiles) {
        const html = await readFile(htmlFile, 'utf8');
        const matches = html.match(/\/_next\/static\/[^"'<> )]+/g) || [];
        for (const match of matches) {
            assetUrls.add(match.split('?')[0]);
        }
    }

    let created = 0;
    for (const assetUrl of assetUrls) {
        const assetPath = join(cwd, assetUrl.replace(/^\/_next\//, '.next/'));
        if (await exists(assetPath)) continue;

        const candidate = candidateForAsset(assetPath, cssFallback);
        if (!candidate || !(await exists(candidate))) continue;

        const linked = await linkAlias(assetPath, candidate);
        if (linked) created += 1;
    }

    if (created > 0) {
        console.error(`[build] materialized ${created} static asset aliases`);
    }
}

await main();
