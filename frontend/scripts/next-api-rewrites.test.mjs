import assert from 'node:assert/strict';
import test from 'node:test';
import pathMatch from 'next/dist/shared/lib/router/utils/path-match.js';

process.env.API_PROXY_TARGET = 'http://127.0.0.1:18000';
const { default: config } = await import('../next.config.mjs');
const rewrites = await config.rewrites();

test('backend APIs resolve before the public dynamic page and after local static handlers', () => {
    assert.ok(Array.isArray(rewrites.afterFiles));
    assert.equal(rewrites.fallback, undefined);
    const proxy = rewrites.afterFiles[0];
    const match = pathMatch.getPathMatch(proxy.source);
    for (const pathname of ['/api/v3/auth/me', '/api/system/health', '/api/cms/v2/public/sites/ccf/theme']) {
        assert.ok(match(pathname), pathname);
    }
    assert.equal(proxy.destination, 'http://127.0.0.1:18000/api/:path*');
});

test('local dynamic API handlers retain their namespaces', () => {
    const match = pathMatch.getPathMatch(rewrites.afterFiles[0].source);
    assert.equal(match('/api/crm/resources/automation-edges/edge-1'), false);
    assert.equal(match('/api/mock/health'), false);
    assert.ok(match('/api/crm/personas'));
});
