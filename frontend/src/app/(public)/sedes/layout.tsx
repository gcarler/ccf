import { Metadata } from "next";
import { SITE_URL } from "@/lib/site-config";

const siteName = "Comunidad Cristiana El Faro (CCF)";
const siteUrl = SITE_URL || "https://ministerioselfaro.org";

export const metadata: Metadata = {
  title: `Nuestras Sedes | ${siteName}`,
  description:
    "Encuentra la sede de Comunidad Cristiana El Faro más cercana a ti. Horarios de cultos, grupos de hogar, FaroKids y atención pastoral en Barranquilla, Cartagena, Soledad y transmisión online.",
  openGraph: {
    title: `Nuestras Sedes | ${siteName}`,
    description:
      "Conoce nuestras sedes y puntos de reunión. Adora a Dios con nosotros y encuentra una familia de fe.",
    url: `${siteUrl}/sedes`,
    siteName,
    images: [
      {
        url: "/images/locations/sede-central.jpg",
        width: 1200,
        height: 630,
        alt: "Sedes de Comunidad Cristiana El Faro",
      },
    ],
    locale: "es_CO",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: `Nuestras Sedes | ${siteName}`,
    description:
      "Encuentra la sede de Comunidad Cristiana El Faro más cercana a ti. Horarios de cultos y atención pastoral.",
    images: ["/images/locations/sede-central.jpg"],
  },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
