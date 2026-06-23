"use client";

import { usePathname } from "next/navigation";
import SeoHead from "./SeoHead";

const ROUTE_META_MAP: Record<string, { slug: string; fallbackTitle: string; fallbackDescription: string }> = {
    "/":                  { slug: "home",      fallbackTitle: "Comunidad Cristiana El Faro",       fallbackDescription: "Una comunidad de fe viva y en crecimiento que existe para conectar corazones con Dios y entre sí." },
    "/nosotros":          { slug: "nosotros",  fallbackTitle: "Quiénes Somos — CCF",              fallbackDescription: "Conoce la historia, visión, misión y valores de la Comunidad Cristiana El Faro." },
    "/pastores":          { slug: "pastores",  fallbackTitle: "Liderazgo Pastoral — CCF",         fallbackDescription: "Conoce a los pastores y líderes que guían la comunidad." },
    "/conocer-a-jesus":   { slug: "conocer",   fallbackTitle: "Conocer a Jesús — CCF",            fallbackDescription: "El comienzo de una relación que transforma la oscuridad en un propósito eterno." },
    "/eventos":           { slug: "eventos",   fallbackTitle: "Eventos — CCF",                    fallbackDescription: "Calendario de eventos comunitarios, conferencias y cursos." },
    "/predicas":          { slug: "predicas",  fallbackTitle: "Prédicas — CCF",                   fallbackDescription: "Alimento para el alma. Prédicas y mensajes que iluminan el camino." },
    "/cursos":            { slug: "cursos",    fallbackTitle: "Cursos y Librería — CCF",          fallbackDescription: "Academia de cursos especializados y selección literaria." },
    "/sedes":             { slug: "sedes",     fallbackTitle: "Nuestras Sedes — CCF",             fallbackDescription: "Encuéntranos en Barranquilla. Horarios y direcciones." },
    "/boletin":           { slug: "boletin",   fallbackTitle: "Boletín Semanal — CCF",            fallbackDescription: "Recibe cada semana una reflexión bíblica y consejos prácticos." },
    "/testimonios":       { slug: "testimonios", fallbackTitle: "Testimonios — CCF",              fallbackDescription: "Historias reales de transformación en nuestra comunidad." },
    "/privacidad":        { slug: "privacidad", fallbackTitle: "Política de Privacidad — CCF",    fallbackDescription: "Conoce cómo protegemos tus datos personales." },
};

function matchRoute(pathname: string): { slug: string; fallbackTitle: string; fallbackDescription: string } | null {
    if (ROUTE_META_MAP[pathname]) return ROUTE_META_MAP[pathname];
    if (pathname.startsWith("/pastores/")) return { slug: "pastores", fallbackTitle: "Pastor — CCF", fallbackDescription: "Conoce a este pastor de la comunidad." };
    if (pathname.startsWith("/cursos/")) return { slug: "cursos", fallbackTitle: "Curso — CCF", fallbackDescription: "Detalles del curso." };
    if (pathname.startsWith("/testimonios/")) return { slug: "testimonios", fallbackTitle: "Testimonio — CCF", fallbackDescription: "Testimonio de transformación." };
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
