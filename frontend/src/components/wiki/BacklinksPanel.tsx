"use client";

import React, { useState, useEffect, useMemo } from 'react';
import Link from 'next/link';
import { Network, ArrowUpRight, ArrowDownLeft, FileText, Sparkles, BookOpen, Layers } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

interface BacklinksPanelProps {
  pageKey: string;
  docTitle: string;
  content: string;
}

interface WikiPageSummary {
  id: string;
  page_key: string;
  title: string;
  category?: string | null;
  updated_at?: string;
  content?: string;
}

interface GraphDataResponse {
  nodes: Array<{ id: string; title: string; category?: string; links_count: number }>;
  links: Array<{ source: string; target: string }>;
}

export default function BacklinksPanel({ pageKey, docTitle, content }: BacklinksPanelProps) {
  const { token } = useAuth();
  const [allPages, setAllPages] = useState<WikiPageSummary[]>([]);
  const [graphData, setGraphData] = useState<GraphDataResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'incoming' | 'outgoing'>('incoming');

  // Load knowledge graph data and pages
  useEffect(() => {
    if (!token) return;
    let isMounted = true;
    setLoading(true);

    const loadData = async () => {
      try {
        const [pagesRes, graphRes] = await Promise.all([
          apiFetch<WikiPageSummary[]>('/wiki/pages?limit=200', { token }),
          apiFetch<GraphDataResponse>('/wiki/graph-data', { token }).catch(() => null),
        ]);

        if (isMounted) {
          if (Array.isArray(pagesRes)) setAllPages(pagesRes);
          if (graphRes && Array.isArray(graphRes.nodes)) setGraphData(graphRes);
        }
      } catch (err) {
        console.error('Error fetching backlinks data:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    loadData();
    return () => {
      isMounted = false;
    };
  }, [token, pageKey]);

  // Extract Outgoing links from current document content
  const outgoingLinks = useMemo(() => {
    const targets = new Set<string>();

    // 1. Bracket syntax [[Title]] or [[key|label]]
    const bracketRegex = /\[\[(.*?)\]\]/g;
    let match;
    while ((match = bracketRegex.exec(content)) !== null) {
      const rawTarget = match[1].split('|')[0].trim();
      targets.add(rawTarget);
    }

    // 2. data-page-key attribute
    const dataKeyRegex = /data-page-key=["']([^"']+)["']/g;
    while ((match = dataKeyRegex.exec(content)) !== null) {
      targets.add(match[1].trim());
    }

    // 3. href links
    const hrefRegex = /href=["'][^"']*(?:\/wiki\/docs\/)([^"'#?]+)["']/g;
    while ((match = hrefRegex.exec(content)) !== null) {
      targets.add(match[1].trim());
    }

    // Resolve target strings to page objects
    const resolved: WikiPageSummary[] = [];
    const seenKeys = new Set<string>();

    targets.forEach((targetStr) => {
      const normalizedTarget = targetStr.toLowerCase().replace(/ /g, '_');
      const found = allPages.find(
        (p) =>
          p.page_key.toLowerCase() === targetStr.toLowerCase() ||
          p.page_key.toLowerCase() === `wiki_${normalizedTarget}` ||
          p.title.toLowerCase() === targetStr.toLowerCase()
      );

      if (found && !seenKeys.has(found.page_key) && found.page_key !== pageKey) {
        seenKeys.add(found.page_key);
        resolved.push(found);
      } else if (!found && !seenKeys.has(targetStr)) {
        seenKeys.add(targetStr);
        const cleanTitle = targetStr.replace(/^wiki_/, '').replace(/[_-]/g, ' ');
        const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);
        resolved.push({
          id: targetStr,
          page_key: targetStr.startsWith('wiki_') ? targetStr : `wiki_${normalizedTarget}`,
          title: formattedTitle || targetStr,
          category: 'Pendiente',
        });
      }
    });

    return resolved;
  }, [content, allPages, pageKey]);

  // Extract Incoming backlinks to the current document
  const incomingBacklinks = useMemo(() => {
    if (graphData && Array.isArray(graphData.links)) {
      // Use graph links
      const incomingSourceKeys = new Set(
        graphData.links
          .filter((l) => l.target === pageKey || l.target === `wiki_${pageKey}`)
          .map((l) => l.source)
      );

      return allPages.filter((p) => incomingSourceKeys.has(p.page_key) && p.page_key !== pageKey);
    }

    // Fallback: analyze content of all loaded pages
    return allPages.filter((p) => {
      if (p.page_key === pageKey) return false;
      const c = p.content || '';
      const normKey = pageKey.replace(/^wiki_/, '');
      return (
        c.includes(pageKey) ||
        (docTitle && c.toLowerCase().includes(`[[${docTitle.toLowerCase()}]]`)) ||
        (normKey && c.toLowerCase().includes(`[[${normKey.toLowerCase()}]]`))
      );
    });
  }, [graphData, allPages, pageKey, docTitle]);

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] dark:border-white/10 dark:bg-[#18191d] shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[hsl(var(--border))] px-4 py-3 dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-white/5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
            <Network size={16} />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-primary))] dark:text-white">
              Red de Conocimiento Ministerial
            </h3>
            <p className="text-[11px] text-[hsl(var(--text-secondary))]">
              Descubrimiento bidireccional Obsidian
            </p>
          </div>
        </div>

        <Link
          href={`/plataforma/wiki/graph?focus=${encodeURIComponent(pageKey)}`}
          className="flex items-center gap-1.5 rounded-lg bg-[hsl(var(--primary))] px-3 py-1.5 text-xs font-bold text-white shadow-md shadow-[hsl(var(--primary)/0.2)] hover:opacity-90 transition-all uppercase tracking-wide"
        >
          <Network size={12} />
          <span>Ver en Grafo 2D</span>
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] dark:border-white/5 dark:bg-black/20 px-4 pt-2 gap-2">
        <button
          type="button"
          onClick={() => setActiveTab('incoming')}
          className={`flex items-center gap-2 px-3 py-2 text-xs font-bold border-b-2 transition-all ${
            activeTab === 'incoming'
              ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))]'
              : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
          }`}
        >
          <ArrowDownLeft size={14} />
          <span>Retroenlaces Entrantes</span>
          <span className="rounded-full bg-[hsl(var(--primary)/0.15)] px-1.5 py-0.2 text-[10px] font-black text-[hsl(var(--primary))]">
            {incomingBacklinks.length}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('outgoing')}
          className={`flex items-center gap-2 px-3 py-2 text-xs font-bold border-b-2 transition-all ${
            activeTab === 'outgoing'
              ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))]'
              : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]'
          }`}
        >
          <ArrowUpRight size={14} />
          <span>Enlaces Salientes</span>
          <span className="rounded-full bg-[hsl(var(--surface-1))] dark:bg-white/10 px-1.5 py-0.2 text-[10px] font-black text-[hsl(var(--text-secondary))]">
            {outgoingLinks.length}
          </span>
        </button>
      </div>

      {/* Tab Content */}
      <div className="p-4">
        {loading ? (
          <div className="py-6 flex items-center justify-center gap-2 text-xs text-[hsl(var(--text-secondary))]">
            <Sparkles size={14} className="animate-spin text-[hsl(var(--primary))]" />
            <span>Mapeando conexiones neuronales...</span>
          </div>
        ) : activeTab === 'incoming' ? (
          <div>
            {incomingBacklinks.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {incomingBacklinks.map((doc) => (
                  <Link
                    key={doc.page_key}
                    href={`/plataforma/wiki/docs/${doc.page_key}`}
                    className="group flex items-start justify-between gap-3 p-3 rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:border-[hsl(var(--primary))] hover:shadow-md transition-all"
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <FileText size={13} className="text-[hsl(var(--primary))] shrink-0" />
                        <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white truncate group-hover:text-[hsl(var(--primary))] transition-colors">
                          {doc.title}
                        </h4>
                      </div>
                      {doc.category && (
                        <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-extrabold uppercase bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))]">
                          {doc.category}
                        </span>
                      )}
                    </div>
                    <ArrowDownLeft size={14} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors shrink-0 mt-0.5" />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center space-y-1.5 opacity-60">
                <BookOpen size={28} className="mx-auto text-[hsl(var(--text-secondary))]" />
                <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">
                  Sin retroenlaces hacia esta página todavía
                </p>
                <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                  Usa <code className="font-bold font-mono text-[hsl(var(--primary))]">[[{docTitle || pageKey}]]</code> en otros documentos ministeriales para conectarlos.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div>
            {outgoingLinks.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                {outgoingLinks.map((doc) => (
                  <Link
                    key={doc.page_key}
                    href={`/plataforma/wiki/docs/${doc.page_key}`}
                    className="group flex items-start justify-between gap-3 p-3 rounded-lg border border-[hsl(var(--border))]/70 dark:border-white/5 bg-[hsl(var(--surface-1))] dark:bg-white/5 hover:border-[hsl(var(--primary))] hover:shadow-md transition-all"
                  >
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <FileText size={13} className="text-[hsl(var(--primary))] shrink-0" />
                        <h4 className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white truncate group-hover:text-[hsl(var(--primary))] transition-colors">
                          {doc.title}
                        </h4>
                      </div>
                      {doc.category && (
                        <span className="inline-block px-1.5 py-0.5 rounded text-[9px] font-extrabold uppercase bg-[hsl(var(--surface-2))] dark:bg-white/10 text-[hsl(var(--text-secondary))]">
                          {doc.category}
                        </span>
                      )}
                    </div>
                    <ArrowUpRight size={14} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors shrink-0 mt-0.5" />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center space-y-1.5 opacity-60">
                <Layers size={28} className="mx-auto text-[hsl(var(--text-secondary))]" />
                <p className="text-xs font-bold text-[hsl(var(--text-primary))] dark:text-white">
                  Este documento no enlaza a otras páginas
                </p>
                <p className="text-[11px] text-[hsl(var(--text-secondary))]">
                  Escribe <code className="font-bold font-mono text-[hsl(var(--primary))]">[[</code> en el editor para agregar enlaces a otros temas.
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
