import type { Metadata } from "next";
import { Roboto, Inter, Open_Sans, Outfit } from "next/font/google";
import "./globals.css";

// ── Typography: Load production fonts via next/font/google (self-hosted, no FOUC) ──
const roboto = Roboto({
    subsets: ["latin"],
    weight: ["300", "400", "500", "700"],
    variable: "--font-roboto",
    display: "swap",
    preload: true,
});

const openSans = Open_Sans({
    subsets: ["latin"],
    weight: ["400", "500", "600", "700", "800"],
    variable: "--font-open-sans",
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

const outfit = Outfit({
    subsets: ["latin"],
    weight: ["400", "500", "600", "700", "800"],
    variable: "--font-outfit",
    display: "swap",
    preload: false,
});

import { AuthProvider } from "@/context/AuthContext";
import { ConfigProvider } from "@/context/ConfigContext";
import { ToastProvider } from "@/context/ToastContext";
import { ClientBootstrap } from "./ClientBootstrap";
import { Toaster } from "sonner";
import SiteBrandAssets from "@/components/SiteBrandAssets";
import { PopupManager } from "@/components/cms/PopupManager";

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
        <html lang="es" suppressHydrationWarning className={`${roboto.variable} ${openSans.variable} ${inter.variable} ${outfit.variable}`}>
            <head>
                <link
                    rel="stylesheet"
                    href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap"
                />
                <script
                    dangerouslySetInnerHTML={{
                        __html: `
                            (function() {
                                try {
                                    var isPublicRoute = window.location.pathname.indexOf('/public') === 0;
                                    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                                    var effectiveTheme;
                                    
                                    if (isPublicRoute) {
                                        // Rutas públicas: respetar preferencia del sistema (day/night)
                                        // sin leer localStorage de la plataforma (theme-mode)
                                        effectiveTheme = prefersDark ? 'night' : 'day';
                                    } else {
                                        // Rutas autenticadas: respetar localStorage (plataforma)
                                        var theme = localStorage.getItem('theme-mode');
                                        effectiveTheme = theme === 'night' ? 'night' : 'day';
                                    }
                                    
                                    if (effectiveTheme === 'night') {
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
                            <SiteBrandAssets />
                            <ClientBootstrap />
                            <Toaster position="bottom-right" expand={false} richColors />
                            <PopupManager />
                            {children}
                        </ToastProvider>
                    </ConfigProvider>
                </AuthProvider>
            </body>
        </html>
    );
}
