import { Metadata } from "next";
import { SITE_NAME, SITE_URL } from "@/lib/site-config";

const siteName = SITE_NAME ?? "Mi Comunidad";
const siteUrl = SITE_URL || "https://ministerioselfaro.org";

export const metadata: Metadata = {
    title: `Eventos y Calendario | ${siteName}`,
    description: "Nuestra agenda comunitaria. Espacios diseñados para el crecimiento, la conexión y la guía espiritual.",
    openGraph: {
        title: `Eventos y Calendario | ${siteName}`,
        description: "Nuestra agenda comunitaria. Espacios diseñados para el crecimiento, la conexión y la guía espiritual.",
        url: `${siteUrl}/eventos`,
        siteName,
        images: [
            {
                url: "/og-default.png",
                width: 1200,
                height: 630,
                alt: `Eventos de ${siteName}`,
            },
        ],
        locale: "es_CO",
        type: "website",
    },
    twitter: {
        card: "summary_large_image",
        title: `Eventos y Calendario | ${siteName}`,
        description: "Nuestra agenda comunitaria. Espacios diseñados para el crecimiento, la conexión y la guía espiritual.",
        images: ["/og-default.png"],
    },
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
