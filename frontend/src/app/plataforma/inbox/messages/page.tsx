"use client";

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCheck,
  ChevronLeft,
  MessageSquare,
  Search,
  Send,
  Plus,
  UserPlus
} from 'lucide-react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';

type Member = { id: string; nombre_completo?: string; first_name?: string; last_name?: string };
type CommunicationLog = {
  id: number;
  persona_id: string;
  channel: string;
  content: string;
  outcome: string;
  created_at: string;
};
type Chat = {
  id: string;
  name: string;
  lastMessage: string;
  time: string;
  channel: string;
};

export default function InboxMessagesPage() {
  const { token } = useAuth();
  const [logs, setLogs] = useState<CommunicationLog[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [activeChat, setActiveChat] = useState<Chat | null>(null);
  const [inputText, setInputText] = useState('');
  const [search, setSearch] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const [isCreatingNew, setIsCreatingNew] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch<CommunicationLog[]>('/messaging/history', {
        token,
        cache: 'no-store',
      }).catch(() => []),
      apiFetch<Member[]>('/crm/personas/', { token, cache: 'no-store' }).catch(
        () => []
      ),
    ]).then(([history, people]) => {
      setLogs(Array.isArray(history) ? history : []);
      setMembers(Array.isArray(people) ? people : []);
    });
  }, [token]);

  const memberNames = useMemo(
    () =>
      new Map(
        members.map(member => [
          member.id,
          member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim(),
        ])
      ),
    [members]
  );
  
  const chats = useMemo<Chat[]>(() => {
    const latest = new Map<string, CommunicationLog>();
    for (const log of logs) {
      const current = latest.get(log.persona_id);
      if (!current || current.created_at < log.created_at)
        latest.set(log.persona_id, log);
    }
    return Array.from(latest.values())
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map(log => ({
        id: log.persona_id,
        name: memberNames.get(log.persona_id) || `Persona ${log.persona_id}`,
        lastMessage: log.content,
        time: new Date(log.created_at).toLocaleString('es-CO'),
        channel: log.channel,
      }));
  }, [logs, memberNames]);
  
  const visibleChats = chats.filter(
    chat =>
      chat.name.toLowerCase().includes(search.toLowerCase()) ||
      chat.lastMessage.toLowerCase().includes(search.toLowerCase())
  );
  
  const visibleMembers = members.filter(
    member =>
        (member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim()).toLowerCase().includes(search.toLowerCase())
  );

  const messages = logs
    .filter(log => log.persona_id === activeChat?.id)
    .sort((a, b) => a.created_at.localeCompare(b.created_at));

  useEffect(() => {
    if (scrollRef.current)
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleStartNewChat = (member: Member) => {
    const existingChat = chats.find(c => c.id === member.id);
    if (existingChat) {
      setActiveChat(existingChat);
    } else {
      setActiveChat({
        id: member.id,
        name: member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim(),
        lastMessage: '',
        time: new Date().toLocaleString('es-CO'),
        channel: 'internal'
      });
    }
    setIsCreatingNew(false);
    setSearch('');
  };

  const sendMessage = async () => {
    if (!token || !activeChat || !inputText.trim()) return;
    const created = await apiFetch<CommunicationLog>('/messaging/send', {
      method: 'POST',
      token,
      body: {
        persona_id: activeChat.id,
        channel: activeChat.channel || 'internal',
        content: inputText.trim(),
      },
    });
    setLogs(prev => [...prev, created]);
    setInputText('');
  };

  return (
    <div className="flex flex-1 overflow-hidden h-full bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21]">
        <aside
        className={clsx(
            'flex w-full flex-col border-r border-slate-100 dark:border-white/5 transition-all md:w-80 shrink-0 bg-slate-50/50 dark:bg-black/10',
            activeChat && 'hidden md:flex'
        )}
        >
        <div className="p-3 border-b border-slate-100 dark:border-white/5">
            <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-bold tracking-tight text-slate-800 dark:text-white uppercase">
                {isCreatingNew ? 'Nuevo Chat' : 'Conversaciones'}
                </h2>
                <button
                onClick={() => {
                    setIsCreatingNew(!isCreatingNew);
                    setSearch('');
                }}
                className={clsx(
                    "flex size-7 items-center justify-center rounded-lg transition-all shadow-sm",
                    isCreatingNew 
                        ? "bg-slate-200 text-slate-600 hover:bg-slate-300 dark:bg-white/10 dark:text-slate-300" 
                        : "bg-[hsl(var(--primary))] text-white hover:bg-[hsl(var(--primary))] hover:shadow-blue-500/30"
                )}
                title={isCreatingNew ? 'Cancelar' : 'Nueva conversación'}
                >
                {isCreatingNew ? <ChevronLeft size={14} /> : <Plus size={14} />}
                </button>
            </div>
            <div className="relative">
            <input
                value={search}
                onChange={event => setSearch(event.target.value)}
                placeholder={isCreatingNew ? "Buscar persona..." : "Buscar chat..."}
                className="w-full rounded-lg bg-[hsl(var(--bg-primary))] border border-slate-200 pl-8 pr-3 py-1.5 text-[11px] font-semibold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20 dark:bg-white/5 dark:border-white/10 transition-all shadow-sm"
            />
            <Search
                size={12}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
            />
            </div>
        </div>
        
        <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1 scrollbar-thin">
            <AnimatePresence mode="wait">
                {isCreatingNew ? (
                    <motion.div
                    key="directory"
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -5 }}
                    className="space-y-1"
                    >
                        <p className="px-2 py-1 text-[9px] font-semibold uppercase tracking-wide text-slate-400">Contactos ({visibleMembers.length})</p>
                        {visibleMembers.map(member => (
                        <button
                            key={member.id}
                            onClick={() => handleStartNewChat(member)}
                            className="flex w-full items-center gap-3 rounded-md p-2 text-left hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors group"
                        >
                            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-[10px] font-semibold uppercase text-slate-600 dark:bg-white/10 dark:text-white group-hover:bg-blue-200 group-hover:text-[hsl(var(--primary))] transition-colors">
                            {member.nombre_completo?.split(/\s+/).filter(Boolean)[0]?.[0] ?? member.first_name?.charAt(0) ?? ''}{member.nombre_completo?.split(/\s+/).filter(Boolean).slice(-1)[0]?.[0] ?? member.last_name?.charAt(0) ?? ''}
                            </div>
                            <div className="min-w-0 flex-1">
                            <h4 className="truncate font-semibold text-slate-800 dark:text-slate-100">
                                {member.nombre_completo || `${member.first_name ?? ''} ${member.last_name ?? ''}`.trim()}
                            </h4>
                            </div>
                            <UserPlus size={14} className="text-slate-300 group-hover:text-[hsl(var(--primary))] transition-colors" />
                        </button>
                        ))}
                        {visibleMembers.length === 0 && (
                            <div className="p-4 text-center">
                                <p className="text-xs font-bold text-slate-500">Ningún persona encontrado</p>
                            </div>
                        )}
                    </motion.div>
                ) : (
                    <motion.div
                    key="chats"
                    initial={{ opacity: 0, x: 5 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 5 }}
                    className="space-y-1"
                    >
                        <p className="px-2 py-1 text-[9px] font-semibold uppercase tracking-wide text-slate-400">Recientes</p>
                        {visibleChats.map(chat => (
                        <button
                            key={chat.id}
                            onClick={() => setActiveChat(chat)}
                            className={clsx(
                            'flex w-full items-center gap-3 rounded-md p-2 text-left transition-colors group',
                            activeChat?.id === chat.id
                                ? 'bg-blue-50 dark:bg-blue-600/10'
                                : 'hover:bg-slate-100 dark:hover:bg-white/5'
                            )}
                        >
                            <div className={clsx(
                            "flex size-8 shrink-0 items-center justify-center rounded-lg text-[10px] font-semibold uppercase transition-colors shadow-sm",
                            activeChat?.id === chat.id
                                ? "bg-[hsl(var(--primary))] text-white shadow-blue-500/20"
                                : "bg-slate-800 text-white dark:bg-white/10 group-hover:bg-slate-700"
                            )}>
                            {chat.name.charAt(0)}
                            </div>
                            <div className="min-w-0 flex-1">
                            <div className="mb-0.5 flex items-baseline justify-between">
                                <h4 className={clsx(
                                    "truncate font-semibold",
                                    activeChat?.id === chat.id ? "text-[hsl(var(--primary))] dark:text-[hsl(var(--primary))]" : "text-slate-800 dark:text-slate-100"
                                )}>
                                {chat.name}
                                </h4>
                                <span className="text-[8px] font-bold uppercase text-slate-400 shrink-0 ml-2">
                                {chat.time.split(',')[0]}
                                </span>
                            </div>
                            <p className={clsx(
                                "truncate text-[10px] font-medium",
                                activeChat?.id === chat.id ? "text-blue-600/80 dark:text-blue-300" : "text-slate-500"
                            )}>
                                {chat.lastMessage}
                            </p>
                            </div>
                        </button>
                        ))}
                        {visibleChats.length === 0 && (
                            <div className="p-4 text-center space-y-2 mt-4">
                                <div className="mx-auto size-8 bg-slate-200 dark:bg-white/5 rounded-md flex items-center justify-center">
                                    <MessageSquare size={14} className="text-slate-400" />
                                </div>
                                <div>
                                <p className="text-xs font-bold text-slate-600 dark:text-slate-300">Bandeja vacía</p>
                                </div>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
        </aside>

        <main
        className={clsx(
            'relative flex flex-1 flex-col bg-[hsl(var(--bg-primary))] dark:bg-[#1E1F21]',
            !activeChat && 'hidden items-center justify-center text-center md:flex'
        )}
        >
        {activeChat ? (
            <>
            <header className="flex items-center gap-3 border-b border-slate-100 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/5 dark:bg-[#1E1F21] sticky top-0 z-10 shrink-0">
                <button
                onClick={() => setActiveChat(null)}
                className="p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors md:hidden bg-slate-100 dark:bg-white/5 rounded-lg"
                >
                <ChevronLeft size={16} />
                </button>
                <div className="flex size-7 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-sky-600 text-[10px] font-semibold uppercase text-white shadow-sm">
                {activeChat.name.charAt(0)}
                </div>
                <div>
                <h3 className="text-xs font-semibold text-slate-800 dark:text-white leading-tight">
                    {activeChat.name}
                </h3>
                <p className="text-[9px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] leading-tight">
                    {activeChat.channel}
                </p>
                </div>
            </header>
            
            <div
                ref={scrollRef}
                className="flex-1 space-y-4 overflow-y-auto p-4 bg-slate-50/30 dark:bg-black/5 scrollbar-thin"
            >
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-2 opacity-60">
                        <MessageSquare size={24} />
                        <p className="text-xs font-bold">Inicia la conversación</p>
                    </div>
                ) : (
                    messages.map(message => (
                    <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="ml-auto flex max-w-[85%] md:max-w-[70%] flex-col items-end"
                    >
                        <div className="rounded-md rounded-br-sm bg-[hsl(var(--primary))] px-3 py-2 text-[11px] leading-relaxed font-medium text-white shadow-sm shadow-blue-500/10">
                        {message.content}
                        </div>
                        <div className="mt-1 flex items-center gap-1 px-1">
                        <span className="text-[8px] font-bold uppercase tracking-wider text-slate-400">
                            {new Date(message.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </span>
                        <CheckCheck size={10} className="text-[hsl(var(--primary))]" />
                        </div>
                    </motion.div>
                    ))
                )}
            </div>
            
            <footer className="border-t border-slate-100 bg-[hsl(var(--bg-primary))] p-3 dark:border-white/5 dark:bg-[#1E1F21] shrink-0">
                <div className="mx-auto flex w-full items-center gap-2 rounded-md bg-slate-50 border border-slate-200/80 p-1 pl-3 pr-1 dark:border-white/10 dark:bg-white/5 focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-300 transition-all shadow-sm">
                <input
                    value={inputText}
                    onChange={event => setInputText(event.target.value)}
                    onKeyDown={event =>
                    event.key === 'Enter' && sendMessage()
                    }
                    placeholder="Escribe un mensaje..."
                    className="flex-1 bg-transparent py-1.5 text-xs font-medium outline-none dark:text-white"
                />
                <button
                    onClick={sendMessage}
                    disabled={!inputText.trim()}
                    className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-[hsl(var(--primary))] text-white shadow-sm transition-all hover:bg-[hsl(var(--primary))] active:scale-95 disabled:opacity-50 disabled:active:scale-100 disabled:hover:bg-[hsl(var(--primary))]"
                >
                    <Send size={12} fill="currentColor" className="ml-0.5" />
                </button>
                </div>
            </footer>
            </>
        ) : (
            <div className="space-y-3 flex flex-col items-center">
            <div className="mx-auto flex size-8 items-center justify-center rounded-lg bg-blue-50 text-[hsl(var(--primary))] dark:bg-blue-600/10 shadow-inner">
                <MessageSquare size={24} strokeWidth={2} />
            </div>
            <div className="space-y-1">
                <h3 className="text-sm font-semibold text-slate-800 dark:text-white">
                    Mis Mensajes
                </h3>
                <p className="mx-auto max-w-xs text-[10px] font-medium text-slate-500 leading-relaxed">
                    Selecciona un chat o inicia uno nuevo.
                </p>
            </div>
            <button 
                onClick={() => setIsCreatingNew(true)}
                className="mt-2 px-3 py-1.5 bg-[hsl(var(--primary))] text-white text-[10px] font-semibold uppercase tracking-wide rounded-lg hover:bg-[hsl(var(--primary))] hover:shadow-md hover:shadow-blue-500/20 active:scale-95 transition-all flex items-center gap-2"
            >
                <Plus size={12} /> Nuevo Chat
            </button>
            </div>
        )}
        </main>
    </div>
  );
}
