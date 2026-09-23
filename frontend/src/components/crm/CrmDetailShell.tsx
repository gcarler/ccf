"use client";

import { ReactNode, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

type Variant = "sky" | "emerald" | "amber" | "rose";

const VARIANT_PRESETS: Record<Variant, { primary: string; accent: string }> = {
    sky: {
        primary: "to-[hsl(var(--info)/20%)]",
        accent: "to-[hsl(var(--info)/20%)]"
    },
    emerald: {
        primary: "to-[hsl(var(--success)/15%)]",
        accent: "from-[hsl(var(--domain-teal)/20%)]"
    },
    amber: {
        primary: "to-[hsl(var(--warning)/20%)]",
        accent: "from-[hsl(var(--warning)/15%)]"
    },
    rose: {
        primary: "to-[hsl(var(--danger)/20%)]",
        accent: "to-[hsl(var(--info)/15%)]"
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
    variant = "sky",
    onBack,
    contentClassName
}: CrmDetailShellProps) {
    const router = useRouter();
    const preset = VARIANT_PRESETS[variant] || VARIANT_PRESETS.sky;
    const baseBg = 'bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))]';
    const headerBg = 'bg-[hsl(var(--surface-1)/0.85)] border-[hsl(var(--border))]';
    const subtleText = 'text-[hsl(var(--muted-foreground))]';
    const accentText = 'text-[hsl(var(--muted-foreground))]';
    const handleBack = useCallback(() => {
        if (onBack) return onBack();
        router.back();
    }, [router, onBack]);

    return (
        <div className={`min-h-screen relative overflow-hidden font-display ${baseBg}`}>
            <div className="relative z-10 max-w-6xl mx-auto flex flex-col min-h-screen px-4">
                <header className={`sticky top-0 backdrop-blur-2xl border-b py-2 flex flex-col gap-4 ${headerBg}`}>
                    <div className="flex items-center justify-between gap-4">
                        <button
                            onClick={handleBack}
                            className="size-8 rounded-full border border-[hsl(var(--border))] flex items-center justify-center transition-colors text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] hover:border-[hsl(var(--primary))]"
                            aria-label="Regresar"
                        >
                            <ArrowLeft size={18} />
                        </button>
                        <div className="flex-1 text-center">
                            <p className={`text-2xs font-bold uppercase tracking-wide ${accentText}`}>Consolidación</p>
                            <h1 className="text-lg font-bold tracking-tight text-[hsl(var(--foreground))]">{title}</h1>
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
