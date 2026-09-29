import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Nuestras Sedes | Comunidad Cristiana El Faro (CCF)",
  description:
    "Encuentra la sede de Comunidad Cristiana El Faro más cercana a ti. Horarios de cultos, grupos de hogar, FaroKids y atención pastoral en Barranquilla, Cartagena, Soledad y transmisión online.",
  openGraph: {
    title: "Nuestras Sedes | Comunidad Cristiana El Faro (CCF)",
    description:
      "Conoce nuestras sedes y puntos de reunión. Adora a Dios con nosotros y encuentra una familia de fe.",
    url: "https://ccf.org/sedes",
    siteName: "Comunidad Cristiana El Faro (CCF)",
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
    title: "Nuestras Sedes | Comunidad Cristiana El Faro (CCF)",
    description:
      "Encuentra la sede de Comunidad Cristiana El Faro más cercana a ti. Horarios de cultos y atención pastoral.",
    images: ["/images/locations/sede-central.jpg"],
  },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
