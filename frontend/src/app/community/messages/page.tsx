"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Search, Plus, Send, Phone, Video, Info, MoreVertical, Image as ImageIcon, Smile, Paperclip } from 'lucide-react';

export default function MessagesPage() {
    const chats = [
        {
            id: 1,
            name: "Grupo de Oración",
            lastMsg: "Amén hermanos, quedamos así.",
            time: "10:24 AM",
            unread: 3,
            isGroup: true
        },
        {
            id: 2,
            name: "Carlos Méndez",
            lastMsg: "¿Pudiste revisar el material?",
            time: "9:15 AM",
            unread: 0,
            isGroup: false
        },
        {
            id: 3,
            name: "Secretaría CCF",
            lastMsg: "Tu solicitud ha sido aprobada.",
            time: "Ayer",
            unread: 0,
            isGroup: false
        }
    ];

    return (
        <div className="h-[calc(100vh-180px)] bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[3rem] overflow-hidden flex animate-in fade-in duration-700 shadow-sm">
            {/* Sidebar List */}
            <div className="w-80 border-r border-[hsl(var(--border))] flex flex-col bg-[hsl(var(--surface-1))]">
                <div className="p-6 border-b border-[hsl(var(--border))] space-y-4">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-black text-[hsl(var(--text-primary))] tracking-tighter">Mensajes</h2>
                        <button className="size-8 rounded-lg bg-[hsl(var(--primary))] text-white flex items-center justify-center hover:opacity-90 transition-all">
                            <Plus size={16} strokeWidth={3} />
                        </button>
                    </div>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))] size-3.5" />
                        <input 
                            placeholder="Buscar chats..."
                            className="w-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-xl h-10 pl-10 pr-4 text-xs font-medium outline-none focus:ring-2 focus:ring-[hsl(var(--primary)/0.2)] transition-all"
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto p-3 space-y-1">
                    {chats.map((chat) => (
                        <div 
                            key={chat.id}
                            className={`p-4 rounded-[2rem] flex items-center gap-4 cursor-pointer transition-all hover:bg-[hsl(var(--surface-2))] ${chat.id === 1 ? 'bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] shadow-sm' : ''}`}
                        >
                            <div className="size-12 rounded-[1rem] bg-[hsl(var(--surface-3))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--primary))] font-black text-xs">
                                {chat.name.substring(0, 2).toUpperCase()}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between mb-0.5">
                                    <h4 className="font-black text-[hsl(var(--text-primary))] text-sm truncate tracking-tight">{chat.name}</h4>
                                    <span className="text-[9px] font-bold text-[hsl(var(--text-secondary)/0.5)] uppercase">{chat.time}</span>
                                </div>
                                <p className="text-[11px] text-[hsl(var(--text-secondary))] truncate font-medium">{chat.lastMsg}</p>
                            </div>
                            {chat.unread > 0 && (
                                <div className="size-5 rounded-full bg-[hsl(var(--primary))] text-white text-[9px] font-black flex items-center justify-center shadow-lg shadow-primary/30">
                                    {chat.unread}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Chat Area */}
            <div className="flex-1 flex flex-col bg-[hsl(var(--surface-2))]">
                {/* Chat Header */}
                <header className="h-20 border-b border-[hsl(var(--border))] px-8 flex items-center justify-between bg-[hsl(var(--surface-1))]">
                    <div className="flex items-center gap-4">
                        <div className="size-10 rounded-xl bg-[hsl(var(--primary)/0.1)] border border-[hsl(var(--primary)/0.2)] flex items-center justify-center text-[hsl(var(--primary))] font-black text-xs">
                            GO
                        </div>
                        <div>
                            <h3 className="font-black text-[hsl(var(--text-primary))] tracking-tighter">Grupo de Oración</h3>
                            <p className="text-[10px] text-[hsl(var(--primary))] font-black uppercase tracking-widest">En línea</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button className="size-10 rounded-xl hover:bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--text-secondary))] transition-colors">
                            <Phone size={18} />
                        </button>
                        <button className="size-10 rounded-xl hover:bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--text-secondary))] transition-colors">
                            <Video size={18} />
                        </button>
                        <button className="size-10 rounded-xl hover:bg-[hsl(var(--surface-2))] flex items-center justify-center text-[hsl(var(--text-secondary))] transition-colors">
                            <Info size={18} />
                        </button>
                    </div>
                </header>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-10 space-y-8 flex flex-col">
                    <div className="self-center py-2 px-6 rounded-full bg-[hsl(var(--surface-3))] text-[9px] font-black uppercase tracking-[0.2em] text-[hsl(var(--text-secondary))] mb-4 border border-[hsl(var(--border))]">
                        Hoy
                    </div>

                    <div className="flex flex-col gap-2 max-w-[70%] self-start">
                        <div className="bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-5 rounded-[2rem] rounded-tl-none shadow-sm">
                            <p className="text-[hsl(var(--text-primary))] text-sm leading-relaxed font-medium">Bencidiones amados hermanos, les recordamos la reunión de esta noche a las 7:30 PM por Zoom.</p>
                        </div>
                        <span className="text-[9px] font-bold text-[hsl(var(--text-secondary)/0.5)] uppercase ml-2">9:00 AM</span>
                    </div>

                    <div className="flex flex-col gap-2 max-w-[70%] self-end">
                        <div className="bg-[hsl(var(--primary))] text-white p-5 rounded-[2rem] rounded-tr-none shadow-xl shadow-primary/10">
                            <p className="text-sm leading-relaxed font-medium">¡Gracias! Estaremos presentes para interceder juntos.</p>
                        </div>
                        <span className="text-[9px] font-bold text-[hsl(var(--text-secondary)/0.5)] uppercase mr-2 self-end">9:45 AM</span>
                    </div>
                </div>

                {/* Input Area */}
                <footer className="p-6 border-t border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
                    <div className="bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] rounded-[2rem] p-2 flex items-center gap-2 pr-4 focus-within:border-[hsl(var(--primary)/0.5)] transition-all">
                        <button className="size-10 rounded-full hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))] transition-colors">
                            <Smile size={20} />
                        </button>
                        <button className="size-10 rounded-full hover:bg-[hsl(var(--surface-3))] flex items-center justify-center text-[hsl(var(--text-secondary))] transition-colors">
                            <Paperclip size={20} />
                        </button>
                        <input 
                            placeholder="Escribe un mensaje..."
                            className="flex-1 bg-transparent border-none outline-none text-sm font-medium h-12 px-2 text-[hsl(var(--text-primary))]"
                        />
                        <button className="size-10 rounded-2xl bg-[hsl(var(--primary))] text-white flex items-center justify-center shadow-lg shadow-primary/20 hover:opacity-90 transition-all">
                            <Send size={18} strokeWidth={2.5} />
                        </button>
                    </div>
                </footer>
            </div>
        </div>
    );
}
