import type { Metadata } from "next";
import { PASTORS } from "@/data/pastors";

const BASE_URL = "https://elfarocc.tech";

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
    const pastor = PASTORS.find(p => p.id === params.slug);
    const name = pastor?.name ?? "Pastor";
    const title = pastor?.title ?? "Liderazgo Pastoral";
    const description = pastor?.shortStory ?? `Conoce al ${title} de la Comunidad Cristiana El Faro.`;
    const image = pastor?.image ? `${BASE_URL}${pastor.image}` : `${BASE_URL}/og-default.png`;

    return {
        title: `${name} | Comunidad Cristiana El Faro`,
        description,
        openGraph: {
            title: `${name} — ${title}`,
            description,
            url: `${BASE_URL}/pastores/${params.slug}`,
            siteName: "Comunidad Cristiana El Faro",
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
