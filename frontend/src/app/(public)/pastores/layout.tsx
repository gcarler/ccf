import { Metadata } from "next";
import { SITE_URL } from "@/lib/site-config";

const siteName = "Comunidad Cristiana El Faro (CCF)";
const siteUrl = SITE_URL || "https://ministerioselfaro.org";

export const metadata: Metadata = {
  title: `Equipo Pastoral y Liderazgo | ${siteName}`,
  description:
    "Conoce a los pastores y líderes de Comunidad Cristiana El Faro. Un equipo con vocación de servicio, sabiduría bíblica y amor por Dios y las familias.",
  openGraph: {
    title: `Equipo Pastoral y Liderazgo | ${siteName}`,
    description:
      "Conoce a los pastores y líderes de Comunidad Cristiana El Faro. Un equipo con vocación de servicio y amor por Dios y las personas.",
    url: `${siteUrl}/pastores`,
    siteName,
    images: [
      {
        url: "/images/locations/sede-central.jpg",
        width: 1200,
        height: 630,
        alt: "Equipo Pastoral y Liderazgo - Comunidad Cristiana El Faro",
      },
    ],
    locale: "es_CO",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: `Equipo Pastoral y Liderazgo | ${siteName}`,
    description:
      "Conoce a los pastores y líderes de Comunidad Cristiana El Faro. Un equipo con vocación de servicio y amor por las personas.",
    images: ["/images/locations/sede-central.jpg"],
  },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
