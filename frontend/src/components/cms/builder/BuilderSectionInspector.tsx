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
      <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] font-bold">Inspector sección</p>
            {!activeSection ? (
              <p className="text-xs text-[hsl(var(--text-secondary))]">Selecciona una sección del canvas.</p>
            ) : (
              <fieldset disabled={!canEdit} className="space-y-2.5 disabled:opacity-60">
                <p className="text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{activeSection.type}</p>

                {/* Hero-specific editor */}
                {activeSection.type === "hero" ? (
                  <div className="space-y-3">
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Eyebrow</label>
                      <input
                        value={safeString(activeSection.props_json?.eyebrow)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), eyebrow: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("eyebrow", e.target.value)}
                        placeholder="UNA COMUNIDAD QUE ILUMINA"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título Lead</label>
                      <input
                        value={safeString(activeSection.props_json?.title_lead)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title_lead: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("title_lead", e.target.value)}
                        placeholder="CCF:"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título Accent (color)</label>
                      <input
                        value={safeString(activeSection.props_json?.title_accent)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title_accent: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("title_accent", e.target.value)}
                        placeholder="Tu Guía,"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título Tail</label>
                      <input
                        value={safeString(activeSection.props_json?.title_tail)}
                        onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), title_tail: e.target.value } } : s))}
                        onBlur={(e) => saveSectionField("title_tail", e.target.value)}
                        placeholder="Su Luz"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Descripción</label>
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
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Primary CTA</label>
                        <input
                          value={safeString(activeSection.props_json?.primary_cta)}
                          onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), primary_cta: e.target.value } } : s))}
                          onBlur={(e) => saveSectionField("primary_cta", e.target.value)}
                          placeholder="Texto botón"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Primary CTA URL</label>
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
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Secondary CTA</label>
                        <input
                          value={safeString(activeSection.props_json?.secondary_cta)}
                          onChange={(e) => setSections((prev) => prev.map((s) => s.id === activeSection.id ? { ...s, props_json: { ...(s.props_json || {}), secondary_cta: e.target.value } } : s))}
                          onBlur={(e) => saveSectionField("secondary_cta", e.target.value)}
                          placeholder="Texto botón"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Secondary CTA URL</label>
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
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Scroll Indicator</label>
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      {activeSection.type === "hero" ? "Imagen de fondo" : "Imagen de galeria"}
                    </p>
                    {safeString(activeSection.props_json?.bg_image || activeSection.props_json?.image_url) ? (
                      <div className="overflow-hidden rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5">
                        <OptimizedImage src={safeString(activeSection.props_json?.bg_image || activeSection.props_json?.image_url)} alt={safeString(activeSection.props_json?.image_alt) || "Imagen seleccionada"} width={200} height={112} className="h-28 w-full object-cover" />
                      </div>
                    ) : (
                      <div className="rounded-md border border-dashed border-[hsl(var(--border))] dark:border-white/20 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 text-center text-2xs font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        Sin imagen seleccionada
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        setMediaPickerTarget("section");
                        setMediaPickerOpen(true);
                      }}
                      className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2"
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Items de tarjetas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                      <div key={`card-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                        {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
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
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}
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
                      className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide"
                    >
                      + Añadir tarjeta
                    </button>
                  </div>
                )}

                {activeSection.type === "faq" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Preguntas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                      <div key={`faq-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                        {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
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
                          className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}
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
                      className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide"
                    >
                      + Añadir pregunta
                    </button>
                  </div>
                )}

                {activeSection.type === "video_hero" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Video de fondo</p>
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Segunda columna</p>
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Fecha objetivo</p>
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Pop-up</p>
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
                      data-testid="popup-show-on-paths"
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Metricas</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`stat-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.value)} onChange={(e) => upsertArrayItem("items", index, { value: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { value: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Valor: 10K+" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.label)} onChange={(e) => upsertArrayItem("items", index, { label: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Etiqueta" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { value: "0", label: "Nueva metrica", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir metrica
                    </button>
                  </div>
                )}

                {activeSection.type === "team" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Equipo</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`team-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.name)} onChange={(e) => upsertArrayItem("items", index, { name: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { name: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Nombre" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.role)} onChange={(e) => upsertArrayItem("items", index, { role: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { role: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Rol" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.image)} onChange={(e) => upsertArrayItem("items", index, { image: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { image: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL imagen" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar persona" : "Archivar persona"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { name: "Nombre", role: "Rol", image: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir persona
                    </button>
                  </div>
                )}

                {activeSection.type === "pricing" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Planes / donaciones</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`pricing-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.name)} onChange={(e) => upsertArrayItem("items", index, { name: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { name: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Nombre del plan" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.price)} onChange={(e) => upsertArrayItem("items", index, { price: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { price: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Precio" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.features)} onChange={(e) => upsertArrayItem("items", index, { features: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { features: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Beneficios, uno por linea" className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.btn)} onChange={(e) => upsertArrayItem("items", index, { btn: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { btn: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Texto del boton" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.btn_href)} onChange={(e) => upsertArrayItem("items", index, { btn_href: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { btn_href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL del boton (opcional)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            <input type="checkbox" checked={safeString(itemObject.featured) === "true"} onChange={(e) => { const nextProps = upsertArrayItem("items", index, { featured: String(e.target.checked) }); if (nextProps) saveSectionProps(nextProps); }} />
                            Destacado (featured)
                          </label>
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar plan" : "Archivar plan"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { name: "Nuevo plan", price: "$0", features: "Beneficio", btn: "Seleccionar", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir plan
                    </button>
                  </div>
                )}

                {activeSection.type === "gallery" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Imágenes de galería (items)</p>
                    <p className="text-2xs text-[hsl(var(--text-secondary))]">Si agregas items aquí se usa galería múltiple; si no, se usa la imagen hero de arriba.</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`gallery-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          {safeString(itemObject.url) && <OptimizedImage src={safeString(itemObject.url)} alt={safeString(itemObject.alt)} width={200} height={80} className="w-full h-20 object-cover rounded-md" />}
                          <input value={safeString(itemObject.url)} onChange={(e) => upsertArrayItem("items", index, { url: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { url: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL de imagen" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.alt)} onChange={(e) => upsertArrayItem("items", index, { alt: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { alt: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Alt text" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.caption)} onChange={(e) => upsertArrayItem("items", index, { caption: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { caption: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Leyenda (opcional)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { url: "", alt: "", caption: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir imagen
                    </button>
                  </div>
                )}

                {activeSection.type === "image_text" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Imagen + Texto</p>
                    <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                      <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Imagen</p>
                      {safeString(activeSection.props_json?.image_url) && (
                        <OptimizedImage src={safeString(activeSection.props_json?.image_url)} alt="" width={200} height={96} className="w-full h-24 object-cover rounded-md" />
                      )}
                      <button type="button" onClick={() => { setMediaPickerTarget("section"); setMediaPickerOpen(true); }} className="w-full rounded-lg bg-[hsl(var(--primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-white inline-flex items-center justify-center gap-2">
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Hitos de línea de tiempo</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`timeline-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.year)} onChange={(e) => upsertArrayItem("items", index, { year: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { year: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Año o etiqueta (ej: 2020)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.title)} onChange={(e) => upsertArrayItem("items", index, { title: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { title: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Título del hito" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.body)} onChange={(e) => upsertArrayItem("items", index, { body: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { body: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción" className="w-full min-h-[48px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar hito" : "Archivar hito"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { year: "2024", title: "Nuevo hito", body: "Descripción", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir hito
                    </button>
                  </div>
                )}

                {activeSection.type === "icon_grid" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Items del grid</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`icon-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.icon)} onChange={(e) => upsertArrayItem("items", index, { icon: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { icon: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Emoji icono (ej: 🎯)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.title)} onChange={(e) => upsertArrayItem("items", index, { title: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { title: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Título" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.body)} onChange={(e) => upsertArrayItem("items", index, { body: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { body: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción breve" className="w-full min-h-[48px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { icon: "✨", title: "Nuevo item", body: "Descripción", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir item
                    </button>
                  </div>
                )}

                {activeSection.type === "newsletter" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Suscripción Email</p>
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Segundo botón (opcional)</p>
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
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Testimonios manuales de esta seccion</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`manual-testimonial-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.author)} onChange={(e) => upsertArrayItem("items", index, { author: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { author: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Autor" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.role)} onChange={(e) => upsertArrayItem("items", index, { role: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { role: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Rol" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.content)} onChange={(e) => upsertArrayItem("items", index, { content: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { content: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Contenido" className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <select value={safeString(itemObject.stars) || "5"} onChange={(e) => { const nextProps = upsertArrayItem("items", index, { stars: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs">
                            <option value="5">★★★★★ 5 estrellas</option>
                            <option value="4">★★★★☆ 4 estrellas</option>
                            <option value="3">★★★☆☆ 3 estrellas</option>
                          </select>
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { author: "Autor", role: "Rol", content: "Testimonio", stars: "5", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir testimonio
                    </button>
                  </div>
                )}

                {/* ── Divider ───────────────────────────────────────────── */}
                {activeSection.type === "divider" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Divisor</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Estilo de línea</label>
                      <select
                        value={safeString(activeSection.props_json?.style) || "solid"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), style: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("style", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="solid">Sólida</option>
                        <option value="dashed">Discontinua</option>
                        <option value="dotted">Punteada</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Ancho</label>
                      <select
                        value={safeString(activeSection.props_json?.width) || "full"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), width: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("width", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="full">Completo (full)</option>
                        <option value="80%">80%</option>
                        <option value="60%">60%</option>
                        <option value="40%">40%</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Margen superior</label>
                      <input
                        type="number"
                        value={safeString(activeSection.props_json?.margin_top) || "8"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), margin_top: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("margin_top", e.target.value)}
                        placeholder="8"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Margen inferior</label>
                      <input
                        type="number"
                        value={safeString(activeSection.props_json?.margin_bottom) || "8"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), margin_bottom: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("margin_bottom", e.target.value)}
                        placeholder="8"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                  </div>
                )}

                {/* ── Spacer ────────────────────────────────────────────── */}
                {activeSection.type === "spacer" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Espaciador</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Altura (px)</label>
                      <input
                        type="number"
                        value={safeString(activeSection.props_json?.height) || "32"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), height: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("height", e.target.value)}
                        placeholder="32"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Etiqueta (solo para editor)</label>
                      <input
                        value={safeString(activeSection.props_json?.label)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), label: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("label", e.target.value)}
                        placeholder="Espacio"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                  </div>
                )}

                {/* ── Social Links ──────────────────────────────────────── */}
                {activeSection.type === "social_links" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Redes sociales</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Disposición</label>
                      <select
                        value={safeString(activeSection.props_json?.layout) || "row"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), layout: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("layout", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="row">Fila horizontal</option>
                        <option value="column">Columna vertical</option>
                      </select>
                    </div>
                    <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <input
                        type="checkbox"
                        checked={activeSection.props_json?.show_labels !== false}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), show_labels: e.target.checked }; updateSectionPropsLocal(nextProps); saveSectionProps(nextProps); }}
                      />
                      Mostrar etiquetas de texto
                    </label>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      return (
                        <div key={`social-${index}`} className="space-y-2 rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/10 p-2">
                          <select
                            value={safeString(itemObject.platform) || "facebook"}
                            onChange={(e) => { upsertArrayItem("items", index, { platform: e.target.value }); }}
                            onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { platform: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          >
                            <option value="facebook">Facebook</option>
                            <option value="instagram">Instagram</option>
                            <option value="youtube">YouTube</option>
                            <option value="tiktok">TikTok</option>
                            <option value="whatsapp">WhatsApp</option>
                            <option value="twitter">Twitter / X</option>
                            <option value="telegram">Telegram</option>
                            <option value="linkedin">LinkedIn</option>
                            <option value="spotify">Spotify</option>
                            <option value="apple-podcasts">Apple Podcasts</option>
                          </select>
                          <input
                            value={safeString(itemObject.url)}
                            onChange={(e) => upsertArrayItem("items", index, { url: e.target.value })}
                            onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { url: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            placeholder="https://..."
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          />
                          <input
                            value={safeString(itemObject.label)}
                            onChange={(e) => upsertArrayItem("items", index, { label: e.target.value })}
                            onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            placeholder="Etiqueta (opcional)"
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          />
                        </div>
                      );
                    })}
                    <button
                      onClick={() => { const nextProps = addArrayItem("items", { platform: "facebook", url: "https://", label: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }}
                      className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide"
                    >
                      + Añadir red social
                    </button>
                  </div>
                )}

                {/* ── Button ────────────────────────────────────────────── */}
                {activeSection.type === "button" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Botones</p>
                    {(Array.isArray(activeSection.props_json?.buttons) ? activeSection.props_json.buttons : []).map((item, index) => {
                      const itemObject = asObject(item);
                      return (
                        <div key={`btn-${index}`} className="space-y-2 rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/10 p-2">
                          <input
                            value={safeString(itemObject.label)}
                            onChange={(e) => { upsertArrayItem("buttons", index, { label: e.target.value }); }}
                            onBlur={(e) => { const nextProps = upsertArrayItem("buttons", index, { label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            placeholder="Texto del botón"
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          />
                          <input
                            value={safeString(itemObject.href)}
                            onChange={(e) => upsertArrayItem("buttons", index, { href: e.target.value })}
                            onBlur={(e) => { const nextProps = upsertArrayItem("buttons", index, { href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            placeholder="/ruta o https://..."
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          />
                          <div className="grid grid-cols-3 gap-2">
                            <select
                              value={safeString(itemObject.variant) || "primary"}
                              onChange={(e) => { upsertArrayItem("buttons", index, { variant: e.target.value }); }}
                              onBlur={(e) => { const nextProps = upsertArrayItem("buttons", index, { variant: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                              className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                            >
                              <option value="primary">Primario</option>
                              <option value="outline">Contorno</option>
                              <option value="ghost">Fantasma</option>
                            </select>
                            <select
                              value={safeString(itemObject.size) || "md"}
                              onChange={(e) => { upsertArrayItem("buttons", index, { size: e.target.value }); }}
                              onBlur={(e) => { const nextProps = upsertArrayItem("buttons", index, { size: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                              className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                            >
                              <option value="sm">Pequeño</option>
                              <option value="md">Mediano</option>
                              <option value="lg">Grande</option>
                            </select>
                            <input
                              value={safeString(itemObject.icon)}
                              onChange={(e) => upsertArrayItem("buttons", index, { icon: e.target.value })}
                              onBlur={(e) => { const nextProps = upsertArrayItem("buttons", index, { icon: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                              placeholder="🚀"
                              className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                            />
                          </div>
                        </div>
                      );
                    })}
                    <button
                      onClick={() => { const nextProps = addArrayItem("buttons", { label: "Botón", href: "/", variant: "primary", size: "md", status: "published" }); if (nextProps) saveSectionProps(nextProps); }}
                      className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide"
                    >
                      + Añadir botón
                    </button>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Alineación</label>
                      <select
                        value={safeString(activeSection.props_json?.align) || "center"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), align: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("align", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="left">Izquierda</option>
                        <option value="center">Centro</option>
                        <option value="right">Derecha</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Espaciado entre botones</label>
                      <select
                        value={safeString(activeSection.props_json?.gap) || "4"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), gap: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("gap", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="2">Pequeño (2)</option>
                        <option value="4">Mediano (4)</option>
                        <option value="6">Grande (6)</option>
                        <option value="8">Muy grande (8)</option>
                      </select>
                    </div>
                  </div>
                )}

                {/* ── Mobile Menu Config ────────────────────────────────── */}
                {activeSection.type === "mobile_menu_config" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Items del menú móvil</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`mmenu-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.label)} onChange={(e) => upsertArrayItem("items", index, { label: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Etiqueta del item" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.href)} onChange={(e) => upsertArrayItem("items", index, { href: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="/ruta" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.icon)} onChange={(e) => upsertArrayItem("items", index, { icon: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { icon: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="🏠 emoji" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { label: "Nuevo item", href: "/", icon: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir item
                    </button>
                  </div>
                )}

                {/* ── Events Calendar ──────────────────────────────────── */}
                {activeSection.type === "events_calendar" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Calendario de eventos</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título</label>
                      <input
                        value={safeString(activeSection.props_json?.title)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), title: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("title", e.target.value)}
                        placeholder="Próximos Eventos"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Subtítulo</label>
                      <input
                        value={safeString(activeSection.props_json?.subtitle)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), subtitle: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("subtitle", e.target.value)}
                        placeholder="(opcional)"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Máximo de eventos a mostrar</label>
                      <input
                        type="number"
                        value={safeString(activeSection.props_json?.max_events) || "50"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), max_events: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("max_events", e.target.value)}
                        placeholder="50"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <input
                        type="checkbox"
                        checked={activeSection.props_json?.show_filters !== false}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), show_filters: e.target.checked }; updateSectionPropsLocal(nextProps); saveSectionProps(nextProps); }}
                      />
                      Mostrar filtros de categoría
                    </label>
                    <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <input
                        type="checkbox"
                        checked={activeSection.props_json?.show_ics_export !== false}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), show_ics_export: e.target.checked }; updateSectionPropsLocal(nextProps); saveSectionProps(nextProps); }}
                      />
                      Permitir exportar a calendario (.ics)
                    </label>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Mensaje sin eventos</label>
                      <input
                        value={safeString(activeSection.props_json?.empty_title)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), empty_title: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("empty_title", e.target.value)}
                        placeholder="Sin eventos publicados"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                  </div>
                )}

                {/* ── Video Grid ────────────────────────────────────────── */}
                {activeSection.type === "video_grid" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Cuadrícula de videos</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título</label>
                      <input
                        value={safeString(activeSection.props_json?.title)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), title: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("title", e.target.value)}
                        placeholder="Prédicas & Mensajes"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Subtítulo</label>
                      <input
                        value={safeString(activeSection.props_json?.subtitle)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), subtitle: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("subtitle", e.target.value)}
                        placeholder="(opcional)"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">URL del canal (YouTube)</label>
                      <input
                        value={safeString(activeSection.props_json?.channel_url)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), channel_url: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("channel_url", e.target.value)}
                        placeholder="https://youtube.com/@canal"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Texto del botón del canal</label>
                      <input
                        value={safeString(activeSection.props_json?.channel_label) || "Ver canal"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), channel_label: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("channel_label", e.target.value)}
                        placeholder="Ver canal"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Máximo de videos</label>
                      <input
                        type="number"
                        value={safeString(activeSection.props_json?.max_videos) || "12"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), max_videos: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("max_videos", e.target.value)}
                        placeholder="12"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Placeholder de búsqueda</label>
                      <input
                        value={safeString(activeSection.props_json?.search_placeholder)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), search_placeholder: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("search_placeholder", e.target.value)}
                        placeholder="Buscar por título o predicador…"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                  </div>
                )}

                {/* ── Map ──────────────────────────────────────────────── */}
                {activeSection.type === "map" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Mapa</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Título</label>
                      <input
                        value={safeString(activeSection.props_json?.title)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), title: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("title", e.target.value)}
                        placeholder="Encuéntranos"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">URL de embed (Google Maps)</label>
                      <input
                        value={safeString(activeSection.props_json?.embed_url)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), embed_url: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("embed_url", e.target.value)}
                        placeholder="https://www.google.com/maps/embed?..."
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Dirección (texto)</label>
                      <input
                        value={safeString(activeSection.props_json?.address)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), address: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("address", e.target.value)}
                        placeholder="Calle 123, Ciudad"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Altura (px)</label>
                      <input
                        type="number"
                        value={safeString(activeSection.props_json?.height) || "400"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), height: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("height", e.target.value)}
                        placeholder="400"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <input
                        type="checkbox"
                        checked={activeSection.props_json?.show_directions_link !== false}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), show_directions_link: e.target.checked }; updateSectionPropsLocal(nextProps); saveSectionProps(nextProps); }}
                      />
                      Mostrar enlace &quot;Cómo llegar&quot;
                    </label>
                  </div>
                )}

                {/* ── Accordion ───────────────────────────────────────── */}
                {activeSection.type === "accordion" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Acordeón</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Subtítulo</label>
                      <input
                        value={safeString(activeSection.props_json?.subtitle)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), subtitle: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("subtitle", e.target.value)}
                        placeholder="(opcional)"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`acc-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.question)} onChange={(e) => upsertArrayItem("items", index, { question: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { question: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Pregunta / Título de la pestaña" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.answer)} onChange={(e) => upsertArrayItem("items", index, { answer: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { answer: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Respuesta / Contenido" className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { question: "Nueva pregunta", answer: "Respuesta", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir pestaña
                    </button>
                  </div>
                )}

                {/* ── Calendar ─────────────────────────────────────────── */}
                {activeSection.type === "calendar" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Calendario de eventos</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Vista</label>
                      <select
                        value={safeString(activeSection.props_json?.view) || "list"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), view: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("view", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="list">Lista</option>
                        <option value="month">Mensual</option>
                        <option value="week">Semanal</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Máximo de eventos</label>
                      <input
                        type="number"
                        value={safeString(activeSection.props_json?.max_events) || "10"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), max_events: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("max_events", e.target.value)}
                        placeholder="10"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <input type="checkbox" checked={activeSection.props_json?.show_time !== false} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), show_time: e.target.checked }; updateSectionPropsLocal(nextProps); saveSectionProps(nextProps); }} />
                      Mostrar la hora
                    </label>
                    <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <input type="checkbox" checked={activeSection.props_json?.show_location !== false} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), show_location: e.target.checked }; updateSectionPropsLocal(nextProps); saveSectionProps(nextProps); }} />
                      Mostrar la ubicación
                    </label>
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] pt-1">Eventos manuales</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`cal-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.title)} onChange={(e) => upsertArrayItem("items", index, { title: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { title: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Título del evento" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.date)} onChange={(e) => upsertArrayItem("items", index, { date: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { date: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="2026-12-31" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.time)} onChange={(e) => upsertArrayItem("items", index, { time: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { time: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="19:00" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.location)} onChange={(e) => upsertArrayItem("items", index, { location: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { location: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Sede principal" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { title: "Nuevo evento", date: "", time: "", location: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir evento
                    </button>
                  </div>
                )}

                {/* ── Content Blocks ───────────────────────────────────── */}
                {activeSection.type === "content_blocks" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Bloques de contenido</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Disposición</label>
                      <select
                        value={safeString(activeSection.props_json?.layout) || "grid"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), layout: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("layout", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="grid">Cuadrícula</option>
                        <option value="masonry">Mosaico (masonry)</option>
                        <option value="stack">Apilado</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Columnas</label>
                      <select
                        value={safeString(activeSection.props_json?.columns) || "2"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), columns: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("columns", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="2">2 columnas</option>
                        <option value="3">3 columnas</option>
                        <option value="4">4 columnas</option>
                      </select>
                    </div>
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] pt-1">Bloques</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`cb-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <select value={safeString(itemObject.type) || "text"} onChange={(e) => { upsertArrayItem("items", index, { type: e.target.value }); }} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { type: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs">
                            <option value="text">Texto</option>
                            <option value="image">Imagen</option>
                            <option value="video">Video</option>
                            <option value="quote">Cita</option>
                            <option value="divider">Separador</option>
                            <option value="spacer">Espacio</option>
                            <option value="list">Lista</option>
                          </select>
                          {["text", "quote", "list"].includes(safeString(itemObject.type) || "text") && (
                            <textarea value={safeString(itemObject.content)} onChange={(e) => upsertArrayItem("items", index, { content: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { content: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Contenido de texto" className="w-full min-h-[64px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          )}
                          {safeString(itemObject.type) === "video" && (
                            <input value={safeString(itemObject.content)} onChange={(e) => upsertArrayItem("items", index, { content: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { content: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL del video" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          )}
                          {["image", "video", "quote"].includes(safeString(itemObject.type) || "text") && (
                            <>
                              <input value={safeString(itemObject.image_url)} onChange={(e) => upsertArrayItem("items", index, { image_url: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { image_url: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL de imagen (si aplica)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                              <input value={safeString(itemObject.alt)} onChange={(e) => upsertArrayItem("items", index, { alt: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { alt: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Texto alternativo" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                              <input value={safeString(itemObject.caption)} onChange={(e) => upsertArrayItem("items", index, { caption: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { caption: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Leyenda (opcional)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                            </>
                          )}
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { type: "text", content: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir bloque
                    </button>
                  </div>
                )}

                {/* ── Locations List ───────────────────────────────────── */}
                {activeSection.type === "locations_list" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Lista de sedes</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Placeholder de búsqueda</label>
                      <input value={safeString(activeSection.props_json?.search_placeholder)} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), search_placeholder: e.target.value }; updateSectionPropsLocal(nextProps); }} onBlur={(e) => saveSectionField("search_placeholder", e.target.value)} placeholder="Buscar ciudad o dirección..." className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs" />
                    </div>
                    <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                      <input type="checkbox" checked={activeSection.props_json?.show_map !== false} onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), show_map: e.target.checked }; updateSectionPropsLocal(nextProps); saveSectionProps(nextProps); }} />
                      Mostrar mini-mapa por sede
                    </label>
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] pt-1">Sedes</p>
                    {(Array.isArray(activeSection.props_json?.locations) ? activeSection.props_json.locations : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`loc-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.name)} onChange={(e) => upsertArrayItem("locations", index, { name: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("locations", index, { name: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Nombre de la sede" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.address)} onChange={(e) => upsertArrayItem("locations", index, { address: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("locations", index, { address: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Dirección" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.city)} onChange={(e) => upsertArrayItem("locations", index, { city: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("locations", index, { city: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Ciudad" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.phone)} onChange={(e) => upsertArrayItem("locations", index, { phone: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("locations", index, { phone: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Teléfono" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.schedule)} onChange={(e) => upsertArrayItem("locations", index, { schedule: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("locations", index, { schedule: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Horario" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.embed_url)} onChange={(e) => upsertArrayItem("locations", index, { embed_url: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("locations", index, { embed_url: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL de embed de Google Maps" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                            <input type="checkbox" checked={itemObject.is_main === true} onChange={(e) => upsertArrayItem("locations", index, { is_main: e.target.checked })} onBlur={(e) => { const nextProps = upsertArrayItem("locations", index, { is_main: e.target.checked }); if (nextProps) saveSectionProps(nextProps); }} />
                            Sede principal
                          </label>
                          <button onClick={() => { const nextProps = upsertArrayItem("locations", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("locations", { name: "Nueva sede", address: "", city: "", phone: "", schedule: "", embed_url: "", is_main: false, status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir sede
                    </button>
                  </div>
                )}

                {/* ── Civic File Downloads ─────────────────────────────── */}
                {activeSection.type === "civic_file_downloads" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Documentos para descarga</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`cfd-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.name)} onChange={(e) => upsertArrayItem("items", index, { name: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { name: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Nombre del documento" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.file_url)} onChange={(e) => upsertArrayItem("items", index, { file_url: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { file_url: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="URL del archivo (PDF, DOC, etc.)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <div className="grid grid-cols-3 gap-2">
                            <input value={safeString(itemObject.format)} onChange={(e) => upsertArrayItem("items", index, { format: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { format: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="PDF" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                            <input value={safeString(itemObject.size_label)} onChange={(e) => upsertArrayItem("items", index, { size_label: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { size_label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="2.4MB" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                            <input value={safeString(itemObject.description)} onChange={(e) => upsertArrayItem("items", index, { description: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { description: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción corta" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          </div>
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { name: "Nuevo documento", file_url: "", format: "PDF", size_label: "", description: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir documento
                    </button>
                  </div>
                )}

                {/* ── Civic Convocatoria Cards ─────────────────────────── */}
                {activeSection.type === "civic_convocatoria_cards" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Convocatorias</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`ccc-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.title)} onChange={(e) => upsertArrayItem("items", index, { title: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { title: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Título de la convocatoria" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <textarea value={safeString(itemObject.description)} onChange={(e) => upsertArrayItem("items", index, { description: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { description: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción" className="w-full min-h-[48px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.status)} onChange={(e) => upsertArrayItem("items", index, { status: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { status: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Abierta / Cerrada / Próximamente" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.deadline)} onChange={(e) => upsertArrayItem("items", index, { deadline: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { deadline: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Fecha límite (2026-12-31)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.category)} onChange={(e) => upsertArrayItem("items", index, { category: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { category: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Categoría" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.href)} onChange={(e) => upsertArrayItem("items", index, { href: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="/convocatoria/detalle" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { title: "Nueva convocatoria", description: "", status: "published", deadline: "", category: "", href: "" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir convocatoria
                    </button>
                  </div>
                )}

                {/* ── Civic Quick Links ───────────────────────────────── */}
                {activeSection.type === "civic_quick_links" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Accesos rápidos</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Número de columnas</label>
                      <select
                        value={safeString(activeSection.props_json?.columns) || "4"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), columns: e.target.value }; updateSectionPropsLocal(nextProps); saveSectionField("columns", e.target.value); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="2">2</option>
                        <option value="3">3</option>
                        <option value="4">4</option>
                        <option value="5">5</option>
                        <option value="6">6</option>
                      </select>
                    </div>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`cql-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input value={safeString(itemObject.label)} onChange={(e) => upsertArrayItem("items", index, { label: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Etiqueta del acceso" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.href)} onChange={(e) => upsertArrayItem("items", index, { href: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { href: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="/ruta" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.icon)} onChange={(e) => upsertArrayItem("items", index, { icon: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { icon: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="🏛 emoji" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.description)} onChange={(e) => upsertArrayItem("items", index, { description: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { description: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Descripción corta" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <input value={safeString(itemObject.color)} onChange={(e) => upsertArrayItem("items", index, { color: e.target.value })} onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { color: e.target.value }); if (nextProps) saveSectionProps(nextProps); }} placeholder="Color de acento (opcional, hex)" className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs" />
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { icon: "🔗", label: "Nuevo acceso", href: "#", description: "", color: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir acceso
                    </button>
                  </div>
                )}

                {/* ── Animated Counter ─────────────────────────── */}
                {activeSection.type === "animated_counter" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Items del Contador</p>
                    {(Array.isArray(activeSection.props_json?.items) ? activeSection.props_json.items : []).map((item, index) => {
                      const itemObject = asObject(item);
                      const isItemArchived = safeString(itemObject.status) === "archived";
                      return (
                        <div key={`counter-${index}`} className={`space-y-2 rounded-lg border p-2 ${isItemArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isItemArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input
                            value={safeString(itemObject.label)}
                            onChange={(e) => upsertArrayItem("items", index, { label: e.target.value })}
                            onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { label: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            placeholder="Etiqueta (ej: Miembros)"
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          />
                          <div className="grid grid-cols-2 gap-2">
                            <input
                              type="number"
                              value={safeString(itemObject.value)}
                              onChange={(e) => upsertArrayItem("items", index, { value: Number(e.target.value) || 0 })}
                              onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { value: Number(e.target.value) || 0 }); if (nextProps) saveSectionProps(nextProps); }}
                              placeholder="Valor final (ej: 1200)"
                              className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                            />
                            <input
                              type="number"
                              value={safeString(itemObject.duration_ms)}
                              onChange={(e) => upsertArrayItem("items", index, { duration_ms: Number(e.target.value) || 2000 })}
                              onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { duration_ms: Number(e.target.value) || 2000 }); if (nextProps) saveSectionProps(nextProps); }}
                              placeholder="Duración ms (ej: 2000)"
                              className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            <input
                              value={safeString(itemObject.prefix)}
                              onChange={(e) => upsertArrayItem("items", index, { prefix: e.target.value })}
                              onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { prefix: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                              placeholder="Prefijo (ej: $)"
                              className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                            />
                            <input
                              value={safeString(itemObject.suffix)}
                              onChange={(e) => upsertArrayItem("items", index, { suffix: e.target.value })}
                              onBlur={(e) => { const nextProps = upsertArrayItem("items", index, { suffix: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                              placeholder="Sufijo (ej: +)"
                              className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                            />
                          </div>
                          <button onClick={() => { const nextProps = upsertArrayItem("items", index, { status: isItemArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isItemArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isItemArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isItemArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("items", { label: "Nuevo contador", value: 100, prefix: "", suffix: "+", duration_ms: 2000, status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir contador
                    </button>
                  </div>
                )}

                {/* ── Video Embed ─────────────────────────── */}
                {activeSection.type === "video_embed" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Configuración de Video Embed</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">URL de video (YouTube / Vimeo / Directo)</label>
                      <input
                        value={safeString(activeSection.props_json?.video_url)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), video_url: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("video_url", e.target.value)}
                        placeholder="https://www.youtube.com/watch?v=..."
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Leyenda / Caption</label>
                      <textarea
                        value={safeString(activeSection.props_json?.caption)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), caption: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("caption", e.target.value)}
                        placeholder="Descripción del video..."
                        className="w-full min-h-[48px] rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Poster / Imagen de portada (opcional)</label>
                      <input
                        value={safeString(activeSection.props_json?.poster)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), poster: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("poster", e.target.value)}
                        placeholder="https://..."
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <label className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] cursor-pointer">
                      <input
                        type="checkbox"
                        checked={Boolean(activeSection.props_json?.autoplay)}
                        onChange={(e) => {
                          const nextProps = { ...asObject(activeSection.props_json), autoplay: e.target.checked };
                          updateSectionPropsLocal(nextProps);
                          saveSectionProps(nextProps);
                        }}
                        className="rounded border-[hsl(var(--border))]"
                      />
                      Autoplay
                    </label>
                  </div>
                )}

                {/* ── Gallery Masonry ─────────────────────────── */}
                {activeSection.type === "gallery_masonry" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Galería Masonry</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Columnas</label>
                      <select
                        value={safeString(activeSection.props_json?.columns) || "3"}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), columns: Number(e.target.value) || 3 }; updateSectionPropsLocal(nextProps); saveSectionProps(nextProps); }}
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      >
                        <option value="2">2 Columnas</option>
                        <option value="3">3 Columnas</option>
                        <option value="4">4 Columnas</option>
                      </select>
                    </div>
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Imágenes</p>
                    {(Array.isArray(activeSection.props_json?.images) ? activeSection.props_json.images : []).map((img, index) => {
                      const imgObject = asObject(img);
                      const isImgArchived = safeString(imgObject.status) === "archived";
                      return (
                        <div key={`gm-img-${index}`} className={`space-y-2 rounded-lg border p-2 ${isImgArchived ? "border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[hsl(var(--text-secondary))] dark:border-white/10 dark:bg-white/[0.03]" : "border-[hsl(var(--border))]/70 dark:border-white/10"}`}>
                          {isImgArchived && <p className="text-2xs font-semibold uppercase tracking-wide text-warning-text">Archivado</p>}
                          <input
                            value={safeString(imgObject.url)}
                            onChange={(e) => upsertArrayItem("images", index, { url: e.target.value })}
                            onBlur={(e) => { const nextProps = upsertArrayItem("images", index, { url: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            placeholder="URL de la imagen"
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          />
                          <input
                            value={safeString(imgObject.alt)}
                            onChange={(e) => upsertArrayItem("images", index, { alt: e.target.value })}
                            onBlur={(e) => { const nextProps = upsertArrayItem("images", index, { alt: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            placeholder="Texto alternativo (alt)"
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          />
                          <input
                            value={safeString(imgObject.caption)}
                            onChange={(e) => upsertArrayItem("images", index, { caption: e.target.value })}
                            onBlur={(e) => { const nextProps = upsertArrayItem("images", index, { caption: e.target.value }); if (nextProps) saveSectionProps(nextProps); }}
                            placeholder="Leyenda / Caption"
                            className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-2 py-1.5 text-xs"
                          />
                          <button onClick={() => { const nextProps = upsertArrayItem("images", index, { status: isImgArchived ? "published" : "archived" }); if (nextProps) saveSectionProps(nextProps); }} className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-2xs font-semibold uppercase tracking-wide ${isImgArchived ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                            {isImgArchived ? <RotateCcw size={11} /> : <Archive size={11} />}
                            {isImgArchived ? "Restaurar" : "Archivar"}
                          </button>
                        </div>
                      );
                    })}
                    <button onClick={() => { const nextProps = addArrayItem("images", { url: "", alt: "", caption: "", status: "published" }); if (nextProps) saveSectionProps(nextProps); }} className="rounded-md border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1 text-2xs font-semibold uppercase tracking-wide">
                      + Añadir imagen
                    </button>
                  </div>
                )}

                {/* ── Map Embed ─────────────────────────── */}
                {activeSection.type === "map_embed" && (
                  <div className="space-y-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-3 bg-[hsl(var(--surface-1))]/50 dark:bg-white/[0.02]">
                    <p className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Configuración de Mapa Embed</p>
                    <div>
                      <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Dirección</label>
                      <input
                        value={safeString(activeSection.props_json?.address)}
                        onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), address: e.target.value }; updateSectionPropsLocal(nextProps); }}
                        onBlur={(e) => saveSectionField("address", e.target.value)}
                        placeholder="Bogotá, Colombia"
                        className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Latitud</label>
                        <input
                          type="number"
                          step="any"
                          value={safeString(activeSection.props_json?.lat)}
                          onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), lat: e.target.value ? parseFloat(e.target.value) : null }; updateSectionPropsLocal(nextProps); }}
                          onBlur={(e) => { const nextProps = { ...asObject(activeSection.props_json), lat: e.target.value ? parseFloat(e.target.value) : null }; saveSectionProps(nextProps); }}
                          placeholder="4.6097"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Longitud</label>
                        <input
                          type="number"
                          step="any"
                          value={safeString(activeSection.props_json?.lng)}
                          onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), lng: e.target.value ? parseFloat(e.target.value) : null }; updateSectionPropsLocal(nextProps); }}
                          onBlur={(e) => { const nextProps = { ...asObject(activeSection.props_json), lng: e.target.value ? parseFloat(e.target.value) : null }; saveSectionProps(nextProps); }}
                          placeholder="-74.0817"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Zoom (1-20)</label>
                        <input
                          type="number"
                          value={safeString(activeSection.props_json?.zoom) || "14"}
                          onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), zoom: Number(e.target.value) || 14 }; updateSectionPropsLocal(nextProps); }}
                          onBlur={(e) => { const nextProps = { ...asObject(activeSection.props_json), zoom: Number(e.target.value) || 14 }; saveSectionProps(nextProps); }}
                          placeholder="14"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-1 block">Alto (px)</label>
                        <input
                          type="number"
                          value={safeString(activeSection.props_json?.height_px) || "400"}
                          onChange={(e) => { const nextProps = { ...asObject(activeSection.props_json), height_px: Number(e.target.value) || 400 }; updateSectionPropsLocal(nextProps); }}
                          onBlur={(e) => { const nextProps = { ...asObject(activeSection.props_json), height_px: Number(e.target.value) || 400 }; saveSectionProps(nextProps); }}
                          placeholder="400"
                          className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs"
                        />
                      </div>
                    </div>
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2">
                  <button onClick={() => setSectionVisibility(!activeSection.is_visible)} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1">
                    {activeSection.is_visible ? <EyeOff size={11} /> : <Eye size={11} />} {activeSection.is_visible ? "Ocultar" : "Mostrar"}
                  </button>
                  <button onClick={() => duplicateSection()} className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1">
                    <Copy size={11} /> Duplicar
                  </button>
                  <button onClick={() => toggleSectionArchive()} className={`col-span-2 rounded-lg border px-2 py-1.5 text-2xs font-semibold uppercase tracking-wide inline-flex items-center justify-center gap-1 ${activeSection.status === "archived" ? "border-[hsl(var(--success)/25%)] text-success-text" : "border-[hsl(var(--warning)/25%)] text-warning-text"}`}>
                    {activeSection.status === "archived" ? <RotateCcw size={11} /> : <Archive size={11} />}
                    {activeSection.status === "archived" ? "Restaurar seccion" : "Archivar seccion"}
                  </button>
                </div>
                <p className="text-2xs text-[hsl(var(--text-secondary))]">{saving ? "Guardando..." : "Cambios guardados al salir del campo"}</p>
              </fieldset>
            )}
    </div>
  );
}
