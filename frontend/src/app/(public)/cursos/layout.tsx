import { Metadata } from "next";

const siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `Cursos y Academia | ${siteName}`,
    description: "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria para iluminar tu entendimiento.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
