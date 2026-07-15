"use client";

import React, { createContext, useContext } from "react";
import type { PublicBootstrapState } from "@/lib/publicBootstrap";
import { readPublicBootstrap } from "@/lib/publicBootstrap";

const PublicBootstrapContext = createContext<PublicBootstrapState | null>(null);

export function PublicBootstrapProvider({
    bootstrap,
    children,
}: {
    bootstrap: PublicBootstrapState;
    children: React.ReactNode;
}) {
    return (
        <PublicBootstrapContext.Provider value={bootstrap}>
            {children}
        </PublicBootstrapContext.Provider>
    );
}

export function usePublicBootstrap() {
    return useContext(PublicBootstrapContext) || readPublicBootstrap();
}
