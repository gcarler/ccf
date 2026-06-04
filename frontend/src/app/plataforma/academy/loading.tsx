import React from 'react';

const shimmer = 'bg-gradient-to-r from-transparent via-white/40 to-transparent dark:via-white/10 animate-[shimmer_2s_infinite]';

export default function AcademyLoading() {
    return (
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] overflow-hidden font-display">
            <div className="h-8 border-b border-white/10 bg-white/60 dark:bg-black/40" />
            <main className="flex-1 overflow-y-auto scrollbar-none p-4 lg:p-3 space-y-3">
                <div className="h-48 rounded-lg bg-slate-200/60 dark:bg-white/5 relative overflow-hidden">
                    <div className={`absolute inset-0 ${shimmer}`} />
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                    <div className="lg:col-span-8 space-y-3">
                        {[1, 2, 3].map((key) => (
                            <div key={key} className="rounded-md border border-white/10 bg-slate-100 dark:bg-white/5 p-4 space-y-4 relative overflow-hidden">
                                <div className={`absolute inset-0 ${shimmer}`} />
                                <div className="h-6 w-40 bg-white/40 rounded-full" />
                                <div className="h-10 w-3/4 bg-white/30 rounded-full" />
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="h-32 rounded-md bg-white/20" />
                                    <div className="h-32 rounded-md bg-white/20" />
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="lg:col-span-4 space-y-3">
                        {[1, 2].map((key) => (
                            <div key={key} className="h-48 rounded-md border border-white/10 bg-slate-100 dark:bg-white/5 relative overflow-hidden">
                                <div className={`absolute inset-0 ${shimmer}`} />
                            </div>
                        ))}
                        <div className="h-48 rounded-md border border-white/10 bg-gradient-to-br from-sky-500/30 to-sky-500/30 relative overflow-hidden">
                            <div className={`absolute inset-0 ${shimmer}`} />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}

