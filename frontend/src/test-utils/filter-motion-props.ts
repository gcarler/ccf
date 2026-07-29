/**
 * Strip framer-motion specific props so that the mocked `motion.*` components
 * do not leak invalid DOM attributes (e.g. `initial`, `animate`, `layoutId`).
 *
 * Use this in tests that mock `framer-motion` with plain HTML elements.
 */
export function filterMotionProps(props: Record<string, unknown>): Record<string, unknown> {
  const skip = new Set([
    'initial',
    'animate',
    'exit',
    'transition',
    'whileHover',
    'whileTap',
    'whileFocus',
    'whileDrag',
    'layout',
    'layoutId',
    'layoutDependency',
  ]);
  const out: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(props)) {
    if (!skip.has(key)) {
      out[key] = value;
    }
  }
  return out;
}
