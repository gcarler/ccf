"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiUrl } from '@/lib/api';
import { Search, UserPlus, MoreVertical, Edit2, Loader2, Users } from 'lucide-react';
import Link from 'next/link';

interface Member {
    id: number;
    username: string;
    email: string;
    role: string;
}

export default function AdminMembersPage() {
    const { token } = useAuth();
    const [members, setMembers] = useState<Member[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [filterRole, setFilterRole] = useState('all');

    useEffect(() => {
        // Fetch all users using a generic endpoint (adjust if you have a specific members endpoint)
        // For MVP, we might just mock this or use an existing endpoint if one exists.
        // Assuming we need to add an endpoint or use a mock for now to demonstrate UI.
        
        // Mock data for UI demonstration since we don't have a /users/ list endpoint yet
        setMembers([
            { id: 1, username: 'Juan Pérez', email: 'juan@example.com', role: 'estudiante' },
            { id: 2, username: 'María García', email: 'maria@example.com', role: 'coordinador' },
            { id: 3, username: 'Carlos Rodríguez', email: 'carlos@example.com', role: 'estudiante' },
            { id: 4, username: 'Ana Martínez', email: 'ana@example.com', role: 'admin' },
            { id: 5, username: 'Roberto Sánchez', email: 'roberto@example.com', role: 'docente' },
        ]);
        setLoading(false);
    }, [token]);

    const filteredMembers = members.filter(member => {
        const matchesSearch = member.username.toLowerCase().includes(searchTerm.toLowerCase()) || member.email.toLowerCase().includes(searchTerm.toLowerCase());
        const matchesRole = filterRole === 'all' || member.role === filterRole;
        return matchesSearch && matchesRole;
    });

    const getRoleBadge = (role: string) => {
        switch(role) {
            case 'admin': return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest bg-amber-500/10 text-amber-500">Administrador</span>;
            case 'coordinador': return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest bg-purple-500/10 text-purple-500">Coordinador</span>;
            case 'docente': return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest bg-emerald-500/10 text-emerald-500">Docente</span>;
            default: return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-widest bg-primary/10 text-primary">Estudiante</span>;
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in duration-500 max-w-5xl mx-auto">
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
                <div>
                    <h1 className="flex items-center gap-3 text-3xl font-black text-slate-900 dark:text-white tracking-tight">
                        <Users className="text-primary" size={32} /> Gestión de Usuarios
                    </h1>
                    <p className="text-slate-500 font-medium mt-1">Administra los roles y accesos de los miembros.</p>
                </div>
                <button className="flex items-center gap-2 bg-primary text-white px-6 py-3.5 rounded-2xl shadow-lg shadow-primary/40 active:scale-95 transition-all hover:bg-primary/90">
                    <UserPlus size={18} />
                    <span className="font-bold text-xs uppercase tracking-widest">Añadir Usuario</span>
                </button>
            </header>

            <div className="bg-white dark:bg-slate-900/40 rounded-[2.5rem] border border-slate-200 dark:border-white/5 shadow-xl overflow-hidden">
                <div className="p-6 border-b border-slate-200 dark:border-white/5 flex flex-col md:flex-row gap-4 justify-between items-center bg-slate-50/50 dark:bg-transparent">
                    {/* Search Bar */}
                    <div className="relative w-full md:max-w-md">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input 
                            type="text" 
                            placeholder="Buscar por nombre o email..." 
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-12 pr-4 py-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-xl text-sm focus:ring-2 focus:ring-primary transition-all font-medium shadow-sm"
                        />
                    </div>

                    {/* Filters */}
                    <div className="flex items-center gap-2 overflow-x-auto w-full md:w-auto pb-2 md:pb-0 hide-scrollbar">
                        {['all', 'estudiante', 'docente', 'admin'].map((role) => (
                            <button 
                                key={role}
                                onClick={() => setFilterRole(role)}
                                className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-widest whitespace-nowrap transition-all ${filterRole === role ? 'bg-primary text-white shadow-md shadow-primary/20' : 'bg-slate-100 dark:bg-white/5 text-slate-500 hover:bg-slate-200 dark:hover:bg-white/10'}`}
                            >
                                {role === 'all' ? 'Todos' : role}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="divide-y divide-slate-100 dark:divide-white/5">
                    {loading ? (
                        <div className="p-12 flex justify-center"><Loader2 className="animate-spin text-primary" size={32} /></div>
                    ) : filteredMembers.length > 0 ? (
                        filteredMembers.map(member => (
                            <div key={member.id} className="flex items-center justify-between p-6 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                                <div className="flex items-center gap-4">
                                    <div className="h-14 w-14 rounded-2xl overflow-hidden bg-primary/10 flex items-center justify-center border border-primary/20 group-hover:scale-105 transition-transform">
                                        <img 
                                            src={`https://ui-avatars.com/api/?name=${member.username}&background=random&color=fff`} 
                                            alt={member.username} 
                                            className="w-full h-full object-cover"
                                        />
                                    </div>
                                    <div>
                                        <p className="font-black text-slate-900 dark:text-white text-base leading-none mb-2">{member.username}</p>
                                        <div className="flex items-center gap-3">
                                            <p className="text-xs text-slate-500 font-medium">{member.email}</p>
                                            {getRoleBadge(member.role)}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    <button className="p-2.5 bg-white dark:bg-slate-800 text-slate-400 hover:text-primary rounded-xl border border-slate-200 dark:border-white/10 shadow-sm transition-all active:scale-95">
                                        <Edit2 size={16} />
                                    </button>
                                    <button className="p-2.5 bg-white dark:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-white rounded-xl border border-slate-200 dark:border-white/10 shadow-sm transition-all active:scale-95">
                                        <MoreVertical size={16} />
                                    </button>
                                </div>
                            </div>
                        ))
                    ) : (
                        <div className="p-16 text-center text-slate-500 font-medium italic">
                            No se encontraron usuarios que coincidan con la búsqueda.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
