"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, CheckCircle2, Clock, User } from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import { apiFetch } from "@/lib/http";
import PublicHeroWithSlides, { type PublicSlide } from "@/components/public/PublicHeroWithSlides";
import type { CourseSummary } from "@/types/academy";

type PublicCourse = CourseSummary & {
  cta?: string;
  lessons?: number;
  instructor?: string;
  description?: string;
  modality?: string;
};

export default function CursosPage() {
  const heroPage = useCmsV2Page("courses");
  const heroContent = heroPage?.blocks?.hero;
  const feedContent = heroPage?.blocks?.feed;

  const [courses, setCourses] = useState<PublicCourse[]>([]);
  const [loading, setLoading] = useState(true);

  const heroEyebrow = typeof heroContent?.eyebrow === "string" ? heroContent.eyebrow : "";
  const heroTitleLead = typeof heroContent?.title_lead === "string" ? heroContent.title_lead : "";
  const heroAccent = typeof heroContent?.title_accent === "string" ? heroContent.title_accent : "";
  const heroDescription = typeof heroContent?.description === "string" ? heroContent.description : "";
  const heroImageUrl = typeof feedContent?.parsed === "object" && feedContent?.parsed && !Array.isArray(feedContent.parsed) && typeof (feedContent.parsed as Record<string, unknown>).hero_image_url === "string"
    ? String((feedContent.parsed as Record<string, unknown>).hero_image_url)
    : "";
  const ctaImages = typeof feedContent?.parsed === "object" && feedContent?.parsed && !Array.isArray(feedContent.parsed) && Array.isArray((feedContent.parsed as Record<string, unknown>).cta_images)
    ? ((feedContent.parsed as Record<string, unknown>).cta_images as Array<Record<string, unknown>>)
    : [];
  const coursesTitle = typeof feedContent?.parsed === "object" && feedContent?.parsed && !Array.isArray(feedContent.parsed) && typeof (feedContent.parsed as Record<string, unknown>).courses_title === "string"
    ? String((feedContent.parsed as Record<string, unknown>).courses_title)
    : "";
  const coursesDescription = typeof feedContent?.parsed === "object" && feedContent?.parsed && !Array.isArray(feedContent.parsed) && typeof (feedContent.parsed as Record<string, unknown>).courses_description === "string"
    ? String((feedContent.parsed as Record<string, unknown>).courses_description)
    : "";
  const emptyTitle = typeof feedContent?.parsed === "object" && feedContent?.parsed && !Array.isArray(feedContent.parsed) && typeof (feedContent.parsed as Record<string, unknown>).empty_title === "string"
    ? String((feedContent.parsed as Record<string, unknown>).empty_title)
    : "";
  const emptyDescription = typeof feedContent?.parsed === "object" && feedContent?.parsed && !Array.isArray(feedContent.parsed) && typeof (feedContent.parsed as Record<string, unknown>).empty_description === "string"
    ? String((feedContent.parsed as Record<string, unknown>).empty_description)
    : "";

  useEffect(() => {
    let alive = true;
    apiFetch<PublicCourse[]>("/academy/courses", { silent: true })
      .then((data) => {
        if (!alive) return;
        setCourses(Array.isArray(data) ? data.filter((c) => Boolean(c.id) && Boolean(c.title)) : []);
      })
      .catch(() => {
        if (!alive) return;
        setCourses([]);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const featured = courses[0];
  const rest = courses.slice(1);
  const hasHero = Boolean(heroTitleLead || heroAccent || heroDescription);
  const heroSlides: PublicSlide[] = ([
    heroImageUrl
      ? {
          src: heroImageUrl,
          alt: heroTitleLead || heroAccent || "Cursos CCF",
          title: heroTitleLead || heroAccent || "Cursos",
          caption: heroDescription || undefined,
        }
      : null,
    ...ctaImages.slice(0, 3).map((slide, index) => {
      const src = typeof slide.src === "string" ? slide.src : "";
      if (!src) return null;
      return {
        src,
        alt: typeof slide.alt === "string" && slide.alt.trim() ? slide.alt : `Curso ${index + 1}`,
        title: index === 0 ? coursesTitle || "Formación" : undefined,
        caption: index === 0 ? coursesDescription || undefined : undefined,
      };
    }),
  ] as (PublicSlide | null)[]).filter((slide): slide is PublicSlide => Boolean(slide));

  return (
    <main className="pt-[88px] pb-4 overflow-hidden">
      {hasHero && (
        <PublicHeroWithSlides
          eyebrow={heroEyebrow}
          titleLead={heroTitleLead}
          titleAccent={heroAccent}
          description={heroDescription}
          slides={heroSlides}
        />
      )}

      <section className="ccf-section ccf-container">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-14 gap-3">
          <div className="max-w-2xl">
            {coursesTitle && <h2 className="ccf-headline text-2xl md:text-3xl font-bold mb-4" style={{ color: "var(--site-on-surface)" }}>{coursesTitle}</h2>}
            {coursesDescription && <p className="ccf-body text-lg" style={{ color: "var(--site-on-surface-variant)" }}>{coursesDescription}</p>}
          </div>
        </div>

        {loading ? (
          <div className="py-16 flex justify-center">
            <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin" style={{ borderColor: "var(--site-primary) transparent transparent transparent" }} />
          </div>
        ) : featured ? (
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5 md:gap-6">
            <motion.article className="md:col-span-8 group relative rounded-lg overflow-hidden min-h-[280px] md:min-h-[450px] cursor-pointer" style={{ background: "var(--site-surface-container-low)" }} whileHover={{ y: -2 }}>
              <Link href={`/academy/courses/${featured.id}`} className="absolute inset-0 z-20" />
              <div className="absolute inset-0">
                <Image src={heroImageUrl || "/og-default.png"} alt={featured.title} fill className="object-cover transition-transform duration-700 group-hover:scale-105" style={{ opacity: 0.5 }} />
              </div>
              <div className="absolute inset-0" style={{ background: "linear-gradient(to top, var(--site-surface-container-lowest) 0%, transparent 60%)" }} />
              <div className="absolute bottom-0 p-4 md:p-4 w-full relative z-10 flex flex-col justify-end h-full">
                <span className="inline-block px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wide mb-3" style={{ background: "var(--site-card-highlight)", color: "var(--site-primary)" }}>
                  {featured.modality || "Publicado por Academia"}
                </span>
                <h3 className="text-2xl md:text-3xl font-black mb-4 text-[hsl(var(--text-primary))] dark:text-white">{featured.title}</h3>
                <p className="text-base leading-relaxed max-w-2xl mb-6 text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">{featured.description || featured.title}</p>
                <span className="inline-flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-[hsl(var(--primary))]">{featured.cta || "Ver curso"} <ArrowRight size={16} /></span>
              </div>
            </motion.article>

            <div className="md:col-span-4 grid gap-4">
              {rest.slice(0, 3).map((course) => (
                <motion.article key={course.id} className="group rounded-lg overflow-hidden border bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] dark:border-white/10" whileHover={{ y: -2 }}>
                  <Link href={`/academy/courses/${course.id}`} className="block">
                    <div className="relative h-40 bg-[hsl(var(--surface-2))]">
                      <Image src={heroImageUrl || "/og-default.png"} alt={course.title} fill className="object-cover" />
                    </div>
                    <div className="p-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide mb-3" style={{ background: "var(--site-primary-container)", color: "var(--site-primary)" }}>
                        {course.modality || "Academia"}
                      </span>
                      <h3 className="font-bold text-[hsl(var(--text-primary))] dark:text-white line-clamp-2">{course.title}</h3>
                      <p className="mt-2 text-sm text-[hsl(var(--text-secondary))] line-clamp-2">{course.description || course.title}</p>
                    </div>
                  </Link>
                </motion.article>
              ))}
            </div>
          </div>
        ) : (
          <div className="rounded-lg p-8 text-center" style={{ background: "var(--site-surface-container-low)" }}>
            {emptyTitle && <h3 className="text-xl font-bold mb-2">{emptyTitle}</h3>}
            {emptyDescription && <p className="text-sm text-[hsl(var(--text-secondary))]">{emptyDescription}</p>}
          </div>
        )}
      </section>

      <section className="ccf-section ccf-container">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {rest.slice(3).map((course) => (
            <Link key={course.id} href={`/academy/courses/${course.id}`} className="rounded-lg border p-5 bg-[hsl(var(--surface-1))] border-[hsl(var(--border))] dark:border-white/10 hover:shadow-lg transition-shadow">
              <div className="flex items-center justify-between gap-3 mb-3">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide" style={{ background: "var(--site-surface-container)", color: "var(--site-primary)" }}>
                  {course.modality || "Academia"}
                </span>
                <CheckCircle2 size={16} className="text-[hsl(var(--primary))]" />
              </div>
              <h3 className="font-bold mb-2">{course.title}</h3>
              <p className="text-sm text-[hsl(var(--text-secondary))] line-clamp-3">{course.description || course.title}</p>
              <div className="mt-4 flex items-center gap-4 text-xs text-[hsl(var(--text-secondary))]">
                {course.lessons ? <span className="inline-flex items-center gap-1"><Clock size={12} /> {course.lessons} clases</span> : null}
                {course.instructor ? <span className="inline-flex items-center gap-1"><User size={12} /> {course.instructor}</span> : null}
              </div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
