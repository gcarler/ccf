"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

export type CommandItem = {
    id: string;
    label: string;
    description?: string;
    shortcut?: string;
    group?: string;
    icon?: React.ComponentType<{ size?: number }>;
    action: () => void;
};

type CommandContextValue = {
    commands: CommandItem[];
    registerCommands: (scopeId: string, items: CommandItem[]) => () => void;
};

const CommandCenterContext = createContext<CommandContextValue | null>(null);

export function CommandCenterProvider({ children }: { children: React.ReactNode }) {
    const [commandSets, setCommandSets] = useState<Record<string, CommandItem[]>>({});

    const registerCommands = useCallback((scopeId: string, items: CommandItem[]) => {
        setCommandSets((prev) => ({ ...prev, [scopeId]: items }));
        return () => {
            setCommandSets((prev) => {
                const next = { ...prev };
                delete next[scopeId];
                return next;
            });
        };
    }, []);

    const commands = useMemo(() => Object.values(commandSets).flat(), [commandSets]);

    return (
        <CommandCenterContext.Provider value={{ commands, registerCommands }}>
            {children}
        </CommandCenterContext.Provider>
    );
}

export function useCommandCenter() {
    const ctx = useContext(CommandCenterContext);
    if (!ctx) {
        throw new Error("useCommandCenter debe usarse dentro de CommandCenterProvider");
    }
    return ctx;
}
