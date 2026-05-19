import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Nuestras Sedes | FARO",
    description: "Nuestra presencia. Encuentra la sede de FARO más cercana a ti.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
