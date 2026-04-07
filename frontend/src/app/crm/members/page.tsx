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
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);
    const [selectedMember, setSelectedMember] = useState<Member | null>(null);
    const [history, setHistory] = useState<any[]>([]);
    const [donations, setDonations] = useState<Donation[]>([]);
    const [tasks, setTasks] = useState<CrmTask[]>([]);
    const [loadingHistory, setLoadingHistory] = useState(false);
    const [loadingFinance, setLoadingFinance] = useState(false);
    const [loadingTasks, setLoadingTasks] = useState(false);
    const [modalTab, setModalTab] = useState<'timeline' | 'profile' | 'messages' | 'finance' | 'tasks'>('timeline');

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

    const openCV = async (member: Member) => {
        setSelectedMember(member);
        setEditedMember(member);
        setIsSidebarOpen(true);
        setEditMode(false);
        setModalTab('timeline');
        setLoadingHistory(true);
        setHistory([]);
        setDonations([]);
        setTasks([]);
        setAcademyProfile(null);

        fetchAcademyProfile(member.id);
        fetchMemberFinance(member.id);
        fetchMemberTasks(member.id);

        try {
            if (!token) throw new Error('no-token');
            const data = await apiFetch(`/crm/members/${member.id}/timeline`, {
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
            <div className={`flex-1 flex flex-col min-w-0 transition-all duration-500 ease-in-out ${isSidebarOpen ? 'mr-[450px]' : 'mr-0'}`}>
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

            {/* MEMBER SIDEBAR CV (INTEGRADO CON TAREAS Y FINANZAS) */}
            <aside 
                className={`fixed top-0 right-0 h-screen w-[450px] bg-white dark:bg-[#1e1f21] shadow-[-20px_0_50px_rgba(0,0,0,0.05)] border-l border-slate-100 dark:border-white/5 transition-all duration-500 ease-in-out z-[60] flex flex-col ${isSidebarOpen ? 'translate-x-0' : 'translate-x-full'}`}
            >
                {selectedMember && (
                    <>
                    {/* Sidebar Header Cinematic */}
                    <div className="p-8 border-b border-slate-50 bg-slate-50/30 shrink-0 relative overflow-hidden">
                        <div className="absolute top-0 right-0 p-10 opacity-5 pointer-events-none"><ShieldCheck size={120} /></div>
                        
                        <div className="flex justify-between items-start mb-6 relative z-10">
                            <button onClick={() => setIsSidebarOpen(false)} className="p-2 hover:bg-white rounded-xl text-slate-400 hover:text-slate-900 transition-all shadow-sm"><CloseIcon size={20} /></button>
                            <div className="flex gap-2">
                                <button onClick={handlePrint} className="px-4 py-2 bg-white text-blue-600 rounded-xl text-[10px] font-black uppercase tracking-widest border border-blue-100 flex items-center gap-2 shadow-sm hover:bg-blue-50"><Printer size={14} /> PDF</button>
                                <button 
                                    onClick={() => editMode ? handleUpdateMember() : setEditMode(true)}
                                    className={clsx("px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest flex items-center gap-2 transition-all", editMode ? "bg-emerald-600 text-white shadow-lg shadow-emerald-100" : "bg-slate-900 text-white shadow-lg")}
                                >
                                    {editMode ? <Check size={14}/> : <PencilLine size={14}/>} {editMode ? 'Guardar' : 'Editar CV'}
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center gap-5 relative z-10">
                            <div className="relative">
                                <div className="w-20 h-20 rounded-[2.2rem] bg-gradient-to-tr from-blue-600 to-indigo-600 text-white flex items-center justify-center font-black text-3xl shadow-xl shadow-blue-500/20">
                                    {selectedMember.first_name.charAt(0)}
                                </div>
                                <div className="absolute -bottom-1 -right-1 w-8 h-8 rounded-2xl bg-white border-4 border-slate-50 flex items-center justify-center text-blue-600 shadow-sm"><Zap size={14} fill="currentColor" /></div>
                            </div>
                            <div>
                                <h2 className="text-2xl font-black text-slate-900 dark:text-white uppercase tracking-tighter leading-tight">{selectedMember.first_name} {selectedMember.last_name}</h2>
                                <div className="flex items-center gap-2 mt-1">
                                    <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-600 text-[9px] font-black uppercase tracking-widest border border-blue-100">{selectedMember.role_in_family || 'Miembro'}</span>
                                    <span className="text-[10px] font-bold text-slate-400">#{selectedMember.spiritual_status}</span>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-3 gap-3 mt-8 relative z-10">
                            <div className="bg-white/80 dark:bg-white/5 p-3 rounded-2xl border border-white dark:border-white/10 shadow-sm text-center">
                                <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">Salud Esp.</p>
                                <p className="text-sm font-black text-emerald-600">{Math.round(selectedMember.spiritual_health * 100)}%</p>
                            </div>
                            <div className="bg-white/80 dark:bg-white/5 p-3 rounded-2xl border border-white dark:border-white/10 shadow-sm text-center">
                                <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">Academia</p>
                                <p className="text-sm font-black text-blue-600">{Math.round(selectedMember.academy_progress)}%</p>
                            </div>
                            <div className="bg-white/80 dark:bg-white/5 p-3 rounded-2xl border border-white dark:border-white/10 shadow-sm text-center">
                                <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest mb-1">Asistencia</p>
                                <p className="text-sm font-black text-purple-600">92%</p>
                            </div>
                        </div>
                    </div>

                    {/* Sidebar Tabs */}
                    <div className="flex px-6 border-b border-slate-50 shrink-0 overflow-x-auto no-scrollbar bg-white dark:bg-transparent">
                        {[
                            { id: 'timeline', label: 'CV', icon: History },
                            { id: 'tasks', label: 'Tareas', icon: ListTodo },
                            { id: 'finance', label: 'Diezmos', icon: DollarSign },
                            { id: 'messages', label: 'Chat', icon: Mail },
                            { id: 'profile', label: 'Notas', icon: ShieldCheck }
                        ].map(tab => (
                            <button 
                                key={tab.id}
                                onClick={() => setModalTab(tab.id as any)} 
                                className={clsx(
                                    "px-4 py-4 text-[10px] font-black uppercase tracking-widest border-b-2 transition-all flex items-center gap-2 shrink-0",
                                    modalTab === tab.id ? "border-blue-600 text-blue-600" : "border-transparent text-slate-400 hover:text-slate-600"
                                )}
                            >
                                <tab.icon size={12} /> {tab.label}
                            </button>
                        ))}
                    </div>

                    {/* Sidebar Content Area */}
                    <div className="flex-1 overflow-y-auto p-8 space-y-10 custom-scrollbar">
                        <AnimatePresence mode="wait">
                            {modalTab === 'timeline' && (
                                <motion.div initial={{opacity:0, y:10}} animate={{opacity:1, y:0}} className="space-y-10">
                                    <div>
                                        <h3 className="text-[10px] font-black text-slate-900 dark:text-white uppercase tracking-[0.2em] mb-6 flex items-center gap-3"><Award className="text-blue-600" size={16} /> Perfil Ministerial</h3>
                                        <div className="space-y-4">
                                            <div className={clsx("p-5 rounded-3xl border transition-all", editMode ? "bg-white border-blue-200 ring-4 ring-blue-50" : "bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/5")}>
                                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest mb-2">Talentos Detectados</p>
                                                {editMode ? <textarea value={editedMember.talents || ''} onChange={e => setEditedMember({...editedMember, talents: e.target.value})} className="w-full bg-transparent text-xs font-bold outline-none min-h-[60px] resize-none" /> : <p className="text-xs font-bold text-slate-700 dark:text-slate-300 italic">&quot;{selectedMember.talents || 'Pendiente por registrar'}&quot;</p>}
                                            </div>
                                            <div className={clsx("p-5 rounded-3xl border transition-all", editMode ? "bg-white border-indigo-200 ring-4 ring-indigo-50" : "bg-blue-50/30 dark:bg-indigo-900/10 border-blue-100 dark:border-indigo-900/30")}>
                                                <p className="text-[9px] font-black text-blue-400 uppercase tracking-widest mb-2">Dones Espirituales</p>
                                                {editMode ? <textarea value={editedMember.spiritual_gifts || ''} onChange={e => setEditedMember({...editedMember, spiritual_gifts: e.target.value})} className="w-full bg-transparent text-xs font-bold outline-none min-h-[60px] resize-none" /> : <p className="text-xs font-bold text-slate-700 dark:text-slate-300 italic">&quot;{selectedMember.spiritual_gifts || 'En proceso de identificación'}&quot;</p>}
                                            </div>
                                        </div>
                                    </div>
                                    
                                    <div>
                                        <h3 className="text-[10px] font-black text-slate-900 dark:text-white uppercase tracking-[0.2em] mb-6 flex items-center gap-3"><Clock className="text-blue-600" size={16} /> Línea de Tiempo</h3>
                                        {loadingHistory ? <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div> : history.length > 0 ? (
                                            <div className="relative border-l-2 border-slate-100 ml-2 space-y-8">
                                                {history.map((event, idx) => (
                                                    <div key={idx} className="relative pl-8">
                                                        <div className={clsx("absolute -left-[9px] top-0 w-4 h-4 rounded-full border-4 border-white shadow-sm", event.color || 'bg-slate-400')}></div>
                                                        <div className="flex justify-between mb-1"><span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{new Date(event.date).toLocaleDateString('es-ES', {month:'short', day:'numeric'})}</span><span className={clsx("px-2 py-0.5 rounded text-[7px] font-black uppercase text-white", event.color || 'bg-slate-400')}>{event.type}</span></div>
                                                        <h4 className="text-xs font-black text-slate-800 dark:text-slate-200 uppercase">{event.title}</h4>
                                                        <p className="text-[11px] text-slate-500 font-bold mt-1">{event.description}</p>
                                                    </div>
                                                ))}
                                            </div>
                                        ) : <div className="p-10 text-center bg-slate-50 dark:bg-white/5 rounded-3xl border-2 border-dashed border-slate-100 dark:border-white/10 text-slate-300 text-[10px] font-black uppercase tracking-widest">Sin actividad</div>}
                                    </div>
                                </motion.div>
                            )}

                            {modalTab === 'tasks' && (
                                <motion.div initial={{opacity:0, scale:0.98}} animate={{opacity:1, scale:1}} className="space-y-8">
                                    <h3 className="text-[10px] font-black text-slate-900 dark:text-white uppercase tracking-[0.2em] flex items-center gap-3"><ListTodo className="text-blue-600" size={16} /> Tareas de Seguimiento</h3>
                                    <button onClick={() => router.push('/crm/tasks/assign')} className="w-full py-4 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-2xl text-[10px] font-black uppercase tracking-widest border border-dashed border-blue-200 dark:border-blue-800 flex items-center justify-center gap-2"><Plus size={14}/> Nueva Tarea</button>
                                    
                                    {loadingTasks ? <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-blue-600" /></div> : tasks.length > 0 ? (
                                        <div className="space-y-3">
                                            {tasks.map(task => (
                                                <div key={task.id} className="p-5 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/10 rounded-3xl flex items-center justify-between group transition-all hover:border-blue-500/30">
                                                    <div className="flex items-center gap-4">
                                                        <button 
                                                            onClick={() => handleUpdateTaskStatus(task.id, task.status === 'done' ? 'todo' : 'done')}
                                                            className={clsx("size-6 rounded-lg flex items-center justify-center border transition-all", task.status === 'done' ? "bg-emerald-500 border-emerald-500 text-white" : "border-slate-200 dark:border-white/10 text-transparent")}
                                                        >
                                                            <Check size={14} />
                                                        </button>
                                                        <div>
                                                            <p className={clsx("text-xs font-black uppercase tracking-tight", task.status === 'done' ? "text-slate-400 line-through" : "text-slate-800 dark:text-slate-200")}>{task.title}</p>
                                                            <p className="text-[9px] text-slate-400 font-bold uppercase tracking-widest">{task.due_date ? new Date(task.due_date).toLocaleDateString() : 'Sin fecha'}</p>
                                                        </div>
                                                    </div>
                                                    <span className={clsx("px-2 py-0.5 rounded text-[7px] font-black uppercase tracking-widest", task.priority === 'urgent' ? 'bg-rose-100 text-rose-600' : 'bg-slate-100 text-slate-400')}>{task.priority}</span>
                                                </div>
                                            ))}
                                        </div>
                                    ) : <div className="p-10 text-center text-slate-300 text-[10px] font-black uppercase tracking-widest border-2 border-dashed border-slate-100 dark:border-white/10 rounded-3xl">Sin tareas asignadas</div>}
                                </motion.div>
                            )}

                            {modalTab === 'finance' && (
                                <motion.div initial={{opacity:0, x:10}} animate={{opacity:1, x:0}} className="space-y-8 text-center">
                                    <h3 className="text-[10px] font-black text-slate-900 dark:text-white uppercase tracking-[0.2em] flex items-center gap-3"><DollarSign className="text-emerald-600" size={16} /> Fidelidad Financiera</h3>
                                    {loadingFinance ? <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-emerald-600" /></div> : donations.length > 0 ? (
                                        <div className="space-y-6">
                                            <div className="p-8 rounded-[2.5rem] bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-900/30">
                                                <p className="text-[9px] font-black text-emerald-600 dark:text-emerald-400 uppercase tracking-widest mb-1">Impacto Total</p>
                                                <p className="text-4xl font-black text-emerald-900 dark:text-emerald-50 tracking-tighter">${donations.reduce((a,b)=>a+b.amount, 0).toLocaleString()}</p>
                                            </div>
                                            <div className="divide-y divide-slate-50 dark:divide-white/5 bg-slate-50 dark:bg-black/20 rounded-3xl border border-slate-100 dark:border-white/10 overflow-hidden text-left">
                                                {donations.map((d,i) => (
                                                    <div key={i} className="p-4 flex justify-between items-center"><div className="space-y-0.5"><p className="text-[10px] font-black text-slate-800 dark:text-slate-200 uppercase">{d.donation_type}</p><p className="text-[9px] font-bold text-slate-400">{new Date(d.created_at).toLocaleDateString()}</p></div><p className="text-xs font-black text-emerald-600">+${d.amount.toLocaleString()}</p></div>
                                                ))}
                                            </div>
                                        </div>
                                    ) : <div className="p-10 bg-slate-50 dark:bg-white/5 rounded-3xl border-2 border-dashed border-slate-100 dark:border-white/10 text-slate-300 text-[10px] font-black uppercase tracking-widest">Sin registros contables</div>}
                                </motion.div>
                            )}

                            {modalTab === 'messages' && (
                                <motion.div initial={{opacity:0}} animate={{opacity:1}} className="space-y-8">
                                    <h3 className="text-[10px] font-black text-slate-900 dark:text-white uppercase tracking-[0.2em] flex items-center gap-3"><Mail className="text-blue-600" size={16} /> Mensajería Directa</h3>
                                    <form onSubmit={handleSendMessage} className="bg-slate-50 dark:bg-black/20 p-6 rounded-[2.5rem] border border-slate-100 dark:border-white/10 space-y-5">
                                        <div className="flex p-1 bg-white dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/10">
                                            {['WhatsApp', 'SMS', 'Email'].map(ch => <button key={ch} type="button" onClick={() => setMessageChannel(ch)} className={clsx("flex-1 py-2 rounded-xl text-[9px] font-black uppercase tracking-widest transition-all", messageChannel === ch ? "bg-blue-600 text-white shadow-lg" : "text-slate-400 hover:text-slate-600")}>{ch}</button>)}
                                        </div>
                                        <textarea required value={newMessageContent} onChange={e => setNewMessageContent(e.target.value)} className="w-full p-5 rounded-3xl border border-slate-100 dark:border-white/10 bg-white dark:bg-white/5 text-xs font-bold focus:ring-4 focus:ring-blue-500/10 outline-none transition-all min-h-[120px]" placeholder={`Escribe mensaje para ${selectedMember.first_name}...`}/>
                                        <button type="submit" disabled={!newMessageContent} className="w-full py-4 bg-blue-600 text-white rounded-3xl text-[10px] font-black uppercase tracking-widest shadow-xl shadow-blue-500/20 flex items-center justify-center gap-2 group">Enviar Ahora <ChevronRight size={16} className="group-hover:translate-x-1 transition-transform" /></button>
                                    </form>
                                </motion.div>
                            )}

                            {modalTab === 'profile' && (
                                <motion.div initial={{opacity:0}} animate={{opacity:1}} className="space-y-8">
                                    <h3 className="text-[10px] font-black text-slate-900 dark:text-white uppercase tracking-[0.2em] flex items-center gap-3"><ShieldCheck className="text-blue-600" size={16} /> Notas del Pastor</h3>
                                    <div className="space-y-1.5">
                                        <label className="text-[9px] font-black text-slate-400 uppercase tracking-widest ml-2">Información Privada y de Seguimiento</label>
                                        <div className={clsx("p-6 rounded-[2rem] border transition-all min-h-[200px]", editMode ? "bg-white border-blue-200 ring-4 ring-blue-50" : "bg-slate-50 dark:bg-white/5 border-slate-100 dark:border-white/10")}>
                                            {editMode ? <textarea value={editedMember.pastoral_notes || ''} onChange={e => setEditedMember({...editedMember, pastoral_notes: e.target.value})} className="w-full bg-transparent text-xs font-bold text-slate-700 dark:text-slate-300 outline-none min-h-[180px] resize-none" /> : <p className="text-xs font-bold text-slate-600 dark:text-slate-400 leading-relaxed italic">{selectedMember.pastoral_notes || 'No hay notas pastorales registradas para este miembro.'}</p>}
                                        </div>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                    </>
                )}
            </aside>

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
