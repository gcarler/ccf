import "./public.css";
import { Inter } from "next/font/google";
import { ThemeProvider } from "../../components/public/ThemeProvider";
import Navbar from "../../components/public/Navbar";
import Footer from "../../components/public/Footer";
import MobileNav from "../../components/public/MobileNav";
import PublicSeoManager from "../../components/public/cms/PublicSeoManager";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-inter",
    weight: ["300", "400", "500", "600", "700", "800", "900"],
});

export default function PublicLayout({ children }: { children: React.ReactNode }) {
    return (
        <ThemeProvider>
            {/* Apply theme class to <html> before React hydration so CSS vars resolve immediately */}
            <script
                dangerouslySetInnerHTML={{
                    __html: `(function(){var t=localStorage.getItem("site-theme-v2")||"institutional";document.documentElement.classList.add("theme-"+t);if(t==="dark")document.documentElement.classList.add("dark")})()`,
                }}
            />
            <PublicSeoManager />
            <div className={`min-h-screen overflow-x-clip bg-site-background text-site-on-background font-body antialiased selection:bg-site-primary/30 ${inter.variable}`}>
                <Navbar />
                <main className="relative">
                    {children}
                </main>
                <Footer />
                <div className="h-32 md:h-0" />
                <MobileNav />
            </div>
        </ThemeProvider>
    );
}
