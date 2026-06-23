import "./public.css";
import { Inter } from "next/font/google";
import { FaroThemeProvider } from "../../components/public/FaroThemeProvider";
import FaroNavbar from "../../components/public/FaroNavbar";
import FaroFooter from "../../components/public/FaroFooter";
import FaroMobileNav from "../../components/public/FaroMobileNav";
import PublicSeoManager from "../../components/public/cms/PublicSeoManager";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-inter",
    weight: ["300", "400", "500", "600", "700", "800", "900"],
});

export default function PublicLayout({ children }: { children: React.ReactNode }) {
    return (
        <FaroThemeProvider>
            {/* Apply theme class to <html> before React hydration so CSS vars resolve immediately */}
            <script
                dangerouslySetInnerHTML={{
                    __html: `(function(){var t=localStorage.getItem("site-theme-v2")||localStorage.getItem("faro-theme-v2")||"institutional";document.documentElement.classList.add("theme-"+t);if(t==="dark")document.documentElement.classList.add("dark")})()`,
                }}
            />
            <PublicSeoManager />
            <div className={`min-h-screen overflow-x-clip bg-site-background text-site-on-background font-body antialiased selection:bg-site-primary/30 ${inter.variable}`}>
                <FaroNavbar />
                {children}
                <FaroFooter />
                <div className="h-32 md:h-0" />
                <FaroMobileNav />
            </div>
        </FaroThemeProvider>
    );
}
