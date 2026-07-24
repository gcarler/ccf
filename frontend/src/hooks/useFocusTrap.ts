'use client';

import { useEffect, useRef } from 'react';

const FOCUSABLE_SELECTORS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

interface UseFocusTrapOptions {
  active: boolean;
  onEscape?: () => void;
  lockBodyScroll?: boolean;
}

/**
 * Traps focus inside a container while it is active.
 * - Moves focus to the first focusable element when activated.
 * - Cycles focus with Tab / Shift+Tab.
 * - Calls `onEscape` when Escape is pressed.
 * - Restores focus to the previously focused element when deactivated.
 * - Optionally locks body scroll while active.
 */
export function useFocusTrap<T extends HTMLElement>(
  containerRef: React.RefObject<T | null>,
  { active, onEscape, lockBodyScroll = false }: UseFocusTrapOptions
) {
  const triggerRef = useRef<HTMLElement | null>(null);
  const wasActiveRef = useRef(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const container = containerRef.current;

      if (e.key === 'Escape') {
        e.preventDefault();
        onEscape?.();
        return;
      }

      if (e.key !== 'Tab' || !container) return;

      const focusable = Array.from(
        container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)
      ).filter((el) => el.offsetParent !== null);

      if (focusable.length === 0) {
        e.preventDefault();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const activeElement = document.activeElement as HTMLElement | null;

      if (e.shiftKey) {
        if (activeElement === first || !container.contains(activeElement)) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (activeElement === last || !container.contains(activeElement)) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    if (active) {
      triggerRef.current = document.activeElement as HTMLElement | null;
      document.addEventListener('keydown', handleKeyDown);

      if (lockBodyScroll) {
        document.body.style.overflow = 'hidden';
      }

      // Move focus to the first focusable element inside the container
      const container = containerRef.current;
      if (container) {
        const focusable = Array.from(
          container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS)
        ).filter((el) => el.offsetParent !== null);
        focusable[0]?.focus();
      }
    }

    wasActiveRef.current = active;

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (active && lockBodyScroll) {
        document.body.style.overflow = '';
      }
    };
  }, [active, onEscape, lockBodyScroll, containerRef]);

  // Restore focus to the trigger when the trap deactivates
  useEffect(() => {
    if (!active && wasActiveRef.current) {
      triggerRef.current?.focus();
      wasActiveRef.current = false;
    }
  }, [active]);
}
