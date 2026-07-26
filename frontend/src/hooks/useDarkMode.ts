'use client';

import { useSyncExternalStore } from 'react';

/**
 * Subscribe to changes of the `dark` class on <html>.
 * Works with both platform (ThemeContext) and public (FaroThemeProvider) theme providers,
 * since both add/remove the `dark` class on document.documentElement.
 */
function subscribe(callback: () => void): () => void {
  const observer = new MutationObserver(callback);
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  return () => observer.disconnect();
}

function getServerSnapshot(): boolean {
  return false;
}

function getSnapshot(): boolean {
  const root = document.documentElement;
  return (
    root.classList.contains('dark') ||
    root.getAttribute('data-theme') === 'night'
  );
}

/**
 * Returns true when the application is currently in dark mode.
 * Uses a single MutationObserver subscription, avoiding the duplicated observers
 * previously created by every AgGrid table instance.
 */
export function useDarkMode(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export default useDarkMode;
