"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import { Calendar, ArrowLeft, Tag, FolderOpen, User } from "lucide-react";
import OptimizedImage from "@/components/ui/OptimizedImage";
import { getCmsPublicPost } from "@/lib/cms/v2";
import { CmsPublicPost } from "@/types/cms-v2";
import { SITE_KEY } from "@/lib/site-config";

export default function BlogPostPage() {
  const params = useParams();
  const slug = params?.slug && typeof params.slug === "string" ? params.slug : "";
  const [post, setPost] = useState<CmsPublicPost | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    getCmsPublicPost(SITE_KEY, slug)
      .then((data) => setPost(data))
      .catch(() => setPost(null))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <main className="pt-[88px] pb-4 min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--site-primary) transparent transparent transparent" }} />
        </div>
      </main>
    );
  }

  if (!post) {
    return (
      <main className="pt-[88px] pb-4 min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>Artículo no encontrado</h1>
          <p className="mb-6" style={{ color: "var(--site-on-surface-variant)" }}>El post que buscas no existe o no está publicado.</p>
          <Link href="/blog" className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-bold uppercase tracking-wide" style={{ background: "var(--site-primary)", color: "var(--site-on-primary)" }}>
            <ArrowLeft size={16} /> Volver al blog
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="pt-[88px] pb-4 min-h-screen">
      {/* Hero / Featured Image */}
      {post.featured_image_url && (
        <div className="relative w-full h-[40vh] md:h-[50vh] overflow-hidden">
          <OptimizedImage
            src={post.featured_image_url}
            alt={post.title}
            fill
            sizes="100vw"
            className="object-cover"
            priority
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
        </div>
      )}

      <article className="ccf-container -mt-16 relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl mx-auto rounded-2xl border p-6 md:p-10"
          style={{ background: "var(--site-surface)", borderColor: "var(--site-outline-variant)" }}
        >
          {/* Back link */}
          <Link href="/blog" className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide mb-6 transition-opacity hover:opacity-70" style={{ color: "var(--site-primary)" }}>
            <ArrowLeft size={14} /> Volver al blog
          </Link>

          {/* Meta */}
          <div className="flex flex-wrap items-center gap-3 mb-4 text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--site-on-surface-variant)" }}>
            {post.published_at && (
              <span className="flex items-center gap-1">
                <Calendar size={12} />
                {new Date(post.published_at).toLocaleDateString("es-CO", { day: "2-digit", month: "long", year: "numeric" })}
              </span>
            )}
            {post.author_name && (
              <>
                <span className="w-1 h-1 rounded-full" style={{ background: "var(--site-outline)" }} />
                <span className="flex items-center gap-1">
                  <User size={12} /> {post.author_name}
                </span>
              </>
            )}
          </div>

          {/* Title */}
          <h1 className="text-3xl md:text-4xl font-bold mb-6 leading-tight" style={{ color: "var(--site-on-surface)" }}>
            {post.title}
          </h1>

          {/* Categories & Tags */}
          {(post.categories?.length || post.tags?.length) ? (
            <div className="flex flex-wrap gap-2 mb-8">
              {post.categories?.map((cat) => (
                <Link key={cat.id} href={`/categoria/${cat.slug}`}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wide transition-opacity hover:opacity-70"
                  style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                  <FolderOpen size={10} /> {cat.name}
                </Link>
              ))}
              {post.tags?.map((tag) => (
                <Link key={tag.id} href={`/etiqueta/${tag.slug}`}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-semibold uppercase tracking-wide transition-opacity hover:opacity-70"
                  style={{ background: "var(--site-surface-container-highest)", color: "var(--site-on-surface-variant)" }}>
                  <Tag size={10} /> {tag.name}
                </Link>
              ))}
            </div>
          ) : null}

          {/* Excerpt */}
          {post.excerpt && (
            <p className="text-lg italic leading-relaxed mb-8 p-4 rounded-xl border-l-4" style={{ background: "var(--site-surface-container-low)", borderColor: "var(--site-primary)", color: "var(--site-on-surface-variant)" }}>
              {post.excerpt}
            </p>
          )}

          {/* Content */}
          {post.content && (
            <div
              className="prose prose-lg max-w-none dark:prose-invert"
              style={{ color: "var(--site-on-surface)" }}
              dangerouslySetInnerHTML={{ __html: post.content }}
            />
          )}

          {!post.content && !post.excerpt && (
            <p className="text-center py-1.5 opacity-60" style={{ color: "var(--site-on-surface-variant)" }}>
              Este artículo no tiene contenido aún.
            </p>
          )}
        </motion.div>
      </article>
    </main>
  );
}
