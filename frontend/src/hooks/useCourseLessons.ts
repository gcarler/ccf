"use client";

import { useEffect, useState, useMemo } from 'react';
import { apiFetch } from '@/lib/http';
import type { LessonRecord } from '@/types/academy';

interface LessonsState {
  lessonsByCourse: Record<string, LessonRecord[]>;
  loading: boolean;
  error: string | null;
}

export function useCourseLessons(courseIds: string[], token?: string | null): LessonsState {
  const [lessonsByCourse, setLessonsByCourse] = useState<Record<string, LessonRecord[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const normalizedIds = useMemo(() => courseIds.filter(Boolean), [courseIds]);

  useEffect(() => {
    if (!normalizedIds.length) {
      setLessonsByCourse({});
      return;
    }

    let cancelled = false;
    async function loadLessons() {
      setLoading(true);
      setError(null);
      try {
        const results = await Promise.all(
          normalizedIds.map(async (courseId) => {
            try {
              const lessons = await apiFetch<LessonRecord[]>(`/academy/courses/${courseId}/lessons`, {
                token,
                cache: 'no-store',
              });
              return [courseId, Array.isArray(lessons) ? lessons : []] as const;
            } catch (lessonError) {
              console.error(`Error fetching lessons for course ${courseId}`, lessonError);
              return [courseId, []] as const;
            }
          }),
        );
        if (!cancelled) {
          setLessonsByCourse((prev) => ({ ...prev, ...Object.fromEntries(results) }));
        }
      } catch (err: unknown) {
        // H-11 (cierre 2026-07-24): catch unknown. apiFetch rechaza con
        // Error o un objeto con ``detail`` (HTTP error shape del backend);
        // extraemos el mensaje de forma tipo-safe sin ``any``.
        if (!cancelled) {
          const message =
            (err && typeof err === 'object' && 'detail' in err &&
              typeof (err as { detail?: { message?: string } }).detail?.message === 'string'
              ? (err as { detail: { message: string } }).detail.message
              : undefined) ||
            (err instanceof Error ? err.message : undefined) ||
            'No pudimos cargar el contenido de los cursos';
          setError(message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadLessons();
    return () => {
      cancelled = true;
    };
    }, [normalizedIds, token]);

  return { lessonsByCourse, loading, error };
}
