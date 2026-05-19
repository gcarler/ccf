"use client";

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { ChevronLeft, Share2, MoreHorizontal, History } from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import WikiEditor from '@/components/wiki/WikiEditor';

export default function WikiDocEditPage() {
    const params = useParams();
    const page_key = params ? (params.page_key as string) : null;
    const router = useRouter();
    const { token } = useAuth();
    const [doc, setDoc] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchDoc = async () => {
            if (!token || !page_key) return;
            try {
                const data = await apiFetch<any>(`/content/${page_key}`, { token });
                setDoc(data);
            } catch (error) {
                console.error("Error fetching doc:", error);
            } finally {
                setLoading(false);
            }
        };
        fetchDoc();
    }, [token, page_key]);

    const handleSave = async (newContent: string) => {
        if (!token || !page_key) return;
        await apiFetch(`/content/${page_key}`, {
            method: 'PATCH',
            token,
            body: {
                content: newContent
            }
        });
    };

    if (loading) return (
        <div className="flex-1 flex items-center justify-center bg-white dark:bg-[#141517]">
            <motion.div 
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="size-8 border-2 border-indigo-600 border-t-transparent rounded-full"
            />
        </div>
    );

    return (
        <div className="flex-1 flex flex-col bg-white dark:bg-[#141517] overflow-hidden">
            {/* Minimal Header */}
            <header className="h-14 px-6 border-b border-slate-100 dark:border-white/5 flex items-center justify-between shrink-0 bg-white/80 dark:bg-[#141517]/80 backdrop-blur-md sticky top-0 z-10">
                <div className="flex items-center gap-4">
                    <button 
                        onClick={() => router.push('/wiki')}
                        className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-400 transition-all"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <div className="w-[1px] h-4 bg-slate-200 dark:bg-white/10" />
                    <h1 className="text-[13px] font-bold text-slate-900 dark:text-white truncate max-w-[300px]">
                        {doc?.title || "Sin título"}
                    </h1>
                </div>

                <div className="flex items-center gap-2">
                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-400">
                        <History size={18} />
                    </button>
                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-400">
                        <Share2 size={18} />
                    </button>
                    <button className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl text-slate-400">
                        <MoreHorizontal size={18} />
                    </button>
                </div>
            </header>

            {/* Editor Area */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                <WikiEditor 
                    initialContent={doc?.content || ""} 
                    onSave={handleSave}
                    placeholder="Comienza la base de conocimiento..."
                />
            </div>
        </div>
    );
}
