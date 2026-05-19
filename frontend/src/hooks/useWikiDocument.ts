"use client";

import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

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

    useEffect(() => {
        contentRef.current = content;
    }, [content]);

    useEffect(() => {
        let alive = true;
        hydratedRef.current = false;
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
                const document = await apiFetch<WikiDocument>(`/content/${pageKey}`, {
                    token,
                    cache: 'no-store',
                });
                if (!alive) return;
                const serverContent = normalizeWikiContent(document.content);
                if (serverContent) {
                    setContent(serverContent);
                    localStorage.setItem(pageKey, serverContent);
                } else if (localValue) {
                    await apiFetch(`/content/${pageKey}`, {
                        method: 'POST',
                        token,
                        body: {
                            title: options.title,
                            content: localValue,
                        },
                    });
                    setLastSaved(new Date());
                }
            } catch (err) {
                console.error(err);
                if (alive) setError('No se pudo cargar la wiki compartida.');
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
            await apiFetch(`/content/${pageKey}`, {
                method: 'POST',
                token,
                body: {
                    title: options.title,
                    content: nextContent,
                },
            });
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
