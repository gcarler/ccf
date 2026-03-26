'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
    Search,
    Filter,
    Plus,
    MoreVertical,
    Mail,
    Phone,
    Users as FamilyIcon,
    User,
    X as CloseIcon,
    Calendar,
    Check,
    History,
    GraduationCap,
    ShieldCheck,
    ExternalLink,
    Loader2,
    Users,
    Clock
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import ViewSwitcher, { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';

interface Member {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    family_id: number;
    role_in_family: string;
    status: string;
    user_id?: number | null;
}

interface Family {
    id: number;
    name: string;
}

const KANBAN_STAGES = [
    { id: 'Activo', label: 'Activo', color: 'emerald' },
    { id: 'Visitante', label: 'Visitante', color: 'blue' },
    { id: 'Consolidación', label: 'Consolidación', color: 'amber' },
    { id: 'Inactivo', label: 'Inactivo', color: 'slate' },
];

export default function MembersPage() {
    const { addToast } = useToast();
    const { token } = useAuth();
    const [activeTab, setActiveTab] = useState('members');
    const [viewType, setViewType] = useState<ViewType>(() => getStoredView('crm_members_view', 'table'));
    const [members, setMembers] = useState<Member[]>([]);
    const [families, setFamilies] = useState<Family[]>([]);
    const [loading, setLoading] = useState(true);

    // Modal State
    const [isRegModalOpen, setIsRegModalOpen] = useState(false);
    const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
    const [selectedMember, setSelectedMember] = useState<Member | null>(null);
    const [history, setHistory] = useState<any[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);

    // Academy Bridge State
    const [academyProfile, setAcademyProfile] = useState<any>(null);
    const [loadingAcademy, setLoadingAcademy] = useState(false);
    const [academyPassword, setAcademyPassword] = useState('CCF123**');
    const [isCreatingAccount, setIsCreatingAccount] = useState(false);

    // Messaging State
    const [newMessageContent, setNewMessageContent] = useState('');
    const [messageChannel, setMessageChannel] = useState('whatsapp');

    // Form State
    const [newMember, setNewMember] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        family_id: '',
        role_in_family: 'Miembro',
        birthday: ''
    });

    const [isFamilyRegModalOpen, setIsFamilyRegModalOpen] = useState(false);
    const [newFamily, setNewFamily] = useState({ name: '' });


    const heroWatchers = ['Comunidad', 'Optimus Brain'];

    const fetchData = useCallback(async () => {
        if (!token) {
            setMembers([]);
            setFamilies([]);
            setLoading(false);
            return;
        }
        setLoading(true);
        try {
            const [membersData, familiesData] = await Promise.all([
                apiFetch<Member[]>('/crm/members/', { token, cache: 'no-store' }),
                apiFetch<Family[]>('/crm/families/', { token, cache: 'no-store' })
            ]);
            setMembers(Array.isArray(membersData) ? membersData : []);
            setFamilies(Array.isArray(familiesData) ? familiesData : []);
        } catch (err) {
            console.error('Error loading members', err);
            addToast("Error al cargar datos", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newMember.first_name || !newMember.last_name || !newMember.family_id) {
            addToast("Por favor completa los campos obligatorios", "warning");
            return;
        }

        if (!token) {
            addToast("Sesión no válida", "error");
            return;
        }

        try {
            await apiFetch('/crm/members/', {
                method: 'POST',
                token,
                body: {
                    ...newMember,
                    family_id: parseInt(newMember.family_id),
                    birthday: newMember.birthday ? new Date(newMember.birthday).toISOString() : null
                }
            });

            addToast("Miembro registrado exitosamente", "success");
            setIsRegModalOpen(false);
            setNewMember({ first_name: '', last_name: '', email: '', phone: '', family_id: '', role_in_family: 'Miembro', birthday: '' });
            fetchData();
        } catch (err) {
            console.error('register member error', err);
            addToast("Error al registrar miembro", "error");
        }
    };

    const handleRegisterFamily = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newFamily.name) {
            addToast("Por favor ingresa el nombre de la familia", "warning");
            return;
        }

        if (!token) {
            addToast("Sesión no válida", "error");
            return;
        }

        try {
            await apiFetch('/crm/families/', {
                method: 'POST',
                token,
                body: newFamily
            });

            addToast("Familia registrada exitosamente", "success");
            setIsFamilyRegModalOpen(false);
            setNewFamily({ name: '' });
            fetchData();
        } catch (err) {
            console.error('register family error', err);
            addToast("Error al registrar familia", "error");
        }
    };

    const openHistory = async (member: Member) => {
        setSelectedMember(member);
        setIsHistoryModalOpen(true);
        setLoadingHistory(true);
        setHistory([]);
        setAcademyProfile(null);

        fetchAcademyProfile(member.id);

        try {
            if (!token) throw new Error('no-token');
            const data = await apiFetch(`/crm/members/${member.id}/communications`, {
                token,
                cache: 'no-store'
            });
            setHistory(Array.isArray(data) ? data : []);
        } catch (err) {
            addToast("Error al cargar historial", "error");
            setHistory([]);
        } finally {
            setLoadingHistory(false);
        }
    };

    const fetchAcademyProfile = async (memberId: number) => {
        if (!token) return;
        setLoadingAcademy(true);
        try {
            const data = await apiFetch(`/crm/members/${memberId}/academy-profile`, {
                token,
                cache: 'no-store'
            });
            setAcademyProfile(data);
        } catch (err) {
            console.error("Error fetching academy profile", err);
        } finally {
            setLoadingAcademy(false);
        }
    };

    const handleCreateAcademyAccount = async () => {
        if (!selectedMember) return;
        setIsCreatingAccount(true);
        if (!token) {
            addToast("Sesión no válida", "error");
            return;
        }

        try {
            const result = await apiFetch(`/crm/members/${selectedMember.id}/create-academy-account`, {
                method: 'POST',
                token,
                body: { password: academyPassword }
            });

            addToast("Cuenta de academia creada exitosamente", "success");
            fetchAcademyProfile(selectedMember.id);
            fetchData();
        } catch (err: any) {
            const detail = err?.detail?.detail;
            addToast(detail || "Error al crear cuenta", "error");
        } finally {
            setIsCreatingAccount(false);
        }
    };

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedMember || !newMessageContent) return;

        if (!token) {
            addToast("Sesión no válida", "error");
            return;
        }

        try {
            await apiFetch('/messaging/send', {
                method: 'POST',
                token,
                body: {
                    member_id: selectedMember.id,
                    channel: messageChannel,
                    content: newMessageContent
                }
            });

            addToast("Mensaje enviado exitosamente", "success");
            setNewMessageContent('');
            const logs = await apiFetch(`/crm/members/${selectedMember.id}/communications`, {
                token,
                cache: 'no-store'
            });
            setHistory(Array.isArray(logs) ? logs : []);
        } catch (err) {
            console.error('send message error', err);
            addToast("Error al enviar mensaje", "error");
        }
    };

    const getFamilyName = (id: number) => families.find(f => f.id === id)?.name || 'Sin Familia';

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Membresía', icon: Users }]}
            rightActions={
                activeTab === 'members'
                    ? (
                        <button
                            onClick={() => setIsRegModalOpen(true)}
                            className="flex items-center gap-2 bg-blue-600 px-5 py-2 rounded-2xl text-xs font-black text-white hover:bg-blue-700 transition-all shadow-lg shadow-blue-900/20 uppercase tracking-widest"
                        >
                            <Plus size={14} /> Registrar miembro
                        </button>
                    ) : (
                        <button
                            onClick={() => setIsFamilyRegModalOpen(true)}
                            className="flex items-center gap-2 bg-slate-900 px-5 py-2 rounded-2xl text-xs font-black text-white hover:bg-black transition-all shadow-lg uppercase tracking-widest"
                        >
                            <Plus size={14} /> Registrar familia
                        </button>
                    )
            }
        >
        <AdminHero
            eyebrow="Membresía"
            title="Gestión de membresía"
            description="Administra personas, familias y su avance pastoral desde un solo panel."
            tags={['Familias', 'Academia', 'IA']}
            watchers={heroWatchers}
            primaryAction={{ label: 'Registrar miembro', icon: Plus, onClick: () => setIsRegModalOpen(true) }}
            secondaryAction={{ label: 'Registrar familia', icon: Plus, onClick: () => setIsFamilyRegModalOpen(true) }}
        />
        <div className="space-y-8">

            {/* Tabs & Filters */}
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
                <div className="flex p-1 bg-slate-100 dark:bg-white/5 rounded-2xl w-full md:w-auto">
                    <button
                        onClick={() => setActiveTab('members')}
                        className={`px-6 py-2 rounded-xl text-sm font-bold transition-all ${activeTab === 'members' ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Miembros
                    </button>
                    <button
                        onClick={() => setActiveTab('families')}
                        className={`px-6 py-2 rounded-xl text-sm font-bold transition-all ${activeTab === 'families' ? 'bg-white dark:bg-slate-700 text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Familias
                    </button>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                    <div className="relative flex-1 md:w-72">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
                        <input
                            type="text"
                            placeholder="Buscar miembro..."
                            className="w-full pl-11 pr-4 py-2.5 rounded-xl border border-slate-100 dark:border-white/10 focus:outline-none focus:ring-2 focus:ring-blue-500/20 bg-white dark:bg-white/5 text-sm"
                        />
                    </div>
                    {activeTab === 'members' && (
                        <ViewSwitcher
                            viewType={viewType}
                            setViewType={setViewType}
                            availableViews={['table', 'list', 'grid', 'kanban']}
                            storageKey="crm_members_view"
                        />
                    )}
                    <button className="p-2.5 rounded-xl border border-slate-100 dark:border-white/10 bg-white dark:bg-white/5 text-slate-500 hover:bg-slate-50 transition-colors">
                        <Filter size={16} />
                    </button>
                </div>
            </div>

            {/* Members & Families Display */}
            <div className="bg-white dark:bg-[#1e1f21] rounded-[2rem] border border-slate-100 dark:border-white/5 overflow-hidden shadow-sm">
                {loading ? (
                    <div className="flex justify-center py-20">
                        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : activeTab === 'members' ? (
                    <>
                    {/* TABLE VIEW */}
                    {viewType === 'table' && (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-slate-100 dark:border-white/5 bg-slate-50/50 dark:bg-white/5">
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest">Miembro</th>
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest">Familia / Rol</th>
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest">Contacto</th>
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest text-center">Estado</th>
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest text-right">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                                {members.map((member) => (
                                    <tr key={member.id} className="hover:bg-slate-50/80 dark:hover:bg-white/5 transition-colors group">
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-4">
                                                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-100 to-indigo-50 flex items-center justify-center text-blue-600 font-bold border border-blue-50">
                                                    {member.first_name.charAt(0)}
                                                </div>
                                                <div>
                                                    <h4 className="font-bold text-slate-800 dark:text-slate-100">{member.first_name} {member.last_name}</h4>
                                                    <p className="text-[10px] uppercase font-black tracking-widest text-slate-400">#M{member.id.toString().padStart(4, '0')}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex flex-col">
                                                <span className="text-sm font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                                                    <FamilyIcon size={14} className="text-slate-400" /> {getFamilyName(member.family_id)}
                                                </span>
                                                <span className="text-xs text-slate-400 mt-0.5">{member.role_in_family}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex items-center gap-2 text-xs text-slate-500">
                                                    <Mail size={12} className="text-slate-300" /> {member.email || '—'}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-slate-500">
                                                    <Phone size={12} className="text-slate-300" /> {member.phone || '—'}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5 text-center">
                                            <span className="px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 text-[10px] font-black uppercase tracking-widest">
                                                {member.status || 'Activo'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-5 text-right">
                                            <div className="flex justify-end gap-2">
                                                <button onClick={() => openHistory(member)} className="p-2 rounded-lg text-slate-400 hover:bg-blue-50 hover:text-blue-600 transition-all" title="Ver Historial">
                                                    <History size={16} />
                                                </button>
                                                <button className="p-2 rounded-lg text-slate-300 hover:bg-slate-100 hover:text-slate-600 transition-colors">
                                                    <MoreVertical size={16} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                    )}

                    {/* LIST VIEW */}
                    {viewType === 'list' && (
                    <div className="divide-y divide-slate-100 dark:divide-white/5">
                        {members.map((member) => (
                            <div key={member.id} className="flex items-center gap-4 px-6 py-4 hover:bg-slate-50 dark:hover:bg-white/5 transition-colors group">
                                <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-blue-100 to-indigo-50 flex items-center justify-center text-blue-600 font-bold text-sm shrink-0">
                                    {member.first_name.charAt(0)}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-bold text-slate-800 dark:text-slate-100 text-sm truncate">{member.first_name} {member.last_name}</p>
                                    <p className="text-xs text-slate-400 truncate">{getFamilyName(member.family_id)} · {member.role_in_family}</p>
                                </div>
                                <div className="hidden md:flex items-center gap-4">
                                    <span className="text-xs text-slate-400 flex items-center gap-1"><Mail size={11} /> {member.email || '—'}</span>
                                    <span className="text-xs text-slate-400 flex items-center gap-1"><Phone size={11} /> {member.phone || '—'}</span>
                                </div>
                                <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 text-[10px] font-black uppercase">
                                    {member.status || 'Activo'}
                                </span>
                                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
                                    <button onClick={() => openHistory(member)} className="p-1.5 rounded-lg text-slate-400 hover:bg-blue-50 hover:text-blue-600 transition-all">
                                        <History size={14} />
                                    </button>
                                    <button className="p-1.5 rounded-lg text-slate-300 hover:bg-slate-100">
                                        <MoreVertical size={14} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                    )}

                    {/* GRID VIEW */}
                    {viewType === 'grid' && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 p-6">
                        {members.map((member) => (
                            <div key={member.id} className="group relative p-6 rounded-2xl border border-slate-100 dark:border-white/5 bg-white dark:bg-white/5 hover:shadow-lg hover:shadow-blue-50 dark:hover:bg-white/10 transition-all">
                                <div className="flex flex-col items-center text-center gap-3">
                                    <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center text-white font-black text-xl shadow-lg">
                                        {member.first_name.charAt(0)}
                                    </div>
                                    <div>
                                        <h4 className="font-bold text-slate-800 dark:text-slate-100">{member.first_name} {member.last_name}</h4>
                                        <p className="text-xs text-slate-400 mt-0.5">{getFamilyName(member.family_id)}</p>
                                    </div>
                                    <span className="px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 text-[10px] font-black uppercase">
                                        {member.status || 'Activo'}
                                    </span>
                                    {member.email && (
                                        <p className="text-xs text-slate-400 flex items-center gap-1 truncate max-w-full"><Mail size={10} /> {member.email}</p>
                                    )}
                                </div>
                                <div className="absolute top-3 right-3 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <button onClick={() => openHistory(member)} className="p-1.5 rounded-lg text-slate-400 hover:bg-blue-50 hover:text-blue-600 bg-white dark:bg-slate-800 shadow-sm border border-slate-100">
                                        <History size={12} />
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                    )}

                    {/* KANBAN VIEW */}
                    {viewType === 'kanban' && (
                    <div className="flex gap-4 p-6 overflow-x-auto pb-8">
                        {KANBAN_STAGES.map((stage) => {
                            const stageMembers = members.filter(m => (m.status || 'Activo') === stage.id);
                            const allActivos = stage.id === 'Activo' ? members : stageMembers;
                            const displayed = stage.id === 'Activo' ? members.filter(m => !m.status || m.status === 'Activo') : stageMembers;
                            return (
                                <div key={stage.id} className="flex-none w-72 flex flex-col gap-3">
                                    <div className="flex items-center justify-between mb-1">
                                        <h3 className="text-[11px] font-black uppercase tracking-widest text-slate-500 dark:text-slate-400">{stage.label}</h3>
                                        <span className="text-[11px] font-bold bg-slate-100 dark:bg-white/10 text-slate-500 px-2 py-0.5 rounded-full">{displayed.length}</span>
                                    </div>
                                    {displayed.map((member) => (
                                        <div key={member.id} className="p-4 rounded-2xl border border-slate-100 dark:border-white/5 bg-white dark:bg-[#1e1f21] shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all cursor-pointer group">
                                            <div className="flex items-center gap-3 mb-3">
                                                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-400 to-indigo-500 flex items-center justify-center text-white font-bold text-sm shrink-0">
                                                    {member.first_name.charAt(0)}
                                                </div>
                                                <div className="min-w-0">
                                                    <p className="font-bold text-slate-800 dark:text-slate-100 text-sm truncate">{member.first_name} {member.last_name}</p>
                                                    <p className="text-[10px] text-slate-400 truncate">{getFamilyName(member.family_id)}</p>
                                                </div>
                                            </div>
                                            {member.email && <p className="text-[11px] text-slate-400 flex items-center gap-1 truncate"><Mail size={10}/> {member.email}</p>}
                                            <div className="flex justify-end mt-2 gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                <button onClick={() => openHistory(member)} className="p-1 rounded-lg text-slate-400 hover:bg-blue-50 hover:text-blue-600">
                                                    <History size={12} />
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                    {displayed.length === 0 && (
                                        <div className="flex items-center justify-center py-8 rounded-2xl border-2 border-dashed border-slate-100 dark:border-white/5 text-slate-300 text-xs">Sin registros</div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                    )}
                    </>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                        {families.map(family => {
                            const familyMembers = members.filter(m => m.family_id === family.id);
                            return (
                                <div key={family.id} className="p-6 rounded-3xl border border-slate-100 bg-white hover:border-indigo-100 hover:shadow-2xl hover:shadow-indigo-50 transition-all group">
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                                            <FamilyIcon size={24} />
                                        </div>
                                        <span className="px-3 py-1 bg-slate-50 text-slate-500 text-[10px] font-black uppercase tracking-widest rounded-full">
                                            ID: #F{family.id.toString().padStart(3, '0')}
                                        </span>
                                    </div>
                                    <h3 className="text-lg font-black text-slate-900 mb-2">Familia {family.name}</h3>
                                    <p className="text-sm font-bold text-slate-500 mb-6">{familyMembers.length} Miembros registrados</p>

                                    <div className="flex -space-x-3 mt-4">
                                        {familyMembers.slice(0, 5).map(m => (
                                            <div key={m.id} className="w-10 h-10 rounded-full border-2 border-white bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-600 shadow-sm" title={`${m.first_name} ${m.last_name} (${m.role_in_family})`}>
                                                {m.first_name.charAt(0)}
                                            </div>
                                        ))}
                                        {familyMembers.length > 5 && (
                                            <div className="w-10 h-10 rounded-full border-2 border-white bg-slate-50 flex items-center justify-center text-[10px] font-black text-slate-400">
                                                +{familyMembers.length - 5}
                                            </div>
                                        )}
                                        {familyMembers.length === 0 && (
                                            <div className="text-xs text-slate-400 italic">Sin miembros</div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}

                <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/30 flex justify-between items-center text-sm text-slate-500">
                    <p className="font-medium text-slate-400">
                        Mostrando {activeTab === 'members' ? `${members.length} miembros` : `${families.length} familias`} en total
                    </p>
                    <div className="flex gap-2">
                        <button className="px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 font-bold transition-colors">Anterior</button>
                        <button className="px-4 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 font-bold transition-colors">Siguiente</button>
                    </div>
                </div>
            </div>

            {/* Registration Modal */}
            {isRegModalOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/20 backdrop-blur-md animate-in fade-in duration-300">
                    <div className="w-full max-w-xl bg-white rounded-[2rem] shadow-2xl border border-white/20 overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <div>
                                <h2 className="text-xl font-black text-slate-900 uppercase tracking-tight">Nuevo Miembro</h2>
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Completa los datos de registro</p>
                            </div>
                            <button onClick={() => setIsRegModalOpen(false)} className="p-3 bg-white text-slate-400 hover:text-slate-900 rounded-full transition-all shadow-sm">
                                <CloseIcon size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleRegister} className="p-8 space-y-6">
                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Nombre *</label>
                                    <input
                                        required
                                        value={newMember.first_name}
                                        onChange={e => setNewMember({ ...newMember, first_name: e.target.value })}
                                        className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm"
                                        placeholder="Ej: Juan"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Apellido *</label>
                                    <input
                                        required
                                        value={newMember.last_name}
                                        onChange={e => setNewMember({ ...newMember, last_name: e.target.value })}
                                        className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm"
                                        placeholder="Ej: Pérez"
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Email</label>
                                    <input
                                        type="email"
                                        value={newMember.email}
                                        onChange={e => setNewMember({ ...newMember, email: e.target.value })}
                                        className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm"
                                        placeholder="juan@email.com"
                                    />
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Teléfono</label>
                                    <input
                                        value={newMember.phone}
                                        onChange={e => setNewMember({ ...newMember, phone: e.target.value })}
                                        className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm"
                                        placeholder="+57 300..."
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Familia *</label>
                                    <select
                                        required
                                        value={newMember.family_id}
                                        onChange={e => setNewMember({ ...newMember, family_id: e.target.value })}
                                        className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm appearance-none bg-white"
                                    >
                                        <option value="">Selecciona...</option>
                                        {families.map(f => (
                                            <option key={f.id} value={f.id}>{f.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Rol</label>
                                    <input
                                        value={newMember.role_in_family}
                                        onChange={e => setNewMember({ ...newMember, role_in_family: e.target.value })}
                                        className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm"
                                        placeholder="Ej: Padre, Hijo..."
                                    />
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Fecha de Nacimiento</label>
                                <div className="relative">
                                    <Calendar className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                                    <input
                                        type="date"
                                        value={newMember.birthday}
                                        onChange={e => setNewMember({ ...newMember, birthday: e.target.value })}
                                        className="w-full pl-12 pr-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm"
                                    />
                                </div>
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setIsRegModalOpen(false)}
                                    className="flex-1 py-4 bg-slate-50 text-slate-400 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all border border-slate-100"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    className="flex-2 px-12 py-4 bg-blue-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-700 transition-all shadow-xl shadow-blue-100 flex items-center justify-center gap-2"
                                >
                                    Registrar <Check size={16} />
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Family Registration Modal */}
            {isFamilyRegModalOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/20 backdrop-blur-md animate-in fade-in duration-300">
                    <div className="w-full max-w-md bg-white rounded-[2rem] shadow-2xl border border-white/20 overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-indigo-50/30">
                            <div>
                                <h2 className="text-xl font-black text-slate-900 uppercase tracking-tight">Nueva Familia</h2>
                                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mt-1">Registra un núcleo familiar</p>
                            </div>
                            <button onClick={() => setIsFamilyRegModalOpen(false)} className="p-3 bg-white text-slate-400 hover:text-slate-900 rounded-full transition-all shadow-sm">
                                <CloseIcon size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleRegisterFamily} className="p-8 space-y-6">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Apellidos o Nombre de Familia *</label>
                                <input
                                    required
                                    value={newFamily.name}
                                    onChange={e => setNewFamily({ name: e.target.value })}
                                    className="w-full px-4 py-3 rounded-2xl border border-slate-100 focus:ring-2 focus:ring-indigo-500/20 outline-none font-bold text-sm"
                                    placeholder="Ej: Pérez Rodríguez"
                                />
                            </div>

                            <div className="pt-4 flex gap-3">
                                <button
                                    type="button"
                                    onClick={() => setIsFamilyRegModalOpen(false)}
                                    className="flex-1 py-4 bg-slate-50 text-slate-400 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all border border-slate-100"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    className="flex-2 px-12 py-4 bg-indigo-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-indigo-700 transition-all shadow-xl shadow-indigo-100 flex items-center justify-center gap-2"
                                >
                                    Guardar <Check size={16} />
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* History Modal */}
            {isHistoryModalOpen && selectedMember && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/20 backdrop-blur-md animate-in fade-in duration-300">
                    <div className="w-full max-w-2xl bg-white rounded-[2rem] shadow-2xl border border-white/20 overflow-hidden animate-in zoom-in-95 duration-300">
                        <div className="p-8 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 rounded-2xl bg-blue-600 text-white flex items-center justify-center font-black text-xl shadow-lg shadow-blue-100">
                                    {selectedMember.first_name.charAt(0)}
                                </div>
                                <div>
                                    <h2 className="text-xl font-black text-slate-900 uppercase tracking-tight">{selectedMember.first_name} {selectedMember.last_name}</h2>
                                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">Perfil Pastoral & Académico</p>
                                </div>
                            </div>
                            <button onClick={() => setIsHistoryModalOpen(false)} className="p-3 bg-white text-slate-400 hover:text-slate-900 rounded-full transition-all shadow-sm">
                                <CloseIcon size={20} />
                            </button>
                        </div>

                        <div className="p-8 max-h-[70vh] overflow-y-auto space-y-8">
                            {/* Interactions Section */}
                            <div>
                                <h3 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.2em] mb-4 flex items-center gap-3">
                                    <History className="text-blue-600" size={16} />
                                    Historial de Mensajería
                                </h3>

                                <div className="space-y-3">
                                    {loadingHistory ? (
                                        <div className="flex justify-center py-6">
                                            <Loader2 className="animate-spin text-blue-600" size={24} />
                                        </div>
                                    ) : history.length > 0 ? (
                                        history.map((log) => (
                                            <div key={log.id} className="p-4 rounded-2xl border border-slate-50 bg-slate-50/30">
                                                <div className="flex justify-between items-start mb-1">
                                                    <span className="text-[9px] font-black uppercase tracking-widest text-blue-600">{log.channel}</span>
                                                    <span className="text-[9px] font-bold text-slate-400">
                                                        {new Date(log.sent_at).toLocaleString()}
                                                    </span>
                                                </div>
                                                <p className="text-xs font-bold text-slate-700">{log.content}</p>
                                            </div>
                                        ))
                                    ) : (
                                        <div className="text-center py-6 bg-slate-50 rounded-2xl">
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sin registros recientes.</p>
                                        </div>
                                    )}
                                </div>

                                {/* Quick Message Form */}
                                <form onSubmit={handleSendMessage} className="mt-4 flex gap-2">
                                    <select
                                        value={messageChannel}
                                        onChange={e => setMessageChannel(e.target.value)}
                                        className="px-3 py-2 rounded-xl border border-slate-100 text-[10px] font-black uppercase tracking-widest bg-slate-50 outline-none"
                                    >
                                        <option value="whatsapp">WA</option>
                                        <option value="sms">SMS</option>
                                        <option value="email">Email</option>
                                    </select>
                                    <input
                                        required
                                        value={newMessageContent}
                                        onChange={e => setNewMessageContent(e.target.value)}
                                        className="flex-1 px-4 py-2 rounded-xl border border-slate-100 focus:ring-2 focus:ring-blue-500/10 outline-none font-bold text-xs"
                                        placeholder="Enviar nota rápida..."
                                    />
                                    <button
                                        type="submit"
                                        disabled={!newMessageContent}
                                        className="p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50"
                                    >
                                        <Check size={16} />
                                    </button>
                                </form>
                            </div>

                            {/* Academy Bridge Section */}
                            <div className="pt-8 border-t border-slate-100">
                                <h3 className="text-[10px] font-black text-slate-900 uppercase tracking-[0.2em] mb-4 flex items-center gap-3">
                                    <GraduationCap className="text-blue-600" size={16} />
                                    Estatus en la Academia
                                </h3>

                                {loadingAcademy ? (
                                    <div className="flex justify-center py-4">
                                        <Loader2 className="animate-spin text-blue-600" size={24} />
                                    </div>
                                ) : academyProfile?.is_linked ? (
                                    <div className="bg-blue-50/50 rounded-2xl p-5 border border-blue-100 flex items-center gap-4">
                                        <div className="w-12 h-12 rounded-xl bg-white flex items-center justify-center text-blue-600 shadow-sm">
                                            <ShieldCheck size={24} />
                                        </div>
                                        <div className="flex-1">
                                            <h4 className="font-black text-slate-900 uppercase text-[10px] tracking-tight mb-1">Usuario: @{academyProfile.username}</h4>
                                            <div className="flex flex-wrap gap-1">
                                                {academyProfile.enrollments && academyProfile.enrollments.length > 0 ? (
                                                    academyProfile.enrollments.map((en: any) => (
                                                        <span key={en.id} className="px-2 py-0.5 bg-white rounded text-[8px] font-black text-blue-600 border border-blue-100">
                                                            {en.course?.code || 'CUR'}
                                                        </span>
                                                    ))
                                                ) : (
                                                    <span className="text-[8px] font-black text-slate-400 uppercase">Sin cursos activos</span>
                                                )}
                                            </div>
                                        </div>
                                        <a href="/academy" className="p-2 bg-white text-blue-600 rounded-lg shadow-sm">
                                            <ExternalLink size={16} />
                                        </a>
                                    </div>
                                ) : (
                                    <div className="bg-slate-50 rounded-2xl p-6 border border-slate-100 text-center">
                                        <p className="text-[10px] font-bold text-slate-500 mb-4 px-4 uppercase tracking-wider">No tiene cuenta de academia vinculada.</p>
                                        <div className="flex gap-2 max-w-sm mx-auto">
                                            <input
                                                type="text"
                                                value={academyPassword}
                                                onChange={(e) => setAcademyPassword(e.target.value)}
                                                className="flex-1 px-3 py-2 rounded-xl border border-slate-200 text-[10px] font-black text-center"
                                                placeholder="Clave Temporal"
                                            />
                                            <button
                                                onClick={handleCreateAcademyAccount}
                                                disabled={isCreatingAccount || !selectedMember?.email}
                                                className="px-4 py-2 bg-slate-900 text-white rounded-xl text-[9px] font-black uppercase tracking-widest flex items-center gap-2"
                                            >
                                                {isCreatingAccount ? <Loader2 className="animate-spin" size={14} /> : <Plus size={14} />}
                                                Vincular
                                            </button>
                                        </div>
                                        {!selectedMember?.email && (
                                            <p className="text-[8px] font-black text-rose-500 uppercase mt-2 tracking-widest">Se requiere registrar un email primero</p>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
        </CrmShell>
    );
}
