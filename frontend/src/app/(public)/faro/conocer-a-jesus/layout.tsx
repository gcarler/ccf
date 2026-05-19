import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Conocer a Jesús | FARO",
    description: "Inicia tu camino. Conocer a Jesús no es una religión, es el comienzo de una relación que transforma la oscuridad en un propósito eterno.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
