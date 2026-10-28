import assert from 'node:assert/strict';
import test from 'node:test';
import { planPlaywrightPhases, runPlaywrightPhases } from './managed-playwright-phases.mjs';

const focused = ['--grep-invert', '@auth', 'tests/e2e/projects/gantt-readonly.spec.ts'];

test('default behavior runs only the requested tests', () => {
  assert.deepEqual(planPlaywrightPhases(focused, false), [{ name: 'test', args: focused }]);
});

test('opt-in full phase removes focused file filters and preserves the auth exclusion', () => {
  assert.deepEqual(planPlaywrightPhases(focused, true), [
    { name: 'focused', args: focused },
    { name: 'full', args: ['--grep-invert', '@auth', '--workers', '1'] },
  ]);
});

test('invalid focused-to-full requests fail before provisioning a build or server', () => {
  assert.throws(() => planPlaywrightPhases(['--grep-invert', '@auth'], true));
  assert.throws(() => planPlaywrightPhases(['tests/e2e/projects/gantt-readonly.spec.ts'], true));
});

test('a failing or interrupted focused phase never runs the full suite', () => {
  for (const result of [{ status: 7 }, { status: null }]) {
    let calls = 0;
    const status = runPlaywrightPhases(planPlaywrightPhases(focused, true), 'npx', {}, () => { calls++; return result; }, () => {});
    assert.equal(calls, 1);
    assert.equal(status, result.status ?? 1);
  }
});

test('process startup errors fail closed', () => {
  assert.throws(() => runPlaywrightPhases(planPlaywrightPhases(focused, true), 'npx', {}, () => ({ error: new Error('spawn failed') }), () => {}));
});

test('full suite runs only after focused success and retains its own exit code and environment', () => {
  const env = { NEXT_DIST_DIR: '.next-playwright-test', API_BASE_URL: 'http://127.0.0.1:8001/api' };
  const calls = [];
  const status = runPlaywrightPhases(planPlaywrightPhases(focused, true), 'npx', env, (...args) => {
    calls.push(args);
    return { status: calls.length === 1 ? 0 : 4 };
  }, () => {});
  assert.equal(calls.length, 2);
  assert.equal(calls[0][2].env, env);
  assert.equal(calls[1][2].env, env);
  assert.equal(status, 4);
});
