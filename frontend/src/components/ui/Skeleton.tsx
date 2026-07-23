"use client";

import React from "react";
import { DSSkeleton } from "@/design";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
    className?: string;
}

export default function Skeleton({ className, ...props }: SkeletonProps) {
    return <DSSkeleton className={className} rounded="md" {...props} />;
}
