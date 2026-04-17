"use client";

import React, { useEffect, useState } from "react";
import { Palette, Save } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { activateCmsTheme, createCmsTheme, listCmsSites, listCmsThemes, patchCmsTheme } from "@/lib/cms/v2";
import { canEditCms, canPublishCms } from "@/lib/cms/permissions";

const DEFAULT_TOKENS = {
  "--faro-primary": "#a5c8ff",
  "--faro-secondary": "#80d0ff",
  "--faro-background": "#001134",
  "--faro-on-background": "#d9e2ff",
};

export default function CmsThemesPage() {
  const { token, user } = useAuth();
  const [siteKey, setSiteKey] = useState("faro");
  const [sites, setSites] = useState<Array<{ site_key: string; name: string }>>([]);
  const [themes, setThemes] = useState<Array<{ id: number; name: string; is_active: boolean; tokens_json?: Record<string, string> }>>([]);
  const [name, setName] = useState("Tema personalizado");
  const [tokens, setTokens] = useState(DEFAULT_TOKENS);
  const [editingThemeId, setEditingThemeId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const canEdit = canEditCms(user?.role);
  const canPublish = canPublishCms(user?.role);

  const load = async (activeSite: string) => {
    if (!token) return;
    const [nextSites, nextThemes] = await Promise.all([listCmsSites(token), listCmsThemes(activeSite, token)]);
    setSites((nextSites || []).map((site) => ({ site_key: site.site_key, name: site.name })));
    setThemes((nextThemes || []).map((theme) => ({ id: theme.id, name: theme.name, is_active: theme.is_active, tokens_json: theme.tokens_json })));
  };

  useEffect(() => {
    load(siteKey).catch(() => undefined);
    setEditingThemeId(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, siteKey]);

  const saveTheme = async () => {
    if (!token || !canEdit) return;
    setSaving(true);
    setMessage(null);
    try {
      const shouldActivate = canPublish;
      if (editingThemeId) {
        await patchCmsTheme(siteKey, editingThemeId, { name, tokens_json: tokens, is_active: shouldActivate }, token);
        if (shouldActivate) {
          await activateCmsTheme(siteKey, editingThemeId, token);
          setMessage("Tema actualizado y activado.");
        } else {
          setMessage("Tema actualizado. Solo un publicador puede activarlo.");
        }
      } else {
        const created = await createCmsTheme(siteKey, { name, tokens_json: tokens, is_active: shouldActivate }, token);
        if (shouldActivate) {
          await activateCmsTheme(siteKey, created.id, token);
          setMessage("Tema guardado y activado.");
        } else {
          setMessage("Tema guardado. Solo un publicador puede activarlo.");
        }
      }
      await load(siteKey);
    } catch {
      setMessage("No se pudo guardar el tema.");
    } finally {
      setSaving(false);
    }
  };

  const activate = async (themeId: number) => {
    if (!token || !canPublish) return;
    await activateCmsTheme(siteKey, themeId, token);
    await load(siteKey);
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between rounded-3xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-6">
        <div>
          <p className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">CMS V2</p>
          <h1 className="mt-2 text-2xl font-black">Editor de temas multisitio</h1>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-primary/10 px-3 py-2 text-primary text-xs font-black uppercase tracking-wider">
          <Palette size={14} /> Tokens
        </div>
      </div>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-3">
          <label className="text-xs font-black uppercase tracking-wider text-slate-500">Sitio</label>
          <select value={siteKey} onChange={(e) => setSiteKey(e.target.value)} className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm">
            {sites.length === 0 && <option value="faro">faro</option>}
            {sites.map((site) => (
              <option key={site.site_key} value={site.site_key}>{site.name} ({site.site_key})</option>
            ))}
          </select>

          <label className="text-xs font-black uppercase tracking-wider text-slate-500">Nombre del tema</label>
          <input value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" disabled={!canEdit} />
          <button
            onClick={() => {
              setEditingThemeId(null);
              setName("Tema personalizado");
              setTokens(DEFAULT_TOKENS);
              setMessage("Creación de nuevo tema.");
            }}
            disabled={!canEdit}
            className="w-full rounded-xl border border-slate-200 dark:border-white/10 px-4 py-2 text-[10px] font-black uppercase tracking-wider"
          >
            Nuevo tema
          </button>

          {Object.entries(tokens).map(([key, value]) => (
            <div key={key} className="space-y-1">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{key}</p>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={value}
                  onChange={(e) => setTokens((prev) => ({ ...prev, [key]: e.target.value }))}
                  disabled={!canEdit}
                  className="h-9 w-10 rounded-lg border border-slate-200 dark:border-white/10 bg-transparent p-0.5"
                />
                <input
                  value={value}
                  onChange={(e) => setTokens((prev) => ({ ...prev, [key]: e.target.value }))}
                  disabled={!canEdit}
                  className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
                />
              </div>
            </div>
          ))}

          <button onClick={saveTheme} disabled={saving || !canEdit} className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-black uppercase tracking-wider text-white disabled:opacity-60">
            <Save size={13} /> {saving ? "Guardando" : editingThemeId ? "Actualizar y activar" : "Guardar y activar"}
          </button>
          {message && <p className="text-xs text-slate-500">{message}</p>}
        </div>

        <div className="lg:col-span-2 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-3">
          <div
            className="rounded-2xl border border-slate-200 dark:border-white/10 p-6"
            style={{
              background: tokens["--faro-background"],
              color: tokens["--faro-on-background"],
            }}
          >
            <p className="text-[10px] font-black uppercase tracking-[0.3em]" style={{ color: tokens["--faro-secondary"] }}>Preview</p>
            <h3 className="mt-2 text-2xl font-black">Tema en vivo</h3>
            <p className="mt-2 text-sm opacity-80">Así se verían tus variables principales en una sección pública.</p>
            <button
              className="mt-5 rounded-full px-5 py-2.5 text-[11px] font-black uppercase tracking-widest"
              style={{ background: tokens["--faro-primary"], color: tokens["--faro-background"] }}
            >
              Acción principal
            </button>
          </div>

          <h2 className="text-sm font-black uppercase tracking-wider text-slate-500">Temas existentes</h2>
          <div className="space-y-2">
            {themes.map((theme) => (
                <div key={theme.id} className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-white/10 p-3">
                  <div>
                    <p className="text-sm font-bold">{theme.name}</p>
                    <p className="text-[10px] uppercase tracking-widest text-slate-400">{theme.is_active ? "Activo" : "Inactivo"}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        if (!canEdit) return;
                        setEditingThemeId(theme.id);
                        setName(theme.name);
                        setTokens({ ...DEFAULT_TOKENS, ...(theme.tokens_json || {}) });
                        setMessage("Editando tema seleccionado.");
                      }}
                      disabled={!canEdit}
                      className="rounded-lg border border-slate-200 dark:border-white/10 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest"
                    >
                      Editar
                    </button>
                    {!theme.is_active && (
                      <button onClick={() => activate(theme.id)} disabled={!canPublish} className="rounded-lg border border-slate-200 dark:border-white/10 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest disabled:opacity-50">
                        Activar
                      </button>
                    )}
                  </div>
                </div>
              ))}
            {themes.length === 0 && <p className="text-sm text-slate-500">Sin temas para este sitio.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}

