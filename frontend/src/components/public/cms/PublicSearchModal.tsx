"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { Search, X, Loader2, Star, Tag, Folder, ArrowRight } from "lucide-react";

export interface SearchResultItem {
  entity_type: string;
  entity_id: string;
  entity_slug?: string | null;
  title?: string | null;
  body_text?: string | null;
  category?: string | null;
  tags?: string[];
  author_persona_id?: string | null;
  boost_score?: number;
  relevance_score?: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PromotedSearchItem {
  entity_type: string;
  entity_id: string;
  entity_slug?: string | null;
  title?: string | null;
  boost_score?: number;
}

export interface SearchApiResponse {
  query: string;
  total: number;
  page: number;
  limit: number;
  results: SearchResultItem[];
  promoted: PromotedSearchItem[];
}

export interface PublicSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  siteKey?: string;
  availableCategories?: string[];
  availableTags?: string[];
}

export default function PublicSearchModal({
  isOpen,
  onClose,
  siteKey = "ccf",
  availableCategories = ["General", "Noticias", "Eventos", "Recursos"],
  availableTags = ["anuncio", "tutorial", "iglesia", "comunidad"],
}: PublicSearchModalProps) {
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [promoted, setPromoted] = useState<PromotedSearchItem[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when modal opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery("");
      setResults([]);
      setPromoted([]);
      setSelectedCategory(null);
      setSelectedTags([]);
      setHasSearched(false);
    }
  }, [isOpen]);

  // Handle Cmd+K / Ctrl+K and Escape keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (isOpen) {
          onClose();
        } else {
          // Open signal handled if caller triggers isOpen
        }
      } else if (e.key === "Escape" && isOpen) {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Execute API Search
  const performSearch = useCallback(
    async (searchTerm: string, cat: string | null, tags: string[]) => {
      if (!searchTerm.trim() && !cat && tags.length === 0) {
        setResults([]);
        setPromoted([]);
        setLoading(false);
        setHasSearched(false);
        return;
      }

      setLoading(true);
      setHasSearched(true);

      try {
        const params = new URLSearchParams();
        params.set("site_key", siteKey);
        if (searchTerm.trim()) params.set("q", searchTerm.trim());
        if (cat) params.set("category", cat);
        if (tags.length > 0) params.set("tags", tags.join(","));

        const res = await fetch(`/api/cms/v2/search?${params.toString()}`);
        if (!res.ok) {
          throw new Error(`Search failed: ${res.statusText}`);
        }
        const data: SearchApiResponse = await res.json();
        setResults(data.results || []);
        setPromoted(data.promoted || []);
      } catch (err) {
        console.error("Failed to perform search:", err);
        setResults([]);
        setPromoted([]);
      } finally {
        setLoading(false);
      }
    },
    [siteKey]
  );

  // Debounced Search trigger (300ms)
  useEffect(() => {
    if (!isOpen) return;

    const timer = setTimeout(() => {
      performSearch(query, selectedCategory, selectedTags);
    }, 300);

    return () => clearTimeout(timer);
  }, [query, selectedCategory, selectedTags, isOpen, performSearch]);

  const toggleCategory = (cat: string) => {
    setSelectedCategory((prev) => (prev === cat ? null : cat));
  };

  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-16 sm:pt-24 px-4 bg-black/60 backdrop-blur-sm transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-labelledby="search-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-2xl bg-site-surface rounded-xl shadow-2xl overflow-hidden border border-site-outline-variant/30 flex flex-col max-h-[80vh]">
        {/* Header Search Input */}
        <div className="relative flex items-center px-4 py-3 border-b border-site-outline-variant/30">
          <Search className="w-5 h-5 text-site-on-surface-variant shrink-0 mr-3" />
          <input
            ref={inputRef}
            id="search-modal-title"
            type="text"
            className="w-full bg-transparent text-site-on-surface placeholder:text-site-on-surface-variant/60 focus:outline-none text-lg"
            placeholder="Buscar en el sitio... (p.ej. noticias, eventos)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {loading ? (
            <Loader2 className="w-5 h-5 text-site-primary animate-spin shrink-0 ml-2" />
          ) : query ? (
            <button
              onClick={() => setQuery("")}
              className="p-1 rounded-full text-site-on-surface-variant hover:text-site-on-surface transition-colors"
              aria-label="Limpiar búsqueda"
            >
              <X className="w-4 h-4" />
            </button>
          ) : null}
          <button
            onClick={onClose}
            className="ml-3 px-2 py-1 text-xs font-medium text-site-on-surface-variant bg-site-surface-container-high hover:bg-site-surface-bright rounded transition-colors"
          >
            Esc
          </button>
        </div>

        {/* Filter Pills */}
        <div className="px-4 py-2.5 bg-site-surface-container-low border-b border-site-outline-variant/30 flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-site-on-surface-variant flex items-center gap-1">
            <Folder className="w-3.5 h-3.5" /> Categoría:
          </span>
          {availableCategories.map((cat) => (
            <button
              key={cat}
              onClick={() => toggleCategory(cat)}
              className={`px-2.5 py-1 rounded-full transition-colors font-medium ${
                selectedCategory === cat
                  ? "bg-site-primary text-site-on-primary"
                  : "bg-site-surface-container-high text-site-on-surface hover:bg-site-surface-bright"
              }`}
            >
              {cat}
            </button>
          ))}

          <span className="font-semibold text-site-on-surface-variant flex items-center gap-1 ml-2">
            <Tag className="w-3.5 h-3.5" /> Etiquetas:
          </span>
          {availableTags.map((t) => {
            const isSelected = selectedTags.includes(t);
            return (
              <button
                key={t}
                onClick={() => toggleTag(t)}
                className={`px-2.5 py-1 rounded-full transition-colors font-medium ${
                  isSelected
                    ? "bg-site-secondary text-site-on-primary"
                    : "bg-site-surface-container-high text-site-on-surface hover:bg-site-surface-bright"
                }`}
              >
                #{t}
              </button>
            );
          })}
        </div>

        {/* Search Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Loading state indicator */}
          {loading && results.length === 0 && (
            <div className="py-12 flex flex-col items-center justify-center text-zinc-400">
              <Loader2 className="w-8 h-8 animate-spin mb-2 text-sky-500" />
              <p className="text-sm">Buscando resultados...</p>
            </div>
          )}

          {/* Empty State */}
          {!loading && hasSearched && results.length === 0 && promoted.length === 0 && (
            <div className="py-12 text-center text-site-on-surface-variant">
              <p className="text-base font-medium">No se encontraron resultados</p>
              <p className="text-xs mt-1 opacity-75">Intenta con otros términos o elimina los filtros aplicados.</p>
            </div>
          )}

          {/* Promoted Results Section */}
          {promoted.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-site-primary">
                <Star className="w-4 h-4 fill-site-primary" /> Resultados Destacados
              </div>
              <div className="grid gap-2">
                {promoted.map((item, idx) => {
                  const href = item.entity_slug
                    ? `/${item.entity_slug.replace(/^\//, "")}`
                    : `/${item.entity_id}`;
                  return (
                    <Link
                      key={`promoted-${idx}`}
                      href={href}
                      onClick={onClose}
                      className="p-3 bg-site-primary/5 border border-site-primary/20 rounded-lg flex items-center justify-between hover:bg-site-primary/10 transition-colors group"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold px-2 py-0.5 rounded bg-site-primary/15 text-site-primary">
                            Promocionado
                          </span>
                          <span className="font-semibold text-site-on-surface group-hover:text-site-primary">
                            {item.title || item.entity_id}
                          </span>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-site-primary group-hover:translate-x-1 transition-transform" />
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {/* Standard Search Results Section */}
          {results.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-site-on-surface-variant">
                Resultados ({results.length})
              </div>
              <div className="divide-y divide-site-outline-variant/20">
                {results.map((item, idx) => {
                  const href = item.entity_slug
                    ? `/${item.entity_slug.replace(/^\//, "")}`
                    : `/${item.entity_id}`;
                  return (
                    <Link
                      key={`result-${idx}`}
                      href={href}
                      onClick={onClose}
                      className="py-3 px-2 rounded-lg block hover:bg-site-surface-container-high/50 transition-colors group"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-sm font-semibold text-site-on-surface group-hover:text-site-primary transition-colors">
                          {item.title || item.entity_slug || item.entity_id}
                        </h4>
                        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-site-surface-container-high text-site-on-surface-variant shrink-0">
                          {item.entity_type}
                        </span>
                      </div>
                      {item.body_text && (
                        <p className="text-xs text-site-on-surface-variant line-clamp-2 mt-1">
                          {item.body_text}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-2 text-[11px] text-site-on-surface-variant">
                        {item.category && (
                          <span className="inline-flex items-center gap-1 text-site-primary font-medium">
                            <Folder className="w-3 h-3" /> {item.category}
                          </span>
                        )}
                        {item.tags && item.tags.length > 0 && (
                          <span className="inline-flex items-center gap-1">
                            <Tag className="w-3 h-3" /> {item.tags.join(", ")}
                          </span>
                        )}
                      </div>
                    </Link>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer info */}
        <div className="px-4 py-2 bg-site-surface-container-low border-t border-site-outline-variant/30 flex justify-between items-center text-[11px] text-site-on-surface-variant">
          <span>Usa <kbd className="px-1 py-0.5 bg-site-surface-container-high rounded border border-site-outline-variant/20">⌘K</kbd> / <kbd className="px-1 py-0.5 bg-site-surface-container-high rounded border border-site-outline-variant/20">Ctrl+K</kbd> para abrir o cerrar</span>
          <span>Búsqueda CMS 2.0</span>
        </div>
      </div>
    </div>
  );
}
