import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Sobre Nosotros | FARO",
    description: "Nuestra identidad. Somos una comunidad vibrante dedicada a guiar a las personas hacia una vida llena de propósito y luz.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
