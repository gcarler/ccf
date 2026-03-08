"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
    ChevronLeft,
    Search,
    Download,
    BookOpen,
    Star,
    ArrowRight
} from 'lucide-react';
import { apiUrl } from '@/lib/api';

interface Book {
    id: number;
    title: string;
    author: string;
    description: string;
    cover_image_url: string;
    download_url: string;
}

interface PageContent {
    page_key: string;
    title?: string;
    content?: string;
}

export default function BooksPage() {
    const [books, setBooks] = useState<Book[]>([]);
    const [pageContent, setPageContent] = useState<PageContent | null>(null);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [booksRes, contRes] = await Promise.all([
                    fetch(apiUrl('/books/')),
                    fetch(apiUrl('/content/books_hero'))
                ]);
                if (booksRes.ok) setBooks(await booksRes.json());
                if (contRes.ok) setPageContent(await contRes.json());
            } catch (e) {
                console.error(e);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, []);

    const filtered = books.filter(b =>
        b.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        b.author.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
        <div className="min-h-screen bg-background-light dark:bg-background-dark font-display text-slate-900 dark:text-slate-100 pb-24">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-white/80 dark:bg-background-dark/80 backdrop-blur-xl border-b border-slate-200 dark:border-white/5 px-6 py-6">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/academy" className="size-10 rounded-full bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-500 hover:text-primary transition-all">
                            <ChevronLeft size={20} />
                        </Link>
                        <h1 className="text-2xl font-black tracking-tight">{pageContent?.title || "Biblioteca Digital"}</h1>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-10 space-y-10">

                {/* Search */}
                <div className="relative max-w-2xl mx-auto">
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400" size={20} />
                    <input
                        type="text"
                        placeholder="Buscar por título o autor..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full h-14 pl-14 pr-6 bg-white dark:bg-slate-900 rounded-2xl text-sm font-medium focus:ring-2 focus:ring-primary/50 outline-none shadow-sm border border-slate-200 dark:border-white/10 transition-all"
                    />
                </div>

                {/* List */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {filtered.map(book => (
                        <div key={book.id} className="glass dark:bg-slate-900/40 rounded-[2rem] p-6 shadow-sm hover:shadow-xl transition-all border border-slate-200 dark:border-white/5 flex flex-col group">
                            <div className="relative aspect-[3/4] w-full mb-6 rounded-2xl overflow-hidden shadow-lg">
                                <img src={book.cover_image_url} alt={book.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" />
                                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                                <a href={book.download_url} target="_blank" className="absolute bottom-4 left-1/2 -translate-x-1/2 translate-y-10 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all bg-white text-slate-900 px-6 py-3 rounded-xl font-black text-xs uppercase tracking-widest flex items-center gap-2 shadow-xl">
                                    <Download size={16} /> Descargar
                                </a>
                            </div>

                            <h3 className="text-xl font-black mb-1 group-hover:text-primary transition-colors line-clamp-1">{book.title}</h3>
                            <p className="text-sm font-bold text-slate-500 mb-4">{book.author}</p>
                            <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-3 mb-6 flex-1">{book.description}</p>

                            <div className="flex items-center gap-2 pt-4 border-t border-slate-100 dark:border-white/5">
                                <Star size={16} className="text-amber-400 fill-current" />
                                <span className="text-xs font-bold text-slate-500">Material Recomendado</span>
                            </div>
                        </div>
                    ))}
                </div>

            </main>
        </div>
    );
}
