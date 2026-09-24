import React from 'react';

const shimmer = 'bg-gradient-to-r from-transparent via-[hsl(var(--foreground)/0.08)] to-transparent animate-[shimmer_2s_infinite]';

export default function ProjectsLoading() {
    return (
        <div className="flex flex-col h-full bg-[hsl(var(--background))] overflow-hidden font-display">
            <div className="h-8 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]" />
            <main className="flex-1 overflow-y-auto scrollbar-none p-3 lg:p-4 space-y-3">
                <header className="space-y-3">
                    <div className="h-4 w-32 bg-[hsl(var(--surface-2))] rounded-full relative overflow-hidden">
                        <div className={`absolute inset-0 ${shimmer}`} />
                    </div>
                    <div className="h-8 w-1/3 bg-[hsl(var(--surface-2))] rounded-full relative overflow-hidden">
                        <div className={`absolute inset-0 ${shimmer}`} />
                    </div>
                    <div className="h-4 w-1/2 bg-[hsl(var(--surface-2))] rounded-full relative overflow-hidden">
                        <div className={`absolute inset-0 ${shimmer}`} />
                    </div>
                </header>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 pb-4">
                    {[...Array(6)].map((_, idx) => (
                        <div key={idx} className="h-48 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] relative overflow-hidden">
                            <div className={`absolute inset-0 ${shimmer}`} />
                        </div>
                    ))}
                </div>
            </main>
        </div>
    );
}
