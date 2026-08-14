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
  baseUpdatedAt?: string;
  onConflict?: (serverUpdatedAt: string) => void;
  debounceMs?: number;
}

interface UseWhiteboardSaveReturn {
  saveStatus: SaveStatus;
  /** True while there are edits that have not been persisted successfully. */
  isDirty: boolean;
  save: (canvas: Canvas, immediate?: boolean) => void;
  saveNow: (canvas: Canvas) => void;
  /** Flushes any unsaved state (pending debounce or queued write). Call it
   *  before the canvas is disposed (e.g. component unmount) so the last edit
   *  is not lost inside the debounce window. Safe no-op when nothing is
   *  pending. */
  flushPending: () => void;
}

export function useWhiteboardSave(
  options: UseWhiteboardSaveOptions
): UseWhiteboardSaveReturn {
  const { projectId, token, title = "Pizarra Estrategica", debounceMs = 1000, baseUpdatedAt, onConflict } =
    options;

  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const statusResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Set when the consumer unmounts (closing the whiteboard tab). Used by
  // ``persistToApi`` to avoid setState-after-unmount warnings if a save lands
  // while the panel is being torn down.
  const canceledRef = useRef<boolean>(false);
  // Whether a POST is currently in flight and which canvas it serialized.
  // Writes are serialized (chained) so rapid saves cannot arrive out of order
  // and overwrite newer state with older state on the server (last-writer-wins
  // only holds if the *newest* request lands last).
  const inFlightRef = useRef<boolean>(false);
  const inFlightCanvasRef = useRef<Canvas | null>(null);
  // The most recent canvas handed to ``save`` — what a flush must persist.
  const latestCanvasRef = useRef<Canvas | null>(null);
  const persistRef = useRef<(canvas: Canvas) => void>(() => {});
  // Use a ref for the title so callers can change it without causing the
  // returned ``save``/``saveNow`` callbacks to be recreated. This keeps the
  // canvas initialization effect in ``WhiteboardEditor`` stable.
  const titleRef = useRef(title);
  useEffect(() => {
    titleRef.current = title;
  }, [title]);

  const baseUpdatedAtRef = useRef(baseUpdatedAt);
  useEffect(() => {
    baseUpdatedAtRef.current = baseUpdatedAt;
  }, [baseUpdatedAt]);

  const onConflictRef = useRef(onConflict);
  useEffect(() => {
    onConflictRef.current = onConflict;
  }, [onConflict]);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const [isDirty, setIsDirty] = useState(false);

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

  const doPersist = useCallback(
    async (canvas: Canvas) => {
      if (!projectId || !token || canceledRef.current) return;

      setSaveStatus("saving");
      if (statusResetTimerRef.current) {
        clearTimeout(statusResetTimerRef.current);
        statusResetTimerRef.current = null;
      }

      let retries = 3;
      let lastErr: any;
      while (retries > 0) {
        try {
          await apiFetch(`/projects/${projectId}/whiteboard`, {
            method: "POST",
            token,
            body: {
              title: titleRef.current,
              elements_json: JSON.stringify(canvas.toJSON()),
              ...(baseUpdatedAtRef.current ? { base_updated_at: baseUpdatedAtRef.current } : {}),
            },
          });
          if (canceledRef.current) return;
          setIsDirty(false);
          setSaveStatus("saved");
          statusResetTimerRef.current = setTimeout(() => {
            if (canceledRef.current) return;
            setSaveStatus("idle");
            statusResetTimerRef.current = null;
          }, 2000);
          return;
        } catch (err: any) {
          lastErr = err;
          // Don't retry on 409 conflict
          if (err.status === 409 || err.response?.status === 409) {
              break;
          }
          // Retry on network errors
          retries--;
          if (retries > 0) {
              await new Promise((resolve) => setTimeout(resolve, 2000));
          }
        }
      }

      // If we reach here, it means we failed after retries or hit a 409
      const err = lastErr;
      if (err?.status === 409 || err?.response?.status === 409) {
          // PZ-07 Conflict
          const serverUpdatedAt = err.response?.data?.detail?.current_updated_at || err.data?.detail?.current_updated_at;
          if (onConflictRef.current && serverUpdatedAt) {
            onConflictRef.current(serverUpdatedAt);
          }
      }

        // Suppress error feedback while the panel is being torn down or the
        // tab is hidden (requests may be throttled/aborted by the browser).
        if (canceledRef.current) return;
        if (typeof document !== "undefined" && document.visibilityState === "hidden") return;
        setSaveStatus("error");
        statusResetTimerRef.current = setTimeout(() => {
          if (canceledRef.current) return;
          setSaveStatus("idle");
          statusResetTimerRef.current = null;
        }, 3000);
    },
    [projectId, token]
  );

  const persistToApi = useCallback(
    (canvas: Canvas) => {
      if (!projectId || !token) return;

      if (inFlightRef.current) {
        // A write is already in flight — queue the newest state so it is
        // persisted after the current request resolves (ordered writes).
        latestCanvasRef.current = canvas;
        return;
      }

      inFlightRef.current = true;
      inFlightCanvasRef.current = canvas;
      doPersist(canvas).finally(() => {
        inFlightRef.current = false;
        inFlightCanvasRef.current = null;
        const next = latestCanvasRef.current;
        if (next && next !== canvas) persistRef.current(next);
      });
    },
    [doPersist, projectId, token]
  );

  persistRef.current = persistToApi;

  const save = useCallback(
    (canvas: Canvas, immediate = false) => {
      if (!projectId || !token) {
        clearTimers();
        setSaveStatus("idle");
        return;
      }

      latestCanvasRef.current = canvas;
      setIsDirty(true);
      clearTimers();

      if (immediate) {
        persistToApi(canvas);
        return;
      }

      setSaveStatus("saving");
      saveTimerRef.current = setTimeout(() => {
        saveTimerRef.current = null;
        persistToApi(latestCanvasRef.current ?? canvas);
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

  const flushPending = useCallback(() => {
    const hasPendingTimer = saveTimerRef.current !== null;
    const needsResend =
      inFlightRef.current && latestCanvasRef.current !== inFlightCanvasRef.current;
    if (!hasPendingTimer && !needsResend) return;

    const canvas = latestCanvasRef.current;
    if (!canvas) return;

    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
      saveTimerRef.current = null;
    }
    persistToApi(canvas);
  }, [persistToApi]);

  useEffect(() => {
    return () => {
      canceledRef.current = true;
      clearTimers();
    };
  }, [clearTimers]);

  return {
    saveStatus,
    isDirty,
    save,
    saveNow,
    flushPending,
  };
}
