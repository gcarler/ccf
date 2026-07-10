"use client";

import React, { useState } from "react";
import { DSBadge } from "@/design/components/DSBadge";
import { DSButton } from "@/design/components/DSButton";
import { DSCard } from "@/design/components/DSCard";
import { DSCommandEntry } from "@/design/components/DSCommandEntry";
import { DSInput } from "@/design/components/DSInput";
import { DSMetric } from "@/design/components/DSMetric";
import { DSModal } from "@/design/components/DSModal";
import { DSSectionHeader } from "@/design/components/DSSectionHeader";
import { DSSelect } from "@/design/components/DSSelect";
import { DSSkeleton } from "@/design/components/DSSkeleton";
import { DSTabs } from "@/design/components/DSTabs";
import { DSToolbarChip } from "@/design/components/DSToolbarChip";
import { DSTooltip } from "@/design/components/DSTooltip";
import { toast } from "@/design/components/DSToast";

export default function CmsUiKitPage() {
  const [activeChip, setActiveChip] = useState("all");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState("tab1");

  return (
    <div className="flex flex-col h-full bg-[#f8f9fc] dark:bg-[hsl(var(--admin-bg-deep))] overflow-y-auto custom-scrollbar">
      <div className="p-4 space-y-4 w-full max-w-6xl mx-auto">
        {/* Header */}
        <div>
          <h1 className="text-xl font-semibold text-[hsl(var(--text-primary))] dark:text-white tracking-tight">
            UI Kit & Design System
          </h1>
          <p className="text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] mt-2 font-medium">
            Catálogo de componentes base (&quot;Clean Productivity&quot;) utilizados en la plataforma administrativa.
          </p>
        </div>

        {/* --- Buttons --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Botones" description="Acciones primarias, secundarias y de variante." />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <DSCard className="p-3 space-y-3">
              <h3 className="text-sm font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Variantes</h3>
              <div className="flex flex-wrap gap-4">
                <DSButton variant="primary">Primary</DSButton>
                <DSButton variant="secondary">Secondary</DSButton>
                <DSButton variant="ghost">Ghost</DSButton>
              </div>
            </DSCard>
            <DSCard className="p-3 space-y-3">
              <h3 className="text-sm font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Estados</h3>
              <div className="flex flex-wrap items-center gap-4">
                <DSButton variant="primary" loading>Cargando</DSButton>
                <DSButton variant="secondary" disabled>Deshabilitado</DSButton>
              </div>
            </DSCard>
          </div>
        </section>

        {/* --- Badges --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Insignias" description="Indicadores visuales de estado y categoría." />
          <DSCard className="p-3">
            <div className="flex flex-wrap gap-4">
              <DSBadge tone="slate" label="Slate" />
              <DSBadge tone="blue" label="Blue" />
              <DSBadge tone="emerald" label="Emerald" />
              <DSBadge tone="amber" label="Amber" />
            </div>
          </DSCard>
        </section>

        {/* --- Cards --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Tarjetas" description="Contenedores estructurados con hover effects opcionales." />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <DSCard className="p-3">
              <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">Básica</h3>
              <p className="text-sm text-[hsl(var(--text-secondary))] mt-2">Contenedor simple con padding y bordes adaptativos.</p>
            </DSCard>
            <DSCard tone="dark" className="p-3">
              <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">Dark</h3>
              <p className="text-sm text-[hsl(var(--text-secondary))] mt-2">Tema oscuro para paneles laterales.</p>
            </DSCard>
            <DSCard tone="glass" className="p-3">
              <h3 className="text-lg font-bold text-[hsl(var(--text-primary))] dark:text-white">Glass</h3>
              <p className="text-sm text-[hsl(var(--text-secondary))] mt-2">Efecto vidrio esmerilado con blur.</p>
            </DSCard>
          </div>
        </section>

        {/* --- Metrics --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Métricas" description="KPIs para dashboards y estadísticas." />
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <DSMetric label="Total Usuarios" value="1,248" trend="+12" tone="blue" />
            <DSMetric label="Nuevos Hoy" value="42" trend="+5" tone="emerald" />
            <DSMetric label="Bajas" value="3" trend="-2" tone="amber" />
            <DSMetric label="Tasa de Actividad" value="89%" tone="blue" />
          </div>
        </section>

        {/* --- Inputs --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Inputs" description="Campos de formulario con labels, errores e iconos." />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <DSCard className="p-3 space-y-4">
              <h3 className="text-sm font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Variantes</h3>
              <DSInput label="Nombre" placeholder="Tu nombre" />
              <DSInput label="Email" placeholder="correo@ejemplo.com" type="email" />
              <DSInput label="Contraseña" type="password" placeholder="••••••••" />
            </DSCard>
            <DSCard className="p-3 space-y-4">
              <h3 className="text-sm font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Estados</h3>
              <DSInput label="Con error" value="valor@invalido" error="Email inválido" />
              <DSInput label="Con helper" placeholder="Opcional" helperText="Este campo es opcional" />
              <DSInput label="Deshabilitado" value="No editable" disabled />
            </DSCard>
          </div>
        </section>

        {/* --- Select --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Select" description="Selects nativos estilizados." />
          <DSCard className="p-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <DSSelect 
                label="País" 
                placeholder="Selecciona un país"
                options={[
                  { value: 'mx', label: 'México' },
                  { value: 'co', label: 'Colombia' },
                  { value: 'ar', label: 'Argentina' },
                ]}
              />
              <DSSelect 
                label="Rol" 
                options={[
                  { value: 'admin', label: 'Administrador' },
                  { value: 'user', label: 'Usuario' },
                ]}
              />
              <DSSelect 
                label="Con error" 
                error="Selecciona una opción"
                options={[{ value: '', label: 'Seleccionar...' }]}
              />
            </div>
          </DSCard>
        </section>

        {/* --- Tabs --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Tabs" description="Navegación por pestañas." />
          <DSCard className="p-3">
            <DSTabs 
              tabs={[
                { id: 'tab1', label: 'General' },
                { id: 'tab2', label: 'Perfil' },
                { id: 'tab3', label: 'Configuración' },
              ]}
              defaultTab={activeTab}
              onChange={setActiveTab}
            >
              <div className="p-3 text-sm text-[hsl(var(--text-secondary))]">
                Contenido de la pestaña <strong>{activeTab}</strong>
              </div>
            </DSTabs>
          </DSCard>
        </section>

        {/* --- Toolbar Chips --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Filtros" description="Píldoras para filtrado de datos." />
          <DSCard className="p-3 flex flex-wrap gap-2">
            {[
              { id: "all", label: "Todos" },
              { id: "active", label: "Activos" },
              { id: "pending", label: "Pendientes" },
              { id: "archived", label: "Archivados" }
            ].map(f => (
              <DSToolbarChip
                key={f.id}
                active={activeChip === f.id}
                onClick={() => setActiveChip(f.id)}
                label={f.label}
              />
            ))}
          </DSCard>
        </section>

        {/* --- Skeletons --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Skeletons" description="Estados de carga para evitar saltos visuales." />
          <DSCard className="p-3 space-y-4">
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Líneas</h3>
              <DSSkeleton rounded="pill" className="h-4 w-3/4" />
              <DSSkeleton rounded="pill" className="h-4 w-1/2" />
              <DSSkeleton rounded="pill" className="h-4 w-full" />
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Perfil</h3>
              <div className="flex items-center gap-4">
                <DSSkeleton rounded="pill" className="size-7" />
                <div className="flex-1 space-y-2">
                  <DSSkeleton rounded="pill" className="h-4 w-48" />
                  <DSSkeleton rounded="pill" className="h-4 w-32" />
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-[hsl(var(--text-secondary))] uppercase tracking-wide">Tarjeta</h3>
              <DSSkeleton rounded="xl" className="h-24 w-full" />
            </div>
          </DSCard>
        </section>

        {/* --- Tooltips --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Tooltips" description="Información adicional al hacer hover." />
          <DSCard className="p-3">
            <div className="flex flex-wrap gap-4">
              <DSTooltip content="Arriba">
                <DSButton variant="secondary">Top</DSButton>
              </DSTooltip>
              <DSTooltip content="Derecha" side="right">
                <DSButton variant="secondary">Right</DSButton>
              </DSTooltip>
              <DSTooltip content="Abajo" side="bottom">
                <DSButton variant="secondary">Bottom</DSButton>
              </DSTooltip>
              <DSTooltip content="Izquierda" side="left">
                <DSButton variant="secondary">Left</DSButton>
              </DSTooltip>
            </div>
          </DSCard>
        </section>

        {/* --- Modal --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Modal" description="Diálogos modales con backdrop." />
          <DSCard className="p-3">
            <DSButton onClick={() => setIsModalOpen(true)}>Abrir Modal</DSButton>
            <DSModal 
              open={isModalOpen} 
              onClose={() => setIsModalOpen(false)} 
              title="Ejemplo de Modal"
            >
              <div className="space-y-3">
                <p className="text-sm text-[hsl(var(--text-secondary))]">
                  Este es un modal de ejemplo con contenido básico.
                </p>
                <div className="flex justify-end gap-2">
                  <DSButton variant="ghost" onClick={() => setIsModalOpen(false)}>
                    Cancelar
                  </DSButton>
                  <DSButton onClick={() => setIsModalOpen(false)}>
                    Aceptar
                  </DSButton>
                </div>
              </div>
            </DSModal>
          </DSCard>
        </section>

        {/* --- Toast --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Toasts" description="Notificaciones efímeras." />
          <DSCard className="p-3">
            <div className="flex flex-wrap gap-2">
              <DSButton onClick={() => toast.success("Operación exitosa")}>
                Success
              </DSButton>
              <DSButton variant="secondary" onClick={() => toast.error("Error al guardar")}>
                Error
              </DSButton>
              <DSButton variant="ghost" onClick={() => toast.warning("Advertencia")}>
                Warning
              </DSButton>
              <DSButton variant="ghost" onClick={() => toast.info("Información")}>
                Info
              </DSButton>
            </div>
          </DSCard>
        </section>

        {/* --- Command Entries --- */}
        <section className="space-y-3">
          <DSSectionHeader title="Command Entries" description="Entradas del palette y acciones rápidas." />
          <DSCard tone="light" className="space-y-2 p-3">
            <DSCommandEntry label="Ir a CRM Pastoral" shortcut="G C" active description="Pipeline, personas y seguimiento." />
            <DSCommandEntry label="Abrir Projects" shortcut="G P" description="Tableros de tareas y recursos." />
            <DSCommandEntry label="Ver Academy" shortcut="G A" description="Cursos, progreso y certificados." />
          </DSCard>
        </section>

        {/* Footer */}
        <div className="pt-4 pb-8 text-center">
          <p className="text-xs text-[hsl(var(--text-secondary))]">
            Design System v1.0 — CCF Platform
          </p>
        </div>
      </div>
    </div>
  );
}
