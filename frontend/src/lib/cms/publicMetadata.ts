import type { Metadata } from "next";
import { serverApiFetch } from "@/lib/serverApi";
import { SITE_KEY } from "@/lib/site-config";

type PublicPage = {
  title?: string;
  sections?: Array<{ section_key?: string; props_json?: Record<string, unknown> }>;
};

function plainText(value: unknown): string | undefined {
  if (typeof value !== "string") return undefined;
  const text = value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
  return text || undefined;
}

/** Metadata for public routes comes from the same published CMS page as the body. */
export async function publicCmsMetadata(slug: string): Promise<Metadata> {
  try {
    const page = await serverApiFetch<PublicPage>(`/cms/v2/public/sites/${SITE_KEY}/pages/${slug}`);
    const hero = page.sections?.find((section) => section.section_key === "hero")?.props_json ?? {};
    return {
      title: page.title || undefined,
      description: plainText(hero.description),
    };
  } catch {
    return {};
  }
}
