"use client";

import React, { createContext, useContext, useEffect } from 'react';
import { useSidebarStore, SidebarId, SidebarPanel } from '@/stores/sidebarStore';

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
    const layers = useSidebarStore((s) => s.layers);
    const rightMode = useSidebarStore((s) => s.rightMode);
    const sidebarStack = useSidebarStore((s) => s.sidebarStack);
    const stackDirection = useSidebarStore((s) => s.stackDirection);

    const openLayer = useSidebarStore((s) => s.openLayer);
    const closeLayer = useSidebarStore((s) => s.closeLayer);
    const toggleLayer = useSidebarStore((s) => s.toggleLayer);
    const closeTopLayer = useSidebarStore((s) => s.closeTopLayer);
    const setRightMode = useSidebarStore((s) => s.setRightMode);
    const pushSidebarPanel = useSidebarStore((s) => s.pushSidebarPanel);
    const popSidebarPanel = useSidebarStore((s) => s.popSidebarPanel);
    const resetSidebarStack = useSidebarStore((s) => s.resetSidebarStack);

    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                const state = useSidebarStore.getState();
                if (state.sidebarStack.length > 0) {
                    state.popSidebarPanel();
                } else {
                    state.closeTopLayer();
                }
            }
        };
        document.addEventListener('keydown', handler);
        return () => document.removeEventListener('keydown', handler);
    }, []);

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

export function useSidebarLayers() {
    const ctx = useContext(SidebarLayerContext);
    if (!ctx) throw new Error('useSidebarLayers must be used within SidebarLayerProvider');
    return ctx;
}
