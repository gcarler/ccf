"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiFetch } from '@/lib/http';
import { useAuth } from './AuthContext';

interface WorkspaceConfig {
    features_enabled: Record<string, boolean>;
    ui_theme_config: Record<string, any>;
    navigation_schema: any[];
}

interface ConfigContextType {
    config: WorkspaceConfig | null;
    isFeatureEnabled: (featureId: string) => boolean;
    refreshConfig: () => Promise<void>;
    loading: boolean;
}

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: React.ReactNode }) {
    const { token } = useAuth();
    const [config, setConfig] = useState<WorkspaceConfig | null>(null);
    const [loading, setLoading] = useState(true);

    const refreshConfig = useCallback(async () => {
        if (!token) {
            setLoading(false);
            return;
        }
        try {
            const data = await apiFetch<WorkspaceConfig>('/workspace/config', { token });
            setConfig(data);
        } catch (err) {
            console.error("Failed to load workspace config", err);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        refreshConfig();
    }, [refreshConfig]);

    const isFeatureEnabled = (featureId: string) => {
        if (!config) return true; // Default to true if not loaded
        return !!config.features_enabled[featureId];
    };

    return (
        <ConfigContext.Provider value={{ config, isFeatureEnabled, refreshConfig, loading }}>
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
