"use client";

import React, { useEffect, useState } from "react";
import { Globe, Plus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { createCmsSite, listCmsSites, patchCmsSite } from "@/lib/cms/v2";
import { canManageSites } from "@/lib/cms/permissions";

function sanitizeSiteKey(value: string) {
  return value.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
}

export default function CmsSitesPage() {
  const { token, user } = useAuth();
  const [sites, setSites] = useState<Array<{ id: string; site_key: string; name: string; base_path: string; is_active: boolean }>>([]);
  const [name, setName] = useState("");
  const [siteKey, setSiteKey] = useState("");
  const [basePath, setBasePath] = useState("");
  const [loading, setLoading] = useState(true);
  const canManage = canManageSites(user?.role);

  const load = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const next = await listCmsSites(token);
      setSites((next || []).map((site) => ({
        id: site.id,
        site_key: site.site_key,
        name: site.name,
        base_path: site.base_path,
        is_active: site.is_active,
      })));
    } catch {
      setSites([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load().catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const create = async () => {
    if (!token || !name.trim() || !canManage) return;
    const key = sanitizeSiteKey(siteKey || name);
    const path = (basePath || `/${key}`).startsWith("/") ? (basePath || `/${key}`) : `/${basePath}`;
    await createCmsSite({ site_key: key, name: name.trim(), base_path: path, is_active: true }, token);
    setName("");
    setSiteKey("");
    setBasePath("");
    await load();
  };

  const toggle = async (target: { site_key: string; is_active: boolean }) => {
    if (!token || !canManage) return;
    await patchCmsSite(target.site_key, { is_active: !target.is_active }, token);
    await load();
  };

  return (
    <div className="space-y-3 p-3">
      <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-3 flex items-center justify-between">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">CMS V2</p>
          <h1 className="mt-2 text-lg font-semibold">Gestión de sitios</h1>
        </div>
        <div className="rounded-md bg-primary/10 px-3 py-2 text-primary text-xs font-semibold uppercase tracking-wide inline-flex items-center gap-2">
          <Globe size={14} /> Multisitio
        </div>
      </div>

      <section className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-4 space-y-3">
          {!canManage && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700">
              Tu rol puede consultar sitios, pero no crear ni activar/desactivar.
            </div>
          )}
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Nuevo sitio</p>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Nombre (ej. Comunidad)" className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" disabled={!canManage} />
          <input value={siteKey} onChange={(e) => setSiteKey(sanitizeSiteKey(e.target.value))} placeholder="site_key (ej. comunidad)" className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" disabled={!canManage} />
          <input value={basePath} onChange={(e) => setBasePath(e.target.value)} placeholder="base_path (ej. /comunidad)" className="w-full rounded-md border border-slate-200 dark:border-white/10 bg-transparent px-3 py-2 text-sm" disabled={!canManage} />
          <button onClick={create} disabled={!canManage} className="w-full rounded-md bg-primary px-4 py-2.5 text-xs font-semibold uppercase tracking-wider text-white inline-flex items-center justify-center gap-2 disabled:opacity-50"><Plus size={13} /> Crear sitio</button>
        </div>

        <div className="lg:col-span-2 rounded-lg border border-slate-200 dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[#111418] p-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Sitios registrados</p>
          {loading ? (
            <p className="text-sm text-slate-500">Cargando sitios...</p>
          ) : (
            <div className="space-y-2">
              {sites.map((site) => (
                <div key={site.id} className="rounded-md border border-slate-200 dark:border-white/10 p-3 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-bold">{site.name}</p>
                    <p className="text-[10px] uppercase tracking-wide text-slate-400">{site.site_key} · {site.base_path}</p>
                  </div>
                  <button onClick={() => toggle(site)} disabled={!canManage} className={`rounded-lg px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide ${site.is_active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"} disabled:opacity-50`}>
                    {site.is_active ? "Activo" : "Inactivo"}
                  </button>
                </div>
              ))}
              {sites.length === 0 && <p className="text-sm text-slate-500">No hay sitios creados.</p>}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

