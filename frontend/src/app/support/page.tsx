"use client";

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { 
    LifeBuoy, 
    Mail, 
    Loader2, 
    Send, 
    X, 
    ExternalLink, 
    MessageSquare, 
    Book, 
    FileText, 
    Search, 
    Filter, 
    Plus, 
    Layout, 
    CheckCircle, 
    Clock, 
    AlertCircle,
    ChevronRight,
    MoreHorizontal,
    Edit3,
    History
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { ViewType } from '@/components/ViewSwitcher';
import StatusPicker, { StatusOption } from '@/components/ui/StatusPicker';
import clsx from 'clsx';
import { DataTable } from '@/components/ui/DataTable';
import { ColumnDef } from '@tanstack/react-table';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { useRouter } from 'next/navigation';

const TICKET_STATUS_OPTIONS: StatusOption[] = [
    { label: 'ABIERTO', value: 'abierto', color: 'bg-blue-500', text: 'text-blue-600 dark:text-blue-400', bg: 'bg-blue-50 dark:bg-blue-900/20' },
    { label: 'EN PROGRESO', value: 'proceso', color: 'bg-amber-500', text: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-900/20' },
    { label: 'RESUELTO', value: 'resuelto', color: 'bg-emerald-500', text: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-900/20' },
    { label: 'CERRADO', value: 'cerrado', color: 'bg-slate-400', text: 'text-slate-500 dark:text-slate-400', bg: 'bg-slate-100 dark:bg-white/5' },
];

export default function SupportPage() {
    const { token, user } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [viewType, setViewType] = useState<ViewType>('table');
    const [tickets, setTickets] = useState<any[]>([]);
    const [selectedTicket, setSelectedTicket] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);
    
    // New ticket form state
    const [newTicket, setNewTicket] = useState({ subject: '', description: '', category: 'General' });
    const [isSubmitting, setIsSubmitting] = useState(false);

    const isStaff = user?.role === 'admin' || user?.role === 'staff';

    useEffect(() => {
        const fetchTickets = async () => {
            if (!token) return;
            try {
                const data = await apiFetch('/support/', { token });
                if (Array.isArray(data)) {
                    setTickets(data);
                }
            } catch (err) {
                console.error("Error fetching tickets:", err);
            } finally {
                setLoading(false);
            }
        };
        fetchTickets();
    }, [token]);

    const updateTicketStatus = useCallback(async (id: number, newStatus: string) => {
        setTickets(prev => prev.map(t => t.id === id ? { ...t, status: newStatus } : t));
        if (!token) return;
        try {
            await apiFetch(`/support/${id}`, {
                method: 'PATCH',
                token,
                body: { status: newStatus }
            });
            addToast('Estado de ticket actualizado', 'success');
        } catch (err) {
            console.error("Failed to update ticket status:", err);
            addToast('Error al actualizar estado', 'error');
        }
    }, [token, addToast]);

    const handleCreateTicket = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newTicket.subject.trim() || !newTicket.description.trim()) {
            addToast('Por favor completa todos los campos', 'warning');
            return;
        }

        setIsSubmitting(true);
        try {
            const created = await apiFetch('/support/', {
                method: 'POST',
                token,
                body: { ...newTicket, user_id: user?.id }
            });
            setTickets([created, ...tickets]);
            setNewTicket({ subject: '', description: '', category: 'General' });
            setIsCreateModalOpen(false);
            addToast('Ticket enviado correctamente', 'success');
        } catch (err) {
            console.error(err);
            addToast('Error al enviar ticket', 'error');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleOpenTicket = (ticket: any) => {
        setSelectedTicket(ticket);
        setIsDrawerOpen(true);
    };

    const filteredTickets = useMemo(() => {
        return tickets.filter(t => 
            t.subject.toLowerCase().includes(search.toLowerCase()) ||
            t.description.toLowerCase().includes(search.toLowerCase())
        );
    }, [tickets, search]);

    const supportBaseCommands = useMemo(() => [
        { id: 'support-new-ticket', label: 'Crear ticket de soporte', description: 'Reportar incidente o duda', group: 'Soporte', action: () => setIsCreateModalOpen(true) },
        { id: 'support-view-table', label: 'Vista tabla', description: 'Gestionar tickets en lista', group: 'Soporte', action: () => setViewType('table') },
        { id: 'support-go-faq', label: 'Ver base de conocimiento', description: 'Guías y manuales', group: 'Soporte', action: () => router.push('/support#faq') },
        { id: 'support-dashboard', label: 'Volver al dashboard', group: 'Soporte', action: () => router.push('/support') },
    ], [router]);

    const supportTicketCommands = useMemo(() => filteredTickets.slice(0, 6).map((ticket) => ({
        id: `support-ticket-${ticket.id}`,
        label: ticket.subject,
        description: `Estado: ${ticket.status}`,
        group: 'Tickets',
        action: () => handleOpenTicket(ticket),
    })), [filteredTickets]);

    const supportCommands = useMemo(() => [...supportBaseCommands, ...supportTicketCommands], [supportBaseCommands, supportTicketCommands]);

    useRegisterCommands('support-hub', supportCommands);

    const columns = useMemo<ColumnDef<any>[]>(() => [
        {
            accessorKey: 'id',
            header: '#',
            size: 60,
            cell: info => <span className="text-[11px] font-bold text-slate-400">#{info.getValue() as number}</span>
        },
        {
            accessorKey: 'subject',
            header: 'Asunto / Descripción',
            size: 400,
            cell: ({ row }) => (
                <div className="flex flex-col pr-4">
                    <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200 truncate">{row.original.subject}</span>
                    <span className="text-[10px] text-slate-400 font-medium truncate">{row.original.description}</span>
                </div>
            )
        },
        {
            accessorKey: 'category',
            header: 'Categoría',
            cell: info => (
                <span className="text-[11px] font-bold text-slate-500 flex items-center gap-2">
                    <Book size={12} className="text-slate-300" />
                    {info.getValue() as string}
                </span>
            )
        },
        {
            accessorKey: 'status',
            header: 'Estado',
            cell: ({ row }) => (
                <div className="flex justify-center" onClick={(e) => e.stopPropagation()}>
                    <StatusPicker 
                        currentValue={row.original.status} 
                        options={TICKET_STATUS_OPTIONS}
                        onSelect={(val) => updateTicketStatus(row.original.id, val)}
                    />
                </div>
            )
        },
        {
            accessorKey: 'priority',
            header: 'Prioridad',
            cell: ({ row }) => {
                const p = row.original.priority;
                return (
                    <div className={clsx(
                        "text-[9px] font-black px-1.5 py-0.5 rounded uppercase tracking-widest w-fit",
                        p === 'alta' ? "bg-rose-50 text-rose-500 dark:bg-rose-900/20" : "bg-slate-50 text-slate-500 dark:bg-white/5"
                    )}>
                        {p}
                    </div>
                );
            }
        },
        {
            accessorKey: 'created_at',
            header: 'Fecha',
            cell: ({ row }) => (
                <span className="text-[11px] font-bold text-slate-500">
                    {new Date(row.original.created_at).toLocaleDateString()}
                </span>
            )
        }
    ], [updateTicketStatus]);

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'CCF', icon: Layout },
                    { label: 'Soporte y Ayuda', icon: LifeBuoy }
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={['grid', 'table']}
                onSearch={setSearch}
                onAdd={() => setIsCreateModalOpen(true)}
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {isStaff && viewType === 'table' ? (
                    <div className="h-full flex flex-col">
                        <DataTable data={filteredTickets} columns={columns} onRowClick={handleOpenTicket} />
                    </div>
                ) : (
                    <div className="p-6 max-w-4xl mx-auto space-y-10">
                        {/* User View */}
                        <section className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-3xl p-10 text-white shadow-xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
                            <div className="relative z-10">
                                <h2 className="text-3xl font-black mb-4">¿Cómo podemos ayudarte?</h2>
                                <p className="text-blue-100 font-medium text-lg mb-8 max-w-xl">Nuestro equipo pastoral y técnico está listo para apoyarte en lo que necesites.</p>
                                <button 
                                    onClick={() => setIsCreateModalOpen(true)}
                                    className="px-8 py-4 bg-white text-blue-600 rounded-2xl font-black text-sm uppercase tracking-widest shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all"
                                >
                                    Abrir Nuevo Ticket
                                </button>
                            </div>
                        </section>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-[2rem] shadow-sm space-y-4">
                                <div className="size-12 rounded-2xl bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600"><Mail size={24} /></div>
                                <h3 className="text-xl font-bold">Correo Electrónico</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Escríbenos directamente a soporte@ccf.org para consultas institucionales.</p>
                            </div>
                            <div className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-[2rem] shadow-sm space-y-4">
                                <div className="size-12 rounded-2xl bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600"><MessageSquare size={24} /></div>
                                <h3 className="text-xl font-bold">WhatsApp</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Respuesta rápida para emergencias pastorales y dudas técnicas.</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h3 className="text-[12px] font-black text-slate-400 uppercase tracking-widest ml-2">Tus Solicitudes Recientes</h3>
                            {tickets.length === 0 ? (
                                <div className="p-10 text-center border-2 border-dashed border-slate-100 dark:border-white/5 rounded-3xl text-slate-400 text-sm font-medium italic">No has abierto tickets recientemente.</div>
                            ) : tickets.map(ticket => (
                                <div key={ticket.id} onClick={() => handleOpenTicket(ticket)} className="p-5 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-2xl hover:border-blue-500/30 transition-all cursor-pointer flex items-center justify-between group">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-xl bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400"><FileText size={20} /></div>
                                        <div>
                                            <h4 className="font-bold text-slate-700 dark:text-white">{ticket.subject}</h4>
                                            <p className="text-xs text-slate-400">{new Date(ticket.created_at).toLocaleDateString()}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <div className={clsx(
                                            "px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-tight",
                                            ticket.status === 'abierto' ? "bg-blue-50 text-blue-600" : "bg-emerald-50 text-emerald-600"
                                        )}>{ticket.status}</div>
                                        <ChevronRight size={16} className="text-slate-300 group-hover:text-blue-500 transition-colors" />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </main>

            <WorkspaceDrawer 
                isOpen={isDrawerOpen} 
                onClose={() => setIsDrawerOpen(false)}
                title={selectedTicket?.subject || 'Detalles del Ticket'}
                subtitle={`${selectedTicket?.category || 'Soporte'} • #${selectedTicket?.id}`}
                actions={
                    <>
                        <button className="px-4 py-2 text-[11px] font-bold text-slate-500" onClick={() => setIsDrawerOpen(false)}>Cerrar</button>
                        <button className="px-6 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-blue-500/20 active:scale-95 transition-all">Enviar Mensaje</button>
                    </>
                }
            >
                <div className="space-y-8 animate-fade-in">
                    <section className="grid grid-cols-2 gap-4">
                        <DrawerStat label="Estado" value={selectedTicket?.status} icon={CheckCircle} />
                        <DrawerStat label="Prioridad" value={selectedTicket?.priority} icon={AlertCircle} />
                        <DrawerStat label="Creado" value={selectedTicket ? new Date(selectedTicket.created_at).toLocaleDateString() : ''} icon={Clock} />
                        <DrawerStat label="Categoría" value={selectedTicket?.category} icon={Book} />
                    </section>

                    <section className="space-y-4">
                        <div className="flex items-center gap-2">
                            <FileText size={14} className="text-slate-400" />
                            <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest">Descripción del Problema</h4>
                        </div>
                        <div className="p-5 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-2xl text-[13px] text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                            {selectedTicket?.description}
                        </div>
                    </section>

                    <section className="space-y-4 pt-6 border-t border-slate-100 dark:border-white/5">
                        <h4 className="text-[11px] font-black text-slate-400 uppercase tracking-widest flex items-center gap-2">
                            <History size={14} className="text-blue-500" /> Historial de Resolución
                        </h4>
                        <div className="space-y-3">
                            <div className="flex gap-4 p-4 bg-slate-50 dark:bg-white/5 rounded-xl border border-slate-200 dark:border-white/5">
                                <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 shrink-0"><Send size={14} /></div>
                                <div><p className="text-[12px] font-bold text-slate-700 dark:text-slate-200">Ticket Recibido</p><p className="text-[10px] text-slate-400">Asignado automáticamente al departamento correspondiente.</p></div>
                            </div>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>

            {/* Create Ticket Modal */}
            {isCreateModalOpen && (
                <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4">
                    <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-md" onClick={() => setIsCreateModalOpen(false)} />
                    <div className="relative w-full max-w-lg bg-white dark:bg-[#1e1f21] rounded-3xl shadow-2xl border border-slate-200 dark:border-white/10 overflow-hidden">
                        <div className="p-8">
                            <h3 className="text-2xl font-black text-slate-900 dark:text-white mb-6">Nuevo Ticket de Soporte</h3>
                            <form onSubmit={handleCreateTicket} className="space-y-4">
                                <div>
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 block">Asunto</label>
                                    <input 
                                        type="text" 
                                        required
                                        value={newTicket.subject}
                                        onChange={(e) => setNewTicket({...newTicket, subject: e.target.value})}
                                        placeholder="Ej: No puedo ver mi certificado" 
                                        className="w-full px-4 py-3 bg-slate-50 dark:bg-black/20 border-0 rounded-2xl text-[14px] outline-none focus:ring-2 focus:ring-blue-500/20" 
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2 block">Descripción</label>
                                    <textarea 
                                        required
                                        value={newTicket.description}
                                        onChange={(e) => setNewTicket({...newTicket, description: e.target.value})}
                                        placeholder="Describe tu problema con detalle..." 
                                        className="w-full h-32 px-4 py-3 bg-slate-50 dark:bg-black/20 border-0 rounded-2xl text-[14px] outline-none focus:ring-2 focus:ring-blue-500/20 resize-none" 
                                    />
                                </div>
                                <div className="flex gap-4 justify-end mt-8">
                                    <button type="button" onClick={() => setIsCreateModalOpen(false)} className="px-6 py-3 text-slate-500 font-bold text-sm">Cancelar</button>
                                    <button 
                                        type="submit" 
                                        disabled={isSubmitting}
                                        className="px-8 py-3 bg-blue-600 text-white rounded-2xl font-black text-sm uppercase tracking-widest shadow-lg shadow-blue-500/20 flex items-center gap-2"
                                    >
                                        {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : 'Enviar Solicitud'}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function DrawerStat({ label, value, icon: Icon }: any) {
    return (
        <div className="p-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-xl">
            <div className="flex items-center gap-2 mb-1">
                <Icon size={12} className="text-slate-400" />
                <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">{label}</span>
            </div>
            <p className="text-[12px] font-bold text-slate-700 dark:text-slate-200 capitalize">{value || 'N/A'}</p>
        </div>
    );
}
