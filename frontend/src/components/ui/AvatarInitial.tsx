"use client";

import clsx from "clsx";

interface AvatarInitialProps {
    name: string;
    size?: "sm" | "md" | "lg";
    className?: string;
}

const COLORS = [
    "from-[hsl(var(--primary))] to-[hsl(var(--info))]",
    "from-[hsl(var(--domain-fuchsia))] to-[hsl(var(--info))]",
    "from-[hsl(var(--success))] to-[hsl(var(--success))]",
    "from-[hsl(var(--danger))] to-[hsl(var(--danger))]",
    "from-[hsl(var(--warning))] to-[hsl(var(--warning))]",
];

export function AvatarInitial({ name, size = "md", className }: AvatarInitialProps) {
    const safeName = (name || "U").slice(0, 2).toUpperCase();
    const color = COLORS[(name || "U").charCodeAt(0) % COLORS.length];

    return (
        <div
            className={clsx(
                "rounded-lg bg-gradient-to-br flex items-center justify-center text-white font-bold shrink-0",
                color,
                size === "sm" && "size-7 text-2xs",
                size === "md" && "size-8 text-2xs",
                size === "lg" && "size-10 text-xs",
                className
            )}
        >
            {safeName}
        </div>
    );
}
