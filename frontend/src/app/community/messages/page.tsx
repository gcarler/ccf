'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  CheckCheck,
  ChevronLeft,
  MessageSquare,
  Search,
  Send,
  Users,
  Plus,
  UserPlus
} from 'lucide-react';
import clsx from 'clsx';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import type { ViewType } from '@/components/ViewSwitcher';

type Member = { id: number; first_name: string; last_name: string };
type CommunicationLog = {
  id: number;
  member_id: number;
  channel: string;
  content: string;
  outcome: string;
  created_at: string;
};
type Chat = {
  id: number;
  name: string;
  lastMessage: string;
  time: string;
  channel: string;
};

export default function MessagingPage() {
  const { token } = useAuth();
  const [logs, setLogs] = useState<CommunicationLog[]>([]);
  const [members, setMembers] = useState<Member[]>([]);
  const [activeChat, setActiveChat] = useState<Chat | null>(null);
  const [inputText, setInputText] = useState('');
  const [search, setSearch] = useState('');
  const [viewType, setViewType] = useState<ViewType>('list');
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // New Message State
  const [isCreatingNew, setIsCreatingNew] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      apiFetch<CommunicationLog[]>('/messaging/history', {
        token,
        cache: 'no-store',
      }).catch(() => []),
      apiFetch<Member[]>('/crm/members/', { token, cache: 'no-store' }).catch(
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
          `${member.first_name} ${member.last_name}`,
        ])
      ),
    [members]
  );
  
  const chats = useMemo<Chat[]>(() => {
    const latest = new Map<number, CommunicationLog>();
    for (const log of logs) {
      const current = latest.get(log.member_id);
      if (!current || current.created_at < log.created_at)
        latest.set(log.member_id, log);
    }
    return Array.from(latest.values())
      .sort((a, b) => b.created_at.localeCompare(a.created_at))
      .map(log => ({
        id: log.member_id,
        name: memberNames.get(log.member_id) || `Miembro ${log.member_id}`,
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
  
  // Members filtering for New Message view
  const visibleMembers = members.filter(
    member =>
        `${member.first_name} ${member.last_name}`.toLowerCase().includes(search.toLowerCase())
  );

  const messages = logs
    .filter(log => log.member_id === activeChat?.id)
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
        name: `${member.first_name} ${member.last_name}`,
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
        member_id: activeChat.id,
        channel: activeChat.channel || 'internal',
        content: inputText.trim(),
      },
    });
    setLogs(prev => [...prev, created]);
    setInputText('');
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-white font-display dark:bg-[#1e1f21]">
      <WorkspaceToolbar
        breadcrumbs={[
          { label: 'Comunidad', icon: Users },
          { label: 'Mensajería Interna', icon: MessageSquare },
        ]}
        viewType={viewType}
        setViewType={setViewType}
        availableViews={['list', 'grid', 'table', 'board', 'kanban']}
      />

      {viewType === 'table' && (
        <main className="flex-1 overflow-y-auto p-8">
          <div className="overflow-hidden rounded-3xl border border-slate-200 dark:border-white/10">
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-[10px] font-black uppercase tracking-widest text-slate-400 dark:bg-white/5">
                <tr>
                  <th className="px-6 py-4">Conversación</th>
                  <th className="px-6 py-4">Último mensaje</th>
                  <th className="px-6 py-4">Hora</th>
                  <th className="px-6 py-4">Canal</th>
                </tr>
              </thead>
              <tbody>
                {visibleChats.map(chat => (
                  <tr
                    key={chat.id}
                    onClick={() => setActiveChat(chat)}
                    className="cursor-pointer border-t border-slate-100 hover:bg-slate-50 dark:border-white/5 dark:hover:bg-white/5"
                  >
                    <td className="px-6 py-4 font-bold">{chat.name}</td>
                    <td className="px-6 py-4 text-slate-500">
                      {chat.lastMessage}
                    </td>
                    <td className="px-6 py-4 text-slate-500">{chat.time}</td>
                    <td className="px-6 py-4 text-slate-500">{chat.channel}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </main>
      )}

      {(viewType === 'grid' ||
        viewType === 'board' ||
        viewType === 'kanban') && (
        <main className="flex-1 overflow-y-auto p-8">
          <div
            className={clsx(
              'grid gap-5',
              viewType === 'grid' ? 'md:grid-cols-3' : 'md:grid-cols-2'
            )}
          >
            {visibleChats.map(chat => (
              <button
                key={chat.id}
                onClick={() => setActiveChat(chat)}
                className="rounded-3xl border border-slate-200 bg-white p-6 text-left hover:border-blue-300 dark:border-white/10 dark:bg-white/5 shadow-sm transition-all"
              >
                <h3 className="font-black text-slate-800 dark:text-white">{chat.name}</h3>
                <p className="mt-2 text-sm text-slate-500">
                  {chat.lastMessage}
                </p>
                <p className="mt-5 text-[10px] font-black uppercase tracking-widest text-slate-400">
                  {chat.time}
                </p>
              </button>
            ))}
          </div>
        </main>
      )}

      {viewType === 'list' && (
        <div className="flex flex-1 overflow-hidden">
          <aside
            className={clsx(
              'flex w-full flex-col border-r border-slate-100 bg-white dark:bg-[#1a1b1e] transition-all md:w-96 dark:border-white/5',
              activeChat && 'hidden md:flex'
            )}
          >
            <div className="p-6 pb-4">
              <div className="flex items-center gap-3 mb-4">
                 <h2 className="text-xl font-black tracking-tight text-slate-800 dark:text-white flex-1">
                   {isCreatingNew ? 'Nuevo Mensaje' : 'Mensajes'}
                 </h2>
                 <button
                   onClick={() => {
                       setIsCreatingNew(!isCreatingNew);
                       setSearch('');
                   }}
                   className={clsx(
                       "flex size-9 items-center justify-center rounded-xl transition-all shadow-sm",
                       isCreatingNew 
                         ? "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/10 dark:text-slate-300" 
                         : "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-blue-500/30"
                   )}
                   title={isCreatingNew ? 'Cancelar' : 'Nueva conversación'}
                 >
                   {isCreatingNew ? <ChevronLeft size={18} /> : <Plus size={18} />}
                 </button>
              </div>
              <div className="relative">
                <input
                  value={search}
                  onChange={event => setSearch(event.target.value)}
                  placeholder={isCreatingNew ? "Buscar miembro..." : "Buscar conversaciones..."}
                  className="w-full rounded-xl bg-slate-50 border border-slate-200 px-10 py-2.5 text-[13px] font-semibold text-slate-800 dark:text-white outline-none focus:ring-2 focus:ring-blue-500/20 dark:bg-white/5 dark:border-white/10 transition-all"
                />
                <Search
                  size={16}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400"
                />
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto px-3 pb-6 space-y-1 scrollbar-thin">
              <AnimatePresence mode="wait">
                  {isCreatingNew ? (
                      <motion.div
                        key="directory"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -10 }}
                        className="space-y-1"
                      >
                          <p className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400">Directorio ({visibleMembers.length})</p>
                          {visibleMembers.map(member => (
                            <button
                              key={member.id}
                              onClick={() => handleStartNewChat(member)}
                              className="flex w-full items-center gap-3 rounded-2xl p-3 text-left hover:bg-blue-50 dark:hover:bg-blue-500/10 transition-colors group"
                            >
                              <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-slate-100 text-[11px] font-black uppercase text-slate-600 dark:bg-white/10 dark:text-white group-hover:bg-blue-200 group-hover:text-blue-700 transition-colors">
                                {member.first_name.charAt(0)}{member.last_name.charAt(0)}
                              </div>
                              <div className="min-w-0 flex-1">
                                <h4 className="truncate text-[13px] font-bold text-slate-800 dark:text-slate-100">
                                  {member.first_name} {member.last_name}
                                </h4>
                                <p className="truncate text-[11px] text-slate-400 font-medium">Click para iniciar chat</p>
                              </div>
                              <UserPlus size={16} className="text-slate-300 group-hover:text-blue-500 transition-colors" />
                            </button>
                          ))}
                          {visibleMembers.length === 0 && (
                              <div className="p-8 text-center">
                                  <p className="text-sm font-bold text-slate-500">Ningún miembro encontrado</p>
                              </div>
                          )}
                      </motion.div>
                  ) : (
                      <motion.div
                        key="chats"
                        initial={{ opacity: 0, x: 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 10 }}
                        className="space-y-1"
                      >
                          <p className="px-3 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400">Recientes</p>
                          {visibleChats.map(chat => (
                            <button
                              key={chat.id}
                              onClick={() => setActiveChat(chat)}
                              className={clsx(
                                'flex w-full items-center gap-3 rounded-2xl p-3 text-left transition-colors group',
                                activeChat?.id === chat.id
                                  ? 'bg-blue-50 dark:bg-blue-600/10'
                                  : 'hover:bg-slate-50 dark:hover:bg-white/5'
                              )}
                            >
                              <div className={clsx(
                                "flex size-10 shrink-0 items-center justify-center rounded-xl text-[11px] font-black uppercase transition-colors",
                                activeChat?.id === chat.id
                                    ? "bg-blue-600 text-white shadow-lg shadow-blue-500/20"
                                    : "bg-slate-900 text-white dark:bg-white/10 group-hover:bg-slate-800"
                              )}>
                                {chat.name.charAt(0)}
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="mb-0.5 flex items-baseline justify-between">
                                  <h4 className={clsx(
                                      "truncate text-[13px] font-bold",
                                      activeChat?.id === chat.id ? "text-blue-700 dark:text-blue-400" : "text-slate-800 dark:text-slate-100"
                                  )}>
                                    {chat.name}
                                  </h4>
                                  <span className="text-[9px] font-bold uppercase text-slate-400">
                                    {chat.time}
                                  </span>
                                </div>
                                <p className={clsx(
                                    "truncate text-[12px]",
                                    activeChat?.id === chat.id ? "text-blue-600/80 dark:text-blue-300" : "text-slate-500"
                                )}>
                                  {chat.lastMessage}
                                </p>
                              </div>
                            </button>
                          ))}
                          {visibleChats.length === 0 && (
                              <div className="p-8 text-center space-y-3">
                                  <div className="mx-auto size-12 bg-slate-100 dark:bg-white/5 rounded-2xl flex items-center justify-center">
                                      <MessageSquare size={20} className="text-slate-400" />
                                  </div>
                                  <div>
                                    <p className="text-sm font-bold text-slate-600 dark:text-slate-300">Bandeja vacía</p>
                                    <p className="text-[11px] text-slate-400 mt-1">Haz clic en + para iniciar un chat.</p>
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
              'relative flex flex-1 flex-col bg-slate-50/50 dark:bg-[#151618]',
              !activeChat &&
                'hidden items-center justify-center p-20 text-center md:flex'
            )}
          >
            {activeChat ? (
              <>
                <header className="flex items-center gap-4 border-b border-slate-200/60 bg-white/80 p-5 dark:border-white/5 dark:bg-white/5 backdrop-blur-md sticky top-0 z-10 shadow-sm">
                  <button
                    onClick={() => setActiveChat(null)}
                    className="p-2 text-slate-400 hover:text-slate-700 dark:hover:text-white transition-colors md:hidden bg-slate-50 dark:bg-white/5 rounded-xl"
                  >
                    <ChevronLeft size={20} />
                  </button>
                  <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 text-[12px] font-black uppercase text-white shadow-md">
                    {activeChat.name.charAt(0)}
                  </div>
                  <div>
                    <h3 className="text-[14px] font-black text-slate-800 dark:text-white">
                      {activeChat.name}
                    </h3>
                    <p className="text-[10px] font-bold uppercase tracking-widest text-blue-500">
                      Canal: {activeChat.channel}
                    </p>
                  </div>
                </header>
                
                <div
                  ref={scrollRef}
                  className="flex-1 space-y-6 overflow-y-auto p-6 lg:p-10"
                >
                  {messages.length === 0 ? (
                      <div className="flex flex-col items-center justify-center h-full text-slate-400 space-y-3 opacity-60">
                          <MessageSquare size={32} />
                          <p className="text-sm font-bold">Inicia la conversación con {activeChat.name}</p>
                      </div>
                  ) : (
                      messages.map(message => (
                        <motion.div
                          key={message.id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="ml-auto flex max-w-[85%] md:max-w-[70%] flex-col items-end"
                        >
                          <div className="rounded-3xl rounded-br-sm bg-blue-600 px-5 py-3 text-[14px] leading-relaxed font-medium text-white shadow-md shadow-blue-500/10">
                            {message.content}
                          </div>
                          <div className="mt-1.5 flex items-center gap-1.5 px-2">
                            <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400">
                              {new Date(message.created_at).toLocaleString('es-CO')}
                            </span>
                            <CheckCheck size={12} className="text-blue-500" />
                          </div>
                        </motion.div>
                      ))
                  )}
                </div>
                
                <footer className="border-t border-slate-200/60 bg-white/90 p-4 dark:border-white/5 dark:bg-white/5 backdrop-blur-md">
                  <div className="mx-auto flex w-full max-w-4xl items-center gap-3 rounded-2xl bg-slate-50 border border-slate-200/80 p-1.5 pl-5 pr-1.5 dark:border-white/10 dark:bg-black/20 focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-300 transition-all shadow-sm">
                    <input
                      value={inputText}
                      onChange={event => setInputText(event.target.value)}
                      onKeyDown={event =>
                        event.key === 'Enter' && sendMessage()
                      }
                      placeholder="Escribe un mensaje..."
                      className="flex-1 bg-transparent py-2.5 text-[14px] font-medium outline-none dark:text-white"
                    />
                    <button
                      onClick={sendMessage}
                      disabled={!inputText.trim()}
                      className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md transition-all hover:bg-blue-700 active:scale-95 disabled:opacity-50 disabled:active:scale-100 disabled:hover:bg-blue-600"
                    >
                      <Send size={16} fill="currentColor" className="ml-1" />
                    </button>
                  </div>
                </footer>
              </>
            ) : (
              <div className="space-y-6 flex flex-col items-center">
                <div className="mx-auto flex size-24 items-center justify-center rounded-[2rem] bg-blue-50 text-blue-600 dark:bg-blue-600/10 shadow-inner">
                  <MessageSquare size={40} strokeWidth={1.5} />
                </div>
                <div className="space-y-2">
                    <h3 className="text-2xl font-black text-slate-800 dark:text-white">
                      Centro de Mensajes
                    </h3>
                    <p className="mx-auto max-w-sm text-[12px] font-medium text-slate-500 leading-relaxed">
                      Selecciona una conversación del panel lateral o inicia un nuevo chat para comunicarte con la comunidad.
                    </p>
                </div>
                <button 
                  onClick={() => setIsCreatingNew(true)}
                  className="mt-4 px-6 py-3 bg-blue-600 text-white text-[12px] font-black uppercase tracking-widest rounded-xl hover:bg-blue-700 hover:shadow-lg hover:shadow-blue-500/20 active:scale-95 transition-all flex items-center gap-2"
                >
                    <Plus size={16} /> Iniciar nueva conversación
                </button>
              </div>
            )}
          </main>
        </div>
      )}
    </div>
  );
}
