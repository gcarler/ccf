"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, Play } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import OptimizedImage from "@/components/ui/OptimizedImage";

export type PublicSlide = {
  src: string;
  alt: string;
  title?: string;
  caption?: string;
  href?: string;
};

type Props = {
  eyebrow?: string;
  titleLead?: string;
  titleAccent?: string;
  titleTail?: string;
  title?: string;
  description?: string;
  primaryCta?: { label: string; href: string };
  secondaryCta?: { label: string; href: string };
  slides: PublicSlide[];
  home?: boolean;
};

export default function PublicHeroWithSlides({
  eyebrow,
  titleLead,
  titleAccent,
  titleTail,
  title,
  description,
  primaryCta,
  secondaryCta,
  slides,
  home = false,
}: Props) {
  const safeSlides = useMemo(() => slides.filter((slide) => slide.src), [slides]);
  const [activeIndex, setActiveIndex] = useState(0);
  const totalSlides = safeSlides.length;

  useEffect(() => {
    if (totalSlides <= 1) return;
    const id = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % totalSlides);
    }, 5200);
    return () => window.clearInterval(id);
  }, [totalSlides]);

  const activeSlide = safeSlides[activeIndex] || safeSlides[0];
  const titleBlock = title ?? (
    <>
      {titleLead && <>{titleLead}{" "}</>}
      {titleAccent && (
        <span style={{ background: "var(--site-hero-accent-1)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          {titleAccent}
        </span>
      )}
      {titleLead || titleAccent ? <br /> : null}
      {titleTail && (
        <span style={{ background: "var(--site-hero-accent-2)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          {titleTail}
        </span>
      )}
    </>
  );

  if (home) {
    return (
      <section className="relative left-1/2 w-screen -translate-x-1/2 overflow-hidden" style={{ minHeight: "var(--ccf-hero-min-h)" }}>
        <AnimatePresence mode="wait">
          {activeSlide && (
            <motion.div
              key={activeSlide.src}
              initial={{ opacity: 0, scale: 1.02 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.6 }}
              className="absolute inset-0"
            >
              <OptimizedImage src={activeSlide.src} alt={activeSlide.alt} fill sizes="100vw" className="object-cover" priority={activeIndex === 0} />
            </motion.div>
          )}
        </AnimatePresence>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_20%,rgba(255,255,255,0.14),transparent_24%),linear-gradient(to_top,rgba(0,0,0,0.82)_0%,rgba(0,0,0,0.46)_50%,rgba(0,0,0,0.18)_100%)]" />
        <div className="absolute inset-0 z-10">
          <div className="flex h-full w-full items-end px-5 sm:px-8 md:px-12 lg:px-16 pb-16 md:pb-20">
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: "easeOut" }}
              className="max-w-5xl text-white"
            >
              {eyebrow && (
                <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.32em] mb-5 px-4 py-2 rounded-full border border-white/20 bg-white/10 backdrop-blur">
                  {eyebrow}
                </span>
              )}
              {titleBlock && (
                <h1 className={`font-bold ccf-display max-w-4xl ${home ? "text-5xl sm:text-6xl lg:text-7xl xl:text-8xl" : "text-4xl sm:text-5xl lg:text-6xl"}`}>
                  {titleBlock}
                </h1>
              )}
              {description && (
                <p className="ccf-body mt-5 text-base sm:text-lg max-w-2xl text-white/90">
                  {description}
                </p>
              )}
              {(primaryCta || secondaryCta) && (
                <div className="mt-8 flex flex-col sm:flex-row gap-4">
                  {primaryCta && (
                    <Link href={primaryCta.href} className="ccf-button group" style={{ background: "var(--site-hero-cta-gradient)", boxShadow: "var(--site-hero-cta-shadow)", color: "var(--site-on-hero)" }}>
                      {primaryCta.label}
                      <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                    </Link>
                  )}
                  {secondaryCta && (
                    <Link href={secondaryCta.href} className="ccf-button" style={{ background: "var(--site-hero-bg-light)", border: "2px solid var(--site-hero-border-light)", color: "var(--site-on-hero)", backdropFilter: "blur(10px)" }}>
                      <Play size={14} />
                      {secondaryCta.label}
                    </Link>
                  )}
                </div>
              )}
            </motion.div>
          </div>
        </div>
        <div className="absolute inset-x-0 top-0 z-20 flex items-center justify-between p-4 md:p-6 text-white/90">
          <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.35em] backdrop-blur">
            Home
          </span>
          {totalSlides > 1 && (
            <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.35em] backdrop-blur">
              {String(activeIndex + 1).padStart(2, "0")} / {String(totalSlides).padStart(2, "0")}
            </span>
          )}
        </div>
        {totalSlides > 1 && (
          <div className="absolute bottom-4 right-4 z-20 flex gap-2">
            {safeSlides.slice(0, 6).map((slide, index) => (
              <button
                key={slide.src}
                type="button"
                onClick={() => setActiveIndex(index)}
                aria-label={`Ir al slide ${index + 1}`}
                className={`h-2.5 rounded-full transition-all duration-300 ${index === activeIndex ? "w-8 bg-white" : "w-2.5 bg-white/40 hover:bg-white/70"}`}
              />
            ))}
          </div>
        )}
      </section>
    );
  }

  return (
    <section className="ccf-section">
      <div className="ccf-container grid gap-10 lg:grid-cols-[1fr_1.08fr] lg:items-center lg:gap-16">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="order-1 max-w-3xl lg:py-8"
        >
          {eyebrow && (
            <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.32em] mb-5 px-4 py-2 rounded-full border" style={{ color: "var(--site-primary)", borderColor: "var(--site-primary-container)", background: "var(--site-surface-container-low)" }}>
              {eyebrow}
            </span>
          )}
          {titleBlock && (
            <h1 className="font-bold ccf-display text-4xl sm:text-5xl lg:text-6xl" style={{ color: "var(--site-on-background)" }}>
              {titleBlock}
            </h1>
          )}
          {description && (
            <p className="ccf-body mt-5 text-base sm:text-lg max-w-2xl" style={{ color: "var(--site-on-surface-variant)" }}>
              {description}
            </p>
          )}
          {(primaryCta || secondaryCta) && (
            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              {primaryCta && (
                <Link href={primaryCta.href} className="ccf-button group" style={{ background: "var(--site-hero-cta-gradient)", boxShadow: "var(--site-hero-cta-shadow)", color: "var(--site-on-hero)" }}>
                  {primaryCta.label}
                  <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                </Link>
              )}
              {secondaryCta && (
                <Link href={secondaryCta.href} className="ccf-button" style={{ background: "var(--site-hero-bg-light)", border: "2px solid var(--site-hero-border-light)", color: "var(--site-on-hero)", backdropFilter: "blur(10px)" }}>
                  <Play size={14} />
                  {secondaryCta.label}
                </Link>
              )}
            </div>
          )}
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: "easeOut", delay: 0.08 }}
          className="order-2 relative"
        >
          <div className="relative overflow-hidden rounded-[2rem] shadow-2xl min-h-[28rem] lg:min-h-[38rem]">
            <AnimatePresence mode="wait">
              {activeSlide && (
                <motion.div
                  key={activeSlide.src}
                  initial={{ opacity: 0, scale: 1.02 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.6 }}
                  className="absolute inset-0"
                >
                  <OptimizedImage src={activeSlide.src} alt={activeSlide.alt} fill sizes="(max-width: 1024px) 100vw, 45vw" className="object-cover" priority={activeIndex === 0} />
                </motion.div>
              )}
            </AnimatePresence>
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_20%,rgba(255,255,255,0.2),transparent_30%),linear-gradient(to_top,rgba(0,0,0,0.9)_0%,rgba(0,0,0,0.42)_45%,transparent_100%)]" />
            <div className="absolute inset-x-0 top-0 flex items-center justify-between p-4 md:p-6 text-white/90">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.35em] backdrop-blur">
                Banner
              </span>
              {totalSlides > 1 && (
                <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.35em] backdrop-blur">
                  {String(activeIndex + 1).padStart(2, "0")} / {String(totalSlides).padStart(2, "0")}
                </span>
              )}
            </div>
            <div className="absolute inset-x-0 bottom-0 p-5 md:p-8 text-white">
              {activeSlide?.title && <h2 className="text-xl md:text-3xl font-black mb-2 leading-tight max-w-xl">{activeSlide.title}</h2>}
              {activeSlide?.caption && <p className="text-sm md:text-base text-white/86 max-w-2xl leading-relaxed">{activeSlide.caption}</p>}
            </div>
          </div>
          {totalSlides > 1 && (
            <div className="mt-4 grid grid-cols-3 gap-3 sm:grid-cols-4">
              {safeSlides.slice(0, 4).map((slide, index) => (
                <button
                  key={slide.src}
                  type="button"
                  onClick={() => setActiveIndex(index)}
                  className={`relative aspect-[4/3] overflow-hidden rounded-2xl border transition-all duration-300 ${index === activeIndex ? "border-[hsl(var(--primary))] ring-2 ring-[hsl(var(--primary))/0.18] scale-[1.03] opacity-100" : "border-[hsl(var(--border))] opacity-70 hover:opacity-95"}`}
                >
                  <OptimizedImage src={slide.src} alt={slide.alt} fill sizes="(max-width: 768px) 33vw, 14vw" className="object-cover" />
                </button>
              ))}
              {totalSlides > 4 && (
                <div className="flex items-center justify-center rounded-2xl border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[10px] font-bold uppercase tracking-[0.3em] text-[hsl(var(--text-secondary))]">
                  +{totalSlides - 4}
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>
    </section>
  );
}
