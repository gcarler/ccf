"use client";

import { useCallback, useEffect, useState } from 'react';
import { apiFetch } from '@/lib/http';
import { useDebounce } from '@/hooks/useDebounce';

export interface SearchedUser {
    id: string;
    username: string;
    email: string;
    avatar_url: string | null;
}

interface UseUserSearchOptions {
    token: string | null;
    debounceMs?: number;
    minLength?: number;
}

export function useUserSearch({ token, debounceMs = 300, minLength = 2 }: UseUserSearchOptions) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchedUser[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const debouncedQuery = useDebounce(query, debounceMs);

    const search = useCallback(async () => {
        if (!token || debouncedQuery.trim().length < minLength) {
            setResults([]);
            setError(null);
            return;
        }
        // A-10: per-search AbortController cancels overlapping requests so
        // a slow earlier response can't clobber newer results.
        const controller = new AbortController();
        setLoading(true);
        setError(null);
        try {
            const data = await apiFetch<SearchedUser[]>(
                `/chat/users/search?q=${encodeURIComponent(debouncedQuery.trim())}`,
                { token, signal: controller.signal }
            );
            if (controller.signal.aborted) return;
            const list = Array.isArray(data) ? data : [];
            setResults(list);
            if (list.length === 0) setError('No se encontraron usuarios');
        } catch {
            if (controller.signal.aborted) return;
            setError('Error al buscar usuarios');
            setResults([]);
        } finally {
            if (!controller.signal.aborted) setLoading(false);
        }
    }, [token, debouncedQuery, minLength]);

    useEffect(() => {
        search();
    }, [search]);

    return {
        query,
        setQuery,
        results,
        loading,
        error,
        setError,
        reset: useCallback(() => {
            setQuery('');
            setResults([]);
            setError(null);
        }, []),
    };
}
