"use client";

import React, { createContext, useContext, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { useConfigStore } from '@/stores/configStore';

interface ConfigContextType {
    config: any | null;
    isFeatureEnabled: (featureId: string) => boolean;
    refreshConfig: () => Promise<void>;
    loading: boolean;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: React.ReactNode }) {
    const { token } = useAuth();
    const config = useConfigStore((s) => s.config);
    const loading = useConfigStore((s) => s.loading);
    const isFeatureEnabled = useConfigStore((s) => s.isFeatureEnabled);
    const refreshConfig = useConfigStore((s) => s.refreshConfig);

    useEffect(() => {
        refreshConfig(token);
    }, [token, refreshConfig]);

    return (
        <ConfigContext.Provider value={{
            config,
            isFeatureEnabled,
            refreshConfig: () => refreshConfig(token),
            loading,
        }}>
            {children}
        </ConfigContext.Provider>
    );
}

export function useConfig() {
    const context = useContext(ConfigContext);
    if (context === undefined) {
        throw new Error('useConfig must be used within a ConfigProvider');
    }
    return context;
}
