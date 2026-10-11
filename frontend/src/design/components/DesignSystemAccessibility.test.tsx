import React from 'react';
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe } from 'jest-axe';

import { DSBadge } from './DSBadge';
import { DSButton } from './DSButton';
import { DSCard } from './DSCard';
import { DSInput } from './DSInput';
import { DSMetric } from './DSMetric';
import { DSSelect } from './DSSelect';
import { DSTabs } from './DSTabs';
import { MINISTERIAL_ACCENTS, UI_SCALE_TOKENS, MinisterialAccentId, UiScaleId } from '../tokens-semantic';

describe('Design System Atomic Components — Accessibility & Scale Integration', () => {
    beforeEach(() => {
        document.documentElement.className = '';
        document.documentElement.removeAttribute('style');
    });

    afterEach(() => {
        document.documentElement.className = '';
        document.documentElement.removeAttribute('style');
    });

    function applyScaleAndTokens(scale: UiScaleId, accent: MinisterialAccentId, mode: 'day' | 'night' = 'day') {
        const scaleToken = UI_SCALE_TOKENS[scale];
        const accentToken = MINISTERIAL_ACCENTS[accent];
        const colorPair = mode === 'night' ? accentToken.night : accentToken.day;

        document.documentElement.style.setProperty('--ui-scale', String(scaleToken.scale));
        document.documentElement.style.fontSize = scaleToken.fontSize;
        document.documentElement.style.setProperty('--primary', colorPair.primary);
        document.documentElement.style.setProperty('--primary-foreground', colorPair.primaryForeground);

        if (mode === 'night') {
            document.documentElement.classList.add('dark');
            document.documentElement.setAttribute('data-theme', 'night');
        } else {
            document.documentElement.classList.remove('dark');
            document.documentElement.setAttribute('data-theme', 'day');
        }
    }

    describe('1. UI Scale Injections across all 4 levels', () => {
        const scales: UiScaleId[] = ['compact', 'normal', 'comfortable', 'large'];

        scales.forEach((scale) => {
            it(`adapts atomic components under "${scale}" scale (${UI_SCALE_TOKENS[scale].percentage})`, () => {
                applyScaleAndTokens(scale, 'ccf-blue', 'day');

                expect(document.documentElement.style.getPropertyValue('--ui-scale')).toBe(
                    String(UI_SCALE_TOKENS[scale].scale)
                );
                expect(document.documentElement.style.fontSize).toBe(UI_SCALE_TOKENS[scale].fontSize);

                const { container } = render(
                    <div className="space-y-4" style={{ transform: 'scale(var(--ui-scale))' }}>
                        <DSButton variant="primary">Guardar Cambios</DSButton>
                        <DSInput label="Nombre Completo" placeholder="Escriba aquí" />
                        <DSCard>Tarjeta de prueba</DSCard>
                        <DSTabs
                            tabs={[
                                { id: 'tab-1', label: 'General' },
                                { id: 'tab-2', label: 'Ajustes' },
                            ]}
                        />
                        <DSBadge label="En Proceso" tone="primary" />
                        <DSSelect
                            label="Sede Ministerial"
                            options={[
                                { value: 'cali', label: 'Cali Central' },
                                { value: 'bogota', label: 'Bogotá Norte' },
                            ]}
                        />
                        <DSMetric label="Miembros Activos" value="2,450" tone="primary" />
                    </div>
                );

                expect(screen.getByText('Guardar Cambios')).toBeInTheDocument();
                expect(screen.getByText('Nombre Completo')).toBeInTheDocument();
                expect(screen.getByText('Tarjeta de prueba')).toBeInTheDocument();
                expect(screen.getByText('General')).toBeInTheDocument();
                expect(screen.getByText('En Proceso')).toBeInTheDocument();
                expect(screen.getByText('Sede Ministerial')).toBeInTheDocument();
                expect(screen.getByText('Miembros Activos')).toBeInTheDocument();
                expect(container).toBeDefined();
            });
        });
    });

    describe('2. Ministerial Accent Injections across all 6 accents', () => {
        const accents: MinisterialAccentId[] = [
            'ccf-blue',
            'emerald',
            'royal',
            'burgundy',
            'amber',
            'ocean',
        ];

        accents.forEach((accentId) => {
            it(`injects tokens for accent "${accentId}" in Day and Night modes with audited ratios`, () => {
                const token = MINISTERIAL_ACCENTS[accentId];

                // Verify audited ratios meet WCAG AA (>= 4.5)
                expect(token.wcagDayRatio).toBeGreaterThanOrEqual(4.5);
                expect(token.wcagNightRatio).toBeGreaterThanOrEqual(4.5);

                // Day mode injection
                applyScaleAndTokens('normal', accentId, 'day');
                expect(document.documentElement.style.getPropertyValue('--primary')).toBe(token.day.primary);
                expect(document.documentElement.style.getPropertyValue('--primary-foreground')).toBe(
                    token.day.primaryForeground
                );

                const { unmount } = render(
                    <DSButton variant="primary">Acción {token.label}</DSButton>
                );
                expect(screen.getByText(`Acción ${token.label}`)).toBeInTheDocument();
                unmount();

                // Night mode injection
                applyScaleAndTokens('normal', accentId, 'night');
                expect(document.documentElement.style.getPropertyValue('--primary')).toBe(token.night.primary);
                expect(document.documentElement.style.getPropertyValue('--primary-foreground')).toBe(
                    token.night.primaryForeground
                );

                render(<DSButton variant="primary">Acción Noche {token.label}</DSButton>);
                expect(screen.getByText(`Acción Noche ${token.label}`)).toBeInTheDocument();
            });
        });
    });

    describe('3. Automated WCAG 2.1 AA Accessibility (axe-core)', () => {
        it('passes axe check for DSButton (variants, loading, disabled)', async () => {
            const { container } = render(
                <div>
                    <DSButton variant="primary">Primario</DSButton>
                    <DSButton variant="secondary">Secundario</DSButton>
                    <DSButton variant="ghost">Fantasma</DSButton>
                    <DSButton disabled>Deshabilitado</DSButton>
                    <DSButton loading aria-label="Guardando datos">
                        Guardar
                    </DSButton>
                </div>
            );

            const results = await axe(container);
            expect(results.violations).toHaveLength(0);
        });

        it('passes axe check for DSInput (label, helperText, error)', async () => {
            const { container } = render(
                <div>
                    <DSInput label="Email de Contacto" placeholder="correo@ccf.org" />
                    <DSInput
                        label="Contraseña"
                        type="password"
                        error="Mínimo 8 caracteres"
                    />
                    <DSInput
                        label="Teléfono"
                        helperText="Incluya el código de área"
                    />
                </div>
            );

            const results = await axe(container);
            expect(results.violations).toHaveLength(0);
        });

        it('passes axe check for DSCard (tones, content)', async () => {
            const { container } = render(
                <div>
                    <DSCard tone="light">Tarjeta Clara</DSCard>
                    <DSCard tone="dark">Tarjeta Oscura</DSCard>
                    <DSCard tone="glass">Tarjeta Vidrio</DSCard>
                </div>
            );

            const results = await axe(container);
            expect(results.violations).toHaveLength(0);
        });

        it('passes axe check for DSTabs (accessible tablist and panels)', async () => {
            const { container } = render(
                <DSTabs
                    tabs={[
                        { id: 'tab-dashboard', label: 'Dashboard' },
                        { id: 'tab-reports', label: 'Reportes' },
                    ]}
                    panels={{
                        'tab-dashboard': <div>Panel de Control</div>,
                        'tab-reports': <div>Panel de Reportes</div>,
                    }}
                />
            );

            const results = await axe(container);
            expect(results.violations).toHaveLength(0);
        });

        it('passes axe check for DSBadge (all semantic tones)', async () => {
            const { container } = render(
                <div>
                    <DSBadge label="Slate" tone="slate" />
                    <DSBadge label="Blue" tone="blue" />
                    <DSBadge label="Primary" tone="primary" />
                    <DSBadge label="Emerald" tone="emerald" />
                    <DSBadge label="Amber" tone="amber" />
                </div>
            );

            const results = await axe(container);
            expect(results.violations).toHaveLength(0);
        });

        it('passes axe check for DSSelect (label, options, loading)', async () => {
            const { container } = render(
                <DSSelect
                    label="Seleccione un Ministerio"
                    options={[
                        { value: 'evangelismo', label: 'Evangelismo' },
                        { value: 'alabanza', label: 'Alabanza' },
                        { value: 'discipulado', label: 'Discipulado' },
                    ]}
                />
            );

            const results = await axe(container);
            expect(results.violations).toHaveLength(0);
        });

        it('passes axe check for DSMetric (tones, interactive)', async () => {
            const { container } = render(
                <div>
                    <DSMetric label="Total Alumnos" value="340" tone="blue" />
                    <DSMetric label="Nuevos Bautismos" value="52" tone="emerald" />
                    <DSMetric label="Alertas de Asistencia" value="8" tone="amber" />
                    <DSMetric label="Índice Ministerial" value="98%" tone="primary" />
                </div>
            );

            const results = await axe(container);
            expect(results.violations).toHaveLength(0);
        });

        it('passes comprehensive composite suite audit with 0 violations', async () => {
            applyScaleAndTokens('comfortable', 'emerald', 'night');

            const { container } = render(
                <main className="p-6 space-y-6 bg-[hsl(var(--surface-1))]">
                    <h1 className="text-xl font-bold text-[hsl(var(--text-primary))]">
                        Panel Ministerial CCF
                    </h1>

                    <section aria-labelledby="metrics-title" className="grid grid-cols-2 gap-4">
                        <h2 id="metrics-title" className="sr-only">Métricas Generales</h2>
                        <DSMetric label="Crecimiento Anual" value="+14.2%" tone="emerald" trend="+2.4% este mes" />
                        <DSMetric label="Voluntarios Activos" value="184" tone="primary" />
                    </section>

                    <section aria-labelledby="form-title" className="space-y-4">
                        <h2 id="form-title" className="text-base font-semibold text-[hsl(var(--text-primary))]">
                            Formulario de Registro
                        </h2>
                        <DSInput label="Nombre del Líder" placeholder="Pastor o Coordinador" />
                        <DSSelect
                            label="Zona Pastoral"
                            options={[
                                { value: 'norte', label: 'Zona Norte' },
                                { value: 'sur', label: 'Zona Sur' },
                            ]}
                        />
                        <div className="flex items-center gap-2">
                            <DSBadge label="Aprobación Pendiente" tone="amber" />
                            <DSBadge label="Ministerio Acreditado" tone="primary" />
                        </div>
                        <DSButton variant="primary">Guardar Registro</DSButton>
                    </section>
                </main>
            );

            const results = await axe(container);
            expect(results.violations).toHaveLength(0);
        });
    });
});
