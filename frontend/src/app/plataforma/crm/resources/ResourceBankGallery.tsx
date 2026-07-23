'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import clsx from 'clsx';
import {
  BookOpen,
  Loader2,
  Mail,
  MessageSquare,
  Plus,
  Search,
  Send,
  X,
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import type {
  CanalEnvio,
  PlantillaMensaje,
  SystemTemplate,
  SystemTemplateCatalog,
} from '@/types/crm';

const CANAL_META: Record<CanalEnvio, { label: string; icon: React.ElementType; color: string; bg: string }> = {
  WHATSAPP: { label: 'WhatsApp', icon: MessageSquare, color: 'text-[hsl(var(--success))] dark:text-[hsl(var(--success))]', bg: 'bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success)/0.2)]' },
  EMAIL: { label: 'Email', icon: Mail, color: 'text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]', bg: 'bg-[hsl(var(--info-muted))] dark:bg-[hsl(var(--primary)/0.2)]' },
  SMS: { label: 'SMS', icon: Send, color: 'text-[hsl(var(--warning))] dark:text-[hsl(var(--warning))]', bg: 'bg-[hsl(var(--warning-muted))] dark:bg-[hsl(var(--warning)/0.2)]' },
};

interface ResourceBankGalleryProps {
  open: boolean;
  onClose: () => void;
  token: string;
  onApplied: (plantilla: PlantillaMensaje) => void;
}

export default function ResourceBankGallery({
  open,
  onClose,
  token,
  onApplied,
}: ResourceBankGalleryProps) {
  const [catalog, setCatalog] = useState<SystemTemplateCatalog | null>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    apiFetch<SystemTemplateCatalog>('/crm/resources/system-templates', { token })
      .then(data => setCatalog(data ?? { categorias: [], plantillas: [] }))
      .catch(() => {
        setCatalog({ categorias: [], plantillas: [] });
        setError('No se pudo cargar el banco de recursos');
      })
      .finally(() => setLoading(false));
  }, [open, reloadKey, token]);

  const categories = useMemo(() => catalog?.categorias ?? [], [catalog]);
  const templates = useMemo(() => catalog?.plantillas ?? [], [catalog]);

  const filteredTemplates = useMemo(() => {
    let rows = templates;
    if (selectedCategory) {
      rows = rows.filter(t => t.categoria === selectedCategory);
    }
    if (search.trim()) {
      const term = search.toLowerCase();
      rows = rows.filter(
        t =>
          (t.titulo ?? '').toLowerCase().includes(term) ||
          (t.contenido_texto ?? '').toLowerCase().includes(term) ||
          (t.categoria ?? '').toLowerCase().includes(term)
      );
    }
    return rows;
  }, [templates, selectedCategory, search]);

  const categoryCounts = useMemo(() => {
    const map = new Map<string, number>();
    templates.forEach(t => {
      const key = t.categoria ?? 'Sin categoría';
      map.set(key, (map.get(key) ?? 0) + 1);
    });
    return map;
  }, [templates]);

  const applyTemplate = useCallback(
    async (tpl: SystemTemplate) => {
      setApplying(tpl.titulo);
      setError(null);
      try {
        const created = await apiFetch<PlantillaMensaje>('/crm/resources/system-templates/apply', {
          token,
          method: 'POST',
          body: { template_id: tpl.id },
          headers: { 'Content-Type': 'application/json' },
        });
        if (created) {
          onApplied(created);
          onClose();
        }
      } catch (err) {
        setError('No se pudo aplicar la plantilla. Intenta de nuevo.');
      } finally {
        setApplying(null);
      }
    },
    [token, onApplied, onClose]
  );

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed inset-x-4 top-[5vh] bottom-[5vh] md:inset-x-10 lg:inset-x-20 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--bg-muted))] z-50 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[hsl(var(--border))] dark:border-white/10">
          <div>
            <h2 className="text-base font-semibold text-[hsl(var(--text-primary))] dark:text-white flex items-center gap-2">
              <BookOpen size={18} className="text-[hsl(var(--primary))]" />
              Banco de recursos
            </h2>
            <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
              Plantillas predefinidas para iglesia. Selecciona una para usarla en tu sede.
            </p>
          </div>
          <button
            onClick={onClose}
            className="size-8 flex items-center justify-center rounded-lg text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row gap-3 px-6 py-3 border-b border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/[0.02]">
          <div className="relative flex-1">
            <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
            <input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Buscar plantillas…"
              className="w-full pl-9 pr-3 h-9 text-xs rounded-lg bg-[hsl(var(--bg-primary))] dark:bg-white/5 border border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-primary))] dark:text-white placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.4)]"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 sm:pb-0">
            <button
              onClick={() => setSelectedCategory(null)}
              className={clsx(
                'shrink-0 h-9 px-3 rounded-lg text-xs font-medium transition-colors',
                selectedCategory === null
                  ? 'bg-[hsl(var(--primary))] text-white'
                  : 'bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/20'
              )}
            >
              Todas
            </button>
                      {categories.map(cat => (
              <button
                key={cat.nombre}
                onClick={() =>
                  setSelectedCategory(prev => (prev === cat.nombre ? null : cat.nombre))
                }
                className={clsx(
                  'shrink-0 h-9 px-3 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5',
                  selectedCategory === cat.nombre
                    ? 'bg-[hsl(var(--primary))] text-white'
                    : 'bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-3))] dark:hover:bg-white/20'
                )}
                >
                  <span
                    className="size-2 rounded-full"
                  style={{ background: cat.color_ui_hex ?? '#6B7280' }}
                  />
                  {cat.nombre}
                  <span className="text-[10px] opacity-70">({categoryCounts.get(cat.nombre) ?? 0})</span>
                </button>
              ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {!loading && error && (
            <div className="mb-4 flex items-center justify-between gap-3 rounded-lg border border-[hsl(var(--warning)/0.2)] bg-[hsl(var(--warning-muted))] px-4 py-3 text-[hsl(var(--warning))] dark:border-[hsl(var(--warning)/0.2)] dark:bg-[hsl(var(--warning)/0.1)] dark:text-[hsl(var(--warning))]">
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wide">Banco de recursos sin respuesta</p>
                <p className="text-xs">{error}</p>
              </div>
              <button
                onClick={() => setReloadKey(key => key + 1)}
                className="rounded-md border border-[hsl(var(--warning)/0.3)] px-3 py-1.5 text-[11px] font-bold uppercase tracking-wide hover:bg-[hsl(var(--warning-muted))] dark:border-[hsl(var(--warning)/0.4)] dark:hover:bg-[hsl(var(--warning)/0.2)]"
              >
                Reintentar
              </button>
            </div>
          )}

          {loading && (
            <div className="flex flex-col items-center justify-center py-16">
              <Loader2 className="animate-spin text-[hsl(var(--text-secondary))]" size={28} />
              <p className="text-xs text-[hsl(var(--text-secondary))] mt-3">Cargando banco de recursos…</p>
            </div>
          )}

          {!loading && !error && filteredTemplates.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <BookOpen size={40} className="text-[hsl(var(--text-secondary))] dark:text-white/20 mb-3" />
              <p className="text-sm font-medium text-[hsl(var(--text-secondary))]">No se encontraron plantillas</p>
              <p className="text-xs text-[hsl(var(--text-secondary))] mt-1">Prueba con otro término de búsqueda</p>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {filteredTemplates.map(tpl => {
              const canalMeta = CANAL_META[tpl.canal] ?? CANAL_META.WHATSAPP;
              const Icon = canalMeta.icon;
              return (
                <div
                  key={`${tpl.categoria}-${tpl.titulo}`}
                  className="group rounded-xl border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-4 hover:border-[hsl(var(--primary)/0.5)] hover:shadow-lg transition-all flex flex-col"
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-1.5">
                      <span
                        className={clsx(
                          'inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full',
                          canalMeta.bg,
                          canalMeta.color
                        )}
                      >
                        <Icon size={11} />
                        {canalMeta.label}
                      </span>
                      {tpl.html_template_type && (
                        <span className="inline-flex items-center text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
                          HTML
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-[hsl(var(--text-secondary))] truncate max-w-[120px]">
                      {tpl.categoria ?? 'Sin categoría'}
                    </span>
                  </div>

                  <h3 className="text-sm font-semibold text-[hsl(var(--text-primary))] dark:text-white mb-2">
                    {tpl.titulo ?? 'Plantilla sin título'}
                  </h3>

                  <p className="text-xs text-[hsl(var(--text-secondary))] line-clamp-3 mb-3 flex-1 whitespace-pre-wrap">
                    {tpl.contenido_texto ?? ''}
                  </p>

                  {(tpl.variables_requeridas ?? []).length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {(tpl.variables_requeridas ?? []).map(v => (
                        <span
                          key={v}
                          className="text-[10px] font-mono bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] px-1.5 py-0.5 rounded"
                        >
                          {'{{' + v + '}}'}
                        </span>
                      ))}
                    </div>
                  )}

                  <button
                    onClick={() => applyTemplate(tpl)}
                    disabled={applying === tpl.titulo}
                    className="w-full h-8 rounded-lg bg-[hsl(var(--primary))] text-white text-xs font-medium hover:opacity-90 disabled:opacity-50 flex items-center justify-center gap-1.5 transition-opacity"
                  >
                    {applying === tpl.titulo ? (
                      <>
                        <Loader2 size={12} className="animate-spin" />
                        Aplicando…
                      </>
                    ) : (
                      <>
                        <Plus size={12} />
                        Usar plantilla
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[hsl(var(--border))] dark:border-white/10 flex items-center justify-between">
          <p className="text-xs text-[hsl(var(--text-secondary))]">
            {filteredTemplates.length} plantilla{filteredTemplates.length !== 1 ? 's' : ''} disponible{filteredTemplates.length !== 1 ? 's' : ''}
          </p>
          {error && <p className="text-xs text-[hsl(var(--destructive))]">{error}</p>}
        </div>
      </div>
    </>
  );
}
