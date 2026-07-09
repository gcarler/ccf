"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Calendar, ArrowRight, ArrowLeft, Tag, FileText } from "lucide-react";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { getCmsPublicPosts } from "@/lib/cms/v2";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { CmsPublicPost } from "@/types/cms-v2";
import { SITE_KEY } from "@/lib/site-config";

function applyTemplate(template: string, name: string) {
  return template.replace(/{\s*tagName\s*}/g, name);
}

export default function TagArchivePage() {
  const cmsPage = useCmsV2Page("blog");
  const archiveContent = cmsPage?.blocks?.archive_template;
  const tagTitlePrefix = (archiveContent?.tag_title_prefix as string) ?? "";
  const tagDescriptionTemplate = (archiveContent?.tag_description_template as string) ?? "";

  const params = useParams();
  const slug = params?.slug && typeof params.slug === "string" ? params.slug : "";
  const [posts, setPosts] = useState<CmsPublicPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [tagName, setTagName] = useState(slug);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    getCmsPublicPosts(SITE_KEY, { tag_slug: slug })
      .then((data) => {
        const items = Array.isArray(data) ? data : [];
        setPosts(items);
        if (items.length > 0 && items[0].tags) {
          const t = items[0].tags.find((tg) => tg.slug === slug);
          if (t) setTagName(t.name);
        }
      })
      .catch(() => setPosts([]))
      .finally(() => setLoading(false));
  }, [slug]);

  return (
    <main className="pt-[88px] pb-4 min-h-screen">
      {/* Header */}
      <section className="ccf-section relative flex flex-col items-center text-center">
        <div className="absolute inset-0 bg-beam-gradient pointer-events-none opacity-60" />
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="ccf-container relative z-10 max-w-4xl"
        >
          {tagTitlePrefix && (
            <span className="text-xs font-semibold uppercase tracking-wide block mb-3" style={{ color: "var(--site-primary)" }}>
              {tagTitlePrefix} {tagName}
            </span>
          )}
          <h1 className="mx-auto max-w-4xl font-bold ccf-display text-4xl sm:text-5xl lg:text-6xl mb-3" style={{ color: "var(--site-on-background)" }}>
            #{tagName}
          </h1>
          {tagDescriptionTemplate && (
            <p className="ccf-body text-base sm:text-lg max-w-2xl mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>
              {applyTemplate(tagDescriptionTemplate, tagName)}
            </p>
          )}
        </motion.div>
      </section>

      {/* Back + Posts */}
      <section className="ccf-section-tight ccf-container min-h-[50vh]">
        <Link href="/blog" className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide mb-6 transition-opacity hover:opacity-70" style={{ color: "var(--site-primary)" }}>
          <ArrowLeft size={14} /> Volver al blog
        </Link>

        {loading ? (
          <div className="flex flex-col items-center gap-4 py-1.5">
            <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--site-primary) transparent transparent transparent" }} />
          </div>
        ) : posts.length === 0 ? (
          <div className="flex flex-col items-center justify-center text-center py-1.5">
            <Tag size={64} className="mb-3 opacity-20" style={{ color: "var(--site-primary)" }} />
            <h3 className="text-xl font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>Sin artículos con esta etiqueta</h3>
            <p className="ccf-body text-lg opacity-80 max-w-md mx-auto" style={{ color: "var(--site-on-surface-variant)" }}>
              No hay posts publicados con esta etiqueta todavía.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {posts.map((post, index) => (
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
              </motion.article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
