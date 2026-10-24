'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  CSSProperties,
  KeyboardEvent,
  PointerEvent,
  RefObject,
} from 'react';

interface Options {
  storageKey: string;
  defaultWidth: number;
  minWidth?: number;
  reservedWidth?: number;
  constrainToParent?: boolean;
  panelRef: RefObject<HTMLElement | null>;
  enabled?: boolean;
}

/** Persistent desktop panel width; mobile always uses the available width. */
export function useResizablePanel({
  storageKey,
  defaultWidth,
  minWidth = 300,
  reservedWidth = 48,
  constrainToParent = false,
  panelRef,
  enabled = true,
}: Options) {
  const [preferredWidth, setPreferredWidth] = useState(defaultWidth);
  const [bounds, setBounds] = useState({ desktop: false, max: defaultWidth });
  const [dragging, setDragging] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);
  const widthRef = useRef(defaultWidth);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      const saved = raw === null ? NaN : Number(raw);
      if (Number.isFinite(saved) && saved >= minWidth) setPreferredWidth(saved);
    } catch {
      /* Storage may be unavailable in private sessions. */
    }
  }, [storageKey, minWidth]);

  useEffect(() => {
    const measure = () => {
      const available = constrainToParent
        ? panelRef.current?.parentElement?.clientWidth || window.innerWidth
        : window.innerWidth;
      setBounds({
        desktop: window.innerWidth >= 1024,
        max: Math.max(minWidth, available - reservedWidth),
      });
    };
    measure();
    window.addEventListener('resize', measure);
    const observer =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(measure)
        : null;
    if (panelRef.current?.parentElement)
      observer?.observe(panelRef.current.parentElement);
    return () => {
      window.removeEventListener('resize', measure);
      observer?.disconnect();
    };
  }, [constrainToParent, minWidth, panelRef, reservedWidth, enabled]);

  const clamp = useCallback(
    (value: number) => Math.max(minWidth, Math.min(value, bounds.max)),
    [minWidth, bounds.max]
  );
  const width = clamp(preferredWidth);
  widthRef.current = width;
  const save = useCallback(
    (value: number) => {
      try {
        localStorage.setItem(storageKey, String(value));
      } catch {
        /* Keep resizing usable without storage. */
      }
    },
    [storageKey]
  );

  useEffect(() => () => stopRef.current?.(), []);
  useEffect(() => {
    if (!enabled || !bounds.desktop) stopRef.current?.();
  }, [enabled, bounds.desktop]);

  const onPointerDown = useCallback(
    (event: PointerEvent<HTMLElement>) => {
      if (event.button !== 0 || !enabled || !bounds.desktop) return;
      event.preventDefault();
      stopRef.current?.();
      const startX = event.clientX;
      const startWidth = widthRef.current;
      const cursor = document.body.style.cursor;
      const selection = document.body.style.userSelect;
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      setDragging(true);
      const move = (next: globalThis.PointerEvent) => {
        const value = clamp(startWidth + startX - next.clientX);
        widthRef.current = value;
        setPreferredWidth(value);
      };
      const stop = () => {
        save(widthRef.current);
        setDragging(false);
        document.body.style.cursor = cursor;
        document.body.style.userSelect = selection;
        window.removeEventListener('pointermove', move);
        window.removeEventListener('pointerup', stop);
        window.removeEventListener('pointercancel', stop);
        window.removeEventListener('blur', stop);
        stopRef.current = null;
      };
      stopRef.current = stop;
      window.addEventListener('pointermove', move);
      window.addEventListener('pointerup', stop);
      window.addEventListener('pointercancel', stop);
      window.addEventListener('blur', stop);
    },
    [bounds.desktop, clamp, enabled, save]
  );

  const reset = useCallback(() => {
    const value = clamp(defaultWidth);
    setPreferredWidth(value);
    save(value);
  }, [clamp, defaultWidth, save]);
  const onKeyDown = useCallback(
    (event: KeyboardEvent<HTMLElement>) => {
      const step = event.shiftKey ? 80 : 24;
      const next =
        event.key === 'ArrowLeft'
          ? width + step
          : event.key === 'ArrowRight'
            ? width - step
            : event.key === 'Home'
              ? minWidth
              : event.key === 'End'
                ? bounds.max
                : null;
      if (next === null) return;
      event.preventDefault();
      const value = clamp(next);
      setPreferredWidth(value);
      save(value);
    },
    [bounds.max, clamp, minWidth, save, width]
  );

  const style: CSSProperties | undefined = enabled
    ? { width: bounds.desktop ? width : '100%', maxWidth: '100vw', minWidth: 0 }
    : undefined;
  return {
    style,
    width,
    minWidth,
    maxWidth: bounds.max,
    desktop: bounds.desktop,
    dragging,
    onPointerDown,
    onKeyDown,
    reset,
  };
}
