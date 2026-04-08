"use client";
import React, { createContext, useContext, useEffect, useState } from "react";
import { apiFetch } from "@/lib/http";

export type FaroTheme = "institutional" | "light" | "dark";

interface FaroThemeContextType {
    theme: FaroTheme;
    setTheme: (theme: FaroTheme) => void;
    toggle: () => void;
}

const ThemeContext = createContext<FaroThemeContextType>({
    theme: "institutional",
    setTheme: () => {},
    toggle: () => {},
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
        
        // Remove all theme classes
        root.classList.remove("theme-institutional", "theme-light", "theme-dark", "dark");
        
        // Add current theme class
        root.classList.add(`theme-${theme}`);
        
        // Special case: Institutional and Dark (Pure) both act as "dark" for tailwind/global utility purposes
        if (theme === "institutional" || theme === "dark") {
            root.classList.add("dark");
        }
        
        localStorage.setItem("faro-theme-v2", theme);
    }, [theme]);

    useEffect(() => {
        let mounted = true;
        const loadRemoteTheme = async () => {
            try {
                const row = await apiFetch<{ tokens_json?: Record<string, string> }>("/cms/v2/public/sites/faro/theme");
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
        <ThemeContext.Provider value={{ theme, setTheme, toggle }}>
            {children}
        </ThemeContext.Provider>
    );
}
