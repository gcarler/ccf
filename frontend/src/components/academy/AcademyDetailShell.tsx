"use client";

import React, { ReactNode, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

type Variant = "sky" | "emerald" | "amber" | "blue";

const VARIANT_PRESETS: Record<Variant, { primary: string; secondary: string }> = {
    sky: {
        primary: "from-sky-500/20",
        secondary: "from-sky-500/10",
    },
    emerald: {
        primary: "from-emerald-500/15",
        secondary: "from-teal-500/10",
    },
    amber: {
        primary: "from-amber-500/20",
        secondary: "from-rose-500/10",
    },
    blue: {
        primary: "from-blue-500/15",
        secondary: "from-sky-500/10",
    },
};

interface AcademyDetailShellProps {
    title: string;
    description?: string;
    rightAction?: ReactNode;
    headerContent?: ReactNode;
    children: ReactNode;
    variant?: Variant;
    onBack?: () => void;
    contentClassName?: string;
}

export function AcademyDetailShell({
    title,
    description,
    rightAction,
    headerContent,
    children,
    variant = "sky",
    onBack,
    contentClassName,
}: AcademyDetailShellProps) {
    const router = useRouter();
    const colors = VARIANT_PRESETS[variant] || VARIANT_PRESETS.sky;
    const handleBack = useCallback(() => {
        if (onBack) return onBack();
        router.back();
    }, [onBack, router]);

    return (
        <div className="min-h-screen bg-slate-950 font-display text-slate-100 selection:bg-primary/30 relative overflow-hidden">
            <div className="fixed inset-0 z-0 pointer-events-none">
                <div className={`absolute top-0 right-0 w-[800px] h-[800px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] ${colors.primary} via-slate-950 to-slate-950 opacity-60 blur-3xl`} />
                <div className={`absolute bottom-0 left-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] ${colors.secondary} via-slate-950 to-slate-950 opacity-60 blur-[140px]`} />
            </div>

            <div className="relative z-10 max-w-4xl mx-auto flex flex-col min-h-screen">
                <header className="sticky top-0 bg-slate-950/85 backdrop-blur-2xl border-b border-white/5 px-3 pt-6 pb-4 flex flex-col gap-4">
                    <div className="flex items-center justify-between gap-4">
                        <button
                            onClick={handleBack}
                            className="size-10 rounded-full border border-white/10 flex items-center justify-center text-slate-400 hover:text-white hover:border-white/30 transition-colors"
                            aria-label="Regresar"
                        >
                            <ArrowLeft size={18} />
                        </button>
                        <div className="flex-1 text-center">
                            <p className="text-[10px] font-semibold uppercase tracking-wide text-white/40">Academia</p>
                            <h1 className="text-xl font-bold tracking-tight text-white">{title}</h1>
                            {description && <p className="text-xs text-white/60 mt-1 font-medium leading-tight">{description}</p>}
                        </div>
                        <div className="flex items-center justify-end w-10 text-white">
                            {rightAction}
                        </div>
                    </div>

                    {headerContent && <div className="w-full">{headerContent}</div>}
                </header>

                <main className={`flex-1 overflow-y-auto pb-4 px-3 ${contentClassName ?? ""}`}>
                    {children}
                </main>
            </div>
        </div>
    );
}

export default AcademyDetailShell;
