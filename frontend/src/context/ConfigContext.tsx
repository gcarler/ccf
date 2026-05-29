"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';

interface ConfigContextType {
    config: any | null;
    isFeatureEnabled: (featureId: string) => boolean;
    refreshConfig: () => Promise<void>;
    loading: boolean;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: React.ReactNode }) {
    const { token } = useAuth();
    const [config, setConfig] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const refreshConfig = useCallback(async () => {
        if (!token) { setLoading(false); return; }
        try {
            const { apiFetch } = await import('@/lib/http');
            const data = await apiFetch('/workspace/config', { token });
            setConfig(data);
        } catch (err) { console.error("Config load failed", err); }
        finally { setLoading(false); }
    }, [token]);

    useEffect(() => { refreshConfig(); }, [refreshConfig]);

    const isFeatureEnabled = (featureId: string) => {
        if (!config) return true;
        return !!config.features_enabled?.[featureId];
    };

    return (
        <ConfigContext.Provider value={{ config, isFeatureEnabled, refreshConfig, loading }}>
            {children}
        </ConfigContext.Provider>
    );
}

export function useConfig() {
    const ctx = useContext(ConfigContext);
    if (!ctx) throw new Error('useConfig must be used within ConfigProvider');
    return ctx;
}
