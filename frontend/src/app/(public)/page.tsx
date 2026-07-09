import type { Metadata } from "next";
import PublicHomePage from "./PublicHomePage";
import { getCmsPublicPage } from "@/lib/cms/v2";
import { SITE_KEY } from "@/lib/site-config";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://ccf.org";

export async function generateMetadata(): Promise<Metadata> {
  try {
    const page = await getCmsPublicPage(SITE_KEY, "home");
    if (!page) return {};
    const seo = page.seo_json || {};
    const metaTitle = typeof seo.meta_title === "string" && seo.meta_title.trim() ? seo.meta_title : page.title;
    const metaDescription = typeof seo.meta_description === "string" && seo.meta_description.trim() ? seo.meta_description : undefined;
    const metaImage = typeof seo.meta_image === "string" && seo.meta_image.trim() ? seo.meta_image : undefined;
    const canonical = page.canonical_url || `${SITE_URL}/${page.slug}`;
    const robotsMeta = typeof seo.robots_meta === "string" && seo.robots_meta.trim() ? seo.robots_meta : undefined;

    return {
      title: metaTitle,
      description: metaDescription,
      alternates: { canonical },
      robots: robotsMeta
        ? undefined
        : {
            index: true,
            follow: true,
          },
      ...(robotsMeta
        ? {}
        : {
            openGraph: {
              title: metaTitle,
              description: metaDescription,
              url: canonical,
              images: metaImage ? [metaImage] : undefined,
              type: "website",
              locale: "es_CO",
              siteName: "CCF",
            },
            twitter: {
              card: "summary_large_image",
              title: metaTitle,
              description: metaDescription,
              images: metaImage ? [metaImage] : undefined,
            },
          }),
    };
  } catch {
    return {};
  }
}

export default function Page() {
  return <PublicHomePage />;
}
