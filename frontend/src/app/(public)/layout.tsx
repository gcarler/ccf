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

async function loadPublicBootstrap(): Promise<PublicBootstrapState> {
    const [theme, mainMenu, mobileMenu, homePage, eventsPage, footerPage] = await Promise.all([
        serverApiFetch<CmsTheme>(`/cms/v2/public/sites/${SITE_KEY}/theme`).catch(() => null),
        serverApiFetch<CmsPublicMenu>(`/cms/v2/public/sites/${SITE_KEY}/menus/main`).catch(() => null),
        serverApiFetch<CmsPublicMenu>(`/cms/v2/public/sites/${SITE_KEY}/menus/mobile`).catch(() => null),
        serverApiFetch<CmsPublicPage>(`/cms/v2/public/sites/${SITE_KEY}/pages/home`).catch(() => null),
        serverApiFetch<CmsPublicPage>(`/cms/v2/public/sites/${SITE_KEY}/pages/events`).catch(() => null),
        serverApiFetch<CmsPublicPage>(`/cms/v2/public/sites/${SITE_KEY}/pages/footer`).catch(() => null),
    ]);

    return {
        theme: theme ? { name: theme.name, tokens_json: theme.tokens_json || {} } : null,
        menus: {
            main: mainMenu,
            mobile: mobileMenu,
        },
        pages: {
            home: homePage,
            events: eventsPage,
            footer: footerPage,
        },
        footerPage,
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
                        __html: `(function(){var t=localStorage.getItem("site-theme-v2")||"institutional";document.documentElement.classList.add("theme-"+t);if(t==="dark")document.documentElement.classList.add("dark")})()`,
                    }}
                />
                <script
                    dangerouslySetInnerHTML={{
                        __html: `window.__CCF_PUBLIC_BOOTSTRAP__=${serializePublicBootstrap(bootstrap)};`,
                    }}
                />
                <PublicSeoManager />
                <div className="min-h-screen overflow-x-clip bg-site-background text-site-on-background font-body antialiased selection:bg-site-primary/30">
                    <Navbar />
                    <main className="relative min-h-screen">
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
