"use client";

import { ReactNode, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

type Variant = "indigo" | "emerald" | "amber" | "rose";

const VARIANT_PRESETS: Record<Variant, { primary: string; accent: string }> = {
    indigo: {
        primary: "from-blue-500/20",
        accent: "from-indigo-500/20"
    },
    emerald: {
        primary: "from-emerald-500/15",
        accent: "from-teal-500/20"
    },
    amber: {
        primary: "from-amber-500/20",
        accent: "from-orange-500/15"
    },
    rose: {
        primary: "from-rose-500/20",
        accent: "from-sky-500/15"
    }
};

interface CrmDetailShellProps {
    title: string;
    description?: string;
    rightAction?: ReactNode;
    headerContent?: ReactNode;
    children: ReactNode;
    variant?: Variant;
    onBack?: () => void;
    contentClassName?: string;
    appearance?: 'dark' | 'light';
}

export default function CrmDetailShell({
    title,
    description,
    rightAction,
    headerContent,
    children,
    variant = "indigo",
    onBack,
    contentClassName
}: CrmDetailShellProps) {
    const router = useRouter();
    const preset = VARIANT_PRESETS[variant] || VARIANT_PRESETS.indigo;
    const isDark = true;
    const baseBg = isDark ? 'bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]' : 'bg-[hsl(var(--bg-primary))] text-[hsl(var(--text-primary))]';
    const headerBg = isDark ? 'bg-[hsl(var(--bg-primary)/0.85)] border-[hsl(var(--border))]' : 'bg-[hsl(var(--bg-primary)/0.8)] border-[hsl(var(--border))] text-[hsl(var(--text-primary))]';
    const subtleText = isDark ? 'text-[hsl(var(--text-secondary))]' : 'text-[hsl(var(--text-secondary))]';
    const accentText = isDark ? 'text-[hsl(var(--text-secondary))]' : 'text-[hsl(var(--text-secondary))]';
    const overlayHidden = !isDark;
    const handleBack = useCallback(() => {
        if (onBack) return onBack();
        router.back();
    }, [router, onBack]);

    return (
        <div className={`min-h-screen relative overflow-hidden font-display ${baseBg}`}>
            {!overlayHidden && (
                <div className="absolute inset-0 pointer-events-none">
                    <div className={`absolute top-0 right-0 w-[900px] h-[900px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] ${preset.primary} via-[hsl(var(--bg-primary))] to-[hsl(var(--bg-primary))] opacity-60 blur-3xl`} />
                    <div className={`absolute bottom-0 left-0 w-[700px] h-[700px] bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] ${preset.accent} via-[hsl(var(--bg-primary))] to-[hsl(var(--bg-primary))] opacity-60 blur-[140px]`} />
                </div>
            )}

            <div className="relative z-10 max-w-6xl mx-auto flex flex-col min-h-screen px-4">
                <header className={`sticky top-0 backdrop-blur-2xl border-b py-2 flex flex-col gap-4 ${headerBg}`}>
                    <div className="flex items-center justify-between gap-4">
                        <button
                            onClick={handleBack}
                            className={`size-8 rounded-full border flex items-center justify-center transition-colors ${isDark ? 'border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:border-white/30' : 'border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] hover:border-[hsl(var(--primary))]'}`}
                            aria-label="Regresar"
                        >
                            <ArrowLeft size={18} />
                        </button>
                        <div className="flex-1 text-center">
                            <p className={`text-[10px] font-bold uppercase tracking-wide ${accentText}`}>Consolidación</p>
                            <h1 className={`text-lg font-bold tracking-tight ${isDark ? 'text-[hsl(var(--text-primary))]' : 'text-[hsl(var(--text-primary))]'}`}>{title}</h1>
                            {description && <p className={`text-xs mt-1 font-medium ${subtleText}`}>{description}</p>}
                        </div>
                        <div className="flex items-center justify-end min-w-[44px]">
                            {rightAction}
                        </div>
                    </div>

                    {headerContent && <div>{headerContent}</div>}
                </header>

                <main className={`flex-1 py-2 ${contentClassName ?? "space-y-3"}`}>
                    {children}
                </main>
            </div>
        </div>
    );
}

