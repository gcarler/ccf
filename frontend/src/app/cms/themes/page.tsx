"use client";

import React, { useEffect, useState } from "react";
import { Palette, Save } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { activateCmsTheme, createCmsTheme, listCmsSites, listCmsThemes } from "@/lib/cms/v2";

const DEFAULT_TOKENS = {
  "--faro-primary": "#a5c8ff",
  "--faro-secondary": "#80d0ff",
  "--faro-background": "#001134",
  "--faro-on-background": "#d9e2ff",
};

export default function CmsThemesPage() {
  const { token } = useAuth();
  const [siteKey, setSiteKey] = useState("faro");
  const [sites, setSites] = useState<Array<{ site_key: string; name: string }>>([]);
  const [themes, setThemes] = useState<Array<{ id: number; name: string; is_active: boolean }>>([]);
  const [name, setName] = useState("Tema personalizado");
  const [tokens, setTokens] = useState(DEFAULT_TOKENS);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = async (activeSite: string) => {
    if (!token) return;
    const [nextSites, nextThemes] = await Promise.all([listCmsSites(token), listCmsThemes(activeSite, token)]);
    setSites((nextSites || []).map((site) => ({ site_key: site.site_key, name: site.name })));
    setThemes((nextThemes || []).map((theme) => ({ id: theme.id, name: theme.name, is_active: theme.is_active })));
  };

  useEffect(() => {
    load(siteKey).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, siteKey]);

  const saveTheme = async () => {
    if (!token) return;
    setSaving(true);
    setMessage(null);
    try {
      await createCmsTheme(siteKey, { name, tokens_json: tokens, is_active: true }, token);
      setMessage("Tema guardado y activado.");
      await load(siteKey);
    } catch {
      setMessage("No se pudo guardar el tema.");
    } finally {
      setSaving(false);
    }
  };

  const activate = async (themeId: number) => {
    if (!token) return;
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
          <input value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" />

          {Object.entries(tokens).map(([key, value]) => (
            <div key={key} className="space-y-1">
              <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{key}</p>
              <input
                value={value}
                onChange={(e) => setTokens((prev) => ({ ...prev, [key]: e.target.value }))}
                className="w-full rounded-xl border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm"
              />
            </div>
          ))}

          <button onClick={saveTheme} disabled={saving} className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-xs font-black uppercase tracking-wider text-white disabled:opacity-60">
            <Save size={13} /> {saving ? "Guardando" : "Guardar y activar"}
          </button>
          {message && <p className="text-xs text-slate-500">{message}</p>}
        </div>

        <div className="lg:col-span-2 rounded-2xl border border-slate-200 dark:border-white/10 bg-white dark:bg-[#111418] p-4 space-y-3">
          <h2 className="text-sm font-black uppercase tracking-wider text-slate-500">Temas existentes</h2>
          <div className="space-y-2">
            {themes.map((theme) => (
              <div key={theme.id} className="flex items-center justify-between rounded-xl border border-slate-200 dark:border-white/10 p-3">
                <div>
                  <p className="text-sm font-bold">{theme.name}</p>
                  <p className="text-[10px] uppercase tracking-widest text-slate-400">{theme.is_active ? "Activo" : "Inactivo"}</p>
                </div>
                {!theme.is_active && (
                  <button onClick={() => activate(theme.id)} className="rounded-lg border border-slate-200 dark:border-white/10 px-3 py-1.5 text-[10px] font-black uppercase tracking-widest">
                    Activar
                  </button>
                )}
              </div>
            ))}
            {themes.length === 0 && <p className="text-sm text-slate-500">Sin temas para este sitio.</p>}
          </div>
        </div>
      </section>
    </div>
  );
}
