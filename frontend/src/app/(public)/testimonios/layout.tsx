import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Testimonios | ${siteName}`,
    description: "Vidas transformadas por el poder de Dios. Conoce las historias de fe y esperanza de nuestra comunidad.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
