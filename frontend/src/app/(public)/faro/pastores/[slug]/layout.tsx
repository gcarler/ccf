import { Metadata } from "next";
import { getPastorBySlug } from "@/lib/data/pastors";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
    const { slug } = await params;
    const pastor = getPastorBySlug(slug);
    if (!pastor) return { title: "Pastor no encontrado | FARO" };

    return {
        title: `${pastor.name} - ${pastor.role} | FARO`,
        description: pastor.description,
    };
}

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
