"use client";

import { usePathname } from "next/navigation";
import SeoHead from "./SeoHead";

const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

const ROUTE_META_MAP: Record<string, { slug: string; fallbackTitle: string; fallbackDescription: string }> = {
    "/":                  { slug: "home",      fallbackTitle: `${SITE_NAME} | Inicio`,           fallbackDescription: "Una comunidad de fe viva y en crecimiento que existe para conectar corazones con Dios y entre sí." },
    "/nosotros":          { slug: "nosotros",  fallbackTitle: `${SITE_NAME} | Quiénes Somos`,    fallbackDescription: "Conoce la historia, visión, misión y valores de la comunidad." },
    "/pastores":          { slug: "pastores",  fallbackTitle: `${SITE_NAME} | Liderazgo Pastoral`, fallbackDescription: "Conoce a los pastores y líderes que guían la comunidad." },
    "/conocer-a-jesus":   { slug: "conocer",   fallbackTitle: `${SITE_NAME} | Conocer a Jesús`,  fallbackDescription: "El comienzo de una relación que transforma la oscuridad en un propósito eterno." },
    "/eventos":           { slug: "eventos",   fallbackTitle: `${SITE_NAME} | Eventos`,         fallbackDescription: "Calendario de eventos comunitarios, conferencias y cursos." },
    "/predicas":          { slug: "predicas",  fallbackTitle: `${SITE_NAME} | Prédicas`,        fallbackDescription: "Alimento para el alma. Prédicas y mensajes que iluminan el camino." },
    "/cursos":            { slug: "cursos",    fallbackTitle: `${SITE_NAME} | Cursos y Librería`, fallbackDescription: "Academia de cursos especializados y selección literaria." },
    "/sedes":             { slug: "sedes",     fallbackTitle: `${SITE_NAME} | Nuestras Sedes`,  fallbackDescription: "Encuéntranos en Barranquilla. Horarios y direcciones." },
    "/boletin":           { slug: "boletin",   fallbackTitle: `${SITE_NAME} | Boletín Semanal`, fallbackDescription: "Recibe cada semana una reflexión bíblica y consejos prácticos." },
    "/testimonios":       { slug: "testimonios", fallbackTitle: `${SITE_NAME} | Testimonios`,   fallbackDescription: "Historias reales de transformación en nuestra comunidad." },
    "/privacidad":        { slug: "privacidad", fallbackTitle: `${SITE_NAME} | Política de Privacidad`, fallbackDescription: "Conoce cómo protegemos tus datos personales." },
};

function matchRoute(pathname: string): { slug: string; fallbackTitle: string; fallbackDescription: string } | null {
    if (ROUTE_META_MAP[pathname]) return ROUTE_META_MAP[pathname];
    if (pathname.startsWith("/pastores/")) return { slug: "pastores", fallbackTitle: `${SITE_NAME} | Pastor`, fallbackDescription: "Conoce a este pastor de la comunidad." };
    if (pathname.startsWith("/cursos/")) return { slug: "cursos", fallbackTitle: `${SITE_NAME} | Curso`, fallbackDescription: "Detalles del curso." };
    if (pathname.startsWith("/testimonios/")) return { slug: "testimonios", fallbackTitle: `${SITE_NAME} | Testimonio`, fallbackDescription: "Testimonio de transformación." };
    return null;
}

export default function PublicSeoManager() {
    const pathname = usePathname() || "/";
    const match = matchRoute(pathname);

    if (!match) return null;

    return (
        <SeoHead
            slug={match.slug}
            fallbackTitle={match.fallbackTitle}
            fallbackDescription={match.fallbackDescription}
        />
    );
}
