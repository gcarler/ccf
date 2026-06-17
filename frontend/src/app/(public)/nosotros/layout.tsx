import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Quiénes Somos | ${siteName}`,
    description: "Conoce nuestra historia, visión, misión y los valores que nos guían — una comunidad de fe abierta para toda la familia.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
