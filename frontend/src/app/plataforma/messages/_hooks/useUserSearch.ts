"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
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

export function useUserSearch({ token, debounceMs = 200, minLength = 1 }: UseUserSearchOptions) {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState<SearchedUser[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const debouncedQuery = useDebounce(query, debounceMs);
    const inFlightRef = useRef<AbortController | null>(null);

    const search = useCallback(async () => {
        if (!token || debouncedQuery.trim().length < minLength) {
            inFlightRef.current?.abort();
            inFlightRef.current = null;
            setResults([]);
            setError(null);
            setLoading(false);
            return;
        }
        // A-10: each search aborts the previous in-flight request so a slow
        // earlier response can never clobber newer results.
        inFlightRef.current?.abort();
        const controller = new AbortController();
        inFlightRef.current = controller;
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
            if (controller.signal.aborted) return;
            if (inFlightRef.current === controller) inFlightRef.current = null;
            setLoading(false);
        }
    }, [token, debouncedQuery, minLength]);

    useEffect(() => {
        search();
    }, [search]);

    useEffect(() => {
        return () => {
            inFlightRef.current?.abort();
            inFlightRef.current = null;
        };
    }, []);

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
