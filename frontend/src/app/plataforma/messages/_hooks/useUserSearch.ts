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
        setLoading(true);
        setError(null);
        try {
            const data = await apiFetch<SearchedUser[]>(
                `/chat/users/search?q=${encodeURIComponent(debouncedQuery.trim())}`,
                { token }
            );
            const list = Array.isArray(data) ? data : [];
            setResults(list);
            if (list.length === 0) setError('No se encontraron usuarios');
        } catch {
            setError('Error al buscar usuarios');
            setResults([]);
        } finally {
            setLoading(false);
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
