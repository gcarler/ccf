"use client";

import { useRef, useState, useCallback } from "react";
import { useEffect } from "react";
import type { Canvas } from "fabric";
import { apiFetch } from "@/lib/http";

type SaveStatus = "idle" | "saving" | "saved" | "error";

interface UseWhiteboardSaveOptions {
  projectId: string;
  token: string | null;
  title?: string;
  debounceMs?: number;
}

interface UseWhiteboardSaveReturn {
  saveStatus: SaveStatus;
  save: (canvas: Canvas, immediate?: boolean) => void;
  saveNow: (canvas: Canvas) => void;
}

export function useWhiteboardSave(
  options: UseWhiteboardSaveOptions
): UseWhiteboardSaveReturn {
  const { projectId, token, title = "Pizarra Estrategica", debounceMs = 1000 } =
    options;

  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Set when the consumer unmounts (closing the whiteboard tab). Used by
  // ``persistToApi`` to avoid setState-after-unmount warnings if a save lands
  // while the panel is being torn down.
  const canceledRef = useRef<boolean>(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");

  const clearTimers = useCallback(() => {
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    if (statusResetTimerRef.current) {
      clearTimeout(statusResetTimerRef.current);
      statusResetTimerRef.current = null;
    }
  }, []);

  const persistToApi = useCallback(
    async (canvas: Canvas) => {
      if (!projectId || !token) return;

      setSaveStatus("saving");
      if (statusResetTimerRef.current) {
        clearTimeout(statusResetTimerRef.current);
        statusResetTimerRef.current = null;
      }

      try {
        await apiFetch(`/projects/${projectId}/whiteboard`, {
          method: "POST",
          token,
          body: {
            title,
            elements_json: JSON.stringify(canvas.toJSON()),
          },
        });
        if (canceledRef.current) return;
        setSaveStatus("saved");
        statusResetTimerRef.current = setTimeout(() => {
          if (canceledRef.current) return;
          setSaveStatus("idle");
          statusResetTimerRef.current = null;
        }, 2000);
      } catch {
        if (canceledRef.current) return;
        setSaveStatus("error");
        statusResetTimerRef.current = setTimeout(() => {
          if (canceledRef.current) return;
          setSaveStatus("idle");
          statusResetTimerRef.current = null;
        }, 3000);
      }
    },
    [projectId, token, title]
  );

  const save = useCallback(
    (canvas: Canvas, immediate = false) => {
      if (!projectId || !token) {
        clearTimers();
        setSaveStatus("idle");
        return;
      }

      clearTimers();

      if (immediate) {
        persistToApi(canvas);
        return;
      }

      setSaveStatus("saving");
      saveTimerRef.current = setTimeout(() => {
        persistToApi(canvas);
      }, debounceMs);
    },
    [projectId, token, persistToApi, debounceMs, clearTimers]
  );

  const saveNow = useCallback(
    (canvas: Canvas) => {
      save(canvas, true);
    },
    [save]
  );

  useEffect(() => {
    return () => {
      canceledRef.current = true;
      clearTimers();
    };
  }, [clearTimers]);

  return {
    saveStatus,
    save,
    saveNow,
  };
}
