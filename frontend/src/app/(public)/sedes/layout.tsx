import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Nuestras Sedes | ${siteName}`,
    description: "Nuestra presencia. Encuentra la sede más cercana a ti.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
