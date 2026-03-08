'use client';

import React, { useState, useEffect } from 'react';
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
    Loader2
} from 'lucide-react';

import { apiUrl } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';

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

export default function MembersPage() {
    const { addToast } = useToast();
    const [activeTab, setActiveTab] = useState('members');
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


    const fetchData = async () => {
        setLoading(true);
        try {
            const [memRes, famRes] = await Promise.all([
                fetch(apiUrl('/members/')),
                fetch(apiUrl('/families/'))
            ]);
            if (memRes.ok) setMembers(await memRes.json());
            if (famRes.ok) setFamilies(await famRes.json());
        } catch (err) {
            addToast("Error al cargar datos", "error");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newMember.first_name || !newMember.last_name || !newMember.family_id) {
            addToast("Por favor completa los campos obligatorios", "warning");
            return;
        }

        try {
            const response = await fetch(apiUrl('/members/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...newMember,
                    family_id: parseInt(newMember.family_id),
                    birthday: newMember.birthday ? new Date(newMember.birthday).toISOString() : null
                })
            });

            if (response.ok) {
                addToast("Miembro registrado exitosamente", "success");
                setIsRegModalOpen(false);
                setNewMember({ first_name: '', last_name: '', email: '', phone: '', family_id: '', role_in_family: 'Miembro', birthday: '' });
                fetchData();
            } else {
                addToast("Error al registrar miembro", "error");
            }
        } catch (err) {
            addToast("Error de conexión", "error");
        }
    };

    const handleRegisterFamily = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newFamily.name) {
            addToast("Por favor ingresa el nombre de la familia", "warning");
            return;
        }

        try {
            const response = await fetch(apiUrl('/families/'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newFamily)
            });

            if (response.ok) {
                addToast("Familia registrada exitosamente", "success");
                setIsFamilyRegModalOpen(false);
                setNewFamily({ name: '' });
                fetchData();
            } else {
                addToast("Error al registrar familia", "error");
            }
        } catch (err) {
            addToast("Error de conexión", "error");
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
            const response = await fetch(apiUrl(`/members/${member.id}/communications`));
            if (response.ok) {
                const data = await response.json();
                setHistory(data);
            }
        } catch (err) {
            addToast("Error al cargar historial", "error");
        } finally {
            setLoadingHistory(false);
        }
    };

    const fetchAcademyProfile = async (memberId: number) => {
        setLoadingAcademy(true);
        try {
            const response = await fetch(apiUrl(`/members/${memberId}/academy-profile`));
            if (response.ok) {
                const data = await response.json();
                setAcademyProfile(data);
            }
        } catch (err) {
            console.error("Error fetching academy profile", err);
        } finally {
            setLoadingAcademy(false);
        }
    };

    const handleCreateAcademyAccount = async () => {
        if (!selectedMember) return;
        setIsCreatingAccount(true);
        try {
            const response = await fetch(apiUrl(`/members/${selectedMember.id}/create-academy-account`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: academyPassword })
            });

            if (response.ok) {
                addToast("Cuenta de academia creada exitosamente", "success");
                fetchAcademyProfile(selectedMember.id);
                fetchData();
            } else {
                const errData = await response.json();
                addToast(errData.detail || "Error al crear cuenta", "error");
            }
        } catch (err) {
            addToast("Error de conexión", "error");
        } finally {
            setIsCreatingAccount(false);
        }
    };

    const handleSendMessage = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedMember || !newMessageContent) return;

        try {
            const response = await fetch(apiUrl('/messaging/send'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    member_id: selectedMember.id,
                    channel: messageChannel,
                    content: newMessageContent
                })
            });

            if (response.ok) {
                addToast("Mensaje enviado exitosamente", "success");
                setNewMessageContent('');
                // Refresh history without closing modal
                const histRes = await fetch(apiUrl(`/members/${selectedMember.id}/communications`));
                if (histRes.ok) setHistory(await histRes.json());
            } else {
                addToast("Error al enviar mensaje", "error");
            }
        } catch (err) {
            addToast("Error de conexión", "error");
        }
    };

    const getFamilyName = (id: number) => families.find(f => f.id === id)?.name || 'Sin Familia';

    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Gestión de Membresía</h1>
                    <p className="text-slate-500 mt-1">Administra los miembros y familias de la congregación.</p>
                </div>
                {activeTab === 'members' ? (
                    <button
                        onClick={() => setIsRegModalOpen(true)}
                        className="flex items-center gap-2 bg-blue-600 px-6 py-3 rounded-2xl text-sm font-black text-white hover:bg-blue-700 transition-all shadow-lg shadow-blue-100 uppercase tracking-widest"
                    >
                        <Plus size={20} />
                        Registrar Miembro
                    </button>
                ) : (
                    <button
                        onClick={() => setIsFamilyRegModalOpen(true)}
                        className="flex items-center gap-2 bg-indigo-600 px-6 py-3 rounded-2xl text-sm font-black text-white hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 uppercase tracking-widest"
                    >
                        <Plus size={20} />
                        Registrar Familia
                    </button>
                )}
            </div>

            {/* Tabs & Filters */}
            <div className="flex flex-col md:flex-row gap-6 items-center justify-between">
                <div className="flex p-1 bg-slate-100 rounded-2xl w-full md:w-auto">
                    <button
                        onClick={() => setActiveTab('members')}
                        className={`px-6 py-2 rounded-xl text-sm font-bold transition-all ${activeTab === 'members' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Miembros
                    </button>
                    <button
                        onClick={() => setActiveTab('families')}
                        className={`px-6 py-2 rounded-xl text-sm font-bold transition-all ${activeTab === 'families' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                    >
                        Familias
                    </button>
                </div>

                <div className="flex gap-4 w-full md:w-auto">
                    <div className="relative flex-1 md:w-80">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder="Buscar por nombre, email o familia..."
                            className="w-full pl-12 pr-4 py-3 rounded-2xl border border-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all bg-white"
                        />
                    </div>
                    <button className="p-3 rounded-2xl border border-slate-100 bg-white text-slate-500 hover:bg-slate-50 transition-colors">
                        <Filter size={20} />
                    </button>
                </div>
            </div>

            {/* Members & Families Display */}
            <div className="glass-card overflow-hidden border border-slate-100 shadow-xl shadow-slate-100/50">
                {loading ? (
                    <div className="flex justify-center py-20">
                        <div className="w-10 h-10 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                ) : activeTab === 'members' ? (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="border-b border-slate-100 bg-slate-50/50">
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest">Miembro</th>
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest">Familia / Rol</th>
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest">Contacto</th>
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest text-center">Estado</th>
                                    <th className="px-6 py-4 text-xs font-black uppercase text-slate-400 tracking-widest text-right">Acciones</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {members.map((member) => (
                                    <tr key={member.id} className="hover:bg-slate-50/80 transition-colors group">
                                        <td className="px-6 py-5">
                                            <div className="flex items-center gap-4">
                                                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-100 to-indigo-50 flex items-center justify-center text-blue-600 font-bold border border-blue-50">
                                                    {member.first_name.charAt(0)}
                                                </div>
                                                <div>
                                                    <h4 className="font-bold text-slate-800">{member.first_name} {member.last_name}</h4>
                                                    <p className="text-[10px] uppercase font-black tracking-widest text-slate-400">ID: #M{member.id.toString().padStart(4, '0')}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex flex-col">
                                                <span className="text-sm font-bold text-slate-700 flex items-center gap-1.5">
                                                    <FamilyIcon size={14} className="text-slate-400" />
                                                    {getFamilyName(member.family_id)}
                                                </span>
                                                <span className="text-xs text-slate-400 mt-0.5">{member.role_in_family}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5">
                                            <div className="flex flex-col gap-1">
                                                <div className="flex items-center gap-2 text-xs text-slate-500">
                                                    <Mail size={12} className="text-slate-300" />
                                                    {member.email}
                                                </div>
                                                <div className="flex items-center gap-2 text-xs text-slate-500">
                                                    <Phone size={12} className="text-slate-300" />
                                                    {member.phone}
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-5 text-center">
                                            <span className="px-3 py-1 rounded-full bg-emerald-50 text-emerald-600 text-[10px] font-black uppercase tracking-widest border border-emerald-100">
                                                Activo
                                            </span>
                                        </td>
                                        <td className="px-6 py-5 text-right">
                                            <div className="flex justify-end gap-2">
                                                <button
                                                    onClick={() => openHistory(member)}
                                                    className="p-2 rounded-lg text-slate-400 hover:bg-blue-50 hover:text-blue-600 transition-all"
                                                    title="Ver Historial"
                                                >
                                                    <History size={18} />
                                                </button>
                                                <button className="p-2 rounded-lg text-slate-300 hover:bg-slate-100 hover:text-slate-600 transition-colors">
                                                    <MoreVertical size={18} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
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
    );
}
