import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Equipo Pastoral y Liderazgo | Comunidad Cristiana El Faro (CCF)",
  description:
    "Conoce a los pastores y líderes de Comunidad Cristiana El Faro. Un equipo con vocación de servicio, sabiduría bíblica y amor por Dios y las familias.",
  openGraph: {
    title: "Equipo Pastoral y Liderazgo | Comunidad Cristiana El Faro (CCF)",
    description:
      "Conoce a los pastores y líderes de Comunidad Cristiana El Faro. Un equipo con vocación de servicio y amor por Dios y las personas.",
    url: "https://ccf.org/pastores",
    siteName: "Comunidad Cristiana El Faro (CCF)",
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
    title: "Equipo Pastoral y Liderazgo | Comunidad Cristiana El Faro (CCF)",
    description:
      "Conoce a los pastores y líderes de Comunidad Cristiana El Faro. Un equipo con vocación de servicio y amor por las personas.",
    images: ["/images/locations/sede-central.jpg"],
  },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
