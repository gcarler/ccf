"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { SITE_KEY } from "@/lib/site-config";
import SeoHead from "./SeoHead";

const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

const ROUTE_META_MAP: Record<string, { slug: string; fallbackTitle: string; fallbackDescription: string }> = {
    "/":                  { slug: "home",      fallbackTitle: `${SITE_NAME} | Inicio`,           fallbackDescription: "Una comunidad de fe viva y en crecimiento que existe para conectar corazones con Dios y entre sí." },
    "/nosotros":          { slug: "about",     fallbackTitle: `${SITE_NAME} | Quiénes Somos`,    fallbackDescription: "Conoce la historia, visión, misión y valores de la comunidad." },
    "/pastores":          { slug: "pastors",   fallbackTitle: `${SITE_NAME} | Liderazgo Pastoral`, fallbackDescription: "Conoce a los pastores y líderes que guían la comunidad." },
    "/conocer-a-jesus":   { slug: "discover",  fallbackTitle: `${SITE_NAME} | Conocer a Jesús`,  fallbackDescription: "El comienzo de una relación que transforma la oscuridad en un propósito eterno." },
    "/eventos":           { slug: "events",    fallbackTitle: `${SITE_NAME} | Eventos`,         fallbackDescription: "Calendario de eventos comunitarios, conferencias y cursos." },
    "/predicas":          { slug: "sermons",   fallbackTitle: `${SITE_NAME} | Prédicas`,        fallbackDescription: "Alimento para el alma. Prédicas y mensajes que iluminan el camino." },
    "/cursos":            { slug: "courses",   fallbackTitle: `${SITE_NAME} | Cursos y Librería`, fallbackDescription: "Academia de cursos especializados y selección literaria." },
    "/sedes":             { slug: "locations", fallbackTitle: `${SITE_NAME} | Nuestras Sedes`,  fallbackDescription: "Encuéntranos en Barranquilla. Horarios y direcciones." },
    "/boletin":           { slug: "newsletter", fallbackTitle: `${SITE_NAME} | Boletín Semanal`, fallbackDescription: "Recibe cada semana una reflexión bíblica y consejos prácticos." },
    "/testimonios":       { slug: "testimonials", fallbackTitle: `${SITE_NAME} | Testimonios`,   fallbackDescription: "Historias reales de transformación en nuestra comunidad." },
    "/privacidad":        { slug: "privacy",    fallbackTitle: `${SITE_NAME} | Política de Privacidad`, fallbackDescription: "Conoce cómo protegemos tus datos personales." },
};

function matchRoute(pathname: string): { slug: string; fallbackTitle: string; fallbackDescription: string } | null {
    if (ROUTE_META_MAP[pathname]) return ROUTE_META_MAP[pathname];
    if (pathname.startsWith("/pastores/")) return { slug: "pastores", fallbackTitle: `${SITE_NAME} | Pastor`, fallbackDescription: "Conoce a este pastor de la comunidad." };
    if (pathname.startsWith("/cursos/")) return { slug: "cursos", fallbackTitle: `${SITE_NAME} | Curso`, fallbackDescription: "Detalles del curso." };
    if (pathname.startsWith("/testimonios/")) return { slug: "testimonios", fallbackTitle: `${SITE_NAME} | Testimonio`, fallbackDescription: "Testimonio de transformación." };
    return null;
}

interface CmsSeoData {
    title?: string;
    description?: string;
    robots_meta?: string;
    canonical_url?: string;
    json_ld?: Record<string, unknown> | null;
    breadcrumb_json_ld?: Record<string, unknown> | null;
}

export default function PublicSeoManager() {
    const pathname = usePathname() || "/";
    const match = matchRoute(pathname);
    const [cmsSeo, setCmsSeo] = useState<CmsSeoData | null>(null);

    useEffect(() => {
        if (!match) return;

        const controller = new AbortController();
        const url = `${API_BASE}/api/cms/v2/public/sites/${SITE_KEY}/pages/${match.slug}`;

        fetch(url, { signal: controller.signal })
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (!data) return;
                const seo = data.seo_json && typeof data.seo_json === "object" ? data.seo_json : {};
                setCmsSeo({
                    title: typeof seo.meta_title === "string" ? seo.meta_title : undefined,
                    description: typeof seo.meta_description === "string" ? seo.meta_description : undefined,
                    robots_meta: typeof seo.robots_meta === "string" ? seo.robots_meta : undefined,
                    canonical_url: data.canonical_url ?? undefined,
                    json_ld: data.json_ld ?? null,
                    breadcrumb_json_ld: data.breadcrumb_json_ld ?? null,
                });
            })
            .catch(() => {});

        return () => controller.abort();
    }, [match?.slug]);

    if (!match) return null;

    const fallbackTitle = cmsSeo?.title || match.fallbackTitle;
    const fallbackDescription = cmsSeo?.description || match.fallbackDescription;

    return (
        <SeoHead
            slug={match.slug}
            fallbackTitle={fallbackTitle}
            fallbackDescription={fallbackDescription}
            robotsMeta={cmsSeo?.robots_meta}
            canonicalUrl={cmsSeo?.canonical_url}
            jsonLd={cmsSeo?.json_ld}
        />
    );
}
