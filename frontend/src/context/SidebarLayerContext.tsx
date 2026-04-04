"use client";

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';

// ─────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────
export type SidebarId = 'S1' | 'S2' | 'S3' | 'RIGHT';

interface LayerState {
    S1: boolean;  // Mini sidebar (always true, anchor)
    S2: boolean;  // Module nav sidebar
    S3: boolean;  // Context panel (project detail, member profile…)
    RIGHT: boolean; // Right info panel
}

interface SidebarLayerContextType {
    layers: LayerState;
    openLayer: (id: SidebarId) => void;
    closeLayer: (id: SidebarId) => void;
    toggleLayer: (id: SidebarId) => void;
    closeTopLayer: () => void;  // ESC support
    rightMode: 'push' | 'overlay';
    setRightMode: (mode: 'push' | 'overlay') => void;
}

// ─────────────────────────────────────────────────────────────────
// CONTEXT
// ─────────────────────────────────────────────────────────────────
const SidebarLayerContext = createContext<SidebarLayerContextType | null>(null);

export function SidebarLayerProvider({ children }: { children: React.ReactNode }) {
    const [layers, setLayers] = useState<LayerState>({
        S1: true,   // S1 is always mounted — never toggled off by ESC
        S2: true,
        S3: false,
        RIGHT: false,
    });
    const [rightMode, setRightMode] = useState<'push' | 'overlay'>('push');

    const openLayer = useCallback((id: SidebarId) => {
        setLayers(prev => ({ ...prev, [id]: true }));
    }, []);

    const closeLayer = useCallback((id: SidebarId) => {
        setLayers(prev => ({ ...prev, [id]: false }));
    }, []);

    const toggleLayer = useCallback((id: SidebarId) => {
        setLayers(prev => ({ ...prev, [id]: !prev[id] }));
    }, []);

    // ESC closes the lowest-priority open layer (RIGHT → S3 → S2)
    const closeTopLayer = useCallback(() => {
        setLayers(prev => {
            if (prev.RIGHT) return { ...prev, RIGHT: false };
            if (prev.S3)    return { ...prev, S3: false };
            if (prev.S2)    return { ...prev, S2: false };
            return prev;
        });
    }, []);

    // Global ESC listener
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') closeTopLayer();
        };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [closeTopLayer]);

    return (
        <SidebarLayerContext.Provider value={{
            layers, openLayer, closeLayer, toggleLayer,
            closeTopLayer, rightMode, setRightMode
        }}>
            {children}
        </SidebarLayerContext.Provider>
    );
}

// ─────────────────────────────────────────────────────────────────
// HOOK
// ─────────────────────────────────────────────────────────────────
export function useSidebarLayers() {
    const ctx = useContext(SidebarLayerContext);
    if (!ctx) throw new Error('useSidebarLayers must be used within SidebarLayerProvider');
    return ctx;
}
