"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";

export type FaroTheme = "institutional" | "light" | "dark";

interface FaroThemeContextType {
    theme: FaroTheme;
    setTheme: (theme: FaroTheme) => void;
    toggle: () => void;
    themeTokens: Record<string, string>;
}

const ThemeContext = createContext<FaroThemeContextType>({
    theme: "institutional",
    setTheme: () => {},
    toggle: () => {},
    themeTokens: {},
});

export function useFaroTheme() {
    return useContext(ThemeContext);
}

export function FaroThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setTheme] = useState<FaroTheme>("institutional");
    const [remoteTokens, setRemoteTokens] = useState<Record<string, string>>({});

    useEffect(() => {
        const saved = (localStorage.getItem("faro-theme-v2") as FaroTheme) || "institutional";
        setTheme(saved);
    }, []);

    useEffect(() => {
        const root = document.documentElement;

        root.classList.remove("theme-institutional", "theme-light", "theme-dark", "dark");
        root.classList.add(`theme-${theme}`);
        // Tailwind dark: prefix requires the "dark" class on <html>
        if (theme === "dark") root.classList.add("dark");

        localStorage.setItem("faro-theme-v2", theme);
    }, [theme]);

    useEffect(() => {
        let mounted = true;
        const loadRemoteTheme = async () => {
            try {
                const row = await apiFetch<{ tokens_json?: Record<string, string> }>("/cms/v2/public/sites/faro/theme", { silent: true });
                if (mounted && row?.tokens_json && typeof row.tokens_json === "object") {
                    setRemoteTokens(row.tokens_json);
                }
            } catch {
                // fallback to local CSS theme tokens
            }
        };
        loadRemoteTheme();
        return () => {
            mounted = false;
        };
    }, []);

    useEffect(() => {
        const root = document.documentElement;
        Object.entries(remoteTokens).forEach(([key, value]) => {
            if (!key.startsWith("--") || typeof value !== "string") return;
            root.style.setProperty(key, value);
        });
    }, [remoteTokens]);

    const toggle = () => {
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

