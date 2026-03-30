import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ConfigProvider } from "@/context/ConfigContext";
import { ToastProvider } from "@/context/ToastContext";
import { ThemeProvider } from "./theme/ThemeContext";
import "@/lib/fetch-patch";
import { ClientBootstrap } from "./ClientBootstrap";
import { Toaster } from "sonner";
import { CommandCenter } from "@/components/ui/CommandCenter";
import { CommandCenterProvider } from "@/context/CommandCenterContext";
import { CreationProvider } from "@/context/CreationContext";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope", display: "swap" });

export const metadata: Metadata = {
    title: "CCF Platform | Formación y CRM",
    description: "Plataforma académica y de gestión moderna",
    manifest: "/manifest.json",
    appleWebApp: {
        capable: true,
        statusBarStyle: "default",
        title: "CCF Platform",
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
        <html lang="es" className={`${manrope.variable}`} suppressHydrationWarning>
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
            <body className="font-display antialiased text-slate-900 dark:text-slate-100 bg-background-light dark:bg-background-dark min-h-screen">
                <AuthProvider>
                    <ConfigProvider>
                        <ToastProvider>
                            <ThemeProvider>
                                <CommandCenterProvider>
                                    <CreationProvider>
                                        <ClientBootstrap />
                                        <Toaster position="bottom-right" expand={false} richColors />
                                        <CommandCenter />
                                        {children}
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
