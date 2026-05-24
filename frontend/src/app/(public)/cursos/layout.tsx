import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Cursos y Academia | FARO",
    description: "Explora nuestra academia de cursos especializados y sumérgete en una selección literaria para iluminar tu entendimiento.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
