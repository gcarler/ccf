import "./public.css";
import { serverApiFetch } from "@/lib/serverApi";
import { SITE_KEY } from "@/lib/site-config";
import type { CmsPublicMenu, CmsPublicPage, CmsTheme } from "@/types/cms-v2";
import { serializePublicBootstrap, type PublicBootstrapState } from "@/lib/publicBootstrap";
import { PublicBootstrapProvider } from "../../components/public/PublicBootstrapProvider";
import { ThemeProvider } from "../../components/public/ThemeProvider";
import Navbar from "../../components/public/Navbar";
import Footer from "../../components/public/Footer";
import MobileNav from "../../components/public/MobileNav";
import PublicSeoManager from "../../components/public/cms/PublicSeoManager";

/** Slugs de páginas públicas consumidas por useCmsV2Page. Se incluyen en el
 *  bootstrap SSR para que servidor y cliente rendericen el mismo árbol
 *  (evita hydration mismatch y SSR vacío en páginas CMS). */
const PUBLIC_PAGE_SLUGS = [
    "home",
    "about",
    "locations",
    "sermons",
    "courses",
    "newsletter",
    "testimonials",
    "pastors",
    "blog",
    "events",
    "discover",
    "donate",
    "privacy",
    "terms",
    "footer",
] as const;

async function loadPublicBootstrap(): Promise<PublicBootstrapState> {
    const [theme, mainMenu, mobileMenu, ...pages] = await Promise.all([
        serverApiFetch<CmsTheme>(`/cms/v2/public/sites/${SITE_KEY}/theme`).catch(() => null),
        serverApiFetch<CmsPublicMenu>(`/cms/v2/public/sites/${SITE_KEY}/menus/main`).catch(() => null),
        serverApiFetch<CmsPublicMenu>(`/cms/v2/public/sites/${SITE_KEY}/menus/mobile`).catch(() => null),
        ...PUBLIC_PAGE_SLUGS.map((slug) =>
            serverApiFetch<CmsPublicPage>(`/cms/v2/public/sites/${SITE_KEY}/pages/${slug}`).catch(() => null)
        ),
    ]);

    // Promise.all mantiene el orden: pages[index] corresponde a PUBLIC_PAGE_SLUGS[index]
    const pagesMap: Record<string, CmsPublicPage | null> = Object.fromEntries(
        PUBLIC_PAGE_SLUGS.map((slug, index) => [slug, pages[index] ?? null])
    );

    return {
        theme: theme ? { name: theme.name, tokens_json: theme.tokens_json || {} } : null,
        menus: {
            main: mainMenu,
            mobile: mobileMenu,
        },
        pages: pagesMap,
        footerPage: pagesMap.footer ?? null,
    };
}

export default async function PublicLayout({ children }: { children: React.ReactNode }) {
    const bootstrap = await loadPublicBootstrap();
    return (
        <PublicBootstrapProvider bootstrap={bootstrap}>
            <ThemeProvider>
                {/* Apply theme class to <html> before React hydration so CSS vars resolve immediately */}
                <script
                    dangerouslySetInnerHTML={{
                        __html: `(function(){var t=localStorage.getItem("site-theme-v2")||"light";document.documentElement.classList.add("theme-"+t);if(t==="dark")document.documentElement.classList.add("dark")})()`,
                    }}
                />
                <script
                    dangerouslySetInnerHTML={{
                        __html: `window.__CCF_PUBLIC_BOOTSTRAP__=${serializePublicBootstrap(bootstrap)};`,
                    }}
                />
                <PublicSeoManager />
                {/* overflow-x: clip (no hidden): clip NO crea scroll container, así que el hero
                    sticky de la home sigue anclado al viewport, pero el overflow horizontal de
                    cualquier página pública sigue clipeado (hidden rompía position:sticky). */}
                <div className="min-h-screen overflow-x-clip bg-site-background text-site-on-background font-body antialiased selection:bg-site-primary/30">
                    <Navbar />
                    {/* <main> relativo = contenedor sticky del hero reveal de la home */}
                    <main className="relative">
                        {children}
                    </main>
                    <Footer />
                    <div className="h-32 md:h-0" />
                    <MobileNav />
                </div>
            </ThemeProvider>
        </PublicBootstrapProvider>
    );
}
