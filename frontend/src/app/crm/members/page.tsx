'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import SplitDropdownButton from '@/components/ui/SplitDropdownButton';
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
    Home,
    Calendar,
    Check,
    History,
    GraduationCap,
    ShieldCheck,
    ExternalLink,
    Loader2,
    Users,
    Clock,
    Printer,
    FileText,
    Download,
    ChevronRight,
    MapPin,
    Award,
    Heart,
    Zap,
    PencilLine,
    DollarSign,
    CheckCircle2,
    ListTodo
} from 'lucide-react';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import ViewSwitcher, { ViewType, getStoredView } from '@/components/ViewSwitcher';
import CrmShell from '@/components/crm/CrmShell';
import AdminHero from '@/components/admin/AdminHero';
import UniversalTableView from '@/components/ui/UniversalTableView';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { motion, AnimatePresence } from 'framer-motion';
import clsx from 'clsx';
import { useSidebarLayers } from '@/context/SidebarLayerContext';
import MemberDetailSidebar from '@/components/crm/MemberDetailSidebar';

interface Member {
    id: number;
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    family_id: number;
    role_in_family: string;
    status: string;
    spiritual_status: string;
    spiritual_health: number;
    academy_progress: number;
    talents?: string;
    spiritual_gifts?: string;
    pastoral_notes?: string;
    user_id?: number | null;
}

interface Family {
    id: number;
    name: string;
    members_count?: number;
}

interface Donation {
    id: number;
    amount: number;
    donation_type: string;
    created_at: string;
}

interface CrmTask {
    id: number;
    title: string;
    status: string;
    due_date: string | null;
    priority: string;
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

    // Sidebar CV State
    const { pushSidebarPanel, popSidebarPanel } = useSidebarLayers();
    const [selectedMember, setSelectedMember] = useState<Member | null>(null);

    // Registration States — Drawers (NO modals)
    const [isRegDrawerOpen, setIsRegDrawerOpen] = useState(false);
    const [isFamilyRegDrawerOpen, setIsFamilyRegDrawerOpen] = useState(false);

