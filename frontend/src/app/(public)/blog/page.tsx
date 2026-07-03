"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Calendar, ArrowRight, Tag, FolderOpen, Search, FileText } from "lucide-react";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { getCmsPublicPosts } from "@/lib/cms/v2";
import { CmsPublicPost } from "@/types/cms-v2";
import { SITE_KEY } from "@/lib/site-config";

export default function BlogPage() {
  const [posts, setPosts] = useState<CmsPublicPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    getCmsPublicPosts(SITE_KEY)
      .then((data) => setPosts(Array.isArray(data) ? data : []))
      .catch(() => setPosts([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = posts.filter((p) =>
    p.title.toLowerCase().includes(search.toLowerCase()) ||
    (p.excerpt || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <main className="pt-[88px] pb-4 min-h-screen">
      {/* Hero */}
      <section className="ccf-section relative flex flex-col items-center text-center">
        <div className="absolute inset-0 bg-beam-gradient pointer-events-none opacity-60" />
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="ccf-container relative z-10 max-w-4xl"
        >
          <span className="text-xs font-semibold uppercase tracking-wide block mb-3" style={{ color: "var(--site-primary)" }}>
            Blog
          </span>
          <h1 className="mx-auto max-w-4xl font-bold ccf-display text-5xl sm:text-6xl lg:text-7xl mb-3" style={{ color: "var(--site-on-background)" }}>
            Artículos y <br />
            <span className="italic" style={{ background: "linear-gradient(135deg, var(--site-primary), var(--site-secondary))", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Noticias.
            </span>
          </h1>
          <p className="ccf-body text-base sm:text-lg max-w-2xl mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>
            Reflexiones, enseñanzas y actualizaciones de nuestra comunidad.
          </p>
        </motion.div>
      </section>

      {/* Search */}
      <section className="ccf-section-tight ccf-container">
        <div className="rounded-lg p-4 flex items-center gap-4 border transition-all focus-within:shadow-2xl focus-within:-translate-y-1"
          style={{ background: "var(--site-surface-container)", borderColor: "var(--site-outline-variant)" }}>
          <Search size={24} style={{ color: "var(--site-primary)" }} className="opacity-70 ml-2" />
          <input
            type="text"
            placeholder="Buscar artículos..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent border-none outline-none text-lg font-medium"
            style={{ color: "var(--site-on-surface)" }}
          />
        </div>
      </section>

      {/* Posts Grid */}
      <section className="ccf-section-tight ccf-container min-h-[50vh]">
        {loading ? (
          <div className="flex flex-col items-center gap-4 py-1.5">
            <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--site-primary) transparent transparent transparent" }} />
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center py-1.5">
            <FileText size={64} className="mb-3 opacity-20" style={{ color: "var(--site-primary)" }} />
            <h3 className="text-xl font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>Sin artículos publicados</h3>
            <p className="ccf-body text-lg opacity-80 max-w-md mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>
              Cuando se publiquen posts en el CMS, aparecerán aquí.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {filtered.map((post, index) => (
              <motion.article
                key={post.slug}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.08, duration: 0.5 }}
                className="group rounded-2xl border overflow-hidden transition-all duration-500 hover:shadow-2xl hover:-translate-y-1"
                style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}
              >
                <Link href={`/blog/${post.slug}`} className="block">
                  {post.featured_image_url ? (
                    <div className="relative h-48 overflow-hidden">
                      <OptimizedImage
                        src={post.featured_image_url}
                        alt={post.title}
                        fill
                        sizes="(max-width: 768px) 100vw, (max-width: 1280px) 50vw, 33vw"
                        className="object-cover transition-transform duration-700 group-hover:scale-105"
                      />
                    </div>
                  ) : (
                    <div className="h-48 flex items-center justify-center" style={{ background: "var(--site-surface-container)" }}>
                      <FileText size={48} style={{ color: "var(--site-outline)" }} />
                    </div>
                  )}
                  <div className="p-6">
                    <div className="flex items-center gap-3 mb-3 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--site-on-surface-variant)" }}>
                      {post.published_at && (
                        <span className="flex items-center gap-1">
                          <Calendar size={12} />
                          {new Date(post.published_at).toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "numeric" })}
                        </span>
                      )}
                      {post.author_name && (
                        <>
                          <span className="w-1 h-1 rounded-full" style={{ background: "var(--site-outline)" }} />
                          <span>{post.author_name}</span>
                        </>
                      )}
                    </div>
                    <h2 className="text-lg font-bold mb-2 line-clamp-2 group-hover:opacity-80 transition-opacity" style={{ color: "var(--site-on-surface)" }}>
                      {post.title}
                    </h2>
                    {post.excerpt && (
                      <p className="text-sm leading-relaxed line-clamp-3 mb-4" style={{ color: "var(--site-on-surface-variant)" }}>
                        {post.excerpt}
                      </p>
                    )}
                    <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-wide" style={{ color: "var(--site-primary)" }}>
                      Leer más <ArrowRight size={14} />
                    </span>
                  </div>
                </Link>
                {(post.categories?.length || post.tags?.length) ? (
                  <div className="px-6 pb-6 pt-0 flex flex-wrap gap-2">
                    {post.categories?.map((cat) => (
                      <Link key={cat.id} href={`/categoria/${cat.slug}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide transition-opacity hover:opacity-70"
                        style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                        <FolderOpen size={10} /> {cat.name}
                      </Link>
                    ))}
                    {post.tags?.map((tag) => (
                      <Link key={tag.id} href={`/etiqueta/${tag.slug}`}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide transition-opacity hover:opacity-70"
                        style={{ background: "var(--site-surface-container-highest)", color: "var(--site-on-surface-variant)" }}>
                        <Tag size={10} /> {tag.name}
                      </Link>
                    ))}
                  </div>
                ) : null}
              </motion.article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
