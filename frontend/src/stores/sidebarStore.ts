import { create } from 'zustand';

export type SidebarId = 'S1' | 'S2' | 'RIGHT';

export interface SidebarPanel {
    id: string;
    title?: string;
    content: React.ReactNode;
    onBack?: () => void;
    replaceAll?: boolean;
}

interface LayerState {
    S1: boolean;
    S2: boolean;
    RIGHT: boolean;
}

interface SidebarState {
    layers: LayerState;
    rightMode: 'push' | 'overlay';
    sidebarStack: SidebarPanel[];
    stackDirection: 'forward' | 'backward';

    openLayer: (id: SidebarId) => void;
    closeLayer: (id: SidebarId) => void;
    toggleLayer: (id: SidebarId) => void;
    closeTopLayer: () => void;
    setRightMode: (mode: 'push' | 'overlay') => void;
    pushSidebarPanel: (panel: SidebarPanel) => void;
    popSidebarPanel: () => void;
    resetSidebarStack: () => void;
}

export const useSidebarStore = create<SidebarState>((set, get) => ({
    layers: { S1: true, S2: true, RIGHT: false },
    rightMode: 'push',
    sidebarStack: [],
    stackDirection: 'forward',

    openLayer: (id) => set((s) => ({ layers: { ...s.layers, [id]: true } })),

    closeLayer: (id) => set((s) => ({ layers: { ...s.layers, [id]: false } })),

    toggleLayer: (id) => set((s) => ({ layers: { ...s.layers, [id]: !s.layers[id] } })),

    closeTopLayer: () => set((s) => {
        const layers = { ...s.layers };
        if (layers.RIGHT) layers.RIGHT = false;
        else if (layers.S2) layers.S2 = false;
        return { layers };
    }),

    setRightMode: (mode) => set({ rightMode: mode }),

    pushSidebarPanel: (panel) => set((s) => {
        const direction: 'forward' = 'forward';
        if (panel.replaceAll) return { sidebarStack: [panel], stackDirection: direction };
        const existingIndex = s.sidebarStack.findIndex(p => p.id === panel.id);
        if (existingIndex >= 0) {
            const newStack = [...s.sidebarStack];
            newStack[existingIndex] = panel;
            return { sidebarStack: newStack, stackDirection: direction };
        }
        return { sidebarStack: [...s.sidebarStack, panel], stackDirection: direction };
    }),

    popSidebarPanel: () => set((s) => ({
        stackDirection: 'backward' as const,
        sidebarStack: s.sidebarStack.length > 0 ? s.sidebarStack.slice(0, -1) : [],
    })),

    resetSidebarStack: () => set({ stackDirection: 'backward', sidebarStack: [] }),
}));
