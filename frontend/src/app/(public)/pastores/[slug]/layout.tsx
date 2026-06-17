import type { Metadata } from "next";
import { PASTORS } from "@/data/pastors";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
    const resolvedParams = await params;
    const pastor = PASTORS.find(p => p.id === resolvedParams.slug);
    const name = pastor?.name ?? "Pastor";
    const title = pastor?.title ?? "Liderazgo Pastoral";
    const description = pastor?.shortStory ?? `Conoce al ${title} de la ${process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad"}.`;
    const image = pastor?.image ? `${BASE_URL}${pastor.image}` : `${BASE_URL}/og-default.png`;

    return {
        title: `${name} | ${process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad"}`,
        description,
        openGraph: {
            title: `${name} — ${title}`,
            description,
            url: `${BASE_URL}/pastores/${resolvedParams.slug}`,
            siteName: process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad",
            images: [{ url: image, width: 400, height: 500, alt: name }],
            type: "profile",
            locale: "es_CO",
        },
        twitter: {
            card: "summary_large_image",
            title: `${name} — ${title}`,
            description,
            images: [image],
        },
    };
}

export default function PastorSlugLayout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
