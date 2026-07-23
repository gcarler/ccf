"use client";

import React from "react";
import { Archive, Copy, Eye, EyeOff, ImageIcon, RotateCcw } from "lucide-react";
import { safeString, asObject } from "@/components/cms/builder/utils";
import OptimizedImage from "@/components/ui/OptimizedImage";
import type { PageBuilderState } from "@/hooks/usePageBuilder";

export default function BuilderSectionInspector({
  builder,
}: {
  builder: PageBuilderState;
}) {
  const {
    activeSection,
    canEdit,
    saveSectionField,
    saveSectionProps,
    updateSectionPropsLocal,
    setSections,
    setMediaPickerTarget,
    setMediaPickerOpen,
    saving,
    upsertArrayItem,
    addArrayItem,
    setSectionVisibility,
    toggleSectionArchive,
    duplicateSection,
  } = builder;
  return (
    <div className="space-y-2 pt-4 border-t border-[hsl(var(--border))] dark:border-white/10">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] font-bold">Inspector sección</p>
            {!activeSection ? (
              <p className="text-xs text-[hsl(var(--text-secondary))]">Selecciona una sección del canvas.</p>
            ) : (
              <fieldset disabled={!canEdit} className="space-y-2.5 disabled:opacity-60">
                <p className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{activeSection.type}</p>

                {/* Hero-specific editor */}
                {activeSection.type === "hero" ? (
                  <div className="space-y-3">
                    <div>
                      <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Eyebrow</label>
                      <input
                        value={safeString(activeSection.props_json?.eyebrow)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), eyebrow: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("eyebrow", e.target.value)}
                        placeholder="UNA COMUNIDAD QUE ILUMINA"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título Lead</label>
                      <input
                        value={safeString(activeSection.props_json?.title_lead)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title_lead: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("title_lead", e.target.value)}
                        placeholder="CCF:"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título Accent (color)</label>
                      <input
                        value={safeString(activeSection.props_json?.title_accent)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title_accent: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("title_accent", e.target.value)}
                        placeholder="Tu Guía,"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título Tail</label>
                      <input
                        value={safeString(activeSection.props_json?.title_tail)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title_tail: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("title_tail", e.target.value)}
                        placeholder="Su Luz"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Descripción</label>
                      <textarea
                        value={safeString(activeSection.props_json?.description)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), description: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("description", e.target.value)}
                        placeholder="Navegando juntos hacia la verdad..."
                        className="w-full min-h-[60px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Primary CTA</label>
                        <input
                          value={safeString(activeSection.props_json?.primary_cta)}
                          onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), primary_cta: e.target.value } } : s))}
                          onBlur={(e) => saveSectionField("primary_cta", e.target.value)}
                          placeholder="Texto botón"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Primary CTA URL</label>
                        <input
                          value={safeString(activeSection.props_json?.primary_cta_href)}
                          onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), primary_cta_href: e.target.value } } : s))}
                          onBlur={(e) => saveSectionField("primary_cta_href", e.target.value)}
                          placeholder="/conocer-a-jesus"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Secondary CTA</label>
                        <input
                          value={safeString(activeSection.props_json?.secondary_cta)}
                          onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), secondary_cta: e.target.value } } : s))}
                          onBlur={(e) => saveSectionField("secondary_cta", e.target.value)}
                          placeholder="Texto botón"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Secondary CTA URL</label>
                        <input
                          value={safeString(activeSection.props_json?.secondary_cta_href)}
                          onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), secondary_cta_href: e.target.value } } : s))}
                          onBlur={(e) => saveSectionField("secondary_cta_href", e.target.value)}
                          placeholder="/predicas"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="text-[9px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Scroll Indicator</label>
                      <input
                        value={safeString(activeSection.props_json?.scroll_indicator)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), scroll_indicator: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("scroll_indicator", e.target.value)}
                        placeholder="Descubrir"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                  </div>
                ) : (
                  <>
                    <input
                      value={safeString(activeSection.props_json?.title)}
                      onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title: e.target.value } } : s))}
                      onBlur={(e) => saveSectionField("title", e.target.value)}
                      placeholder="Título"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <textarea
                      value={safeString(activeSection.props_json?.body)}
                      onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), body: e.target.value } } : s))}
                      onBlur={(e) => saveSectionField("body", e.target.value)}
                      placeholder="Contenido"
                      className="w-full min-h-[90px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      value={safeString(activeSection.props_json?.cta_label)}
                      onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), cta_label: e.target.value } } : s))}
                      onBlur={(e) => saveSectionField("cta_label", e.target.value)}
                      placeholder="Texto CTA"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      value={safeString(activeSection.props_json?.cta_href)}
                      onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), cta_href: e.target.value } } : s))}
                      onBlur={(e) => saveSectionField("cta_href", e.target.value)}
                      placeholder="URL CTA"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </>
                )}

                {(activeSection.type === "hero" || activeSection.type === "gallery") && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      {activeSection.type === "hero" ? "Imagen de fondo" : "Imagen de galeria"}
                    </p>
                    {safeString(activeSection.props_json?.bg_image || activeSection.props_json?.image_url) ? (
                      <div className="overflow-hidden rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5">
                        <OptimizedImage src={safeString(activeSection.props_json?.bg_image || activeSection.props_json?.image_url)} alt={safeString(activeSection.props_json?.image_alt) || "Imagen seleccionada"} width={200} height={112} className="h-28 w-full object-cover" />
                      </div>
                    ) : (
                      <div className="rounded-md border border-dashed border-[hsl(var(--border))] dark:border-white/20 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 text-center text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        Sin imagen seleccionada
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setMediaPickerTarget("section");
                        setMediaPickerOpen(true);
                      }}
                      className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2"
                    >
                      <ImageIcon size={13} /> Elegir de media
                    </button>
                    <input
                      value={safeString(activeSection.props_json?.bg_image || activeSection.props_json?.image_url)}
                      onChange={(e) => {
                        const field = activeSection.type === "hero" ? "bg_image" : "image_url";
                        const nextProps = { ...asObject(activeSection.props_json), [field]: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => {
                        const field = activeSection.type === "hero" ? "bg_image" : "image_url";
                        saveSectionField(field, e.target.value);
                      }}
                      placeholder="URL manual de imagen"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      value={safeString(activeSection.props_json?.image_alt)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), image_alt: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("image_alt", e.target.value)}
                      placeholder="Texto alternativo"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "embed" && (
                  <input
                    value={safeString(activeSection.props_json?.embed_url)}
                    onChange={(e) => {
                      const nextProps = { ...asObject(activeSection.props_json), embed_url: e.target.value };
                      updateSectionPropsLocal(nextProps);
                    }}
                    onBlur={(e) => saveSectionField("embed_url", e.target.value)}
                    placeholder="URL embed (YouTube, Vimeo, etc.)"
                    className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                  />
                )}

                {activeSection.type === "cards" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Items de tarjetas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                      <div key={`card-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                        {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                        <input
                          value={safeString(itemObject.title)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { title: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { title: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Título tarjeta"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <textarea
                          value={safeString(itemObject.body)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { body: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { body: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Descripción tarjeta"
                          className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <input
                          value={safeString(itemObject.icon)}
                          onChange={(e) => upsertArrayItem("items", index, { icon: e.target.value })}
                          onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { icon: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                          placeholder="Icono emoji (ej: 🎯)"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <input
                          value={safeString(itemObject.href)}
                          onChange={(e) => upsertArrayItem("items", index, { href: e.target.value })}
                          onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                          placeholder="URL (opcional, hace la tarjeta clicable)"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <button
                          onClick={() => {
                            const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}
                        >
                          {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                          {isItemArchived ? "Restaurar" : "Archivar"}
                        </button>
                      </div>
                      );
                    })}
                    <button
                      onClick={() => {
                        const nextProps = addArrayItem("items", { title: "Nueva tarjeta", body: "Descripción", status: "published" });
                        if (nextProps) saveSectionProps(nextProps);
                      }}
                      className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"
                    >
                      + Añadir tarjeta
                    </button>
                  </div>
                )}

                {activeSection.type === "faq" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Preguntas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                      <div key={`faq-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                        {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                        <input
                          value={safeString(itemObject.q)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { q: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { q: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Pregunta"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <textarea
                          value={safeString(itemObject.a)}
                          onChange={(e) => {
                            upsertArrayItem("items", index, { a: e.target.value });
                          }}
                          onBlur={(e) => {
                            const nextProps = upsertArrayItem("items", index, { a: e.target.value });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          placeholder="Respuesta"
                          className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                        />
                        <button
                          onClick={() => {
                            const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" });
                            if (nextProps) saveSectionProps(nextProps);
                          }}
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}
                        >
                          {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                          {isItemArchived ? "Restaurar" : "Archivar"}
                        </button>
                      </div>
                      );
                    })}
                    <button
                      onClick={() => {
                        const nextProps = addArrayItem("items", { q: "Nueva pregunta", a: "Respuesta", status: "published" });
                        if (nextProps) saveSectionProps(nextProps);
                      }}
                      className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide"
                    >
                      + Añadir pregunta
                    </button>
                  </div>
                )}

                {activeSection.type === "video_hero" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Video de fondo</p>
                    <input
                      value={safeString(activeSection.props_json?.video_url)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), video_url: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("video_url", e.target.value)}
                      placeholder="URL del video"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "rich_text_columns" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Segunda columna</p>
                    <textarea
                      value={safeString(activeSection.props_json?.body_2)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), body_2: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("body_2", e.target.value)}
                      placeholder="Contenido de la segunda columna"
                      className="w-full min-h-12 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "countdown" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fecha objetivo</p>
                    <input
                      type="datetime-local"
                      value={safeString(activeSection.props_json?.target_date).slice(0, 16)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), target_date: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("target_date", e.target.value)}
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "popup_banner" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Pop-up</p>
                    <input
                      type="number"
                      value={safeString(activeSection.props_json?.delay_ms) || "2000"}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), delay_ms: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("delay_ms", e.target.value)}
                      placeholder="Retraso en milisegundos"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      type="datetime-local"
                      value={safeString(activeSection.props_json?.start_at).slice(0, 16)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), start_at: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("start_at", e.target.value)}
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      type="datetime-local"
                      value={safeString(activeSection.props_json?.end_at).slice(0, 16)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), end_at: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("end_at", e.target.value)}
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <textarea
                      value={Array.isArray(activeSection.props_json?.show_on_paths) ? activeSection.props_json.show_on_paths.join("\n") : safeString(activeSection.props_json?.show_on_paths)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), show_on_paths: e.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionProps({ ...asObject(activeSection.props_json), show_on_paths: e.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) })}
                      placeholder="/\n/nosotros\n/cursos"
                      className="w-full min-h-16 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <textarea
                      value={Array.isArray(activeSection.props_json?.hide_on_paths) ? activeSection.props_json.hide_on_paths.join("\n") : safeString(activeSection.props_json?.hide_on_paths)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), hide_on_paths: e.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionProps({ ...asObject(activeSection.props_json), hide_on_paths: e.target.value.split(/\n|,/).map((item) => item.trim()).filter(Boolean) })}
                      placeholder="/login\n/checkout"
                      className="w-full min-h-16 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <select
                      value={safeString(activeSection.props_json?.dismiss_mode) || "local"}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), dismiss_mode: e.target.value };
                        updateSectionPropsLocal(nextProps);
                        saveSectionField("dismiss_mode", e.target.value);
                      }}
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    >
                      <option value="local">Persistente (localStorage)</option>
                      <option value="session">Solo sesión</option>
                      <option value="none">Sin persistencia</option>
                    </select>
                    <input
                      type="number"
                      value={safeString(activeSection.props_json?.dismiss_days) || "30"}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), dismiss_days: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("dismiss_days", e.target.value)}
                      placeholder="Duración del cierre en días"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      value={safeString(activeSection.props_json?.dismiss_key)}
                      onChange={(e) => {
                        const nextProps = { ...asObject(activeSection.props_json), dismiss_key: e.target.value };
                        updateSectionPropsLocal(nextProps);
                      }}
                      onBlur={(e) => saveSectionField("dismiss_key", e.target.value)}
                      placeholder="Clave de cierre personalizada (opcional)"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "stats" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Metricas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`stat-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.value)} onChange={(e) => upsertArrayItem("items", index, { value: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { value: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Valor: 10K+" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.label)} onChange={(e) => upsertArrayItem("items", index, { label: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Etiqueta" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { value: "0", label: "Nueva metrica", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir metrica
                    </button>
                  </div>
                )}

                {activeSection.type === "team" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Equipo</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`team-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.name)} onChange={(e) => upsertArrayItem("items", index, { name: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { name: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Nombre" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.role)} onChange={(e) => upsertArrayItem("items", index, { role: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { role: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Rol" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.image)} onChange={(e) => upsertArrayItem("items", index, { image: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { image: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL imagen" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar persona" : "Archivar persona"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { name: "Nombre", role: "Rol", image: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir persona
                    </button>
                  </div>
                )}

                {activeSection.type === "pricing" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Planes / donaciones</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`pricing-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.name)} onChange={(e) => upsertArrayItem("items", index, { name: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { name: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Nombre del plan" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.price)} onChange={(e) => upsertArrayItem("items", index, { price: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { price: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Precio" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.features)} onChange={(e) => upsertArrayItem("items", index, { features: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { features: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Beneficios, uno por linea" className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.btn)} onChange={(e) => upsertArrayItem("items", index, { btn: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { btn: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Texto del boton" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.btn_href)} onChange={(e) => upsertArrayItem("items", index, { btn_href: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { btn_href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL del boton (opcional)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <label className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            <input type="checkbox" checked={safeString(itemObject.featured) === "true"} onChange={(e) => { const nextProps = upsertArrayItem("items", index, { featured: String(e.target.checked) }); if (nextProps) saveSectionProps(nextProps); }} />
                            Destacado (featured)
                          </label>
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar plan" : "Archivar plan"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { name: "Nuevo plan", price: "$0", features: "Beneficio", btn: "Seleccionar", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir plan
                    </button>
                  </div>
                )}

                {activeSection.type === "gallery" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Imágenes de galería (items)</p>
                    <p className="text-[9px] text-[hsl(var(--text-secondary))]">Si agregas items aquí se usa galería múltiple; si no, se usa la imagen hero de arriba.</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`gallery-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          {safeString(itemObject.url) && <OptimizedImage src={safeString(itemObject.url)} alt={safeString(itemObject.alt)} width={200} height={80} className="w-full h-20 object-cover rounded-md" />}
                          <input value={safeString(itemObject.url)} onChange={(e) => upsertArrayItem("items", index, { url: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { url: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL de imagen" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.alt)} onChange={(e) => upsertArrayItem("items", index, { alt: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { alt: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Alt text" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.caption)} onChange={(e) => upsertArrayItem("items", index, { caption: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { caption: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Leyenda (opcional)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { url: "", alt: "", caption: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir imagen
                    </button>
                  </div>
                )}

                {activeSection.type === "image_text" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Imagen + Texto</p>
                    <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                      <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Imagen</p>
                      {safeString(activeSection.props_json?.image_url) && (
                        <OptimizedImage src={safeString(activeSection.props_json?.image_url)} alt="" width={200} height={96} className="w-full h-24 object-cover rounded-md" />
                      )}
                      <button type="button" onClick={() => { setMediaPickerTarget("section"); setMediaPickerOpen(true); }} className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2">
                        <ImageIcon size={13} /> Elegir imagen
                      </button>
                      <input value={safeString(activeSection.props_json?.image_url)} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), image_url: e.target.value }; updateSectionPropsLocal(nextProps); }} onBlur={(e) => saveSectionField("image_url", e.target.value)} placeholder="URL manual" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs" />
                      <input value={safeString(activeSection.props_json?.image_alt)} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), image_alt: e.target.value }; updateSectionPropsLocal(nextProps); }} onBlur={(e) => saveSectionField("image_alt", e.target.value)} placeholder="Alt text" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs" />
                    </div>
                    <select value={safeString(activeSection.props_json?.image_side) || "right"} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), image_side: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("image_side", e.target.value); }} className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs">
                      <option value="right">Imagen a la derecha</option>
                      <option value="left">Imagen a la izquierda</option>
                    </select>
                  </div>
                )}

                {activeSection.type === "timeline" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hitos de línea de tiempo</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`timeline-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.year)} onChange={(e) => upsertArrayItem("items", index, { year: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { year: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Año o etiqueta (ej: 2020)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.title)} onChange={(e) => upsertArrayItem("items", index, { title: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { title: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Título del hito" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.body)} onChange={(e) => upsertArrayItem("items", index, { body: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { body: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción" className="w-full min-h-[48px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar hito" : "Archivar hito"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { year: "2024", title: "Nuevo hito", body: "Descripción", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir hito
                    </button>
                  </div>
                )}

                {activeSection.type === "icon_grid" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Items del grid</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`icon-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.icon)} onChange={(e) => upsertArrayItem("items", index, { icon: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { icon: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Emoji icono (ej: 🎯)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.title)} onChange={(e) => upsertArrayItem("items", index, { title: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { title: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Título" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.body)} onChange={(e) => upsertArrayItem("items", index, { body: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { body: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción breve" className="w-full min-h-[48px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { icon: "✨", title: "Nuevo item", body: "Descripción", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir item
                    </button>
                  </div>
                )}

                {activeSection.type === "newsletter" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Suscripción Email</p>
                    <input
                      value={safeString(activeSection.props_json?.action_url)}
                      onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), action_url: e.target.value }; updateSectionPropsLocal(nextProps); }}
                      onBlur={(e) => saveSectionField("action_url", e.target.value)}
                      placeholder="URL de acción (POST con {name, email})"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "cta_banner" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Segundo botón (opcional)</p>
                    <input
                      value={safeString(activeSection.props_json?.cta_label_2)}
                      onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), cta_label_2: e.target.value }; updateSectionPropsLocal(nextProps); }}
                      onBlur={(e) => saveSectionField("cta_label_2", e.target.value)}
                      placeholder="Texto segundo botón"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                    <input
                      value={safeString(activeSection.props_json?.cta_href_2)}
                      onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), cta_href_2: e.target.value }; updateSectionPropsLocal(nextProps); }}
                      onBlur={(e) => saveSectionField("cta_href_2", e.target.value)}
                      placeholder="URL segundo botón"
                      className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                    />
                  </div>
                )}

                {activeSection.type === "testimonials" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Testimonios manuales de esta seccion</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`manual-testimonial-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-[9px] font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.author)} onChange={(e) => upsertArrayItem("items", index, { author: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { author: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Autor" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.role)} onChange={(e) => upsertArrayItem("items", index, { role: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { role: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Rol" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.content)} onChange={(e) => upsertArrayItem("items", index, { content: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { content: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Contenido" className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <select value={safeString(itemObject.stars) || "5"} onChange={(e) => { const nextProps = upsertArrayItem("items", index, { stars: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs">
                            <option value="5">★★★★★ 5 estrellas</option>
                            <option value="4">★★★★☆ 4 estrellas</option>
                            <option value="3">★★★☆☆ 3 estrellas</option>
                          </select>
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { author: "Autor", role: "Rol", content: "Testimonio", stars: "5", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide">
                      + Añadir testimonio
                    </button>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => setSectionVisibility(!activeSection.is_visible)} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1">
                    {activeSection.is_visible ? <EyeOff size={11} /> : <Eye size={11} />} {activeSection.is_visible ? "Ocultar" : "Mostrar"}
                  </button>
                  <button onClick={duplicateSection} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1">
                    <Copy size={11} /> Duplicar
                  </button>
                  <button onClick={toggleSectionArchive} className={`col-span-2 rounded-lg border px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 ${activeSection.status === "archived" ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                    {activeSection.status === "archived" ? <RotateCcw size={11} /> : <Archive size={11} />}
                    {activeSection.status === "archived" ? "Restaurar seccion" : "Archivar seccion"}
                  </button>
                </div>
                <p className="text-[10px] text-[hsl(var(--text-secondary))]">{saving ? "Guardando..." : "Cambios guardados al salir del campo"}</p>
              </fieldset>
            )}
    </div>
  );
}
