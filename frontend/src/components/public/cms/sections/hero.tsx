"use client";

import { CmsSection } from "@/types/cms-v2";
import type { HeroProps, VideoHeroProps } from "@/types/cms-section-props";
import Link from "next/link";
import PublicHeroWithSlides, { type PublicSlide } from "@/components/public/PublicHeroWithSlides";
import { normalizeHeroProps } from "@/lib/cms/heroPopup";
import { asProps, val } from "./shared";

export function HeroSection({ section }: { section: CmsSection<"hero"> }) {
  const props: HeroProps = section.props_json ?? {};
  const hero = normalizeHeroProps(asProps(props));

  return (
    <PublicHeroWithSlides
      eyebrow={hero.eyebrow}
      title={hero.title}
      titleLead={hero.titleLead}
      titleAccent={hero.titleAccent}
      titleTail={hero.titleTail}
      description={hero.description}
      primaryCta={hero.primaryCta}
      secondaryCta={hero.secondaryCta}
      slides={hero.slides as PublicSlide[]}
    />
  );
}

// ─── Video Hero ────────────────────────────────────────────────────────────────

export function VideoHeroSection({ section }: { section: CmsSection<"video_hero"> }) {
  const props: VideoHeroProps = section.props_json ?? {};
  const p = asProps(props);
  const title = val(p, "title", "");
  const body = val(p, "body", "");
  const ctaLabel = val(p, "cta_label", "");
  const ctaHref = val(p, "cta_href", "/");
  const videoUrl = val(p, "video_url", "");
  const fullBleed = Boolean(p.full_bleed);

  return (
    <section className={`ccf-video-hero relative overflow-hidden ${fullBleed ? "left-1/2 w-screen -translate-x-1/2 rounded-none" : "rounded-2xl"} min-h-[clamp(420px,72vh,760px)] flex items-center`}>
      {videoUrl && (
        <video autoPlay loop muted playsInline className="absolute inset-0 w-full h-full object-cover">
          <source src={videoUrl} type="video/mp4" />
        </video>
      )}
      <div className="absolute inset-0" style={{ background: "linear-gradient(to right, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.3) 100%)" }} />
      <div className="relative z-10 p-8 md:p-12 lg:p-16 max-w-3xl">
        <h1 className="text-3xl md:text-5xl font-black tracking-tight text-white leading-tight">
          {title}
        </h1>
        {body && <p className="mt-5 text-base md:text-xl text-white/85 max-w-xl leading-relaxed">{body}</p>}
        {ctaLabel && (
          <Link
            href={ctaHref}
            className="inline-flex mt-8 items-center gap-2 rounded-full px-6 py-3 text-sm font-bold uppercase tracking-widest text-white shadow-lg transition-transform hover:scale-105"
            style={{ background: "var(--site-cta-gradient)" }}
          >
            {ctaLabel}
          </Link>
        )}
      </div>
    </section>
  );
}

// ─── Rich Text ─────────────────────────────────────────────────────────────────
