import React from 'react';

const shimmer = 'bg-gradient-to-r from-transparent via-white/40 to-transparent dark:via-white/10 animate-[shimmer_2s_infinite]';

export default function CrmLoading() {
    return (
        <div className="flex h-screen bg-[#0b0d11] text-white">
            <div className="w-72 bg-[#0f1116] border-r border-white/5" />
            <div className="flex-1 flex flex-col">
                <div className="h-14 border-b border-white/10 bg-black/30" />
                <main className="flex-1 overflow-y-auto p-4 space-y-3">
                    <div className="h-16 rounded-2xl border border-white/5 bg-white/5 relative overflow-hidden">
                        <div className={`absolute inset-0 ${shimmer}`} />
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {[1, 2, 3].map((key) => (
                            <div key={key} className="h-28 rounded-2xl border border-white/5 bg-white/5 relative overflow-hidden">
                                <div className={`absolute inset-0 ${shimmer}`} />
                            </div>
                        ))}
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="h-[380px] rounded-xl border border-white/5 bg-white/5 relative overflow-hidden">
                            <div className={`absolute inset-0 ${shimmer}`} />
                            <div className="absolute bottom-4 left-4 right-4 space-y-4">
                                {[...Array(4)].map((_, idx) => (
                                    <div key={idx} className="h-12 rounded-xl bg-white/10" />
                                ))}
                            </div>
                        </div>
                        <div className="h-[380px] rounded-xl border border-white/5 bg-white/5 relative overflow-hidden">
                            <div className={`absolute inset-0 ${shimmer}`} />
                            <div className="absolute inset-0 p-4 grid grid-cols-2 gap-3">
                                {[...Array(6)].map((_, idx) => (
                                    <div key={idx} className="rounded-2xl bg-white/10" />
                                ))}
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}

