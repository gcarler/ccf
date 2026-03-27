import "./faro.css";
import { Inter } from "next/font/google";
import FaroNavbar from "../../components/public/FaroNavbar";
import FaroFooter from "../../components/public/FaroFooter";
import FaroMobileNav from "../../components/public/FaroMobileNav";

// Load Inter font for FARO body texts
const inter = Inter({ 
    subsets: ["latin"], 
    variable: "--font-inter",
    weight: ["300", "400", "500", "600", "700"]
});

export default function PublicLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className={`min-h-screen bg-faro-background text-faro-on-background font-body antialiased selection:bg-faro-primary/30 ${inter.variable}`}>
            <FaroNavbar />
            {children}
            <div className="h-32 md:h-0"></div>
            <FaroMobileNav />
            <FaroFooter />
        </div>
    );
}
