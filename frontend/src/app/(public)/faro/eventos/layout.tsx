import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Eventos y Calendario | FARO",
    description: "Nuestra agenda comunitaria. Espacios diseñados para el crecimiento, la conexión y la guía espiritual.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
