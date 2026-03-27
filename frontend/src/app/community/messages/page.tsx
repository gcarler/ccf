"use client";

import React, { useState, useEffect, useRef } from 'react';
import { 
    MessageSquare, 
    Search, 
    MoreHorizontal, 
    Send, 
    Smartphone, 
    User, 
    Phone, 
    Video, 
    Paperclip, 
    Smile, 
    ChevronLeft,
    CheckCheck,
    Bot,
    Zap,
    Users,
    Settings,
    MoreVertical
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';

export default function MessagingPage() {
    const { user, token } = useAuth();
    const [chats, setChats] = useState<any[]>([]);
    const [activeChat, setActiveChat] = useState<any>(null);
    const [messages, setMessages] = useState<any[]>([]);
    const [inputText, setInputText] = useState('');
    const [loading, setLoading] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Quality Mock Data for Chats
        setChats([
            { id: 1, name: 'Pastor Carlos', last_msg: 'Bendiciones, ¿cómo va el curso?', time: '10:30 AM', unread: 2, online: true },
            { id: 2, name: 'Grupo Alabanza', last_msg: 'Ensayo a las 6pm hoy.', time: '09:15 AM', unread: 0, online: false },
            { id: 3, name: 'Elena Rodriguez', last_msg: 'Gracias por la oración.', time: 'Ayer', unread: 0, online: true },
        ]);
        setLoading(false);
    }, []);

    useEffect(() => {
        if (activeChat) {
            setMessages([
                { id: 1, text: 'Hola, ¿tienes un momento para hablar?', sender: 'them', time: '10:25 AM' },
                { id: 2, text: '¡Claro que sí! Cuéntame.', sender: 'me', time: '10:28 AM' },
                { id: 3, text: activeChat.last_msg, sender: 'them', time: activeChat.time },
            ]);
        }
    }, [activeChat]);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSendMessage = () => {
        if (!inputText.trim()) return;
        const newMsg = { id: Date.now(), text: inputText, sender: 'me', time: 'Ahora' };
        setMessages([...messages, newMsg]);
        setInputText('');
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden font-display">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'Comunidad', icon: Users },
                    { label: 'Mensajería Interna', icon: MessageSquare }
                ]}
                viewType="list" setViewType={() => {}}
                rightActions={
                    <button className="p-2.5 bg-slate-100 dark:bg-white/5 rounded-xl text-slate-400 hover:text-blue-600 transition-all"><Settings size={20} /></button>
                }
            />

            <div className="flex-1 flex overflow-hidden">
                {/* Left: Chat List */}
                <aside className={clsx(
                    "w-full md:w-96 flex flex-col border-r border-slate-100 dark:border-white/5 transition-all",
                    activeChat && "hidden md:flex"
                )}>
                    <div className="p-6 space-y-6">
                        <div className="relative">
                            <input placeholder="Buscar conversaciones..." className="w-full bg-slate-50 dark:bg-white/5 border-none rounded-2xl py-3 px-12 text-sm font-bold outline-none focus:ring-4 focus:ring-blue-500/10 transition-all" />
                            <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto scrollbar-thin">
                        {chats.map(chat => (
                            <div 
                                key={chat.id} onClick={() => setActiveChat(chat)}
                                className={clsx(
                                    "p-6 flex items-center gap-4 cursor-pointer transition-all border-l-4",
                                    activeChat?.id === chat.id ? "bg-blue-50 dark:bg-blue-600/10 border-blue-600 shadow-inner" : "border-transparent hover:bg-slate-50 dark:hover:bg-white/5"
                                )}
                            >
                                <div className="relative shrink-0">
                                    <div className="size-12 rounded-2xl bg-slate-900 flex items-center justify-center text-white text-[10px] font-black uppercase">
                                        {chat.name.charAt(0)}
                                    </div>
                                    {chat.online && <div className="absolute -bottom-1 -right-1 size-4 bg-emerald-500 border-2 border-white dark:border-slate-900 rounded-full" />}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-baseline mb-1">
                                        <h4 className="text-[14px] font-black text-slate-800 dark:text-white truncate uppercase">{chat.name}</h4>
                                        <span className="text-[9px] font-bold text-slate-400 uppercase">{chat.time}</span>
                                    </div>
                                    <p className="text-[12px] text-slate-500 truncate leading-none">{chat.last_msg}</p>
                                </div>
                                {chat.unread > 0 && (
                                    <div className="size-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[9px] font-black shadow-lg shadow-blue-500/20">
                                        {chat.unread}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </aside>

                {/* Right: Active Chat */}
                <main className={clsx(
                    "flex-1 flex flex-col bg-slate-50/30 dark:bg-[#1e1f21] transition-all relative",
                    !activeChat && "hidden md:flex items-center justify-center text-center p-20"
                )}>
                    {activeChat ? (
                        <>
                            {/* Chat Header */}
                            <header className="p-6 bg-white/80 dark:bg-white/5 backdrop-blur-md border-b border-slate-100 dark:border-white/5 flex items-center justify-between z-10">
                                <div className="flex items-center gap-4">
                                    <button onClick={() => setActiveChat(null)} className="md:hidden p-2 text-slate-400"><ChevronLeft size={20} /></button>
                                    <div className="size-10 rounded-xl bg-slate-900 flex items-center justify-center text-white text-[10px] font-black uppercase">{activeChat.name.charAt(0)}</div>
                                    <div>
                                        <h3 className="text-sm font-black text-slate-800 dark:text-white uppercase leading-none mb-1">{activeChat.name}</h3>
                                        <p className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">{activeChat.online ? 'En línea' : 'Desconectado'}</p>
                                    </div>
                                </div>
                                <div className="flex gap-2">
                                    <button className="p-2.5 text-slate-400 hover:text-blue-600 transition-colors"><Phone size={20} /></button>
                                    <button className="p-2.5 text-slate-400 hover:text-blue-600 transition-colors"><Video size={20} /></button>
                                    <button className="p-2.5 text-slate-400 hover:text-blue-600 transition-colors"><MoreVertical size={20} /></button>
                                </div>
                            </header>

                            {/* Messages Area */}
                            <div ref={scrollRef} className="flex-1 overflow-y-auto p-8 space-y-6 scrollbar-hide">
                                {messages.map((msg) => (
                                    <motion.div 
                                        key={msg.id} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
                                        className={clsx(
                                            "flex flex-col max-w-[80%]",
                                            msg.sender === 'me' ? "ml-auto items-end" : "items-start"
                                        )}
                                    >
                                        <div className={clsx(
                                            "p-5 rounded-[2rem] text-sm font-medium shadow-sm",
                                            msg.sender === 'me' 
                                                ? "bg-blue-600 text-white rounded-br-none shadow-blue-500/10" 
                                                : "bg-white dark:bg-white/10 text-slate-800 dark:text-slate-200 rounded-bl-none"
                                        )}>
                                            {msg.text}
                                        </div>
                                        <div className="flex items-center gap-2 mt-2 px-2">
                                            <span className="text-[9px] font-bold text-slate-400 uppercase">{msg.time}</span>
                                            {msg.sender === 'me' && <CheckCheck size={12} className="text-blue-500" />}
                                        </div>
                                    </motion.div>
                                ))}
                            </div>

                            {/* Input Bar */}
                            <footer className="p-6 bg-white/80 dark:bg-white/5 backdrop-blur-md border-t border-slate-100 dark:border-white/5">
                                <div className="max-w-4xl mx-auto flex items-center gap-4 bg-slate-50 dark:bg-black/20 rounded-[2.5rem] p-2 pl-6 pr-2 shadow-inner">
                                    <button className="p-2 text-slate-400 hover:text-blue-600 transition-colors"><Smile size={20} /></button>
                                    <button className="p-2 text-slate-400 hover:text-blue-600 transition-colors"><Paperclip size={20} /></button>
                                    <input 
                                        value={inputText} onChange={(e) => setInputText(e.target.value)}
                                        onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                                        placeholder="Escribe un mensaje..." 
                                        className="flex-1 bg-transparent border-none outline-none py-3 text-sm font-medium text-slate-800 dark:text-white placeholder:text-slate-400" 
                                    />
                                    <button 
                                        onClick={handleSendMessage}
                                        className="size-12 bg-blue-600 hover:bg-blue-500 rounded-full flex items-center justify-center text-white shadow-xl shadow-blue-500/20 active:scale-90 transition-all"
                                    >
                                        <Send size={20} fill="currentColor" />
                                    </button>
                                </div>
                            </footer>
                        </>
                    ) : (
                        <div className="space-y-10">
                            <div className="size-32 rounded-[2.5rem] bg-blue-50 dark:bg-blue-600/10 flex items-center justify-center text-blue-600 mx-auto shadow-inner">
                                <Bot size={64} strokeWidth={1} />
                            </div>
                            <div>
                                <h3 className="text-3xl font-black text-slate-900 dark:text-white uppercase tracking-tighter">Tu Centro de Mensajes</h3>
                                <p className="text-slate-500 font-medium max-w-sm mx-auto mt-4 leading-relaxed uppercase tracking-widest text-[10px]">Selecciona una conversación para iniciar. Optimus Brain asegura que tus comunicaciones sean seguras y cifradas.</p>
                            </div>
                            <button className="px-10 py-4 bg-blue-600 text-white rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl shadow-blue-500/20 active:scale-95 transition-all">
                                Nuevo Mensaje
                            </button>
                        </div>
                    )}
                </main>
            </div>
        </div>
    );
}
