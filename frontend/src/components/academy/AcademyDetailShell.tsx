"use client";

import React, { ReactNode } from "react";

/**
 * ACAD-TKT-042 (refactor 2026-07-19): AcademyDetailShell ya NO es una página
 * completa con chrome propio. Es un contenedor temático que vive DENTRO de
 * ``<WorkspaceLayout>``. El shell de plataforma único es WorkspaceLayout.
 *
 * Cambios respecto a la versión anterior:
 * - Eliminado ``min-h-screen`` (lo provee WorkspaceLayout).
 * - Eliminado header sticky con botón de regreso (WorkspaceLayout lo provee
 *   via props ``onBack`` + ``breadcrumbs``).
 * - Gradientes movidos de ``fixed inset-0`` a ``absolute inset-0`` para que
 *   se posicionen respecto al contenedor padre (WorkspaceLayout), no a la
 *   ventana completa.
 * - Quitado import de ``useRouter`` y ``ArrowLeft`` (la navegación vive en
 *   WorkspaceLayout).
 * - Export default ahora es ``AcademyDetailContainer`` semánticamente — el
 *   nombre ``AcademyDetailShell`` se conserva como alias para no romper
 *   consumers existentes.
 */
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

interface AcademyDetailContainerProps {
    children: ReactNode;
    variant?: Variant;
    contentClassName?: string;
}

function AcademyDetailContainer({
    children,
    variant = "sky",
    contentClassName,
}: AcademyDetailContainerProps) {
    const colors = VARIANT_PRESETS[variant] || VARIANT_PRESETS.sky;
    return (
        <div
            data-testid="academy-detail-container"
            data-variant={variant}
            className="relative overflow-hidden bg-[hsl(var(--bg-muted))] font-display text-[hsl(var(--text-secondary))] selection:bg-primary/30"
        >
            {/* Gradientes decorativos — relative al contenedor, no fixed al viewport */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div
                    className={`absolute top-0 right-0 w-[800px] h-[800px] bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] ${colors.primary} via-[hsl(var(--bg-muted))] to-[hsl(var(--bg-muted))] opacity-60 blur-3xl`}
                />
                <div
                    className={`absolute bottom-0 left-0 w-[600px] h-[600px] bg-[radial-gradient(circle_at_bottom_left,_var(--tw-gradient-stops))] ${colors.secondary} via-[hsl(var(--bg-muted))] to-[hsl(var(--bg-muted))] opacity-60 blur-[140px]`}
                />
            </div>
            {/* Contenido — scrollable, sobre los gradientes */}
            <div className={`relative z-10 ${contentClassName ?? ""}`}>
                {children}
            </div>
        </div>
    );
}

export default AcademyDetailContainer;
export { AcademyDetailContainer };
