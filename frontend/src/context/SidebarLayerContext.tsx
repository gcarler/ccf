"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

// ─────────────────────────────────────────────────────────────────
// TYPES
// ─────────────────────────────────────────────────────────────────
export type SidebarId = 'S1' | 'S2' | 'RIGHT';

export interface SidebarPanel {
    id: string;               // Unique identifier for the panel
    title?: string;           // Optional title for the header
    content: React.ReactNode; // The actual panel content
    onBack?: () => void;      // Optional callback when Back is pressed
    replaceAll?: boolean;     // If true, replaces the entire stack with this panel
}

interface LayerState {
    S1: boolean;
    S2: boolean;
    RIGHT: boolean;
}

interface SidebarLayerContextType {
    layers: LayerState;
    openLayer: (id: SidebarId) => void;
    closeLayer: (id: SidebarId) => void;
    toggleLayer: (id: SidebarId) => void;
    closeTopLayer: () => void;
    rightMode: 'push' | 'overlay';
    setRightMode: (mode: 'push' | 'overlay') => void;

    // Stack Navigation (Drill-down)
    sidebarStack: SidebarPanel[];
    stackDirection: 'forward' | 'backward';
    pushSidebarPanel: (panel: SidebarPanel) => void;
    popSidebarPanel: () => void;
    resetSidebarStack: () => void;
}

// ─────────────────────────────────────────────────────────────────
// CONTEXT
// ─────────────────────────────────────────────────────────────────
const SidebarLayerContext = createContext<SidebarLayerContextType | null>(null);

export function SidebarLayerProvider({ children }: { children: React.ReactNode }) {
    const [layers, setLayers] = useState<LayerState>({
        S1: true,
        S2: true,
        RIGHT: false,
    });
    const [rightMode, setRightMode] = useState<'push' | 'overlay'>('push');
    const [sidebarStack, setSidebarStack] = useState<SidebarPanel[]>([]);
    const [stackDirection, setStackDirection] = useState<'forward' | 'backward'>('forward');

    const openLayer = useCallback((id: SidebarId) => {
        setLayers(prev => ({ ...prev, [id]: true }));
    }, []);

    const closeLayer = useCallback((id: SidebarId) => {
        setLayers(prev => ({ ...prev, [id]: false }));
    }, []);

    const toggleLayer = useCallback((id: SidebarId) => {
        setLayers(prev => ({ ...prev, [id]: !prev[id] }));
    }, []);

    const closeTopLayer = useCallback(() => {
        setLayers(prev => {
            if (prev.RIGHT) return { ...prev, RIGHT: false };
            if (prev.S2) return { ...prev, S2: false };
            return prev;
        });
    }, []);

    // Push — replaces all if replaceAll:true, updates existing by ID, or appends
    const pushSidebarPanel = useCallback((panel: SidebarPanel) => {
        setStackDirection('forward');
        setSidebarStack(prev => {
            if (panel.replaceAll) {
                return [panel];
            }
            const existingIndex = prev.findIndex(p => p.id === panel.id);
            if (existingIndex >= 0) {
                return [...prev.slice(0, existingIndex), panel];
            }
            return [...prev, panel];
        });
    }, []);

    const popSidebarPanel = useCallback(() => {
        setStackDirection('backward');
        setSidebarStack(prev => prev.length > 0 ? prev.slice(0, prev.length - 1) : []);
    }, []);

    const resetSidebarStack = useCallback(() => {
        setStackDirection('backward');
        setSidebarStack([]);
    }, []);

    // Global ESC listener — pops top sidebar panel or closes layer
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                setStackDirection('backward');
                setSidebarStack(prev => {
                    if (prev.length > 0) return prev.slice(0, prev.length - 1);
                    return prev;
                });
                if (sidebarStack.length === 0) closeTopLayer();
            }
        };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [closeTopLayer, sidebarStack.length]);

    return (
        <SidebarLayerContext.Provider value={{
            layers, openLayer, closeLayer, toggleLayer,
            closeTopLayer, rightMode, setRightMode,
            sidebarStack, stackDirection, pushSidebarPanel, popSidebarPanel, resetSidebarStack,
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
