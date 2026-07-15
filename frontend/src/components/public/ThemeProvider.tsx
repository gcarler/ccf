"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";
import { SITE_KEY } from "@/lib/site-config";
import { usePublicBootstrap } from "./PublicBootstrapProvider";

export type Theme = "institutional" | "light" | "dark";

interface ThemeContextType {
    theme: Theme;
    setTheme: (theme: Theme) => void;
    toggle: () => void;
    themeTokens: Record<string, string>;
}

const ThemeContext = createContext<ThemeContextType>({
    theme: "institutional",
    setTheme: () => {},
    toggle: () => {},
    themeTokens: {},
});

function inferThemeMode(themeName?: string, tokens?: Record<string, unknown>): Theme {
    const raw = `${themeName || ""} ${String(tokens?.["--site-theme-mode"] ?? tokens?.theme_mode ?? tokens?.mode ?? "")}`
        .toLowerCase()
        .trim();

    if (raw.includes("dark") || raw.includes("oscur")) return "dark";
    if (raw.includes("light") || raw.includes("claro")) return "light";
    return "institutional";
}

const CMS_TOKEN_ALLOWLIST = new Set([
    "--site-logo-url",
    "--site-logo-name",
    "--site-header-cta-label",
    "--site-header-cta-href",
]);

export function useTheme() {
    return useContext(ThemeContext);
}

export const useFaroTheme = useTheme;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const bootstrapTheme = usePublicBootstrap()?.theme ?? null;
    const [theme, setTheme] = useState<Theme>("institutional");
    const [remoteTokens, setRemoteTokens] = useState<Record<string, string>>(bootstrapTheme?.tokens_json || {});
    const [hasManualOverride, setHasManualOverride] = useState(false);

    useEffect(() => {
        if (bootstrapTheme?.name || bootstrapTheme?.tokens_json) {
            if (bootstrapTheme.tokens_json) {
                setRemoteTokens(bootstrapTheme.tokens_json);
            }
            if (!hasManualOverride) {
                setTheme(inferThemeMode(bootstrapTheme.name, bootstrapTheme.tokens_json));
            }
            return;
        }

        const saved = (localStorage.getItem("site-theme-v2") || localStorage.getItem("site-theme-v2") || "").trim();
        if (saved === "institutional" || saved === "light" || saved === "dark") {
            setTheme(saved);
            setHasManualOverride(true);
        }
    }, [bootstrapTheme?.name, bootstrapTheme?.tokens_json, hasManualOverride]);

    useEffect(() => {
        const root = document.documentElement;

        root.classList.remove("theme-institutional", "theme-light", "theme-dark", "dark");
        root.classList.add(`theme-${theme}`);
        if (theme === "dark") root.classList.add("dark");

        localStorage.setItem("site-theme-v2", theme);
    }, [theme]);

    useEffect(() => {
        let mounted = true;

        const loadRemoteTheme = async () => {
            try {
                if (bootstrapTheme?.name || bootstrapTheme?.tokens_json) return;
                const row = await apiFetch<{ name?: string; tokens_json?: Record<string, string> }>(`/cms/v2/public/sites/${SITE_KEY}/theme`, { silent: true });
                if (mounted && row?.tokens_json && typeof row.tokens_json === "object") {
                    setRemoteTokens(row.tokens_json);
                }
                if (mounted && !hasManualOverride) {
                    setTheme(inferThemeMode(row?.name, row?.tokens_json));
                }
            } catch {
                // fallback to local CSS theme tokens
            }
        };

        const syncTheme = () => {
            const saved = (localStorage.getItem("site-theme-v2") || localStorage.getItem("site-theme-v2") || "").trim();
            if (saved === "institutional" || saved === "light" || saved === "dark") {
                setHasManualOverride(true);
                setTheme(saved);
            }
        };

        const onStorage = (event: StorageEvent) => {
            if (event.key === "site-theme-v2" || event.key === "site-theme-v2") {
                syncTheme();
            }
        };

        const onVisibility = () => {
            if (document.visibilityState === "visible") {
                loadRemoteTheme().catch(() => undefined);
                syncTheme();
            }
        };

        loadRemoteTheme();
        const pollId = window.setInterval(() => {
            if (document.visibilityState === "visible") {
                loadRemoteTheme().catch(() => undefined);
            }
        }, 30000);
        window.addEventListener("storage", onStorage);
        document.addEventListener("visibilitychange", onVisibility);

        return () => {
            mounted = false;
            window.clearInterval(pollId);
            window.removeEventListener("storage", onStorage);
            document.removeEventListener("visibilitychange", onVisibility);
        };
    }, [hasManualOverride, bootstrapTheme?.name, bootstrapTheme?.tokens_json]);

    useEffect(() => {
        const root = document.documentElement;
        Object.entries(remoteTokens).forEach(([key, value]) => {
            if (!CMS_TOKEN_ALLOWLIST.has(key) || typeof value !== "string") return;
            root.style.setProperty(key, value);
        });
    }, [remoteTokens]);

    const toggle = () => {
        setHasManualOverride(true);
        setTheme((prev) => {
            if (prev === "institutional") return "light";
            if (prev === "light") return "dark";
            return "institutional";
        });
    };

    return (
        <ThemeContext.Provider value={{ theme, setTheme, toggle, themeTokens: remoteTokens }}>
            {children}
        </ThemeContext.Provider>
    );
}

export const FaroThemeProvider = ThemeProvider;
