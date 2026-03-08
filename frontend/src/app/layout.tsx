import type { Metadata } from "next";
import { Manrope } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";
import { ThemeProvider } from "./theme/ThemeContext";

const manrope = Manrope({ subsets: ["latin"], variable: "--font-manrope", display: "swap" });

export const metadata: Metadata = {
    title: "CCF Platform | Formación y CRM",
    description: "Plataforma académica y de gestión moderna",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="es" className={`${manrope.variable}`} suppressHydrationWarning>
            <head>
                <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
            </head>
            <body className="font-display antialiased text-slate-900 dark:text-slate-100 bg-background-light dark:bg-background-dark min-h-screen">
                <AuthProvider>
                    <ToastProvider>
                        <ThemeProvider>
                            {children}
                        </ThemeProvider>
                    </ToastProvider>
                </AuthProvider>
            </body>
        </html>
    );
}

