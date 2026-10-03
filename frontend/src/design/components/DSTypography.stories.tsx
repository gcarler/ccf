import type { Meta, StoryObj } from '@storybook/react-webpack5';
import { DSTypography } from './DSTypography';
import { DSCard } from './DSCard';

/**
 * Specímen tipográfico del Design System CCF.
 *
 * Documenta las familias (`--font-*`), la escala (`--text-*`),
 * los pesos (`--weight-*`) y el tracking (`--tracking-*`) definidos
 * en `globals.css` y vinculados a Tailwind vía `tailwind.config.ts`.
 */
const meta: Meta<typeof DSTypography> = {
    title: 'Design/Typography',
    component: DSTypography,
    args: {
        as: 'span',
        family: 'body',
        size: 'base',
    },
    parameters: { layout: 'padded' },
};

export default meta;
type Story = StoryObj<typeof DSTypography>;

/** Familias tipográficas semánticas y su rol en la plataforma. */
export const Familias: Story = {
    render: () => (
        <div className="space-y-6 max-w-3xl">
            {(
                [
                    { family: 'display', role: 'Títulos públicos, hero y landing' },
                    { family: 'headline', role: 'Encabezados del workspace (h1–h4)' },
                    { family: 'body', role: 'Texto corrido; fuente base de la plataforma' },
                    { family: 'label', role: 'Etiquetas, micro-copy y UI compacta' },
                    { family: 'mono', role: 'IDs, datos técnicos y código' },
                ] as const
            ).map(({ family, role }) => (
                <DSCard key={family} tone="light" padding="md">
                    <DSTypography family="label" size="2xs" weight="bold" tracking="widest" uppercase className="text-[hsl(var(--text-secondary))]">
                        {role}
                    </DSTypography>
                    <DSTypography family={family} size="2xl" weight="bold" className="mt-2 text-[hsl(var(--text-primary))]">
                        Comunidad Cristiana El Faro
                    </DSTypography>
                    <DSTypography family={family} size="base" className="mt-1 text-[hsl(var(--text-secondary))]">
                        ABCDEFGHIJKLMNÑOPQRSTUVWXYZ abcdefghijklmnñopqrstuvwxyz 0123456789
                    </DSTypography>
                </DSCard>
            ))}
        </div>
    ),
};

/** Escala semántica de tamaños (rejilla base 4pt). */
export const Escala: Story = {
    render: () => (
        <div className="space-y-4 max-w-3xl">
            {(
                [
                    { size: '2xs', px: '10px', sample: 'Micro labels y badges' },
                    { size: 'xs', px: '11px', sample: 'Captions y timestamps' },
                    { size: 'sm', px: '12px', sample: 'Labels secundarios' },
                    { size: 'base', px: '13px', sample: 'Texto base de la plataforma' },
                    { size: 'md', px: '14px', sample: 'Texto grande y botones' },
                    { size: 'lg', px: '16px', sample: 'Encabezados de sección' },
                    { size: 'xl', px: '18px', sample: 'Títulos de página (máx. workspace)' },
                    { size: '2xl', px: '20px', sample: 'Subtítulos hero público' },
                    { size: '3xl', px: '24px', sample: 'Títulos de sección público' },
                    { size: '4xl', px: '32px', sample: 'Títulos hero público' },
                ] as const
            ).map(({ size, px, sample }) => (
                <div key={size} className="flex items-baseline gap-4 border-b border-[hsl(var(--border))] pb-3">
                    <DSTypography family="mono" size="2xs" weight="medium" className="w-24 shrink-0 text-[hsl(var(--text-secondary))]">
                        text-{size}
                    </DSTypography>
                    <DSTypography family="mono" size="2xs" weight="medium" className="w-12 shrink-0 text-[hsl(var(--muted-foreground))]">
                        {px}
                    </DSTypography>
                    <DSTypography size={size} weight="semibold" className="text-[hsl(var(--text-primary))]">
                        {sample}
                    </DSTypography>
                </div>
            ))}
        </div>
    ),
};

/** Pesos tipográficos disponibles (`--weight-*`). */
export const Pesos: Story = {
    render: () => (
        <div className="space-y-3 max-w-3xl">
            {(
                [
                    { weight: 'normal', label: 'Normal 400' },
                    { weight: 'medium', label: 'Medium 500' },
                    { weight: 'semibold', label: 'Semibold 600' },
                    { weight: 'bold', label: 'Bold 700' },
                    { weight: 'extrabold', label: 'Extrabold 800' },
                ] as const
            ).map(({ weight, label }) => (
                <div key={weight} className="flex items-baseline gap-4">
                    <DSTypography family="mono" size="2xs" weight="medium" className="w-28 shrink-0 text-[hsl(var(--text-secondary))]">
                        {label}
                    </DSTypography>
                    <DSTypography size="xl" weight={weight} className="text-[hsl(var(--text-primary))]">
                        Alcanza a las naciones
                    </DSTypography>
                </div>
            ))}
        </div>
    ),
};

/** Tracking (`--tracking-*`) usado en labels uppercase de la plataforma. */
export const Tracking: Story = {
    render: () => (
        <div className="space-y-3 max-w-3xl">
            {(
                [
                    { tracking: 'tight', label: 'Tight -0.02em' },
                    { tracking: 'normal', label: 'Normal 0em' },
                    { tracking: 'wide', label: 'Wide 0.03em' },
                    { tracking: 'wider', label: 'Wider 0.06em' },
                    { tracking: 'widest', label: 'Widest 0.1em' },
                ] as const
            ).map(({ tracking, label }) => (
                <div key={tracking} className="flex items-baseline gap-4">
                    <DSTypography family="mono" size="2xs" weight="medium" className="w-28 shrink-0 text-[hsl(var(--text-secondary))]">
                        {label}
                    </DSTypography>
                    <DSTypography size="xs" weight="bold" tracking={tracking} uppercase className="text-[hsl(var(--text-primary))]">
                        Módulo de Proyectos
                    </DSTypography>
                </div>
            ))}
        </div>
    ),
};

/** Composición real de un encabezado del workspace. */
export const PatronWorkspace: Story = {
    render: () => (
        <DSCard tone="light" padding="md" className="max-w-xl">
            <DSTypography as="label" family="label" size="2xs" weight="bold" tracking="widest" uppercase className="text-[hsl(var(--muted-foreground))]">
                Portafolio · Ministerios
            </DSTypography>
            <DSTypography as="h3" family="headline" size="xl" weight="semibold" tracking="tight" className="mt-1 text-[hsl(var(--text-primary))]">
                Escuela de Liderazgo 2026
            </DSTypography>
            <DSTypography as="p" family="body" size="base" className="mt-2 text-[hsl(var(--text-secondary))]">
                Plan de formación anual para líderes de células. Incluye 12 módulos,
                mentorías quincenales y evaluación pastoral final.
            </DSTypography>
            <div className="mt-3 flex items-center gap-3">
                <DSTypography family="label" size="2xs" weight="bold" tracking="widest" uppercase className="text-[hsl(var(--primary))]">
                    En Marcha
                </DSTypography>
                <DSTypography family="mono" size="2xs" className="text-[hsl(var(--muted-foreground))]">
                    #PRJ-2026-014
                </DSTypography>
            </div>
        </DSCard>
    ),
};
