import type { Metadata } from "next";
import { PASTORS } from "@/data/pastors";
import { apiFetch } from "@/lib/http";
import { SITE_KEY } from "@/lib/site-config";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "";

type CmsPastor = {
    slug: string;
    name: string;
    role?: string;
    image?: string;
    photo_url?: string;
    story?: string;
    bio_short?: string;
};

async function getPastorsFeed(): Promise<CmsPastor[]> {
    try {
        const block = await apiFetch<{ content?: string }>(`/cms/content/${SITE_KEY}_pastores_feed`, {
            cache: "no-store",
            silent: true,
        });
        const parsed = block.content ? JSON.parse(block.content) : null;
        return Array.isArray(parsed?.pastors) ? parsed.pastors : [];
    } catch {
        return [];
    }
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
    const resolvedParams = await params;
    const pastors = await getPastorsFeed();
    const pastor = pastors.find(p => p.slug === resolvedParams.slug);
    const localPastor = PASTORS.find(p => p.id === resolvedParams.slug);
    const name = pastor?.name ?? "Pastor";
    const title = pastor?.role ?? "Liderazgo Pastoral";
    const description = pastor?.bio_short ?? pastor?.story ?? localPastor?.shortStory ?? `Conoce al ${title} de la ${process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad"}.`;
    const imagePath = pastor?.photo_url || pastor?.image;
    const localImage = localPastor?.image;
    const image = imagePath ? `${BASE_URL}${imagePath}` : localImage ? `${BASE_URL}${localImage}` : `${BASE_URL}/og-default.png`;

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
