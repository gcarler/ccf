import type { Metadata } from "next";
import { Space_Grotesk, Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

// ── Typography: Load production fonts via next/font/google (self-hosted, no FOUC) ──
const spaceGrotesk = Space_Grotesk({
    subsets: ["latin"],
    weight: ["300", "400", "500", "600", "700"],
    variable: "--font-space-grotesk",
    display: "swap",
    preload: true,
});

const plusJakartaSans = Plus_Jakarta_Sans({
    subsets: ["latin"],
    weight: ["400", "500", "600", "700", "800"],
    variable: "--font-plus-jakarta",
    display: "swap",
    preload: false,
});

const inter = Inter({
    subsets: ["latin"],
    weight: ["400", "500", "600", "700"],
    variable: "--font-inter",
    display: "swap",
    preload: false,
});

import { AuthProvider } from "@/context/AuthContext";
import { ConfigProvider } from "@/context/ConfigContext";
import { ToastProvider } from "@/context/ToastContext";
import { ThemeProvider } from "./plataforma/theme/ThemeContext";
import { ClientBootstrap } from "./ClientBootstrap";
import { Toaster } from "sonner";
import { CommandCenter } from "@/components/ui/CommandCenter";
import { CommandCenterProvider } from "@/context/CommandCenterContext";
import { CreationProvider } from "@/context/CreationContext";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import SiteBrandAssets from "@/components/SiteBrandAssets";

const _siteName = process.env.NEXT_PUBLIC_SITE_NAME ?? "Mi Comunidad";

export const metadata: Metadata = {
    title: `${_siteName} | Plataforma`,
    description: "Plataforma académica y de gestión para comunidades de fe",
    manifest: "/manifest.json",
    appleWebApp: {
        capable: true,
        statusBarStyle: "default",
        title: _siteName,
    },
    formatDetection: {
        telephone: false,
    },
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="es" suppressHydrationWarning className={`${spaceGrotesk.variable} ${plusJakartaSans.variable} ${inter.variable}`}>
            <head>
                <script
                    dangerouslySetInnerHTML={{
                        __html: `
                            (function() {
                                try {
                                    var theme = localStorage.getItem('theme-mode');
                                    var supportDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches === true;
                                    if (!theme && supportDarkMode) theme = 'night';
                                    if (theme === 'night') {
                                        document.documentElement.classList.add('dark');
                                        document.documentElement.setAttribute('data-theme', 'night');
                                    } else {
                                        document.documentElement.classList.remove('dark');
                                        document.documentElement.setAttribute('data-theme', 'day');
                                    }
                                } catch (e) {}
                            })();
                        `,
                    }}
                />
            </head>
            <body className="font-display antialiased text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-background-light dark:bg-background-dark min-h-screen">
                <AuthProvider>
                    <ConfigProvider>
                        <ToastProvider>
                            <ThemeProvider>
                                <CommandCenterProvider>
                                    <CreationProvider>
                                        <SidebarLayerProvider>
                                            <SiteBrandAssets />
                                            <ClientBootstrap />
                                            <Toaster position="bottom-right" expand={false} richColors />
                                            <CommandCenter />
                                            {children}
                                        </SidebarLayerProvider>
                                    </CreationProvider>
                                </CommandCenterProvider>
                            </ThemeProvider>
                        </ToastProvider>
                    </ConfigProvider>
                </AuthProvider>
            </body>
        </html>
    );
}
