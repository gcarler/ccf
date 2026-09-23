import React from 'react';

const shimmer = 'bg-gradient-to-r from-transparent via-[hsl(var(--surface-2))] to-transparent animate-[shimmer_2s_infinite]';

export default function CrmLoading() {
    return (
        <div className="flex h-screen bg-[hsl(var(--surface-1))] text-[hsl(var(--foreground))]">
            <div className="w-72 bg-[hsl(var(--surface-1))] border-r border-[hsl(var(--border))]" />
            <div className="flex-1 flex flex-col">
                <div className="h-8 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]" />
                <main className="flex-1 overflow-y-auto p-4 space-y-3">
                    <div className="h-8 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] relative overflow-hidden">
                        <div className={`absolute inset-0 ${shimmer}`} />
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                        {[1, 2, 3].map((key) => (
                            <div key={key} className="h-28 rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] relative overflow-hidden">
                                <div className={`absolute inset-0 ${shimmer}`} />
                            </div>
                        ))}
                    </div>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        <div className="h-[380px] rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] relative overflow-hidden">
                            <div className={`absolute inset-0 ${shimmer}`} />
                            <div className="absolute bottom-4 left-4 right-4 space-y-4">
                                {[...Array(4)].map((_, idx) => (
                                    <div key={idx} className="h-8 rounded-md bg-[hsl(var(--surface-2))]" />
                                ))}
                            </div>
                        </div>
                        <div className="h-[380px] rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] relative overflow-hidden">
                            <div className={`absolute inset-0 ${shimmer}`} />
                            <div className="absolute inset-0 p-4 grid grid-cols-2 gap-3">
                                {[...Array(6)].map((_, idx) => (
                                    <div key={idx} className="rounded-lg bg-[hsl(var(--surface-2))]" />
                                ))}
                            </div>
                        </div>
                    </div>
                </main>
            </div>
        </div>
    );
}
