import { Metadata } from "next";

export const metadata: Metadata = {
    title: "Nuestro Equipo Pastoral | FARO",
    description: "Conoce a los apóstoles y pastores que guían nuestra congregación.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
