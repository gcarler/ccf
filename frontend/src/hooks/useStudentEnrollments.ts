"use client";

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import type { EnrollmentRecord } from '@/types/academy';

interface UseEnrollmentsResult {
  enrollments: EnrollmentRecord[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useStudentEnrollments(): UseEnrollmentsResult {
  const { user, token, isAuthenticated } = useAuth();
  const [enrollments, setEnrollments] = useState<EnrollmentRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEnrollments = useCallback(async () => {
    if (!user || !token || !isAuthenticated) {
      setEnrollments([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<EnrollmentRecord[]>('/academy/me/enrollments', {
        token,
        cache: 'no-store',
      });
      setEnrollments(Array.isArray(data) ? data : []);
    } catch (err: unknown) {
      // I-05 (cierre 2026-07-24): antes el error se silenciaba sin feedback.
      // Ahora se hace toast al usuario (UX), se conserva el empty-state y se
      // mantiene el catch ``unknown`` tipo-safe (H-11).
      let message = 'No pudimos cargar tus inscripciones';
      if (err instanceof Error && err.message) {
        message = err.message;
      } else if (
        err && typeof err === 'object' &&
        'detail' in err &&
        typeof (err as { detail?: unknown }).detail === 'string'
      ) {
        message = (err as { detail: string }).detail;
      }
      console.warn("Enrollments fetch warning:", err instanceof Error ? err.message : err);
      toast.error(message);
      setError(message);
      setEnrollments([]);
    } finally {
      setLoading(false);
    }
  }, [user, token, isAuthenticated]);

  useEffect(() => {
    fetchEnrollments();
  }, [fetchEnrollments]);

  return { enrollments, loading, error, refresh: fetchEnrollments };
}
