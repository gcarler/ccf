"use client";

import { useRef, useState, useCallback } from "react";
import type { Canvas } from "fabric";

interface UseWhiteboardHistoryOptions {
  maxStates?: number;
}

interface UseWhiteboardHistoryReturn {
  canUndo: boolean;
  canRedo: boolean;
  undo: (canvas: Canvas) => void;
  redo: (canvas: Canvas) => void;
  pushHistory: (canvas: Canvas) => void;
  clearHistory: () => void;
  restoringRef: React.MutableRefObject<boolean>;
}

export function useWhiteboardHistory(
  options: UseWhiteboardHistoryOptions = {}
): UseWhiteboardHistoryReturn {
  const { maxStates = 50 } = options;

  const historyRef = useRef<string[]>([]);
  const historyIndexRef = useRef(-1);
  const restoringRef = useRef(false);

  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const updateStates = useCallback(() => {
    setCanUndo(historyIndexRef.current > 0);
    setCanRedo(historyIndexRef.current < historyRef.current.length - 1);
  }, []);

  const pushHistory = useCallback(
    (canvas: Canvas) => {
      if (restoringRef.current) return;

      const json = JSON.stringify(canvas.toJSON());
      const idx = historyIndexRef.current;

      // Truncate any redo states beyond current index
      historyRef.current = historyRef.current.slice(0, idx + 1);
      historyRef.current.push(json);

      // Keep max states
      if (historyRef.current.length > maxStates) {
        historyRef.current.shift();
      }

      historyIndexRef.current = historyRef.current.length - 1;
      updateStates();
    },
    [maxStates, updateStates]
  );

  const undo = useCallback(
    (canvas: Canvas) => {
      if (!canvas || historyIndexRef.current <= 0) return;

      const previousIndex = historyIndexRef.current;
      const targetIndex = previousIndex - 1;
      historyIndexRef.current = targetIndex;
      restoringRef.current = true;

      canvas
        .loadFromJSON(JSON.parse(historyRef.current[targetIndex]))
        .then(() => {
          canvas.renderAll();
          updateStates();
        })
        .catch(() => {
          historyIndexRef.current = previousIndex;
          updateStates();
        })
        .finally(() => {
          restoringRef.current = false;
        });
    },
    [updateStates]
  );

  const redo = useCallback(
    (canvas: Canvas) => {
      if (!canvas || historyIndexRef.current >= historyRef.current.length - 1)
        return;

      const previousIndex = historyIndexRef.current;
      const targetIndex = previousIndex + 1;
      historyIndexRef.current = targetIndex;
      restoringRef.current = true;

      canvas
        .loadFromJSON(JSON.parse(historyRef.current[targetIndex]))
        .then(() => {
          canvas.renderAll();
          updateStates();
        })
        .catch(() => {
          historyIndexRef.current = previousIndex;
          updateStates();
        })
        .finally(() => {
          restoringRef.current = false;
        });
    },
    [updateStates]
  );

  const clearHistory = useCallback(() => {
    historyRef.current = [];
    historyIndexRef.current = -1;
    updateStates();
  }, [updateStates]);

  return {
    canUndo,
    canRedo,
    undo,
    redo,
    pushHistory,
    clearHistory,
    restoringRef,
  };
}
