import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Prédicas y Mensajes | FARO",
    description: "Encuentra enseñanzas semanales diseñadas para iluminar tu fe y aplicarlas en tu vida diaria.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
