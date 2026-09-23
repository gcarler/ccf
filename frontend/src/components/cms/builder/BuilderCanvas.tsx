"use client";

import React, { useState } from "react";
import {
  DndContext,
  DragOverlay,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDndContext,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutPanelTop,
  Eye,
  Pencil,
  Monitor,
  Smartphone,
  Plus,
  ArrowUp,
  ArrowDown,
  Palette,
  RefreshCw,
  Copy,
  Trash2,
  X,
  GripVertical,
} from "lucide-react";
import { SectionPreview, SectionRenderPreview } from "@/components/cms/builder/SectionPreview";
import { SECTION_TYPES, SECTION_TYPE_LABEL } from "@/components/cms/builder/constants";
import { safeString } from "@/components/cms/builder/utils";
import { deleteCmsSection } from "@/lib/cms/v2";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import type { CmsSection } from "@/types/cms-v2";
import { useAuth } from "@/context/AuthContext";
import { usePresence } from "@/hooks/usePresence";


// ── Sortable Section Wrapper Component ──────────────────────────────────────────

interface SortableSectionWrapperProps {
  section: CmsSection;
  index: number;
  totalSections: number;
  activeSectionId: string | null;
  hoveredSectionId: string | null;
  setHoveredSectionId: (id: string | null) => void;
  setActiveSectionId: (id: string | null) => void;
  canvasMode: "esquema" | "render" | "wysiwyg";
  previewDevice: "desktop" | "mobile";
  canvasTokens: React.CSSProperties;
  showHeatmap: boolean;
  heatmapType: "clicks" | "scroll" | "attention";
  canEdit: boolean;
  siteKey: string;
  activeSlug: string;
  token: string | null;
  loadSectionsAndVersions: (slug: string) => Promise<void>;
  builder: PageBuilderState;
}