    // Profile Management State
    const [editMode, setEditMode] = useState(false);
    const [editedMember, setEditedMember] = useState<any>({});

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
        birthday: '',
        talents: '',
        spiritual_gifts: '',
        pastoral_notes: ''
    });

    const [newFamily, setNewFamily] = useState({ name: '' });


    const heroWatchers = ['Comunidad', 'Optimus Brain'];

    const [searchTerm, setSearchTerm] = useState('');
    const [sortBy, setSortBy] = useState<'name' | 'id' | 'health'>('name');
    const router = useRouter();

    // Helper: get family name by id
    const getFamilyName = useCallback((familyId: number | null | undefined) => {
        if (!familyId) return 'Sin familia';
        const fam = families.find(f => f.id === familyId);
        return fam ? fam.name : `Familia #${familyId}`;
    }, [families]);

    const fetchData = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (searchTerm) params.append('search', searchTerm);
            
            const [membersData, familiesData] = await Promise.all([
                apiFetch<Member[]>(`/crm/members?${params.toString()}`, { token, cache: 'no-store' }),
                apiFetch<Family[]>('/crm/families/', { token, cache: 'no-store' })
            ]);
            
            let sortedMembers = Array.isArray(membersData) ? [...membersData] : [];
            if (sortBy === 'name') {
                sortedMembers.sort((a, b) => a.first_name.localeCompare(b.first_name));
            } else if (sortBy === 'health') {
                sortedMembers.sort((a, b) => ((b as any).spiritual_health || 0) - ((a as any).spiritual_health || 0));
            }
            
            setMembers(sortedMembers);
            setFamilies(Array.isArray(familiesData) ? familiesData : []);
        } catch (err) {
            console.error('Error loading members', err);
            addToast("Error al cargar datos", "error");
        } finally {
            setLoading(false);
        }
    }, [token, addToast, searchTerm, sortBy]);

    useEffect(() => {
        const delayDebounceFn = setTimeout(() => {
            fetchData();
        }, 300);

        return () => clearTimeout(delayDebounceFn);
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
            setIsRegDrawerOpen(false);
            setNewMember({ first_name: '', last_name: '', email: '', phone: '', family_id: '', role_in_family: 'Miembro', birthday: '', talents: '', spiritual_gifts: '', pastoral_notes: '' });
            fetchData();
        } catch (err) {
            console.error('register member error', err);
            addToast("Error al registrar miembro", "error");
        }
    };

    const handleUpdateMember = async () => {
        if (!selectedMember || !token) return;
        try {
            await apiFetch(`/crm/members/${selectedMember.id}`, {
                method: 'PATCH',
                token,
                body: editedMember
            });
            addToast("Ficha actualizada", "success");
            setEditMode(false);
            setSelectedMember({...selectedMember, ...editedMember});
            fetchData();
        } catch (err) {
            addToast("Error al actualizar", "error");
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
            setIsFamilyRegDrawerOpen(false);
            setNewFamily({ name: '' });
            fetchData();
        } catch (err) {
            console.error('register family error', err);
            addToast("Error al registrar familia", "error");
        }
    };

    const openCV = (member: Member) => {
        setSelectedMember(member);
        pushSidebarPanel({
            id: `member-cv-${member.id}`,
            title: `${member.first_name} ${member.last_name}`,
            content: (
                <MemberDetailSidebar 
                    member={member} 
                    onUpdate={fetchData} 
                    onClose={popSidebarPanel}
                />
            )
        });
    };

    const fetchMemberFinance = async (id: number) => {
        if(!token) return;
        setLoadingFinance(true);
        try {
            const data = await apiFetch<Donation[]>(`/crm/members/${id}/donations`, { token });
            setDonations(Array.isArray(data) ? data : []);
        } catch(e) { console.error(e); }
        finally { setLoadingFinance(false); }
    };

    const fetchMemberTasks = async (id: number) => {
        if(!token) return;
        setLoadingTasks(true);
        try {
            const data = await apiFetch<CrmTask[]>(`/crm/tasks?assignee_id=${id}`, { token });
            setTasks(Array.isArray(data) ? data : []);
        } catch(e) { console.error(e); }
        finally { setLoadingTasks(false); }
    };

    const handleUpdateTaskStatus = async (taskId: number, newStatus: string) => {
        try {
            await apiFetch(`/crm/tasks/${taskId}`, {
                method: 'PATCH',
                token,
                body: { status: newStatus }
            });
            addToast("Estado de tarea actualizado", "success");
            if(selectedMember) fetchMemberTasks(selectedMember.id);
        } catch (err) {
            addToast("Error al actualizar tarea", "error");
        }
    };

    const fetchAcademyProfile = async (memberId: number) => {
        if (!token) return;
        setLoadingAcademy(true);
        try {
            const data = await apiFetch(`/academy/members/${memberId}/profile`, {
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
            const result = await apiFetch(`/academy/members/${selectedMember.id}/create-account`, {
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
            const logs = await apiFetch(`/crm/members/${selectedMember.id}/timeline`, {
                token,
                cache: 'no-store'
            });
            setHistory(Array.isArray(logs) ? logs : []);
        } catch (err) {
            console.error('send message error', err);
            addToast("Error al enviar mensaje", "error");
        }
    };

    const handleAssignMemberToFamily = async (memberId: number, familyId: number) => {
        try {
            await apiFetch(`/crm/members/${memberId}`, {
                method: 'PATCH',
                token,
                body: { family_id: familyId }
            });
            addToast("Miembro asignado a la familia", "success");
            fetchData();
        } catch (err) {
            addToast("Error al asignar miembro", "error");
        }
    };

    const handlePrint = () => {
        window.print();
    };

    return (
        <CrmShell
            breadcrumbs={[{ label: 'CCF', icon: Users }, { label: 'CRM Pastoral', icon: Users }, { label: 'Membresía', icon: Users }]}
            viewOptions={['table', 'list', 'grid', 'board', 'kanban', 'gantt', 'calendar']}
            viewType={viewType}
            onViewChange={(v) => setViewType(v as ViewType)}
            rightActions={
                <SplitDropdownButton
                    mainLabel="Nuevo"
                    icon={activeTab === 'members' ? Plus : FamilyIcon}
                    onMainClick={() => activeTab === 'members' ? setIsRegDrawerOpen(true) : setIsFamilyRegDrawerOpen(true)}
                    options={[
                        { id: 'member', label: 'Miembro', icon: User, onClick: () => setIsRegDrawerOpen(true) },
                        { id: 'family', label: 'Familia', icon: FamilyIcon, onClick: () => setIsFamilyRegDrawerOpen(true) }
                    ]}
                />
            }
        >
        <div className="flex flex-1 relative overflow-hidden h-full">
            {/* MAIN CONTENT AREA */}
            <div className={`flex-1 flex flex-col min-w-0 transition-all duration-500 ease-in-out`}>
                <div className="print:hidden">
                    <AdminHero
                        eyebrow="Membresía"
                        title="Gestión de membresía"
                        description="Administra personas, familias y su avance pastoral desde un solo panel."
                        tags={['Familias', 'Academia', 'IA']}
                        watchers={heroWatchers}
                        primaryAction={{ label: 'Registrar miembro', icon: Plus, onClick: () => setIsRegDrawerOpen(true) }}
                        secondaryAction={{ label: 'Registrar familia', icon: Plus, onClick: () => setIsFamilyRegDrawerOpen(true) }}
                    />
                </div>
                
                <div className="p-4 lg:p-0 space-y-8 print:hidden">
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
                                    value={searchTerm}
                                    onChange={e => setSearchTerm(e.target.value)}
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
                                <UniversalTableView
                                    data={members}
                                    columns={[
                                        { 
                                            key: 'first_name', 
                                            label: 'Miembro', 
                                            type: 'text', 
                                            width: '300px',
                                            render: (val, member) => (
                                                <div className="flex items-center gap-4">
                                                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-100 to-indigo-50 flex items-center justify-center text-blue-600 font-bold border border-blue-50 shrink-0">
                                                        {member.first_name.charAt(0)}
                                                    </div>
                                                    <div className="min-w-0">
                                                        <h4 className="font-bold text-slate-800 dark:text-slate-100 group-hover:text-blue-600 transition-colors truncate">{member.first_name} {member.last_name}</h4>
                                                        <p className="text-[10px] uppercase font-black tracking-widest text-slate-400">#M{member.id.toString().padStart(4, '0')}</p>
                                                    </div>
                                                </div>
                                            )
                                        },
                                        { 
                                            key: 'family_id', 
                                            label: 'Familia / Rol', 
                                            type: 'text',
                                            render: (val, member) => (
                                                <div className="flex flex-col">
                                                    <span className="text-sm font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                                                        <FamilyIcon size={14} className="text-slate-400" /> {getFamilyName(member.family_id)}
                                                    </span>
                                                    <span className="text-xs text-slate-400 mt-0.5">{member.role_in_family}</span>
                                                </div>
                                            )
                                        },
                                        { 
                                            key: 'spiritual_health', 
                                            label: 'Salud Espiritual', 
                                            type: 'progress' 
                                        },
                                        { 
                                            key: 'status', 
                                            label: 'Estado', 
                                            type: 'status' 
                                        }
                                    ]}
                                    groupBy="status"
                                    onRowClick={(member) => router.push(`/crm/members/${member.id}`)}
                                />
                            )}

                            {/* ... (Otras vistas List, Grid, Kanban se mantienen iguales) ... */}
                            </>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
                                {families.map(family => {
                                    const familyMembers = members.filter(m => m.family_id === family.id);
                                    return (
                                        <div key={family.id} className="p-6 rounded-[2.5rem] border border-slate-100 bg-white hover:border-indigo-100 hover:shadow-2xl hover:shadow-indigo-50 transition-all group">
                                            <div className="flex justify-between items-start mb-4">
                                                <div className="w-12 h-12 rounded-[1.5rem] bg-indigo-50 text-indigo-600 flex items-center justify-center">
                                                    <FamilyIcon size={24} />
                                                </div>
                                                <span className="px-3 py-1 bg-slate-50 text-slate-500 text-[10px] font-black uppercase tracking-widest rounded-full">
                                                    ID: #F{family.id.toString().padStart(3, '0')}
                                                </span>
                                            </div>
                                            <h3 className="text-lg font-black text-slate-900 mb-2 uppercase tracking-tight">Familia {family.name}</h3>
                                            <p className="text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-6">{familyMembers.length} Miembros registrados</p>

                                            <div className="flex -space-x-3 mt-4">
                                                {familyMembers.slice(0, 5).map(m => (
                                                    <div key={m.id} onClick={() => openCV(m)} className="w-10 h-10 rounded-full border-2 border-white bg-slate-100 flex items-center justify-center text-xs font-bold text-slate-600 shadow-sm cursor-pointer hover:z-10 hover:scale-110 transition-all">
                                                        {m.first_name.charAt(0)}
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>
                </div>
            </div>




            {/* ─── Drawer: Registrar Miembro ─── */}
            <WorkspaceDrawer
                isOpen={isRegDrawerOpen}
                onClose={() => setIsRegDrawerOpen(false)}
                title="Registrar Miembro"
                subtitle="Nuevo integrante de la comunidad"
                actions={
                    <>
                        <button type="button" onClick={() => setIsRegDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                            Cancelar
                        </button>
                        <button
                            form="member-reg-form"
                            type="submit"
                            className="px-8 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all"
                        >
                            Registrar
                        </button>
                    </>
                }
            >
                <form id="member-reg-form" onSubmit={handleRegister} className="space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Nombre *</label>
                            <input required value={newMember.first_name} onChange={e => setNewMember({ ...newMember, first_name: e.target.value })} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white" placeholder="Nombre" />
                        </div>
                        <div className="space-y-1.5">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Apellido *</label>
                            <input required value={newMember.last_name} onChange={e => setNewMember({ ...newMember, last_name: e.target.value })} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white" placeholder="Apellido" />
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Correo electrónico</label>
                        <input type="email" value={newMember.email} onChange={e => setNewMember({ ...newMember, email: e.target.value })} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white" placeholder="correo@ejemplo.com" />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Teléfono</label>
                        <input value={newMember.phone} onChange={e => setNewMember({ ...newMember, phone: e.target.value })} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white" placeholder="+57 300 000 0000" />
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Familia *</label>
                        <select required value={newMember.family_id} onChange={e => setNewMember({ ...newMember, family_id: e.target.value })} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white appearance-none">
                            <option value="">Selecciona una familia...</option>
                            {families.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Rol en la familia</label>
                        <select value={newMember.role_in_family} onChange={e => setNewMember({ ...newMember, role_in_family: e.target.value })} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white appearance-none">
                            <option>Miembro</option><option>Cabeza de familia</option><option>Cónyuge</option><option>Hijo/a</option>
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Fecha de nacimiento</label>
                        <input type="date" value={newMember.birthday} onChange={e => setNewMember({ ...newMember, birthday: e.target.value })} className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 focus:ring-2 focus:ring-blue-500/20 outline-none font-bold text-sm dark:text-white" />
                    </div>
                </form>
            </WorkspaceDrawer>

            {/* ─── Drawer: Registrar Familia ─── */}
            <WorkspaceDrawer
                isOpen={isFamilyRegDrawerOpen}
                onClose={() => setIsFamilyRegDrawerOpen(false)}
                title="Registrar Familia"
                subtitle="Nueva unidad familiar en la comunidad"
                actions={
                    <>
                        <button type="button" onClick={() => setIsFamilyRegDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                            Cancelar
                        </button>
                        <button
                            form="family-reg-form"
                            type="submit"
                            className="px-8 py-2 bg-slate-900 dark:bg-white dark:text-slate-900 text-white rounded-lg text-[11px] font-black uppercase tracking-widest shadow-lg active:scale-95 transition-all"
                        >
                            Registrar Familia
                        </button>
                    </>
                }
            >
                <form id="family-reg-form" onSubmit={handleRegisterFamily} className="space-y-5">
                    <div className="flex flex-col items-center justify-center py-8 gap-4">
                        <div className="size-16 rounded-3xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 flex items-center justify-center">
                            <Home size={28} />
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400 text-center">Las familias agrupan a los miembros de la congregación en unidades pastorales.</p>
                    </div>
                    <div className="space-y-1.5">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Apellido familiar *</label>
                        <input
                            required
                            value={newFamily.name}
                            onChange={e => setNewFamily({ name: e.target.value })}
                            className="w-full px-4 py-4 rounded-2xl border border-slate-200 dark:border-white/10 bg-slate-50 dark:bg-black/20 focus:ring-2 focus:ring-indigo-500/20 outline-none font-black text-lg dark:text-white"
                            placeholder="Ej: García, Rodríguez..."
                        />
                        <p className="text-[10px] text-slate-400 mt-1 ml-1">Se registrará como &ldquo;Familia García&rdquo;</p>
                    </div>
                </form>
            </WorkspaceDrawer>
        </div>
        </CrmShell>
    );
}
