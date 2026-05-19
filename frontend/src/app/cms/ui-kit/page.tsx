"use client";

import React, { useState } from "react";
import { DSBadge } from "@/design/components/DSBadge";
import { DSButton } from "@/design/components/DSButton";
import { DSCard } from "@/design/components/DSCard";
import { DSMetric } from "@/design/components/DSMetric";
import { DSSectionHeader } from "@/design/components/DSSectionHeader";
import { DSSkeleton } from "@/design/components/DSSkeleton";
import { DSToolbarChip } from "@/design/components/DSToolbarChip";

export default function CmsUiKitPage() {
  const [activeChip, setActiveChip] = useState("all");

  return (
    <div className="flex flex-col h-full bg-[#f8f9fc] dark:bg-[#0d0e11] overflow-y-auto custom-scrollbar">
      <div className="p-8 space-y-12 max-w-6xl mx-auto w-full">
        <div>
          <h1 className="text-3xl font-black text-slate-900 dark:text-white tracking-tight">UI Kit & Design System</h1>
          <p className="text-slate-500 dark:text-slate-400 mt-2 font-medium">Catálogo de componentes base (&quot;Clean Productivity&quot;) utilizados en la plataforma administrativa.</p>
        </div>

        {/* --- Buttons --- */}
        <section className="space-y-6">
          <DSSectionHeader title="Botones (DSButton)" description="Acciones primarias, secundarias y de variante." />
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <DSCard className="p-6 space-y-6">
              <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest">Variantes</h3>
              <div className="flex flex-wrap gap-4">
                <DSButton variant="primary">Primary</DSButton>
                <DSButton variant="secondary">Secondary</DSButton>
                <DSButton variant="ghost">Ghost</DSButton>
              </div>
            </DSCard>
            <DSCard className="p-6 space-y-6">
              <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest">Estados adicionales</h3>
              <div className="flex flex-wrap items-center gap-4">
                <DSButton variant="primary" loading>Cargando</DSButton>
                <DSButton variant="secondary" disabled>Deshabilitado</DSButton>
              </div>
            </DSCard>
          </div>
        </section>

        {/* --- Badges --- */}
        <section className="space-y-6">
          <DSSectionHeader title="Insignias (DSBadge)" description="Indicadores visuales de estado y categoría." />
          <DSCard className="p-6">
            <div className="flex flex-wrap gap-4">
              <DSBadge tone="slate" label="Slate" />
              <DSBadge tone="blue" label="Blue" />
              <DSBadge tone="emerald" label="Emerald" />
              <DSBadge tone="amber" label="Amber" />
              <DSBadge tone="violet" label="Violet" />
            </div>
          </DSCard>
        </section>

        {/* --- Cards --- */}
        <section className="space-y-6">
          <DSSectionHeader title="Tarjetas (DSCard)" description="Contenedores estructurados con hover effects opcionales." />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <DSCard className="p-6">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Tarjeta Básica</h3>
              <p className="text-sm text-slate-500 mt-2">Contenedor simple con padding y bordes adaptativos.</p>
            </DSCard>
            <DSCard className="p-6 transition-all hover:shadow-xl hover:-translate-y-1">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Hoverable</h3>
              <p className="text-sm text-slate-500 mt-2">Se eleva y cambia de borde al hacer hover. Usado en listas clickeables.</p>
            </DSCard>
            <DSCard>
              <div className="p-5 border-b border-slate-100 dark:border-white/5">
                <h3 className="text-sm font-black text-slate-900 dark:text-white uppercase tracking-widest">Con Header/Footer</h3>
              </div>
              <div className="p-5">
                <p className="text-sm text-slate-500">Cuerpo de la tarjeta sin padding extra.</p>
              </div>
              <div className="p-4 bg-slate-50 dark:bg-white/5 border-t border-slate-100 dark:border-white/5 rounded-b-2xl flex justify-end">
                <DSButton variant="secondary">Acción</DSButton>
              </div>
            </DSCard>
          </div>
        </section>

        {/* --- Metrics --- */}
        <section className="space-y-6">
          <DSSectionHeader title="Métricas (DSMetric)" description="KPIs para dashboards y estadísticas." />
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <DSMetric label="Total Usuarios" value="1,248" trend="+12" tone="blue" />
            <DSMetric label="Nuevos Hoy" value="42" trend="+5" tone="emerald" />
            <DSMetric label="Bajas" value="3" trend="-2" tone="amber" />
            <DSMetric label="Tasa de Actividad" value="89%" tone="violet" />
          </div>
        </section>

        {/* --- Toolbar Chips --- */}
        <section className="space-y-6">
          <DSSectionHeader title="Filtros (DSToolbarChip)" description="Píldoras para filtrado de datos." />
          <DSCard className="p-6 flex flex-wrap gap-2">
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
        <section className="space-y-6">
          <DSSectionHeader title="Skeletons (DSSkeleton)" description="Estados de carga para evitar saltos visuales." />
          <DSCard className="p-6 space-y-8">
            <div className="space-y-3">
              <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest">Líneas</h3>
              <DSSkeleton rounded="pill" className="h-4 w-3/4" />
              <DSSkeleton rounded="pill" className="h-4 w-1/2" />
              <DSSkeleton rounded="pill" className="h-4 w-full" />
            </div>
            <div className="space-y-3">
              <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest">Perfil</h3>
              <div className="flex items-center gap-4">
                <DSSkeleton rounded="pill" className="size-12" />
                <div className="flex-1 space-y-2">
                  <DSSkeleton rounded="pill" className="h-4 w-48" />
                  <DSSkeleton rounded="pill" className="h-4 w-32" />
                </div>
              </div>
            </div>
            <div className="space-y-3">
              <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest">Tarjeta/Imagen</h3>
              <DSSkeleton rounded="xl" className="h-32 w-full" />
            </div>
          </DSCard>
        </section>

      </div>
    </div>
  );
}
