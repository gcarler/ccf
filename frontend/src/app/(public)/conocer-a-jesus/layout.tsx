import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Conocer a Jesús | ${siteName}`,
    description: "Inicia tu camino. Conocer a Jesús no es una religión, es el comienzo de una relación que transforma la oscuridad en un propósito eterno.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
