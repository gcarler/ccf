"use client";

import React from "react";
import { ThemeProvider } from "./theme/ThemeContext";
import { CommandCenterProvider } from "@/context/CommandCenterContext";
import { CreationProvider } from "@/context/CreationContext";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import { CommandCenter } from "@/components/ui/CommandCenter";
import ProtectedRoute from "@/components/ProtectedRoute";

export default function PlataformaLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <ThemeProvider>
            <CommandCenterProvider>
                <CreationProvider>
                    <SidebarLayerProvider>
                        <ProtectedRoute>
                            <CommandCenter />
                            {children}
                        </ProtectedRoute>
                    </SidebarLayerProvider>
                </CreationProvider>
            </CommandCenterProvider>
        </ThemeProvider>
    );
}