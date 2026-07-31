// Accessibility helpers for keyboard-activatable non-button elements
// (div/table-row "role=button" patterns). Unifies the inline
// `onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') {...} }}`
// idiom repeated across CRM views.

const ACTIVATE_KEYS = new Set(['Enter', ' ']);

/**
 * Returns a `onKeyDown` handler that fires `handler` when the user presses
 * Enter or Space — the two keys WAI-ARIA prescribes for activating a
 * widget with `role="button"`. `preventDefault` is called so Space never
 * scrolls the page and Enter never submits a form ancestor.
 *
 * Usage:
 *   <div role="button" tabIndex={0} onKeyDown={onActivateKey(() => open(item))}>
 */
export function onActivateKey(
    handler: () => void,
): (e: React.KeyboardEvent) => void {
    return (e: React.KeyboardEvent) => {
        if (ACTIVATE_KEYS.has(e.key)) {
            e.preventDefault();
            handler();
        }
    };
}
