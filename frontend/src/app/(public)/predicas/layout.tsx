import { Metadata } from "next";
import { SITE_URL } from "@/lib/site-config";

const siteName = "Comunidad Cristiana El Faro (CCF)";
const siteUrl = SITE_URL || "https://ministerioselfaro.org";

export const metadata: Metadata = {
  title: `Prédicas y Mensajes | ${siteName}`,
  description:
    "Encuentra enseñanzas semanales diseñadas para iluminar tu fe y aplicarlas en tu vida diaria. Prédicas de los pastores de Comunidad Cristiana El Faro en video de alta calidad.",
  openGraph: {
    title: `Prédicas y Mensajes | ${siteName}`,
    description:
      "Mensajes bíblicos que transforman vidas y familias. Escucha la palabra de Dios compartida por nuestros pastores.",
    url: `${siteUrl}/predicas`,
    siteName,
    images: [
      {
        url: "/images/locations/sede-central.jpg",
        width: 1200,
        height: 630,
        alt: "Prédicas y Mensajes - Comunidad Cristiana El Faro",
      },
    ],
    locale: "es_CO",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: `Prédicas y Mensajes | ${siteName}`,
    description:
      "Encuentra enseñanzas semanales diseñadas para iluminar tu fe y aplicarlas en tu vida diaria.",
    images: ["/images/locations/sede-central.jpg"],
  },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
