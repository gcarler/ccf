export function planPlaywrightPhases(args, fullAfterFocused) {
  if (!fullAfterFocused) return [{ name: 'test', args }];
  if (!args.some(arg => /\.spec\.[cm]?[jt]sx?$/.test(arg))) {
    throw new Error('Focused-to-full mode requires explicit focused spec files');
  }
  if (args[args.indexOf('--grep-invert') + 1] !== '@auth' || !args.includes('--grep-invert')) {
    throw new Error('Focused-to-full mode must retain --grep-invert @auth');
  }
  return [
    { name: 'focused', args },
    { name: 'full', args: ['--grep-invert', '@auth', '--workers', '1'] },
  ];
}

export function runPlaywrightPhases(phases, executable, env, spawnSync, log = console.log) {
  for (const phase of phases) {
    log(`[e2e] Starting ${phase.name} phase`);
    const result = spawnSync(executable, ['playwright', 'test', ...phase.args], { stdio: 'inherit', env });
    if (result.error) throw result.error;
    const status = result.status ?? 1;
    log(`[e2e] Completed ${phase.name} phase: exit ${status}`);
    if (status !== 0) return status;
  }
  return 0;
}
