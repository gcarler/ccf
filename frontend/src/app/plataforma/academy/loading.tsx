import React from 'react';

const shimmer = 'bg-gradient-to-r from-transparent via-[hsl(var(--surface-3)/0.4)] to-transparent animate-[shimmer_2s_infinite]';

export default function AcademyLoading() {
    return (
        <div className="flex flex-col h-full bg-[hsl(var(--surface-1))] overflow-hidden font-display">
            <div className="h-8 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]" />
            <main className="flex-1 overflow-y-auto scrollbar-none p-4 lg:p-3 space-y-3">
                <div className="h-48 rounded-lg bg-[hsl(var(--surface-2))] relative overflow-hidden">
                    <div className={`absolute inset-0 ${shimmer}`} />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    <div className="lg:col-span-8 space-y-3">
                        {[1, 2, 3].map((key) => (
                            <div key={key} className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-4 space-y-4 relative overflow-hidden">
                                <div className={`absolute inset-0 ${shimmer}`} />
                                <div className="h-6 w-40 bg-[hsl(var(--surface-3))] rounded-full" />
                                <div className="h-10 w-3/4 bg-[hsl(var(--surface-3)/0.7)] rounded-full" />
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="h-32 rounded-md bg-[hsl(var(--surface-3)/0.5)]" />
                                    <div className="h-32 rounded-md bg-[hsl(var(--surface-3)/0.5)]" />
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="lg:col-span-4 space-y-3">
                        {[1, 2].map((key) => (
                            <div key={key} className="h-48 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] relative overflow-hidden">
                                <div className={`absolute inset-0 ${shimmer}`} />
                            </div>
                        ))}
                        <div className="h-48 rounded-md border border-[hsl(var(--border))] bg-gradient-to-br from-[hsl(var(--surface-2))] to-[hsl(var(--surface-3))] relative overflow-hidden">
                            <div className={`absolute inset-0 ${shimmer}`} />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
