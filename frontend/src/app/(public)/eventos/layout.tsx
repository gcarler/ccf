import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Eventos y Calendario | ${siteName}`,
    description: "Nuestra agenda comunitaria. Espacios diseñados para el crecimiento, la conexión y la guía espiritual.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
