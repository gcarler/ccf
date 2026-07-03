import "./public.css";
import { Inter } from "next/font/google";
import { CcfThemeProvider } from "../../components/public/CcfThemeProvider";
import CcfNavbar from "../../components/public/CcfNavbar";
import CcfFooter from "../../components/public/CcfFooter";
import CcfMobileNav from "../../components/public/CcfMobileNav";
import PublicSeoManager from "../../components/public/cms/PublicSeoManager";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-inter",
    weight: ["300", "400", "500", "600", "700", "800", "900"],
});

export default function PublicLayout({ children }: { children: React.ReactNode }) {
    return (
        <CcfThemeProvider>
            {/* Apply theme class to <html> before React hydration so CSS vars resolve immediately */}
            <script
                dangerouslySetInnerHTML={{
                    __html: `(function(){var t=localStorage.getItem("site-theme-v2")||"institutional";document.documentElement.classList.add("theme-"+t);if(t==="dark")document.documentElement.classList.add("dark")})()`,
                }}
            />
            <PublicSeoManager />
            <div className={`min-h-screen overflow-x-clip bg-site-background text-site-on-background font-body antialiased selection:bg-site-primary/30 ${inter.variable}`}>
                <CcfNavbar />
                <main className="relative">
                    {children}
                </main>
                <CcfFooter />
                <div className="h-32 md:h-0" />
                <CcfMobileNav />
            </div>
        </CcfThemeProvider>
    );
}
