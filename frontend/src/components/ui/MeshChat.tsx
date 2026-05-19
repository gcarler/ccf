"use client";

import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Send, X, Bot, User, Sparkles, Loader2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import clsx from 'clsx';

interface Message {
    id: string;
    role: 'bot' | 'user';
    content: string;
    timestamp: Date;
    sources?: string[];
}

export default function MeshChat({ isOpen, onClose }: { isOpen: boolean, onClose: () => void }) {
    const { token, user } = useAuth();
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'bot',
            content: `Hola ${user?.username || 'Siervo'}. Soy Optimus Brain, la inteligencia de MESH. ¿En qué puedo apoyarte con la gestión ministerial hoy?`,
            timestamp: new Date()
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || loading) return;

        const userMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const res = await apiFetch<any>('/agents/ask', {
                method: 'POST',
                token,
                body: { query: input }
            });

            const botMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'bot',
                content: res.answer,
                timestamp: new Date(),
                sources: res.sources
            };

            setMessages(prev => [...prev, botMsg]);
        } catch (err) {
            setMessages(prev => [...prev, {
                id: 'err',
                role: 'bot',
                content: "Lo siento, tuve un problema de conexión con el cerebro central. Por favor, intenta de nuevo.",
                timestamp: new Date()
            }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    <motion.div 
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-[1000] bg-slate-900/20 backdrop-blur-sm"
                    />
                    <motion.div 
                        initial={{ opacity: 0, y: 100, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 100, scale: 0.95 }}
                        className="fixed bottom-6 right-6 w-full max-w-[440px] h-[600px] bg-white dark:bg-[#15171c] rounded-[2.5rem] shadow-2xl border border-slate-100 dark:border-white/5 z-[1001] flex flex-col overflow-hidden"
                    >
                        {/* Header */}
                        <header className="p-6 border-b border-slate-50 dark:border-white/5 flex items-center justify-between bg-white dark:bg-white/5 shrink-0">
                            <div className="flex items-center gap-4">
                                <div className="size-12 rounded-2xl bg-sky-600 flex items-center justify-center text-white shadow-lg shadow-sky-500/30 relative">
                                    <Bot size={24} />
                                    <div className="absolute -bottom-1 -right-1 size-4 bg-emerald-500 rounded-full border-2 border-white dark:border-[#15171c]" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-black text-slate-800 dark:text-slate-100 tracking-tight leading-none mb-1">Optimus Brain</h3>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[9px] font-black uppercase tracking-widest text-emerald-500">Neural Active</span>
                                        <div className="size-1 rounded-full bg-emerald-500 animate-pulse" />
                                    </div>
                                </div>
                            </div>
                            <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-all text-slate-400">
                                <X size={20} />
                            </button>
                        </header>

                        {/* Chat Messages */}
                        <div className="flex-1 overflow-y-auto scrollbar-thin p-6 space-y-6">
                            {messages.map((msg) => (
                                <motion.div 
                                    key={msg.id}
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className={clsx(
                                        "flex gap-3",
                                        msg.role === 'user' ? "flex-row-reverse" : "flex-row"
                                    )}
                                >
                                    <div className={clsx(
                                        "size-8 rounded-xl flex items-center justify-center shrink-0 shadow-sm",
                                        msg.role === 'bot' ? "bg-sky-50 dark:bg-sky-900/20 text-sky-600" : "bg-blue-600 text-white"
                                    )}>
                                        {msg.role === 'bot' ? <Sparkles size={16} /> : <User size={16} />}
                                    </div>
                                    <div className={clsx(
                                        "max-w-[80%] space-y-2",
                                        msg.role === 'user' ? "items-end text-right" : "items-start text-left"
                                    )}>
                                        <div className={clsx(
                                            "p-4 rounded-[1.5rem] text-[13px] font-medium leading-relaxed shadow-sm",
                                            msg.role === 'bot' 
                                                ? "bg-slate-50 dark:bg-white/5 text-slate-700 dark:text-slate-200 border border-slate-100 dark:border-white/5" 
                                                : "bg-blue-600 text-white"
                                        )}>
                                            {msg.content}
                                        </div>
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div className="flex flex-wrap gap-2 pt-1">
                                                {msg.sources.map((s, i) => (
                                                    <span key={i} className="text-[9px] font-black uppercase tracking-widest bg-slate-100 dark:bg-white/5 text-slate-400 px-2 py-1 rounded-md border border-slate-200 dark:border-white/5">
                                                        Source: {s}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest px-2">
                                            {msg.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                        </span>
                                    </div>
                                </motion.div>
                            ))}
                            {loading && (
                                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
                                    <div className="size-8 rounded-xl bg-sky-50 dark:bg-sky-900/20 flex items-center justify-center text-sky-600 shrink-0">
                                        <Loader2 size={16} className="animate-spin" />
                                    </div>
                                    <div className="bg-slate-50 dark:bg-white/5 p-4 rounded-[1.5rem] flex gap-1 items-center">
                                        <div className="size-1.5 bg-slate-300 rounded-full animate-bounce" />
                                        <div className="size-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:-0.15s]" />
                                        <div className="size-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:-0.3s]" />
                                    </div>
                                </motion.div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area */}
                        <div className="p-6 bg-slate-50/50 dark:bg-black/20 border-t border-slate-100 dark:border-white/5 shrink-0">
                            <form onSubmit={handleSend} className="relative">
                                <input 
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    placeholder="Preguntar a Optimus..."
                                    className="w-full h-14 bg-white dark:bg-[#1e1f21] border border-slate-200 dark:border-white/10 rounded-2xl pl-6 pr-14 text-sm font-bold text-slate-800 dark:text-white outline-none focus:ring-4 focus:ring-sky-500/10 focus:border-sky-500/50 transition-all shadow-inner"
                                />
                                <button 
                                    type="submit"
                                    disabled={!input.trim() || loading}
                                    className="absolute right-2 top-1/2 -translate-y-1/2 size-10 rounded-xl bg-sky-600 text-white flex items-center justify-center hover:bg-sky-500 active:scale-95 transition-all shadow-lg shadow-sky-500/30 disabled:opacity-50"
                                >
                                    <Send size={18} />
                                </button>
                            </form>
                            <p className="text-[9px] font-bold text-slate-400 text-center mt-4 uppercase tracking-[0.2em]">MESH Neural Engine v3.0</p>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
