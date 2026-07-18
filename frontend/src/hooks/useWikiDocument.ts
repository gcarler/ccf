"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { ApiError, apiFetch } from '@/lib/http';

interface WikiDocument {
    title: string;
    content: string;
}

interface UseWikiDocumentOptions {
    title?: string;
}

function normalizeWikiContent(value: string | null | undefined) {
    if (!value || value === '{}') return '';
    return value;
}

export function useWikiDocument(pageKey: string, options: UseWikiDocumentOptions = {}) {
    const { token } = useAuth();
    const [content, setContent] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [lastSaved, setLastSaved] = useState<Date | null>(null);
    const [error, setError] = useState<string | null>(null);
    const hydratedRef = useRef(false);
    const contentRef = useRef(content);
    const documentExistsRef = useRef(false);

    useEffect(() => {
        contentRef.current = content;
    }, [content]);

    useEffect(() => {
        let alive = true;
        hydratedRef.current = false;
        documentExistsRef.current = false;
        setIsLoading(true);
        setError(null);

        const localValue = typeof window !== 'undefined'
            ? localStorage.getItem(pageKey)
            : null;

        if (localValue) setContent(localValue);

        const load = async () => {
            if (!token) {
                hydratedRef.current = true;
                if (alive) setIsLoading(false);
                return;
            }

            try {
                const document = await apiFetch<WikiDocument>(`/wiki/pages/${pageKey}`, {
                    token,
                    cache: 'no-store',
                });
                documentExistsRef.current = true;
                if (!alive) return;
                const serverContent = normalizeWikiContent(document.content);
                if (serverContent) {
                    setContent(serverContent);
                    localStorage.setItem(pageKey, serverContent);
                }
            } catch (err) {
                if (err instanceof ApiError && err.status === 404) {
                    documentExistsRef.current = false;
                } else {
                    console.error(err);
                    if (alive) setError('No se pudo cargar la wiki compartida.');
                }
            } finally {
                hydratedRef.current = true;
                if (alive) setIsLoading(false);
            }
        };

        load();
        return () => {
            alive = false;
        };
    }, [options.title, pageKey, token]);

    const persist = useCallback(async (nextContent: string) => {
        if (typeof window !== 'undefined') {
            localStorage.setItem(pageKey, nextContent);
        }

        if (!token) {
            setLastSaved(new Date());
            return;
        }

        setIsSaving(true);
        setError(null);
        try {
            const payload = {
                title: options.title || pageKey,
                content: nextContent,
            };

            if (!documentExistsRef.current) {
                try {
                    await apiFetch(`/wiki/pages/${pageKey}`, {
                        method: 'POST',
                        token,
                        body: payload,
                    });
                    documentExistsRef.current = true;
                } catch (err) {
                    if (!(err instanceof ApiError) || err.status !== 409) {
                        throw err;
                    }

                    await apiFetch(`/wiki/pages/${pageKey}`, {
                        method: 'PATCH',
                        token,
                        body: payload,
                    });
                    documentExistsRef.current = true;
                }
            } else {
                try {
                    await apiFetch(`/wiki/pages/${pageKey}`, {
                        method: 'PATCH',
                        token,
                        body: payload,
                    });
                } catch (err) {
                    if (!(err instanceof ApiError) || err.status !== 404) {
                        throw err;
                    }

                    await apiFetch(`/wiki/pages/${pageKey}`, {
                        method: 'POST',
                        token,
                        body: payload,
                    });
                    documentExistsRef.current = true;
                }
            }
            setLastSaved(new Date());
        } catch (err) {
            console.error(err);
            setError('No se pudo guardar la wiki compartida.');
        } finally {
            setIsSaving(false);
        }
    }, [options.title, pageKey, token]);

    useEffect(() => {
        if (!hydratedRef.current) return;
        const timer = setTimeout(() => {
            void persist(contentRef.current);
        }, 700);
        return () => clearTimeout(timer);
    }, [content, persist]);

    const saveNow = useCallback(async () => {
        await persist(contentRef.current);
    }, [persist]);

    return {
        content,
        setContent,
        isLoading,
        isSaving,
        lastSaved,
        error,
        saveNow,
    };
}
