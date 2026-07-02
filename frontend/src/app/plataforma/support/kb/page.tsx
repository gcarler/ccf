"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Book,
  Search,
  ChevronRight,
  Star,
  Zap,
  Users,
  BookOpen,
  Layout,
  TrendingUp,
  FileText,
  Loader2,
  LucideIcon,
} from "lucide-react";
import clsx from "clsx";
import { apiFetch } from "@/lib/http";
import { useAuth } from "@/context/AuthContext";

interface KbCategory {
  id: string;
  label: string;
  count: number;
}

interface KbArticle {
  id: string;
  title: string;
  category: string;
  summary: string;
  views: number;
  helpful: number;
}

const CATEGORY_META: Record<
  string,
  { icon: LucideIcon; color: string }
> = {
  "getting-started": { icon: Zap, color: "text-amber-500 bg-amber-50 dark:bg-amber-500/10" },
  crm: { icon: Users, color: "text-[hsl(var(--primary))] bg-blue-50 dark:bg-blue-500/10" },
  academy: { icon: BookOpen, color: "text-sky-500 bg-sky-50 dark:bg-sky-500/10" },
  projects: { icon: Layout, color: "text-emerald-500 bg-emerald-50 dark:bg-emerald-500/10" },
  finances: { icon: TrendingUp, color: "text-rose-500 bg-rose-50 dark:bg-rose-500/10" },
  admin: { icon: FileText, color: "text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5" },
};

function getCategoryMeta(id: string) {
  return (
    CATEGORY_META[id] ?? {
      icon: Book,
      color: "text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] dark:bg-white/5",
    }
  );
}

export default function SupportKBPage() {
  const { token } = useAuth();
  const [categories, setCategories] = useState<KbCategory[]>([]);
  const [articles, setArticles] = useState<KbArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCat, setSelectedCat] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const fetchData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [cats, arts] = await Promise.all([
        apiFetch<KbCategory[]>("/support/kb/categories", { token }),
        apiFetch<KbArticle[]>("/support/kb/articles?popular=true", { token }),
      ]);
      setCategories(Array.isArray(cats) ? cats : []);
      setArticles(Array.isArray(arts) ? arts : []);
    } catch (err) {
      console.error("Error loading KB:", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredArticles = articles.filter((article) => {
    const matchesSearch = article.title
      .toLowerCase()
      .includes(search.trim().toLowerCase());
    const matchesCat = !selectedCat || article.category === selectedCat;
    return matchesSearch && matchesCat;
  });

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--surface-1))] dark:bg-[#0f1117]">
      {/* Hero Search */}
      <div className="bg-gradient-to-br from-blue-600 to-sky-700 p-4 text-center relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              "radial-gradient(circle at 50% 0%, white 0%, transparent 60%)",
          }}
        />
        <div className="relative">
          <Book size={32} className="text-white/60 mx-auto mb-4" />
          <h1 className="text-lg font-bold text-white mb-2">
            Base de Conocimientos
          </h1>
          <p className="text-blue-200 text-sm mb-3">
            Encuentra respuestas a todas tus preguntas sobre la plataforma CCF
          </p>
          <div className="max-w-lg mx-auto relative">
            <Search
              size={18}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]"
            />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar artículos, guías, tutoriales..."
              className="w-full pl-12 pr-5 py-1.5 rounded-lg bg-[hsl(var(--bg-primary))] shadow-2xl text-sm text-[hsl(var(--text-primary))] outline-none focus:ring-2 focus:ring-blue-400/40 font-medium"
            />
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="w-full space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-[hsl(var(--text-secondary))]">
              <Loader2 size={24} className="animate-spin mr-2" />
              Cargando base de conocimientos...
            </div>
          ) : (
            <>
              {/* Categories */}
              <section>
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-5">
                  Explorar por Categoría
                </p>
                {categories.length === 0 ? (
                  <p className="text-sm text-[hsl(var(--text-secondary))]">
                    No hay categorías disponibles.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {categories.map((cat, i) => {
                      const meta = getCategoryMeta(cat.id);
                      const Icon = meta.icon;
                      return (
                        <motion.button
                          key={cat.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.04 }}
                          onClick={() =>
                            setSelectedCat(selectedCat === cat.id ? null : cat.id)
                          }
                          className={clsx(
                            "flex items-center gap-4 p-3 rounded-lg border transition-all text-left shadow-sm group",
                            selectedCat === cat.id
                              ? "border-blue-500 bg-blue-50 dark:bg-blue-500/10"
                              : "border-[hsl(var(--border))]/60 dark:border-white/5 bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] hover:shadow-md"
                          )}
                        >
                          <div
                            className={clsx(
                              "size-6 rounded-md flex items-center justify-center shrink-0",
                              meta.color
                            )}
                          >
                            <Icon size={20} />
                          </div>
                          <div>
                            <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))]">
                              {cat.label}
                            </p>
                            <p className="text-[10px] text-[hsl(var(--text-secondary))]">
                              {cat.count} artículos
                            </p>
                          </div>
                        </motion.button>
                      );
                    })}
                  </div>
                )}
              </section>

              {/* Popular Articles */}
              <section>
                <div className="flex items-center gap-2 mb-5">
                  <Star size={14} className="text-amber-500" />
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                    {selectedCat ? "Artículos" : "Artículos más Populares"}
                  </p>
                </div>
                {filteredArticles.length === 0 ? (
                  <p className="text-sm text-[hsl(var(--text-secondary))]">
                    No se encontraron artículos.
                  </p>
                ) : (
                  <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1a1d27] rounded-lg border border-[hsl(var(--border))]/60 dark:border-white/5 shadow-sm divide-y divide-[hsl(var(--border))] dark:divide-white/5 overflow-hidden">
                    {filteredArticles.map((article, i) => (
                      <motion.div
                        key={article.id}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 + i * 0.04 }}
                        className="flex items-center gap-4 px-3 py-1.5 hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5 transition-all cursor-pointer group"
                      >
                        <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center font-semibold text-[hsl(var(--text-secondary))]">
                          {i + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] truncate group-hover:text-[hsl(var(--primary))] transition-colors">
                            {article.title}
                          </p>
                          <div className="flex items-center gap-3 mt-0.5">
                            <span className="text-[10px] text-[hsl(var(--text-secondary))]">
                              {article.category}
                            </span>
                            <span className="text-[10px] text-[hsl(var(--text-secondary))]">
                              ·
                            </span>
                            <span className="text-[10px] text-[hsl(var(--text-secondary))]">
                              {article.views} vistas
                            </span>
                            <span className="text-[10px] text-emerald-500 font-bold">
                              {article.helpful}% útil
                            </span>
                          </div>
                        </div>
                        <ChevronRight
                          size={14}
                          className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))] transition-colors shrink-0"
                        />
                      </motion.div>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
