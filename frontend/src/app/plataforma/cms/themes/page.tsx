"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SITE_KEY } from "@/lib/site-config";
import {
  Archive,
  CheckCircle2,
  ChevronDown,
  Copy,
  Download,
  ExternalLink,
  Eye,
  FileJson,
  Layers,
  Palette,
  RotateCcw,
  Save,
  Sparkles,
  Trash2,
  Upload,
  Wand2,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import {
  activateCmsTheme,
  createCmsTheme,
  deleteCmsTheme as archiveCmsTheme,
  listCmsSites,
  listCmsThemes,
  patchCmsTheme,
} from "@/lib/cms/v2";
import { canEditCms, canPublishCms } from "@/lib/cms/permissions";
import {
  ALL_TOKEN_KEYS,
  applyPreset,
  buildDefaultTokens,
  THEME_PRESETS,
  TOKEN_CATEGORIES,
} from "@/components/cms/themes/themeTokens";
import ThemePreview from "@/components/cms/themes/ThemePreview";
import { toast } from "sonner";

/* ── Types ── */
interface CmsTheme {
  id: string;
  name: string;
  is_active: boolean;
  status?: string;
  tokens_json?: Record<string, string>;
}

interface CmsSite {
  site_key: string;
  name: string;
}

/* ── Helpers ── */
function isColorToken(type: string, value: string): boolean {
  if (type === "color" || type === "gradient" || type === "shadow") return true;
  return (
    value.startsWith("#") ||
    value.startsWith("rgb") ||
    value.startsWith("hsl") ||
    value.startsWith("rgba") ||
    value.startsWith("linear-gradient") ||
    value.startsWith("radial-gradient")
  );
}

function hexFromAny(value: string): string {
  if (value.startsWith("#")) return value;
  const m = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (m) {
    const toHex = (n: string) => parseInt(n).toString(16).padStart(2, "0");
    return `#${toHex(m[1])}${toHex(m[2])}${toHex(m[3])}`;
  }
  return "#000000";
}

function updateTokenValue(prev: Record<string, string>, key: string, value: string): Record<string, string> {
  return { ...prev, [key]: value };
}

/* ── Component ── */
export default function CmsThemesPage() {
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState(SITE_KEY);
  const [sites, setSites] = useState<CmsSite[]>([]);
  const [themes, setThemes] = useState<CmsTheme[]>([]);
  const [name, setName] = useState("Tema personalizado");
  const [tokens, setTokens] = useState<Record<string, string>>(buildDefaultTokens);
  const [editingThemeId, setEditingThemeId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null);
  const [expandedCats, setExpandedCats] = useState<Set<string>>(new Set(["colors"]));
  const [showPreview, setShowPreview] = useState(true);
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const canEdit = canEditCms(user?.role);
  const canPublish = canPublishCms(user?.role);

  const load = useCallback(
    async (activeSite: string) => {
      if (!token) return;
      const [nextSites, nextThemes] = await Promise.all([
        listCmsSites(token),
        listCmsThemes(activeSite, token),
      ]);
      setSites(
        (nextSites || []).map((site: CmsSite) => ({
          site_key: site.site_key,
          name: site.name,
        }))
      );
      setThemes(
        (nextThemes || []).map((theme: CmsTheme) => ({
          id: theme.id,
          name: theme.name,
          is_active: theme.is_active,
          status: theme.status || "active",
          tokens_json: theme.tokens_json,
        }))
      );
    },
    [token]
  );

  useEffect(() => {
    load(siteKey).catch(() => toast.error("Error al cargar temas"));
    setEditingThemeId(null);
  }, [token, siteKey, load]);

  /* ── Actions ── */
  const saveTheme = async () => {
    if (!token || !canEdit) return;
    setSaving(true);
    setMessage(null);
    try {
      const payload = { name, tokens_json: tokens, is_active: canPublish, status: "active" };
      if (editingThemeId) {
        await patchCmsTheme(siteKey, editingThemeId, payload, token);
        if (canPublish) {
          await activateCmsTheme(siteKey, editingThemeId, token);
          setMessage({ text: "Tema actualizado y activado.", type: "success" });
        } else {
          setMessage({ text: "Tema actualizado. Solo un publicador puede activarlo.", type: "info" });
        }
      } else {
        const created = await createCmsTheme(siteKey, payload, token);
        if (canPublish) {
          await activateCmsTheme(siteKey, created.id, token);
          setMessage({ text: "Tema guardado y activado.", type: "success" });
        } else {
          setMessage({ text: "Tema guardado. Solo un publicador puede activarlo.", type: "info" });
        }
      }
      await load(siteKey);
    } catch {
      setMessage({ text: "No se pudo guardar el tema.", type: "error" });
    } finally {
      setSaving(false);
    }
  };

  const activate = async (themeId: string) => {
    if (!token || !canPublish) return;
    await activateCmsTheme(siteKey, themeId, token);
    setMessage({ text: "Tema activado.", type: "success" });
    await load(siteKey);
  };

  const archive = async (themeId: string) => {
    if (!token || !canPublish) return;
    await archiveCmsTheme(siteKey, themeId, token);
    if (editingThemeId === themeId) {
      setEditingThemeId(null);
      setName("Tema personalizado");
      setTokens(buildDefaultTokens());
    }
    setMessage({ text: "Tema archivado.", type: "info" });
    await load(siteKey);
  };

  const restore = async (themeId: string) => {
    if (!token || !canEdit) return;
    await patchCmsTheme(siteKey, themeId, { status: "active", is_active: false }, token);
    setMessage({ text: "Tema restaurado.", type: "success" });
    await load(siteKey);
  };

  const applyPresetToEditor = (presetKey: string) => {
    const preset = applyPreset(presetKey);
    setTokens(preset);
    setName(THEME_PRESETS.find((p) => p.key === presetKey)?.name || "Tema personalizado");
    setEditingThemeId(null);
    setMessage({ text: `Preset "${presetKey}" aplicado.`, type: "info" });
  };

  const exportJson = () => {
    const data = JSON.stringify({ name, tokens_json: tokens }, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${name.replace(/\s+/g, "_").toLowerCase()}_theme.json`;
    a.click();
    URL.revokeObjectURL(url);
    setMessage({ text: "JSON exportado.", type: "success" });
  };

  const importJson = () => {
    try {
      const parsed = JSON.parse(importText);
      if (parsed.tokens_json && typeof parsed.tokens_json === "object") {
        setTokens(parsed.tokens_json);
        if (parsed.name) setName(parsed.name);
        setEditingThemeId(null);
        setImportOpen(false);
        setImportText("");
        setMessage({ text: "Tema importado correctamente.", type: "success" });
      } else {
        throw new Error("Formato inválido");
      }
    } catch {
      setMessage({ text: "JSON inválido. Asegúrate de que tenga tokens_json.", type: "error" });
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      setImportText(String(ev.target?.result || ""));
      setImportOpen(true);
    };
    reader.readAsText(file);
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(tokens, null, 2));
      setMessage({ text: "Tokens copiados al portapapeles.", type: "success" });
    } catch {
      setMessage({ text: "No se pudo copiar.", type: "error" });
    }
  };

  const toggleCat = (id: string) => {
    setExpandedCats((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const usedTokensCount = useMemo(() => {
    return Object.keys(tokens).filter((k) => ALL_TOKEN_KEYS.includes(k)).length;
  }, [tokens]);

  return (
    <div className="space-y-4 p-4 max-w-[1600px] mx-auto">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
              CMS V2
            </span>
            <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full bg-primary/10 text-primary">
              {usedTokensCount} tokens
            </span>
          </div>
          <h1 className="text-lg font-bold tracking-tight flex items-center gap-2">
            <Palette size={20} className="text-primary" />
            Editor de Temas
          </h1>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowPreview((p) => !p)}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-[11px] font-bold uppercase tracking-wider transition-all ${
              showPreview
                ? "border-primary/30 bg-primary/10 text-primary"
                : "border-[hsl(var(--border))] dark:border-white/10"
            }`}
          >
            <Eye size={13} />
            {showPreview ? "Preview On" : "Preview Off"}
          </button>
          <button
            onClick={exportJson}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-[11px] font-bold uppercase tracking-wider hover:bg-[hsl(var(--bg-secondary))] transition-colors"
          >
            <Download size={13} />
            Exportar
          </button>
          <button
            onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-[11px] font-bold uppercase tracking-wider hover:bg-[hsl(var(--bg-secondary))] transition-colors"
          >
            <Upload size={13} />
            Importar
          </button>
          <input ref={fileRef} type="file" accept=".json" className="hidden" onChange={handleFileUpload} />
          <button
            onClick={copyToClipboard}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-2 text-[11px] font-bold uppercase tracking-wider hover:bg-[hsl(var(--bg-secondary))] transition-colors"
          >
            <Copy size={13} />
            Copiar
          </button>
        </div>
      </div>

      {/* ── Message Banner ── */}
      {message && (
        <div
          className={`rounded-lg px-4 py-2.5 text-xs font-semibold flex items-center gap-2 animate-fade-in-up ${
            message.type === "success"
              ? "bg-emerald-500/10 border border-emerald-500/20 text-emerald-400"
              : message.type === "error"
              ? "bg-red-500/10 border border-red-500/20 text-red-400"
              : "bg-amber-500/10 border border-amber-500/20 text-amber-400"
          }`}
        >
          {message.type === "success" && <CheckCircle2 size={14} />}
          {message.type === "error" && <Trash2 size={14} />}
          {message.type === "info" && <Sparkles size={14} />}
          {message.text}
          <button onClick={() => setMessage(null)} className="ml-auto opacity-60 hover:opacity-100">
            <Trash2 size={12} />
          </button>
        </div>
      )}

      {/* ── Presets ── */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Wand2 size={14} className="text-primary" />
          <h2 className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
            Presets rápidos
          </h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          {THEME_PRESETS.map((preset) => (
            <button
              key={preset.key}
              onClick={() => applyPresetToEditor(preset.key)}
              className="group relative rounded-xl border border-[hsl(var(--border))] dark:border-white/10 p-3 text-left transition-all hover:scale-[1.02] hover:border-primary/30 hover:shadow-lg"
              style={{ background: "hsl(var(--bg-primary))" }}
            >
              <div className="flex items-center gap-2 mb-2">
                <div
                  className="w-6 h-6 rounded-md border shadow-sm"
                  style={{
                    background: preset.tokens["--site-primary"],
                    borderColor: preset.tokens["--site-outline-variant"],
                  }}
                />
                <div
                  className="w-6 h-6 rounded-md border shadow-sm"
                  style={{
                    background: preset.tokens["--site-background"],
                    borderColor: preset.tokens["--site-outline-variant"],
                  }}
                />
              </div>
              <p className="text-xs font-bold">{preset.name}</p>
              <p className="text-[10px] opacity-60 mt-0.5 line-clamp-2">{preset.description}</p>
              <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <Sparkles size={12} className="text-primary" />
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Main Grid ── */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-4">
        {/* ── Left: Editor ── */}
        <div className="xl:col-span-5 space-y-4">
          {/* Site & Name */}
          <div className="rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                  Sitio
                </label>
                <select
                  value={siteKey}
                  onChange={(e) => setSiteKey(e.target.value)}
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs outline-none focus:ring-1 focus:ring-primary/50"
                >
                  {sites.length === 0 && <option value={SITE_KEY}>{SITE_KEY}</option>}
                  {sites.map((site) => (
                    <option key={site.site_key} value={site.site_key}>
                      {site.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                  Nombre del tema
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={!canEdit}
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-xs outline-none focus:ring-1 focus:ring-primary/50 disabled:opacity-50"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setEditingThemeId(null);
                  setName("Tema personalizado");
                  setTokens(buildDefaultTokens());
                  setMessage({ text: "Nuevo tema iniciado.", type: "info" });
                }}
                disabled={!canEdit}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider hover:bg-[hsl(var(--bg-secondary))] transition-colors disabled:opacity-50"
              >
                <Layers size={11} />
                Nuevo
              </button>
              <button
                onClick={() => setImportOpen((p) => !p)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider hover:bg-[hsl(var(--bg-secondary))] transition-colors"
              >
                <FileJson size={11} />
                {importOpen ? "Cerrar" : "Importar JSON"}
              </button>
            </div>

            {/* Import Panel */}
            {importOpen && (
              <div className="space-y-2 animate-fade-in-up">
                <textarea
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                  placeholder='{"name": "Mi tema", "tokens_json": {"--site-primary": "#ff0000", ...}}'
                  rows={4}
                  className="w-full rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-secondary))] px-3 py-2 text-[11px] font-mono outline-none focus:ring-1 focus:ring-primary/50 resize-none"
                />
                <button
                  onClick={importJson}
                  className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-white hover:bg-primary/90 transition-colors"
                >
                  <Upload size={12} />
                  Aplicar JSON
                </button>
              </div>
            )}
          </div>

          {/* Token Editor */}
          <div className="rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] overflow-hidden">
            <div className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-between">
              <h2 className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                Tokens de diseño
              </h2>
              <span className="text-[10px] opacity-50">{usedTokensCount} / {ALL_TOKEN_KEYS.length}</span>
            </div>
            <div className="divide-y divide-[hsl(var(--border))] dark:divide-white/5">
              {TOKEN_CATEGORIES.map((cat) => {
                const isOpen = expandedCats.has(cat.id);
                return (
                  <div key={cat.id}>
                    <button
                      onClick={() => toggleCat(cat.id)}
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-[hsl(var(--bg-secondary))] transition-colors"
                    >
                      <div className="text-left">
                        <p className="text-xs font-bold">{cat.label}</p>
                        <p className="text-[10px] opacity-50">{cat.description}</p>
                      </div>
                      <ChevronDown
                        size={14}
                        className={`opacity-50 transition-transform ${isOpen ? "rotate-180" : ""}`}
                      />
                    </button>
                    {isOpen && (
                      <div className="px-4 pb-4 space-y-3">
                        {cat.tokens.map((tokenDef) => {
                          const value = tokens[tokenDef.key] || tokenDef.defaultValue;
                          const isColor = isColorToken(tokenDef.type, value);
                          return (
                            <div key={tokenDef.key} className="group">
                              <div className="flex items-center justify-between mb-1">
                                <label className="text-[10px] font-semibold uppercase tracking-wider">
                                  {tokenDef.label}
                                </label>
                                <button
                                  onClick={() =>
                                    setTokens((prev) => updateTokenValue(prev, tokenDef.key, tokenDef.defaultValue))
                                  }
                                  className="opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity text-[10px]"
                                  title="Restaurar default"
                                >
                                  <RotateCcw size={10} />
                                </button>
                              </div>
                              <p className="text-[10px] opacity-40 mb-1.5">{tokenDef.description}</p>
                              <div className="flex items-center gap-2">
                                {isColor && value.startsWith("#") && (
                                  <div className="relative shrink-0">
                                    <input
                                      type="color"
                                      value={hexFromAny(value)}
                                      onChange={(e) =>
                                        setTokens((prev) =>
                                          updateTokenValue(prev, tokenDef.key, e.target.value)
                                        )
                                      }
                                      disabled={!canEdit}
                                      className="w-9 h-9 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 p-0.5 cursor-pointer disabled:opacity-50"
                                    />
                                  </div>
                                )}
                                {isColor && !value.startsWith("#") && (
                                  <div
                                    className="w-9 h-9 rounded-lg border shrink-0"
                                    style={{
                                      background: value,
                                      borderColor: "hsl(var(--border))",
                                    }}
                                  />
                                )}
                                <input
                                  value={value}
                                  onChange={(e) =>
                                    setTokens((prev) => updateTokenValue(prev, tokenDef.key, e.target.value))
                                  }
                                  disabled={!canEdit}
                                  className="flex-1 min-w-0 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-transparent px-3 py-2 text-[11px] font-mono outline-none focus:ring-1 focus:ring-primary/50 disabled:opacity-50"
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* ── Right: Preview ── */}
        {showPreview && (
          <div className="xl:col-span-7 space-y-4">
            <div className="rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Eye size={14} className="text-primary" />
                  <h2 className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
                    Preview en vivo
                  </h2>
                </div>
                <span className="text-[10px] opacity-50">Actualiza en tiempo real</span>
              </div>
              <ThemePreview tokens={tokens} />
            </div>
          </div>
        )}
      </div>

      {/* ── Existing Themes ── */}
      <div className="rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))] p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers size={14} className="text-primary" />
            <h2 className="text-xs font-bold uppercase tracking-widest text-[hsl(var(--text-secondary))]">
              Temas guardados
            </h2>
          </div>
          <span className="text-[10px] opacity-50">{themes.length} temas</span>
        </div>

        <div className="space-y-2">
          {themes.map((theme) => {
            const isArchived = theme.status === "archived";
            const isEditing = editingThemeId === theme.id;
            return (
              <div
                key={theme.id}
                className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-lg border p-3 transition-all ${
                  isEditing
                    ? "border-primary/30 bg-primary/5"
                    : isArchived
                    ? "border-[hsl(var(--border))] dark:border-white/5 bg-[hsl(var(--bg-secondary))] opacity-60"
                    : "border-[hsl(var(--border))] dark:border-white/10 hover:border-primary/20"
                }`}
              >
                <div className="flex items-center gap-3">
                  {theme.tokens_json && (
                    <div
                      className="w-8 h-8 rounded-lg border shrink-0 shadow-sm"
                      style={{
                        background: theme.tokens_json["--site-primary"] || "#a5c8ff",
                        borderColor: theme.tokens_json["--site-outline-variant"] || "#424750",
                      }}
                    />
                  )}
                  <div>
                    <p className="text-sm font-bold flex items-center gap-2">
                      {theme.name}
                      {theme.is_active && (
                        <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                          Activo
                        </span>
                      )}
                      {isArchived && (
                        <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/20">
                          Archivado
                        </span>
                      )}
                    </p>
                    <p className="text-[10px] opacity-50">
                      {Object.keys(theme.tokens_json || {}).length} tokens ·{" "}
                      {theme.tokens_json ? "Custom" : "Default"}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={() => {
                      if (!canEdit) return;
                      setEditingThemeId(theme.id);
                      setName(theme.name);
                      setTokens({ ...buildDefaultTokens(), ...(theme.tokens_json || {}) });
                      setMessage({ text: `Editando "${theme.name}"`, type: "info" });
                      window.scrollTo({ top: 0, behavior: "smooth" });
                    }}
                    disabled={!canEdit || isArchived}
                    className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider transition-colors ${
                      isEditing
                        ? "border-primary/30 bg-primary/10 text-primary"
                        : "border-[hsl(var(--border))] dark:border-white/10 hover:bg-[hsl(var(--bg-secondary))]"
                    } disabled:opacity-40`}
                  >
                    {isEditing ? <CheckCircle2 size={11} /> : <ExternalLink size={11} />}
                    {isEditing ? "Editando" : "Editar"}
                  </button>
                  {!theme.is_active && !isArchived && (
                    <button
                      onClick={() => activate(theme.id)}
                      disabled={!canPublish}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/20 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-40"
                    >
                      <CheckCircle2 size={11} />
                      Activar
                    </button>
                  )}
                  {!isArchived && (
                    <button
                      onClick={() => archive(theme.id)}
                      disabled={!canPublish}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-amber-500/20 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-amber-400 hover:bg-amber-500/10 transition-colors disabled:opacity-40"
                    >
                      <Archive size={11} />
                      Archivar
                    </button>
                  )}
                  {isArchived && (
                    <button
                      onClick={() => restore(theme.id)}
                      disabled={!canEdit}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-primary/20 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-primary hover:bg-primary/10 transition-colors disabled:opacity-40"
                    >
                      <RotateCcw size={11} />
                      Restaurar
                    </button>
                  )}
                </div>
              </div>
            );
          })}
          {themes.length === 0 && (
            <p className="text-sm text-[hsl(var(--text-secondary))] text-center py-8 opacity-60">
              No hay temas guardados para este sitio.
            </p>
          )}
        </div>
      </div>

      {/* ── Floating Save Bar ── */}
      <div className="sticky bottom-4 z-50 flex justify-center">
        <div className="inline-flex items-center gap-3 rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-tertiary))]/95 backdrop-blur-xl px-5 py-3 shadow-xl">
          <div className="text-xs">
            <p className="font-bold">{editingThemeId ? `Editando: ${name}` : name}</p>
            <p className="text-[10px] opacity-50">{usedTokensCount} tokens configurados</p>
          </div>
          <div className="w-px h-8 bg-[hsl(var(--border))] dark:bg-white/10" />
          <button
            onClick={saveTheme}
            disabled={saving || !canEdit}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-xs font-bold uppercase tracking-wider text-white hover:bg-primary/90 transition-all disabled:opacity-50 shadow-lg shadow-primary/20"
          >
            <Save size={13} />
            {saving ? "Guardando..." : editingThemeId ? "Actualizar y activar" : "Guardar y activar"}
          </button>
        </div>
      </div>
    </div>
  );
}
