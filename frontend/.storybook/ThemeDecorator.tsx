import React, { useEffect, useRef } from 'react';
import type { Decorator } from '@storybook/react-webpack5';

/**
 * Storybook decorator that syncs the CCF theme with the Storybook toolbar.
 *
 * Why mutate `document.documentElement`?
 * The platform's `useDarkMode` hook subscribes to `<html>` class/attribute
 * changes, and AG Grid's theme is derived from it. Wrapping the story in a
 * local `<div data-theme="..." />` would not be detected by that hook, so we
 * must update the document root.
 */
export const ThemeDecorator: Decorator = (Story, context) => {
  const theme = (context.globals.theme as 'day' | 'night') ?? 'day';
  const previousThemeRef = useRef(theme);

  useEffect(() => {
    const root = document.documentElement;
    const previousTheme = previousThemeRef.current;
    previousThemeRef.current = theme;

    root.setAttribute('data-theme', theme);
    if (theme === 'night') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    return () => {
      // Restore the previous theme when the decorator unmounts so a later
      // story with a different default does not inherit stale state.
      root.setAttribute('data-theme', previousTheme);
      if (previousTheme === 'night') {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    };
  }, [theme]);

  return (
    <div
      style={{
        minHeight: '100vh',
        padding: '1rem',
        backgroundColor: 'hsl(var(--bg-primary))',
      }}
    >
      <Story />
    </div>
  );
};
