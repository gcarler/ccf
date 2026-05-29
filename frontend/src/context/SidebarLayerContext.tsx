"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

export type SidebarId = 'S1' | 'S2' | 'RIGHT';

export interface SidebarPanel {
    id: string;
    title?: string;
    content: React.ReactNode;
    onBack?: () => void;
    replaceAll?: boolean;
}

interface SidebarLayerContextType {
    layers: { S1: boolean; S2: boolean; RIGHT: boolean };
    openLayer: (id: SidebarId) => void;
    closeLayer: (id: SidebarId) => void;
    toggleLayer: (id: SidebarId) => void;
    closeTopLayer: () => void;
    rightMode: 'push' | 'overlay';
    setRightMode: (mode: 'push' | 'overlay') => void;
    sidebarStack: SidebarPanel[];
    stackDirection: 'forward' | 'backward';
    pushSidebarPanel: (panel: SidebarPanel) => void;
    popSidebarPanel: () => void;
    resetSidebarStack: () => void;
}

const SidebarLayerContext = createContext<SidebarLayerContextType | null>(null);

export function SidebarLayerProvider({ children }: { children: React.ReactNode }) {
    const [layers, setLayers] = useState({ S1: true, S2: true, RIGHT: false });
    const [rightMode, setRightMode] = useState<'push' | 'overlay'>('push');
    const [sidebarStack, setSidebarStack] = useState<SidebarPanel[]>([]);
    const [stackDirection, setStackDirection] = useState<'forward' | 'backward'>('forward');

    const openLayer = useCallback((id: SidebarId) => setLayers(p => ({...p, [id]: true})), []);
    const closeLayer = useCallback((id: SidebarId) => setLayers(p => ({...p, [id]: false})), []);
    const toggleLayer = useCallback((id: SidebarId) => setLayers(p => ({...p, [id]: !p[id]})), []);
    
    const closeTopLayer = useCallback(() => {
        setLayers(prev => {
            if (prev.RIGHT) return {...prev, RIGHT: false};
            if (prev.S2) return {...prev, S2: false};
            return prev;
        });
    }, []);

    const pushSidebarPanel = useCallback((panel: SidebarPanel) => {
        setStackDirection('forward');
        setSidebarStack(prev => {
            if (panel.replaceAll) return [panel];
            const idx = prev.findIndex(p => p.id === panel.id);
            if (idx >= 0) return [...prev.slice(0, idx), panel];
            return [...prev, panel];
        });
    }, []);

    const popSidebarPanel = useCallback(() => {
        setStackDirection('backward');
        setSidebarStack(prev => prev.slice(0, -1));
    }, []);

    const resetSidebarStack = useCallback(() => {
        setStackDirection('backward');
        setSidebarStack([]);
    }, []);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                setSidebarStack(prev => {
                    if (prev.length > 0) return prev.slice(0, -1);
                    closeTopLayer();
                    return prev;
                });
            }
        };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, [closeTopLayer]);

    return (
        <SidebarLayerContext.Provider value={{
            layers, openLayer, closeLayer, toggleLayer, closeTopLayer,
            rightMode, setRightMode, sidebarStack, stackDirection,
            pushSidebarPanel, popSidebarPanel, resetSidebarStack
        }}>
            {children}
        </SidebarLayerContext.Provider>
    );
}

export function useSidebarLayers() {
    const ctx = useContext(SidebarLayerContext);
    if (!ctx) throw new Error('useSidebarLayers must be used within SidebarLayerProvider');
    return ctx;
}
