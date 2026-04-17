import React from 'react';

const shimmer = 'bg-gradient-to-r from-transparent via-white/40 to-transparent dark:via-white/10 animate-[shimmer_2s_infinite]';

export default function ProjectsLoading() {
    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden font-display">
            <div className="h-11 border-b border-white/10 bg-white/60 dark:bg-black/20" />
            <main className="flex-1 overflow-y-auto scrollbar-none p-6 lg:p-10 space-y-8">
                <header className="space-y-3">
                    <div className="h-4 w-32 bg-slate-200/80 dark:bg-white/10 rounded-full relative overflow-hidden">
                        <div className={`absolute inset-0 ${shimmer}`} />
                    </div>
                    <div className="h-12 w-1/3 bg-slate-200 dark:bg-white/10 rounded-full relative overflow-hidden">
                        <div className={`absolute inset-0 ${shimmer}`} />
                    </div>
                    <div className="h-4 w-1/2 bg-slate-200 dark:bg-white/10 rounded-full relative overflow-hidden">
                        <div className={`absolute inset-0 ${shimmer}`} />
                    </div>
                </header>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8 pb-20">
                    {[...Array(6)].map((_, idx) => (
                        <div key={idx} className="h-64 rounded-[3rem] border border-slate-200 dark:border-white/5 bg-slate-100 dark:bg-white/5 relative overflow-hidden">
                            <div className={`absolute inset-0 ${shimmer}`} />
                        </div>
                    ))}
                </div>
            </main>
        </div>
    );
}

