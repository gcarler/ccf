"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  ChevronRight,
  Sparkles,
  Instagram,
  Facebook,
  Twitter,
  Search,
  X,
  User,
  SlidersHorizontal,
  Info,
} from "lucide-react";
import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import PublicHeroWithSlides from "@/components/public/PublicHeroWithSlides";
import PastorDetailDrawer, { PastorItem } from "@/components/public/PastorDetailDrawer";
import { getPublicPastoralTeam, type PastoralProfile } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";
import { safeJsonParse } from "@/lib/safeJson";

function plainText(value: string | undefined): string {
  return (value || "")
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function formatSocialUrl(
  url: string | undefined | null,
  platform: "instagram" | "facebook" | "twitter"
): string | null {
  if (!url || !url.trim()) return null;
  const clean = url.trim();
  const isHandle = clean.startsWith("@") || (!clean.includes("/") && !clean.includes("."));
  if (isHandle) {
    const handle = clean.startsWith("@") ? clean.substring(1) : clean;
    if (platform === "instagram") return `https://instagram.com/${handle}`;
    if (platform === "facebook") return `https://facebook.com/${handle}`;
    if (platform === "twitter") return `https://x.com/${handle}`;
  }
  if (!/^https?:\/\//i.test(clean)) {
    return `https://${clean}`;
  }
  return clean;
}

export default function PastoresIndexPage() {
  const page = useCmsV2Page("pastors");
  const heroCms = page?.blocks?.hero;
  const feedCms = page?.blocks?.feed;

  const heroContent = safeJsonParse<Record<string, unknown>>(heroCms?.content, {});
  const feedContent = safeJsonParse<Record<string, unknown>>(feedCms?.content, {});

  // Fetch pastors from the pastoral-team API (source of truth)
  const [apiPastors, setApiPastors] = useState<PastoralProfile[]>([]);
  const [apiLoading, setApiLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedRole, setSelectedRole] = useState("Todos");
  const [drawerPastor, setDrawerPastor] = useState<PastorItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  useEffect(() => {
    getPublicPastoralTeam(SITE_KEY)
      .then((data) => setApiPastors(Array.isArray(data) ? data : []))
      .catch(() => setApiPastors([]))
      .finally(() => setApiLoading(false));
  }, []);

  const pastors: PastorItem[] = useMemo(() => {
    // Use API data as source of truth; fall back to CMS block if API empty
    if (apiPastors.length > 0) {
      return apiPastors.map((p) => ({
        id: p.id,
        slug: p.slug,
        name: p.name,
        role: p.role ?? "Pastor",
        photo_url: p.photo_url ?? undefined,
        image: p.photo_url ?? undefined,
        bio_short: p.bio_short ?? undefined,
        bio_full: p.bio_full ?? undefined,
        story: p.bio_short ?? undefined,
        social_instagram: p.social_instagram ?? undefined,
        social_facebook: p.social_facebook ?? undefined,
        social_twitter: p.social_twitter ?? undefined,
        is_main_pastor: p.is_main_pastor,
        isMain: p.is_main_pastor,
      }));
    }

    // Fallback: read from CMS content block
    const pastorsCms = page?.blocks?.pastors;
    const rawList = pastorsCms as unknown as {
      pastors?: PastorItem[];
      items?: PastorItem[];
      parsed?: { items?: PastorItem[]; pastors?: PastorItem[] };
    } | null;
    const list =
      rawList?.items ||
      rawList?.pastors ||
      rawList?.parsed?.items ||
      rawList?.parsed?.pastors ||
      [];
    return Array.isArray(list) ? list : [];
  }, [apiPastors, page]);

  // Extract unique roles for dynamic filter chips
  const rolesList = useMemo(() => {
    const set = new Set<string>();
    pastors.forEach((p) => {
      if (p.role) {
        set.add(p.role.trim());
      }
    });
    return ["Todos", ...Array.from(set)];
  }, [pastors]);

  // Filtered pastors by search and role
  const filteredPastors = useMemo(() => {
    const q = search.trim().toLowerCase();
    return pastors.filter((pastor) => {
      // Role filter
      if (selectedRole !== "Todos") {
        const pastorRole = (pastor.role || "").toLowerCase();
        if (pastorRole !== selectedRole.toLowerCase()) return false;
      }

      // Search query
      if (!q) return true;
      const name = pastor.name.toLowerCase();
      const role = (pastor.role || "").toLowerCase();
      const bio = plainText(pastor.bio_short || pastor.story || "").toLowerCase();
      return name.includes(q) || role.includes(q) || bio.includes(q);
    });
  }, [pastors, search, selectedRole]);

  const heroBadge =
    typeof feedContent?.hero_badge === "string" ? feedContent.hero_badge : "Liderazgo y Servicio";
  const heroTitle =
    typeof heroContent?.title === "string" ? heroContent.title : "Equipo Pastoral";
  const heroDescription =
    typeof heroContent?.description === "string"
      ? heroContent.description
      : "Conoce a los hombres y mujeres que Dios ha puesto para pastorear, guiar y servir con amor y dedicación a nuestra congregación.";
  const heroBgImage = heroContent?.bg_image ?? null;
  const loadingLabel =
    typeof feedContent?.loading_label === "string" ? feedContent.loading_label : "Cargando equipo...";
  const emptyTitle =
    typeof feedContent?.empty_title === "string"
      ? feedContent.empty_title
      : "No se encontraron miembros del equipo pastoral con ese criterio.";
  const cardCta =
    typeof feedContent?.card_cta === "string" ? feedContent.card_cta : "Conocer";
  const principalLabel =
    typeof feedContent?.principal_label === "string" ? feedContent.principal_label : "Principal";

  const hasHero = Boolean(heroTitle || heroDescription || heroBadge);

  const handleOpenDrawer = (e: React.MouseEvent, pastor: PastorItem) => {
    e.preventDefault();
    e.stopPropagation();
    setDrawerPastor(pastor);
    setIsDrawerOpen(true);
  };

  return (
    <main
      className="min-h-screen pt-24 pb-16 bg-site-surface text-site-on-surface"
      style={{
        background: "var(--site-surface, #fcfcfd)",
        color: "var(--site-on-surface, #1e1f21)",
      }}
    >
      {/* ── Hero Section ── */}
      {hasHero && (
        <PublicHeroWithSlides
          eyebrow={heroBadge}
          title={heroTitle}
          description={heroDescription}
          slides={
            heroBgImage ? [{ src: String(heroBgImage), alt: heroTitle || "Hero pastoral" }] : []
          }
        />
      )}

      {/* ── Filtros y Buscador Reactivo ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 xl:px-12 pt-8 pb-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 rounded-3xl border border-site-outline-variant/15 bg-site-surface-container-lowest shadow-xs">
          {/* Buscador */}
          <div className="relative flex-1 max-w-md">
            <Search
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2 text-site-outline pointer-events-none opacity-60"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nombre, rol o ministerio..."
              className="w-full rounded-xl pl-10 pr-9 py-2.5 text-xs sm:text-sm text-site-on-surface placeholder:text-site-outline outline-none focus:ring-2 focus:ring-site-primary/40 transition-all border border-site-outline-variant/20 bg-site-surface-container"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-site-outline hover:text-site-on-surface transition-colors"
              >
                <X size={15} />
              </button>
            )}
          </div>

          {/* Contador de Pastores */}
          <div className="text-xs font-bold text-site-on-surface-variant flex items-center gap-1.5 shrink-0">
            <User size={14} style={{ color: "var(--site-primary, #2563eb)" }} />
            <span>
              {filteredPastors.length} pastor{filteredPastors.length !== 1 ? "es" : ""} encontrado
              {filteredPastors.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>

        {/* Chips de Filtro por Rol Pastoral */}
        {rolesList.length > 1 && (
          <div className="mt-4 flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            <span className="text-3xs font-extrabold uppercase tracking-wider text-site-on-surface-variant opacity-70 mr-1 flex items-center gap-1 shrink-0">
              <SlidersHorizontal size={11} /> Roles:
            </span>
            {rolesList.map((role) => {
              const isActive = selectedRole === role;
              return (
                <button
                  key={role}
                  type="button"
                  onClick={() => setSelectedRole(role)}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold tracking-tight whitespace-nowrap transition-all border ${
                    isActive
                      ? "border-site-primary text-white shadow-2xs scale-102"
                      : "border-site-outline-variant/20 bg-site-surface-container text-site-on-surface-variant hover:bg-site-surface-container-high"
                  }`}
                  style={{
                    background: isActive ? "var(--site-primary, #2563eb)" : undefined,
                    color: isActive ? "#ffffff" : undefined,
                  }}
                >
                  {role}
                </button>
              );
            })}
          </div>
        )}
      </section>

      {/* ── Pastors Grid ── */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8 xl:px-12 py-6">
        {apiLoading && !pastors.length ? (
          <div className="flex items-center justify-center py-20">
            <div
              className="w-9 h-9 rounded-full border-3 border-t-transparent animate-spin"
              style={{ borderColor: "var(--site-primary, #2563eb)", borderTopColor: "transparent" }}
            />
            <span className="sr-only">{loadingLabel}</span>
          </div>
        ) : filteredPastors.length === 0 ? (
          <div className="text-center py-16 border border-dashed border-site-outline-variant/20 rounded-3xl p-8 max-w-md mx-auto bg-site-surface-container/30">
            <User size={40} className="mx-auto mb-3 opacity-30 text-site-primary" />
            <p className="text-sm font-semibold text-site-on-surface mb-2">{emptyTitle}</p>
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setSelectedRole("Todos");
              }}
              className="text-xs font-bold text-site-primary hover:underline"
            >
              Restablecer filtros
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 md:gap-7">
            {filteredPastors.map((pastor, idx) => {
              const igUrl = formatSocialUrl(pastor.social_instagram, "instagram");
              const fbUrl = formatSocialUrl(pastor.social_facebook, "facebook");
              const twUrl = formatSocialUrl(pastor.social_twitter, "twitter");
              const hasSocial = Boolean(igUrl || fbUrl || twUrl);
              const isMain = Boolean(pastor.is_main_pastor || pastor.isMain);

              return (
                <div
                  key={pastor.id || pastor.slug}
                  onClick={(e) => handleOpenDrawer(e, pastor)}
                  className="group relative rounded-2xl overflow-hidden border border-site-outline-variant/20 shadow-sm hover:shadow-xl hover:border-site-primary/40 hover:-translate-y-1 transition-all duration-300 flex flex-col cursor-pointer bg-site-surface-container-low"
                  style={{ animationDelay: `${idx * 80}ms` }}
                >
                  {/* Photo Header */}
                  <div className="relative h-60 w-full bg-site-surface-container overflow-hidden block">
                    <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 bg-gradient-to-br from-site-primary/10 to-transparent pointer-events-none z-10" />

                    {pastor.photo_url || pastor.image ? (
                      <Image
                        src={pastor.photo_url || pastor.image || ""}
                        alt={pastor.name}
                        fill
                        className="object-cover object-top transition-transform duration-700 group-hover:scale-105"
                        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 25vw"
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-site-primary/10 to-site-secondary/5">
                        <span className="text-4xl font-bold opacity-30 text-site-primary">
                          {pastor.name.charAt(0)}
                        </span>
                      </div>
                    )}

                    <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-transparent" />

                    {/* Principal Badge */}
                    {isMain && principalLabel && (
                      <div className="absolute top-3 left-3 z-20">
                        <span
                          className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-white text-3xs font-extrabold uppercase tracking-wider shadow-md"
                          style={{ background: "var(--site-cta-gradient, #2563eb)" }}
                        >
                          <Sparkles size={9} /> {principalLabel}
                        </span>
                      </div>
                    )}

                    {/* Quick Drawer Hint */}
                    <div className="absolute top-3 right-3 z-20 opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-black/60 text-white text-3xs font-bold backdrop-blur-md">
                        <Info size={10} /> Ver detalles
                      </span>
                    </div>

                    {/* Name & Role overlay */}
                    <div className="absolute bottom-3 left-4 right-4 z-20">
                      <h3 className="text-base sm:text-lg font-bold text-white drop-shadow-sm truncate">
                        {pastor.name}
                      </h3>
                      <p
                        className="text-xs font-bold uppercase tracking-wider drop-shadow-sm truncate"
                        style={{ color: "var(--site-primary-light, #93c5fd)" }}
                      >
                        {pastor.role || "Pastor"}
                      </p>
                    </div>
                  </div>

                  {/* Body Content */}
                  <div className="p-4 flex-1 flex flex-col justify-between bg-site-surface-container-low">
                    <p className="text-xs text-site-on-surface-variant mb-4 flex-1 leading-relaxed line-clamp-3 opacity-90">
                      {plainText(pastor.bio_short || pastor.story)}
                    </p>

                    {/* Actions & Social */}
                    <div className="flex items-center justify-between pt-3 border-t border-site-outline-variant/15">
                      <div className="flex items-center gap-1.5">
                        {igUrl && (
                          <a
                            href={igUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="w-7 h-7 rounded-lg bg-site-surface-container border border-site-outline-variant/20 flex items-center justify-center text-site-on-surface-variant hover:text-site-primary hover:scale-110 transition-all shadow-2xs"
                            title="Instagram"
                            aria-label={`${pastor.name} en Instagram`}
                          >
                            <Instagram size={13} />
                          </a>
                        )}
                        {fbUrl && (
                          <a
                            href={fbUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="w-7 h-7 rounded-lg bg-site-surface-container border border-site-outline-variant/20 flex items-center justify-center text-site-on-surface-variant hover:text-site-primary hover:scale-110 transition-all shadow-2xs"
                            title="Facebook"
                            aria-label={`${pastor.name} en Facebook`}
                          >
                            <Facebook size={13} />
                          </a>
                        )}
                        {twUrl && (
                          <a
                            href={twUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="w-7 h-7 rounded-lg bg-site-surface-container border border-site-outline-variant/20 flex items-center justify-center text-site-on-surface-variant hover:text-site-primary hover:scale-110 transition-all shadow-2xs"
                            title="X (Twitter)"
                            aria-label={`${pastor.name} en X`}
                          >
                            <Twitter size={13} />
                          </a>
                        )}
                        <button
                          type="button"
                          onClick={(e) => handleOpenDrawer(e, pastor)}
                          className={`text-xs font-bold uppercase tracking-wider text-site-primary hover:underline ${
                            hasSocial ? "ml-1.5" : ""
                          }`}
                        >
                          {cardCta}
                        </button>
                      </div>

                      <button
                        type="button"
                        onClick={(e) => handleOpenDrawer(e, pastor)}
                        aria-label={`Abrir panel de ${pastor.name}`}
                        className="w-8 h-8 rounded-xl bg-site-primary/10 flex items-center justify-center text-site-primary group-hover:bg-site-primary group-hover:text-white transition-all shadow-2xs"
                      >
                        <ChevronRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ── DRAWER LATERAL DESLIZANTE AUTÓNOMO (REGLA MANDATORIA 0 MODALES) ── */}
      <PastorDetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        pastor={drawerPastor}
      />
    </main>
  );
}
