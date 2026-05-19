import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Testimonios | FARO",
    description: "Vidas transformadas por el poder de Dios. Conoce las historias de fe y esperanza de nuestra comunidad.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
