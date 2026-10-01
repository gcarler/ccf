import { Metadata } from "next";
import { SITE_NAME, SITE_URL } from "@/lib/site-config";

const siteName = SITE_NAME ?? "Mi Comunidad";
const siteUrl = SITE_URL || "https://ministerioselfaro.org";

export const metadata: Metadata = {
    title: `Testimonios | ${siteName}`,

    description: "Vidas transformadas por el poder de Dios. Conoce las historias de fe y esperanza de nuestra comunidad.",
    openGraph: {
        title: `Testimonios | ${siteName}`,
        description: "Vidas transformadas por el poder de Dios. Conoce las historias de fe y esperanza de nuestra comunidad.",
        url: `${siteUrl}/testimonios`,
        siteName,
        images: [
            {
                url: "/og-default.png",
                width: 1200,
                height: 630,
                alt: `Testimonios de ${siteName}`,
            },
        ],
        locale: "es_CO",
        type: "website",
    },
    twitter: {
        card: "summary_large_image",
        title: `Testimonios | ${siteName}`,
        description: "Vidas transformadas por el poder de Dios. Conoce las historias de fe y esperanza de nuestra comunidad.",
        images: ["/og-default.png"],
    },
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
