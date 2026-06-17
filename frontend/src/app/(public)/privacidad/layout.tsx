import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Política de Privacidad | ${siteName}`,
    description: "Conoce cómo recopilamos, usamos y protegemos tus datos personales.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
