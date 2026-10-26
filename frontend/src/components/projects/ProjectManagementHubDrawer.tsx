"use client";

import React, { useState, useMemo } from "react";
import { Maximize2, Minimize2, X, type LucideIcon } from "lucide-react";
import clsx from "clsx";
import { RightPanel } from "@/components/ui/RightPanel";

/**
 * Llaves canónicas de los módulos de gestión, control y gobernanza del hub.
 * El orden de la unión define el orden estable de la tira de pestañas.
 */
export type ProjectHubModuleKey =
  | 'components'
  | 'wbs'
  | 'pmo'
  | 'labels'
  | 'kpis'
  | 'progress'
  | 'budget'
  | 'risks'
  | 'workload'
  | 'time'
  | 'templates'
  | 'automations'
  | 'reports'
  | 'indicators'
  | 'ccb'
  | 'evm'
  | 'drive'
  | 'governance';

export interface ProjectHubModuleMeta {
  key: ProjectHubModuleKey;
  label: string;
  icon: LucideIcon;
}

interface ProjectManagementHubDrawerProps {
  /** Hub abierto — true cuando hay al menos una pestaña de módulo abierta. */
  isOpen: boolean;
  /** Llaves de módulos con pestaña abierta (orden en que se abrieron). */
  openModules: readonly ProjectHubModuleKey[];
  /** Metadatos (etiqueta + icono) de los módulos, en su orden canónico. */
  moduleMeta: ProjectHubModuleMeta[];
  /** Módulo activo: el único cuyo contenido se monta (sin drawers apilados). */
  activeModule: ProjectHubModuleKey | null;
  /** Activar (o reactivar) la pestaña de un módulo. */
  onActivateModule: (key: ProjectHubModuleKey) => void;
  /** Cerrar la pestaña individual de un módulo. */
  onCloseModule: (key: ProjectHubModuleKey) => void;
  /** Cerrar el hub completo (todas las pestañas). */
  onCloseHub: () => void;
  /** Título del hub sobre el panel. */
  title?: string;
  /**
   * Modo incrustado: cuando true, el RightPanel no se fija a la ventana
   * (se usa cuando el hub se monta dentro de otro contenedor de herramientas).
   */
  embedded?: boolean;
  /**
   * Desplazamiento lateral (px) para coexistir con paneles adyacentes: el hub
   * NO es modal (sin backdrop ni focus-trap), así que se retira del borde
   * derecho el ancho del sidebar de contexto del proyecto para no taparlo.
   */
  offsetRight?: number;
  /**
   * Renderers por módulo. Solo se invoca el del módulo activo, de modo que
   * nunca coexisten múltiples panels de módulo superpuestos.
   */
  moduleRenderers: Partial<
    Record<ProjectHubModuleKey, () => React.ReactNode>
  >;
}

/**
 * ProjectManagementHubDrawer — Hub unificado de pestañas para los módulos de
 * gestión y control de un proyecto (KPIs, Avance, Presupuesto, Riesgos, Carga,
 * Horas, Plantillas, Automatizaciones, Reportes, Indicadores IDP, EVM y
 * Bóveda/Drive, además de la Gobernanza PMI del ciclo de vida).
 *
 * Garantías del hub:
 *  - Un único panel lateral contenedor: los módulos participan como pestañas,
 *    nunca como drawers apilados en cascada.
 *  - Cada pestaña es activable y cerrable individualmente (botón X propio).
 *  - Botón de pantalla completa (Maximize2/Minimize2) para extender el panel.
 */
