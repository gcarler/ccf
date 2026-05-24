import "./faro.css";
import { Inter } from "next/font/google";
import { FaroThemeProvider } from "../../components/public/FaroThemeProvider";
import FaroNavbar from "../../components/public/FaroNavbar";
import FaroFooter from "../../components/public/FaroFooter";
import FaroMobileNav from "../../components/public/FaroMobileNav";

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
                    __html: `(function(){var t=localStorage.getItem("faro-theme-v2")||"institutional";document.documentElement.classList.add("theme-"+t)})()`,
                }}
            />
            <div className={`min-h-screen bg-faro-background text-faro-on-background font-body antialiased selection:bg-faro-primary/30 ${inter.variable}`}>
                <FaroNavbar />
                {children}
                <div className="h-32 md:h-0" />
                <FaroMobileNav />
                <FaroFooter />
            </div>
        </FaroThemeProvider>
    );
}

