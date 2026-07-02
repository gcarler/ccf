"use client";

import WikiEditor from '@/components/wiki/WikiEditor';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { motion } from 'framer-motion';
import { BookOpen,ChevronLeft,History,MoreHorizontal,Share2 } from 'lucide-react';
import { useParams,useRouter } from 'next/navigation';
import { useEffect,useState } from 'react';

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
                const data = await apiFetch<any>(`/wiki/pages/${page_key}`, { token });
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
        await apiFetch(`/wiki/pages/${page_key}`, {
            method: 'PATCH',
            token,
            body: {
                content: newContent
            }
        });
    };

    if (loading) return (
        <div className="flex-1 flex items-center justify-center bg-[hsl(var(--bg-primary))] dark:bg-[#141517]">
            <motion.div 
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
                className="size-8 border-2 border-[hsl(var(--primary))] border-t-transparent rounded-full"
            />
        </div>
    );

    const sidebarSections = [
        {
            title: 'Wiki',
            items: [
                { id: 'wiki-home', label: 'Inicio', href: '/plataforma/wiki', icon: BookOpen },
            ]
        }
    ];

    return (
        <WorkspaceLayout sidebarTitle="Wiki" sidebarSections={sidebarSections}>
            <div className="flex-1 flex flex-col bg-[hsl(var(--bg-primary))] dark:bg-[#141517] overflow-hidden">
            {/* Minimal Header */}
            <header className="h-8 px-3 border-b border-[hsl(var(--border))] dark:border-white/5 flex items-center justify-between shrink-0 bg-white/80 dark:bg-[#141517]/80 backdrop-blur-md sticky top-0 z-10">
                <div className="flex items-center gap-4">
                    <button 
                        onClick={() => router.push('/plataforma/wiki')}
                        className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))] transition-all"
                    >
                        <ChevronLeft size={20} />
                    </button>
                    <div className="w-[1px] h-4 bg-[hsl(var(--surface-3))] dark:bg-white/10" />
                    <h1 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white truncate max-w-[300px]">
                        {doc?.title || "Sin título"}
                    </h1>
                </div>

                <div className="flex items-center gap-2">
                    <button className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]">
                        <History size={18} />
                    </button>
                    <button className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]">
                        <Share2 size={18} />
                    </button>
                    <button className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/5 rounded-md text-[hsl(var(--text-secondary))]">
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
        </WorkspaceLayout>
    );
}
