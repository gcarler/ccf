import { create } from 'zustand';
import { apiFetch } from '@/lib/http';

interface WorkspaceConfig {
    features_enabled: Record<string, boolean>;
    features_raw?: Record<string, boolean>;
    feature_rules?: Record<string, {
        roles_allow?: string[];
        roles_deny?: string[];
        users_allow?: string[];
        users_deny?: string[];
        rollout_percent?: number;
    }>;
    ui_theme_config: Record<string, any>;
    navigation_schema: any[];
    requested_by?: string;
}

interface ConfigState {
    config: WorkspaceConfig | null;
    loading: boolean;
    isFeatureEnabled: (featureId: string) => boolean;
    refreshConfig: (token: string | null) => Promise<void>;
}

export const useConfigStore = create<ConfigState>((set, get) => ({
    config: null,
    loading: true,

    isFeatureEnabled: (featureId: string) => {
        const { config } = get();
        if (!config) return true;
        return !!config.features_enabled[featureId];
    },

    refreshConfig: async (token: string | null) => {
        if (!token) {
            set({ loading: false });
            return;
        }
        try {
            const data = await apiFetch<WorkspaceConfig>('/workspace/config', { token });
            set({ config: data, loading: false });
        } catch (err) {
            console.error("Failed to load workspace config", err);
            set({ loading: false });
        }
    },
}));
