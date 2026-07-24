"use client";

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
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
      // H-11 (cierre 2026-07-24): catch unknown — toasting was already
      // swallowed upstream (I-05); preserve the empty-state UX while
      // keeping the typed error path for future telemetry.
      console.warn("Enrollments fetch warning:", err instanceof Error ? err.message : err);
      setError(null); // Force empty state instead of red error text for UX
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
