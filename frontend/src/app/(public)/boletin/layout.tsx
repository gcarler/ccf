import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Suscripción al Boletín | ${siteName}`,
    description: "Únete a nuestro boletín y recibe meditaciones y noticias semanales.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
