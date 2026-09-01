"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { Search, X, Loader2, Star, Tag, Folder, ArrowRight } from "lucide-react";
import { uiList, uiRecord, uiText, usePublicUiCopy } from "./usePublicUiCopy";

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
  availableCategories,
  availableTags,
}: PublicSearchModalProps) {
  const ui = uiRecord(usePublicUiCopy().search);
  const categories = availableCategories ?? uiList(ui, "categories");
  const tags = availableTags ?? uiList(ui, "tags");
  const text = (key: string) => uiText(ui, key);
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
      <div className="w-full max-w-2xl bg-white dark:bg-zinc-900 rounded-xl shadow-2xl overflow-hidden border border-zinc-200 dark:border-zinc-800 flex flex-col max-h-[80vh]">
        {/* Header Search Input */}
        <div className="relative flex items-center px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
          <Search className="w-5 h-5 text-zinc-400 shrink-0 mr-3" />
          <input
            ref={inputRef}
            id="search-modal-title"
            type="text"
            className="w-full bg-transparent text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none text-lg"
            placeholder={text("placeholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {loading ? (
            <Loader2 className="w-5 h-5 text-sky-500 animate-spin shrink-0 ml-2" />
          ) : query ? (
            <button
              onClick={() => setQuery("")}
              className="p-1 rounded-full text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors"
              aria-label={text("clear_label")}
            >
              <X className="w-4 h-4" />
            </button>
          ) : null}
          <button
            onClick={onClose}
            className="ml-3 px-2 py-1 text-xs font-medium text-zinc-500 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded transition-colors"
          >
            {text("close_label")}
          </button>
        </div>

        {/* Filter Pills */}
        <div className="px-4 py-2.5 bg-zinc-50 dark:bg-zinc-950 border-b border-zinc-200 dark:border-zinc-800 flex flex-wrap items-center gap-2 text-xs">
          <span className="font-semibold text-zinc-500 dark:text-zinc-400 flex items-center gap-1">
            <Folder className="w-3.5 h-3.5" /> {text("category_label")}
          </span>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => toggleCategory(cat)}
              className={`px-2.5 py-1 rounded-full transition-colors font-medium ${
                selectedCategory === cat
                  ? "bg-sky-600 text-white"
                  : "bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700"
              }`}
            >
              {cat}
            </button>
          ))}

          <span className="font-semibold text-zinc-500 dark:text-zinc-400 flex items-center gap-1 ml-2">
            <Tag className="w-3.5 h-3.5" /> {text("tags_label")}
          </span>
          {tags.map((t) => {
            const isSelected = selectedTags.includes(t);
            return (
              <button
                key={t}
                onClick={() => toggleTag(t)}
                className={`px-2.5 py-1 rounded-full transition-colors font-medium ${
                  isSelected
                    ? "bg-emerald-600 text-white"
                    : "bg-zinc-200 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-700"
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
              <p className="text-sm">{text("loading_label")}</p>
            </div>
          )}

          {/* Empty State */}
          {!loading && hasSearched && results.length === 0 && promoted.length === 0 && (
            <div className="py-12 text-center text-zinc-500 dark:text-zinc-400">
              <p className="text-base font-medium">{text("empty_title")}</p>
              <p className="text-xs mt-1">{text("empty_description")}</p>
            </div>
          )}

          {/* Promoted Results Section */}
          {promoted.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                <Star className="w-4 h-4 fill-amber-500" /> {text("promoted_label")}
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
                      className="p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 rounded-lg flex items-center justify-between hover:bg-amber-100 dark:hover:bg-amber-950/50 transition-colors group"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold px-2 py-0.5 rounded bg-amber-200 dark:bg-amber-800 text-amber-900 dark:text-amber-100">
                            {text("promoted_badge")}
                          </span>
                          <span className="font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-amber-700 dark:group-hover:text-amber-300">
                            {item.title || item.entity_id}
                          </span>
                        </div>
                      </div>
                      <ArrowRight className="w-4 h-4 text-amber-500 group-hover:translate-x-1 transition-transform" />
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {/* Standard Search Results Section */}
          {results.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                {text("results_label")} ({results.length})
              </div>
              <div className="divide-y divide-zinc-100 dark:divide-zinc-800">
                {results.map((item, idx) => {
                  const href = item.entity_slug
                    ? `/${item.entity_slug.replace(/^\//, "")}`
                    : `/${item.entity_id}`;
                  return (
                    <Link
                      key={`result-${idx}`}
                      href={href}
                      onClick={onClose}
                      className="py-3 px-2 rounded-lg block hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors group"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <h4 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 group-hover:text-sky-600 dark:group-hover:text-sky-400 transition-colors">
                          {item.title || item.entity_slug || item.entity_id}
                        </h4>
                        <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 shrink-0">
                          {item.entity_type}
                        </span>
                      </div>
                      {item.body_text && (
                        <p className="text-xs text-zinc-500 dark:text-zinc-400 line-clamp-2 mt-1">
                          {item.body_text}
                        </p>
                      )}
                      <div className="flex items-center gap-2 mt-2 text-[11px] text-zinc-400">
                        {item.category && (
                          <span className="inline-flex items-center gap-1 text-sky-600 dark:text-sky-400 font-medium">
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
        <div className="px-4 py-2 bg-zinc-50 dark:bg-zinc-950 border-t border-zinc-200 dark:border-zinc-800 flex justify-between items-center text-[11px] text-zinc-400">
          <span>{text("shortcut_prefix")} <kbd className="px-1 py-0.5 bg-zinc-200 dark:bg-zinc-800 rounded">⌘K</kbd> / <kbd className="px-1 py-0.5 bg-zinc-200 dark:bg-zinc-800 rounded">Ctrl+K</kbd> {text("shortcut_suffix")}</span>
          <span>{text("product_label")}</span>
        </div>
      </div>
    </div>
  );
}
