"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { apiFetch } from '@/lib/http';
import { useDebounce } from '@/hooks/useDebounce';
import { filtroAPersona, type PersonaBusqueda } from '@/lib/filtroAPersonas';

export interface SearchedUser {
    id: string;
    // username REAL de la cuenta (auth_users): la mención inserta @username.
    username: string;
    // Nombre completo de la persona, para mostrar.
    name?: string;
    email: string;
    avatar_url: string | null;
    church_role?: string | null;
}

/** Mapea un usuario buscado a la forma que entiende filtroAPersona. */
function toPersonaBusqueda(user: SearchedUser): PersonaBusqueda {
    return {
        id: user.id,
        username: user.username,
        // El endpoint puede devolver cuentas sin nombre de persona. En ese
        // caso el username es el único identificador textual disponible y
        // debe seguir siendo buscable sin el prefijo de mención.
        nombre_completo: user.name ?? user.username,
        email: user.email,
    };
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
            // El server no entiende el '@' (estilo mención); se lo quitamos
            // antes de enviar y la semántica de username la aplica el filtro.
            const searchTerm = debouncedQuery.trim().replace(/^@+/, '');
            const data = await apiFetch<SearchedUser[]>(
                `/chat/users/search?q=${encodeURIComponent(searchTerm)}`,
                { token, signal: controller.signal }
            );
            if (controller.signal.aborted) return;
            const list = Array.isArray(data) ? data : [];
            // Filtro reutilizable de personas: '@' → username; sin '@' → nombre/email.
            const filtered = list.filter((u) => filtroAPersona(toPersonaBusqueda(u), debouncedQuery));
            setResults(filtered);
            if (filtered.length === 0) setError('No se encontraron usuarios');
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
