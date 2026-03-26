"use client";

import clsx from 'clsx';

interface SkeletonProps {
    className?: string;
}

export default function Skeleton({ className }: SkeletonProps) {
    return (
        <div className={clsx(
            "relative overflow-hidden bg-slate-200 dark:bg-white/5 rounded-md",
            className
        )}>
            {/* Shimmer Effect Overlay */}
            <div className="absolute inset-0 -translate-x-full animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/20 dark:via-white/5 to-transparent" />
            
            <style jsx>{`
                @keyframes shimmer {
                    100% {
                        transform: translateX(100%);
                    }
                }
            `}</style>
        </div>
    );
}