function SortableSectionWrapper({
  section,
  index,
  totalSections,
  activeSectionId,
  hoveredSectionId,
  setHoveredSectionId,
  setActiveSectionId,
  canvasMode,
  previewDevice,
  canvasTokens,
  showHeatmap,
  heatmapType,
  canEdit,
  siteKey,
  activeSlug,
  token,
  loadSectionsAndVersions,
  builder,
}: SortableSectionWrapperProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: section.id,
    disabled: !canEdit,
  });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  if (isDragging) {
    return (
      <div
        ref={setNodeRef}
        style={style}
        className="opacity-40 border-dashed border-2 border-[hsl(var(--primary))] bg-[hsl(var(--primary)/10%)] rounded-lg min-h-[100px] p-4 flex items-center justify-center transition-all"
      >
        <span className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))] font-mono">
          Moviendo {section.type}...
        </span>
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      onMouseEnter={() => setHoveredSectionId(section.id)}
      onMouseLeave={() => setHoveredSectionId(null)}
      onClick={() => setActiveSectionId(section.id)}
      className={`relative rounded-md border p-3 transition-all cursor-pointer ${
        section.status === "archived"
          ? "opacity-70 border-[hsl(var(--warning)/25%)] bg-[hsl(var(--warning)/10%)]"
          : section.id === activeSectionId
          ? "border-[hsl(var(--primary))] ring-2 ring-[hsl(var(--primary)/40%)] bg-[hsl(var(--primary)/5%)]"
          : hoveredSectionId === section.id && canvasMode !== "esquema"
          ? "border-[hsl(var(--primary))] ring-2 ring-[hsl(var(--primary))] border-2"
          : "border-[hsl(var(--border))]"
      }`}
    >
      {/* Hover Overlay & Section Controls */}
      {hoveredSectionId === section.id && (
        <div className="absolute inset-0 border-2 border-[hsl(var(--primary))] rounded-md pointer-events-none z-20">
          <div
            onPointerDown={(e) => e.stopPropagation()}
            className="absolute -top-3.5 right-3 z-30 flex items-center gap-1 rounded-md border border-[hsl(var(--primary))] bg-[hsl(var(--surface-1))] px-2.5 py-1 shadow-md text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--foreground))] pointer-events-auto"
          >
            {canEdit && (
              <>
                <button
                  type="button"
                  {...listeners}
                  {...attributes}
                  className="inline-flex items-center p-0.5 cursor-grab active:cursor-grabbing text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))]"
                  title="Arrastrar sección"
                  aria-label="Arrastrar sección"
                >
                  <GripVertical size={16} className="cursor-grab active:cursor-grabbing text-[hsl(var(--muted-foreground))]" />
                </button>
                <span className="text-[hsl(var(--border))]">|</span>
              </>
            )}
            <button
              type="button"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={async (e) => {
                e.stopPropagation();
                await builder.moveSection(section.id, "up");
              }}
              disabled={!canEdit || index === 0}
              className="inline-flex items-center gap-1 hover:text-[hsl(var(--primary))] disabled:opacity-40 transition-colors"
              title="Mover arriba"
            >
              <ArrowUp size={11} /> ⬆ Mover arriba
            </button>
            <span className="text-[hsl(var(--border))]">|</span>
            <button
              type="button"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={async (e) => {
                e.stopPropagation();
                await builder.moveSection(section.id, "down");
              }}
              disabled={!canEdit || index === totalSections - 1}
              className="inline-flex items-center gap-1 hover:text-[hsl(var(--primary))] disabled:opacity-40 transition-colors"
              title="Mover abajo"
            >
              <ArrowDown size={11} /> ⬇ Mover abajo
            </button>
            <span className="text-[hsl(var(--border))]">|</span>
            <button
              type="button"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={async (e) => {
                e.stopPropagation();
                if (builder.duplicateSection) {
                  await builder.duplicateSection(section.id);
                }
              }}
              disabled={!canEdit}
              className="inline-flex items-center gap-1 hover:text-[hsl(var(--primary))] disabled:opacity-40 transition-colors"
              title="Duplicar"
            >
              <Copy size={11} /> ⧉ Duplicar
            </button>
            <span className="text-[hsl(var(--border))]">|</span>
            <button
              type="button"
              onPointerDown={(e) => e.stopPropagation()}
              onClick={async (e) => {
                e.stopPropagation();
                if (token && activeSlug) {
                  await deleteCmsSection(siteKey, activeSlug, section.id, token);
                  await loadSectionsAndVersions(activeSlug);
                  if (activeSectionId === section.id) {
                    setActiveSectionId(null);
                  }
                }
              }}
              disabled={!canEdit}
              className="inline-flex items-center gap-1 hover:text-[hsl(var(--destructive))] text-[hsl(var(--destructive))]/90 disabled:opacity-40 transition-colors"
              title="Eliminar"
            >
              <Trash2 size={11} /> ✕ Eliminar
            </button>
          </div>
        </div>
      )}

      {/* Top Bar: Drag Handle + Title + Move Arrows */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {canEdit && (
            <button
              type="button"
              {...attributes}
              {...listeners}
              className="p-1 rounded hover:bg-[hsl(var(--surface-2))] text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--foreground))] transition-colors touch-none shrink-0 cursor-grab active:cursor-grabbing"
              aria-label="Arrastrar para reordenar sección"
              title="Arrastrar para reordenar"
            >
              <GripVertical size={16} className="cursor-grab active:cursor-grabbing text-[hsl(var(--muted-foreground))]" />
            </button>
          )}
          <button
            type="button"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={() => setActiveSectionId(section.id)}
            className="text-left"
          >
            <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))]">
              {section.type} {section.status === "archived" ? "· archivada" : ""}
            </p>
            <p className="text-sm font-bold text-[hsl(var(--foreground))]">
              {safeString(section.props_json?.title) || "Sección"}
            </p>
          </button>
        </div>

        <div className="flex items-center gap-1" onPointerDown={(e) => e.stopPropagation()}>
          <button
            type="button"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              builder.moveSection(section.id, "up");
            }}
            disabled={!canEdit || index === 0}
            className="rounded-lg border border-[hsl(var(--border))] p-1.5 disabled:opacity-50 hover:bg-[hsl(var(--surface-2))] transition-colors text-[hsl(var(--foreground))]"
            aria-label="Subir sección"
            title="Subir sección"
          >
            <ArrowUp size={12} />
          </button>
          <button
            type="button"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              builder.moveSection(section.id, "down");
            }}
            disabled={!canEdit || index === totalSections - 1}
            className="rounded-lg border border-[hsl(var(--border))] p-1.5 disabled:opacity-50 hover:bg-[hsl(var(--surface-2))] transition-colors text-[hsl(var(--foreground))]"
            aria-label="Bajar sección"
            title="Bajar sección"
          >
            <ArrowDown size={12} />
          </button>
        </div>
      </div>

      {/* Main Section Content Preview */}
      <div className="mt-3 relative">
        {canvasMode === "render" || canvasMode === "wysiwyg" ? (
          <SectionRenderPreview
            section={section}
            mobile={previewDevice === "mobile"}
            tokens={canvasTokens}
            canvasMode={canvasMode}
            builder={builder}
          />
        ) : (
          <div style={canvasTokens}>
            <SectionPreview section={section} />
          </div>
        )}

        {/* Heatmap overlay */}
        {showHeatmap && (
          <div data-heatmap-type={heatmapType} className="absolute inset-0 pointer-events-none z-10 overflow-hidden rounded-lg">
            {heatmapType === "clicks" && (
              <div className="absolute inset-0 bg-[hsl(var(--destructive))]/[0.02] backdrop-blur-[0.2px]">
                <div className="absolute top-1/4 left-1/4 w-12 h-12 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.75)_0%,rgba(245,158,11,0.4)_50%,rgba(0,0,0,0)_100%)] animate-pulse inline-flex items-center justify-center">
                  <span className="text-2xs text-[hsl(var(--primary-foreground))] font-bold opacity-80">72%</span>
                </div>
                <div className="absolute top-2/3 left-1/2 w-18 h-18 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.65)_0%,rgba(16,185,129,0.3)_60%,rgba(0,0,0,0)_100%)]" style={{ animationDelay: "300ms" }} />
                <div className="absolute top-1/3 left-2/3 w-14 h-14 rounded-full bg-[radial-gradient(circle,rgba(59,130,246,0.65)_0%,rgba(0,0,0,0)_80%)]" style={{ animationDelay: "600ms" }} />
                <div className="absolute top-1/2 left-[80%] w-10 h-10 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.75)_0%,rgba(0,0,0,0)_90%)]" />
              </div>
            )}
            {heatmapType === "scroll" && (
              <div className="absolute inset-0 flex flex-col justify-between text-2xs font-bold text-[hsl(var(--foreground))]/90">
                <div className="w-full h-[25%] bg-gradient-to-b to-[hsl(var(--success)/20%)] to-transparent border-t border-[hsl(var(--success)/100%)]/40 p-1">100% de usuarios visualizan esta zona (Above the fold)</div>
                <div className="w-full h-[25%] bg-gradient-to-b from-[hsl(var(--warning,var(--primary))/20%)] to-transparent border-t border-[hsl(var(--warning,var(--primary))/40%)] p-1">78% de usuarios se desplazan hasta aquí</div>
                <div className="w-full h-[25%] bg-gradient-to-b from-[hsl(var(--warning,var(--primary))/30%)] to-transparent border-t border-[hsl(var(--warning,var(--primary))/50%)] p-1">45% de usuarios continúan leyendo</div>
                <div className="w-full h-[25%] bg-gradient-to-b from-[hsl(var(--destructive)/20%)] to-[hsl(var(--destructive)/5%)] border-t border-[hsl(var(--destructive)/40%)] p-1">22% de usuarios llegan al final</div>
              </div>
            )}
            {heatmapType === "attention" && (
              <div className="absolute inset-0 bg-[hsl(var(--info))]/[0.02]">
                <div className="absolute top-[30%] left-[20%] w-32 h-32 rounded-full bg-[radial-gradient(circle,rgba(239,68,68,0.45)_0%,rgba(245,158,11,0.25)_40%,rgba(59,130,246,0.1)_70%,transparent_100%)] blur-[4px]" />
                <div className="absolute top-[60%] left-[60%] w-44 h-44 rounded-full bg-[radial-gradient(circle,rgba(245,158,11,0.4)_0%,rgba(16,185,129,0.2)_50%,transparent_100%)] blur-[6px]" />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Active Drag Overlay Component ───────────────────────────────────────────

function ActiveDragOverlay({
  sections,
}: {
  sections: CmsSection[];
}) {
  const { active } = useDndContext();
  const activeDragSection = active ? sections.find((s) => s.id === active.id) : null;
  if (!activeDragSection) return null;

  return (
    <div className="opacity-95 shadow-xl border-2 border-[hsl(var(--primary))] rounded-lg bg-[hsl(var(--surface-1))] p-3 flex items-center justify-between gap-3 cursor-grabbing">
      <div className="flex items-center gap-2">
        <GripVertical size={16} className="cursor-grab active:cursor-grabbing text-[hsl(var(--muted-foreground))]" />
        <div>
          <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">
            {activeDragSection.type}
          </p>
          <p className="text-sm font-bold text-[hsl(var(--foreground))] truncate">
            {safeString(activeDragSection.props_json?.title) || "Sección"}
          </p>
        </div>
      </div>
      <span className="text-2xs font-medium bg-[hsl(var(--primary)/10%)] text-[hsl(var(--primary))] px-2 py-1 rounded font-mono">
        Moviendo...
      </span>
    </div>
  );
}

// ── Main BuilderCanvas Component ─────────────────────────────────────────────

export default function BuilderCanvas({
  builder,
}: {
  builder: PageBuilderState;
}) {
  const {
    sections,
    activeSlug,
    activeSectionId,
    setActiveSectionId,
    newSectionType,
    setNewSectionType,
    addSection,
    canEdit,
    previewDevice,
    setPreviewDevice,
    siteKey,
    token,
    loadSectionsAndVersions,
    canvasTokens,
    canvasThemeName,
    reloadTheme,
    themeLoading,
    showHeatmap,
    heatmapType,
    canvasMode,
    setCanvasMode,
  } = builder;

  const [hoveredSectionId, setHoveredSectionId] = useState<string | null>(null);
  const [showWysiwygBadge, setShowWysiwygBadge] = useState<boolean>(true);
  const [wysiwygBannerSeen, setWysiwygBannerSeen] = useState<boolean>(false);

  // Context Presence Integration
  const auth = useAuth();
  const currentUser = auth?.user ? {
    id: auth.user.id || "anonymous",
    name: auth.user.nombre || auth.user.email || "Usuario",
  } : undefined;

  const { presenceUsers } = usePresence({
    resourceType: "cms_page",
    resourceId: activeSlug || "unselected",
    currentUser,
    token: token || undefined,
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = sections.findIndex((s) => s.id === active.id);
      const newIndex = sections.findIndex((s) => s.id === over.id);
      if (oldIndex !== -1 && newIndex !== -1) {
        await builder.reorderSections(oldIndex, newIndex);
      }
    }
  };

  return (
    <section className="lg:col-span-6 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-4">
      {/* Top Canvas Header Bar */}
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <h2 className="text-lg font-semibold text-[hsl(var(--foreground))]">
            Canvas · {activeSlug ? `/${activeSlug}` : "Selecciona página"}
          </h2>
          {/* Presence Avatar Bar */}
          {presenceUsers.length > 0 && (
            <div className="flex items-center gap-2" title="Usuarios presentes en esta página">
              <div className="flex -space-x-2 overflow-hidden">
                {presenceUsers.slice(0, 4).map((u) => (
                  <div
                    key={u.id}
                    className="relative group flex items-center justify-center size-7 rounded-full text-[hsl(var(--primary-foreground))] text-xs font-bold ring-2 ring-[hsl(var(--surface-1))] cursor-pointer select-none"
                    style={{ backgroundColor: u.color || "hsl(var(--primary))" }}
                  >
                    {u.initials}
                    <div className="absolute top-full mt-1 hidden group-hover:block z-50 whitespace-nowrap rounded bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))] border border-[hsl(var(--border))] text-[10px] py-1 px-2 shadow-lg">
                      {u.name}
                    </div>
                  </div>
                ))}
                {presenceUsers.length > 4 && (
                  <div className="flex items-center justify-center size-7 rounded-full bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] text-xs font-semibold ring-2 ring-[hsl(var(--surface-1))] select-none">
                    +{presenceUsers.length - 4} más
                  </div>
                )}
              </div>
              <span className="text-2xs text-[hsl(var(--muted-foreground))] font-medium">
                {presenceUsers.length === 1
                  ? "1 persona editando ahora"
                  : `${presenceUsers.length} personas editando ahora`}
              </span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">

          {/* Active theme badge + reload + palette hover */}
          <div
            className="hidden sm:inline-flex relative group items-center gap-1.5 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2.5 py-1 text-2xs font-semibold text-[hsl(var(--muted-foreground))] cursor-default"
            title="Tema activo aplicado al canvas"
          >
            <Palette size={10} />
            {canvasThemeName}
            <button
              type="button"
              onClick={reloadTheme}
              disabled={themeLoading}
              className="inline-flex items-center justify-center ml-0.5 disabled:opacity-50"
              title="Recargar tema"
              aria-label="Recargar tema"
            >
              <RefreshCw size={10} className={themeLoading ? "animate-spin" : ""} />
            </button>
            {/* Palette tooltip */}
            <div role="tooltip" className="absolute top-full mt-1.5 right-0 hidden group-hover:block z-50 w-44">
              <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-lg p-2 space-y-1">
                <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--muted-foreground))] px-0.5">
                  Paleta del tema
                </p>
                {Object.entries(canvasTokens)
                  .filter(([k]) => k.startsWith("--site-"))
                  .slice(0, 8)
                  .map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2">
                      <div
                        className="size-4 rounded-sm border border-[hsl(var(--border))] shrink-0"
                        style={{ backgroundColor: value as string }}
                      />
                      <span className="text-2xs font-mono text-[hsl(var(--muted-foreground))] truncate">
                        {key.replace("--site-", "")}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Canvas Mode Toggle */}
          <div className="inline-flex rounded-lg border border-[hsl(var(--border))] overflow-hidden">
            <button
              onClick={() => setCanvasMode("esquema")}
              className={`px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                canvasMode === "esquema" ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" : "bg-transparent text-[hsl(var(--foreground))]"
              }`}
              title="Vista esquemática"
            >
              <LayoutPanelTop size={11} /> Esquema
            </button>
            <button
              onClick={() => setCanvasMode("render")}
              className={`px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                canvasMode === "render" ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" : "bg-transparent text-[hsl(var(--foreground))]"
              }`}
              title="Vista render real"
            >
              <Eye size={11} /> Render
            </button>
            <button
              onClick={() => {
                setCanvasMode("wysiwyg");
                setShowWysiwygBadge(false);
              }}
              className={`relative px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                canvasMode === "wysiwyg" ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" : "bg-transparent text-[hsl(var(--foreground))]"
              }`}
              title="Vista edición WYSIWYG"
            >
              <Pencil size={11} /> ✏ WYSIWYG
              {showWysiwygBadge && (
                <span className="ml-1 rounded-full bg-[hsl(var(--success,var(--primary)))] text-[hsl(var(--primary-foreground))] px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider">
                  Nuevo
                </span>
              )}
            </button>
          </div>

          {/* Device Toggle */}
          <div className="inline-flex rounded-lg border border-[hsl(var(--border))] overflow-hidden">
            <button
              onClick={() => setPreviewDevice("desktop")}
              className={`px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                previewDevice === "desktop" ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" : "bg-transparent text-[hsl(var(--foreground))]"
              }`}
            >
              <Monitor size={11} /> Desktop
            </button>
            <button
              onClick={() => setPreviewDevice("mobile")}
              className={`px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center gap-1 ${
                previewDevice === "mobile" ? "bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]" : "bg-transparent text-[hsl(var(--foreground))]"
              }`}
            >
              <Smartphone size={11} /> Mobile
            </button>
          </div>

          {/* Add Section controls */}
          <select
            value={newSectionType}
            onChange={(e) => setNewSectionType(e.target.value)}
            className="rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm text-[hsl(var(--foreground))]"
          >
            {SECTION_TYPES.map((type) => (
              <option key={type} value={type} className="bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))]">
                {SECTION_TYPE_LABEL[type] ?? type}
              </option>
            ))}
          </select>
          <button
            onClick={() => addSection()}
            disabled={!activeSlug || !canEdit}
            className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide disabled:opacity-50 text-[hsl(var(--foreground))]"
          >
            <Plus size={12} /> Añadir
          </button>
        </div>
      </div>

      {/* Banner Notice */}
      {canvasMode === "wysiwyg" && !wysiwygBannerSeen && (
        <div className="flex items-center justify-between rounded-md border border-[hsl(var(--primary))/30%] bg-[hsl(var(--primary))/10%] px-3 py-2 text-xs text-[hsl(var(--primary))]">
          <span className="flex items-center gap-1.5 font-medium">
            ✏ Doble-click en una sección para editar el texto directamente
          </span>
          <button
            type="button"
            onClick={() => setWysiwygBannerSeen(true)}
            className="text-[hsl(var(--primary))] hover:opacity-75 p-0.5"
            title="Cerrar aviso"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Sortable Section Canvas List */}
      <div className={`space-y-3 ${previewDevice === "mobile" ? "max-w-[420px] mx-auto" : ""}`}>
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragEnd={handleDragEnd}
        >
          <SortableContext items={sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
            <AnimatePresence initial={false}>
              {sections.map((section, index) => (
                <motion.div
                  key={section.id}
                  layout
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 8 }}
                  transition={{ duration: 0.18 }}
                >
                  <SortableSectionWrapper
                    section={section}
                    index={index}
                    totalSections={sections.length}
                    activeSectionId={activeSectionId}
                    hoveredSectionId={hoveredSectionId}
                    setHoveredSectionId={setHoveredSectionId}
                    setActiveSectionId={setActiveSectionId}
                    canvasMode={canvasMode}
                    previewDevice={previewDevice}
                    canvasTokens={canvasTokens}
                    showHeatmap={showHeatmap}
                    heatmapType={heatmapType}
                    canEdit={canEdit}
                    siteKey={siteKey}
                    activeSlug={activeSlug}
                    token={token}
                    loadSectionsAndVersions={loadSectionsAndVersions}
                    builder={builder}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </SortableContext>

          {/* Floating Drag Overlay */}
          <DragOverlay adjustScale={false}>
            <ActiveDragOverlay sections={sections} />
          </DragOverlay>
        </DndContext>

        {sections.length === 0 && (
          <p className="text-sm text-[hsl(var(--muted-foreground))]">
            No hay secciones en esta página.
          </p>
        )}
      </div>
    </section>
  );
}