export function ProjectManagementHubDrawer({
  isOpen,
  openModules,
  moduleMeta,
  activeModule,
  onActivateModule,
  onCloseModule,
  onCloseHub,
  title = 'Centro de gestión del proyecto',
  embedded,
  offsetRight,
  moduleRenderers,
}: ProjectManagementHubDrawerProps) {
  const [isMaximized, setIsMaximized] = useState(false);

  const openMeta = useMemo(
    () =>
      openModules
        .map(key => moduleMeta.find(meta => meta.key === key))
        .filter((meta): meta is ProjectHubModuleMeta => Boolean(meta)),
    [openModules, moduleMeta]
  );

  const activeRenderer =
    activeModule != null ? moduleRenderers[activeModule] : undefined;

  return (
    <RightPanel
      embedded={embedded}
      hasBackdrop={false}
      offsetRight={offsetRight}
      open={isOpen}
      onClose={onCloseHub}
      title={title}
      subtitle="Navega entre los módulos de control con pestañas"
      width={isMaximized ? 'w-screen max-w-none' : 'w-full sm:w-[90vw] lg:w-[78vw] xl:w-[74vw] 2xl:w-[70vw] max-w-none'}
      resizeStorageKey="workspace:project_tools_width"
      resizeDefaultWidth={960}
      maximized={isMaximized}
      contentClassName="bg-[hsl(var(--surface-1))] flex flex-col"
    >
      {isOpen && (
        <div
          className={clsx(
            'flex h-full min-h-0 flex-col',
            isMaximized && 'mx-auto w-full px-4 sm:px-6 lg:px-8'
          )}
        >
          <div className="shrink-0 border-b border-[hsl(var(--border))] px-3 py-2">
            <select
              aria-label="Abrir herramienta"
              value=""
              onChange={event => {
                const selected = moduleMeta.find(module => module.key === event.currentTarget.value);
                if (selected) onActivateModule(selected.key);
              }}
              className="w-full min-w-0 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-xs text-[hsl(var(--foreground))]"
            >
              <option value="">Abrir herramienta…</option>
              {moduleMeta.map(module => <option key={module.key} value={module.key}>{module.label}</option>)}
            </select>
          </div>
          {/* Tira de pestañas abiertas + controles del panel */}
          <div className="flex min-h-10 shrink-0 items-center gap-1 overflow-x-auto border-b border-[hsl(var(--border))] px-3 py-1.5">
            <div
              role="tablist"
              aria-label="Módulos de gestión abiertos"
              className="flex min-w-0 flex-1 items-center gap-1"
            >
              {openMeta.map(({ key, label, icon }) => {
                const TabIcon = icon;
                const isActive = key === activeModule;
                return (
                  <div
                    key={key}
                    role="tab"
                    aria-selected={isActive}
                    tabIndex={0}
                    onClick={() => onActivateModule(key)}
                    onKeyDown={event => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        onActivateModule(key);
                      }
                    }}
                    className={clsx(
                      'group flex shrink-0 cursor-pointer items-center gap-1.5 rounded-md border px-2 py-1 text-2xs font-semibold transition-colors',
                      isActive
                        ? 'border-[hsl(var(--primary)/0.45)] bg-[hsl(var(--primary)/0.12)] text-[hsl(var(--primary))]'
                        : 'border-transparent text-[hsl(var(--text-secondary))] hover:border-[hsl(var(--border))] hover:bg-[hsl(var(--surface-2))]'
                    )}
                  >
                    <TabIcon size={13} aria-hidden="true" className="shrink-0" />
                    <span className="max-w-[10rem] truncate">{label}</span>
                    <button
                      type="button"
                      aria-label={`Cerrar ${label}`}
                      onClick={event => {
                        event.stopPropagation();
                        onCloseModule(key);
                      }}
                      className={clsx(
                        'flex items-center justify-center rounded p-0.5 text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--destructive))]',
                        !isActive && 'opacity-60 group-hover:opacity-100'
                      )}
                    >
                      <X size={12} aria-hidden="true" />
                    </button>
                  </div>
                );
              })}
            </div>
            <div className="ml-2 flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={() => setIsMaximized(prev => !prev)}
                aria-label={
                  isMaximized
                    ? 'Salir de pantalla completa'
                    : 'Pantalla completa'
                }
                title={
                  isMaximized
                    ? 'Salir de pantalla completa'
                    : 'Pantalla completa'
                }
                className="flex size-7 items-center justify-center rounded-md border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-2))] hover:text-[hsl(var(--foreground))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--primary))]"
              >
                {isMaximized ? (
                  <Minimize2 size={14} aria-hidden="true" />
                ) : (
                  <Maximize2 size={14} aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          {/* Contenido del módulo activo — solo se monta una pestaña a la vez */}
          <div
            role="tabpanel"
            aria-label={activeMetaLabel(openMeta, activeModule)}
            className="min-h-0 flex-1 overflow-y-auto"
          >
            {activeRenderer ? activeRenderer() : null}
          </div>
        </div>
      )}
    </RightPanel>
  );
}

function activeMetaLabel(
  openMeta: ProjectHubModuleMeta[],
  activeModule: ProjectHubModuleKey | null
) {
  if (activeModule == null) return 'Sin módulo activo';
  return openMeta.find(meta => meta.key === activeModule)?.label ?? activeModule;
}

export default ProjectManagementHubDrawer;
