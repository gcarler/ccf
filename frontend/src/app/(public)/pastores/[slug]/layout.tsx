import type { Metadata } from "next";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { SITE_KEY, SITE_NAME, SITE_URL } from "@/lib/site-config";

type CmsPastor = {
  slug: string;
  name?: string;
  role?: string;
  photo_url?: string;
  image?: string;
  bio_short?: string;
  story?: string;
};

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const resolvedParams = await params;
  const slug = resolvedParams.slug;
  const baseUrl = SITE_URL || "";

  let pastor: CmsPastor | null = null;
  let page: Awaited<ReturnType<typeof getCmsPublicPage>> | null = null;
  try {
    page = await getCmsPublicPage(SITE_KEY, "pastors", { silent: true });
    const pastors = (page?.blocks?.pastors as { pastors?: CmsPastor[] } | undefined)?.pastors;
    pastor = pastors?.find((p) => p.slug === slug) || null;
  } catch {
    pastor = null;
  }

  const detailTemplate = page?.blocks?.detail_template as Record<string, unknown> | undefined;
  const roleFallback = typeof detailTemplate?.role_fallback === "string" ? detailTemplate.role_fallback : "";
  const name = pastor?.name || "Pastor";
  const role = pastor?.role || roleFallback;
  const description = pastor?.bio_short || pastor?.story || `Conoce al ${role || name} de la ${SITE_NAME}.`;
  const image = pastor?.photo_url || pastor?.image || `${baseUrl}/og-default.png`;

  return {
    title: `${name} | ${SITE_NAME}`,
    description,
    openGraph: {
      title: `${name} — ${role}`,
      description,
      url: `${baseUrl}/pastores/${slug}`,
      siteName: SITE_NAME,
      images: [{ url: image, width: 400, height: 500, alt: name }],
      type: "profile",
      locale: "es_CO",
    },
    twitter: {
      card: "summary_large_image",
      title: `${name} — ${role}`,
      description,
      images: [image],
    },
  };
}

export default function PastorSlugLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
