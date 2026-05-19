import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Suscripción al Boletín | FARO",
    description: "Únete a nuestro boletín y recibe meditaciones y noticias semanales.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
