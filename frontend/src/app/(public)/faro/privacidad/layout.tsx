import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Política de Privacidad | FARO",
    description: "Conoce cómo protegemos tus datos y respetamos tu privacidad en la comunidad FARO.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
