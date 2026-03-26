"use client";

import { useEffect, useState, useMemo } from 'react';
import { apiFetch } from '@/lib/http';
import type { LessonRecord } from '@/types/academy';

interface LessonsState {
  lessonsByCourse: Record<number, LessonRecord[]>;
  loading: boolean;
  error: string | null;
}

export function useCourseLessons(courseIds: number[], token?: string | null): LessonsState {
  const [lessonsByCourse, setLessonsByCourse] = useState<Record<number, LessonRecord[]>>({});
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
              const lessons = await apiFetch<LessonRecord[]>(`/courses/${courseId}/lessons`, {
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
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.detail?.message || 'No pudimos cargar el contenido de los cursos');
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
