import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Prédicas y Mensajes | ${siteName}`,
    description: "Encuentra enseñanzas semanales diseñadas para iluminar tu fe y aplicarlas en tu vida diaria.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
