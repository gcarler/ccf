"use client";

import React from "react";
import { DSTooltip } from "@/design";

interface TooltipProps {
    children: React.ReactNode;
    content: string;
    side?: "top" | "right" | "bottom" | "left";
}

export default function Tooltip({ children, content, side = "top" }: TooltipProps) {
    return (
        <DSTooltip content={content} side={side}>
            {children}
        </DSTooltip>
    );
}
