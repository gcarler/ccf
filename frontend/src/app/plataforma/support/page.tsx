"use client";

import React, { useState, useEffect, useMemo } from 'react';
import {
    LifeBuoy, 
    Mail, 
    Loader2,
    Send,
    MessageSquare, 
    FileText,
    Book,
    Layout, 
    CheckCircle,
    Clock,
    AlertCircle,
    ChevronRight,
    History
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import WorkspaceDrawer from '@/components/WorkspaceDrawer';
import { ViewType } from '@/components/ViewSwitcher';
import clsx from 'clsx';
import UniversalTableView from '@/components/ui/UniversalTableView';
import UniversalCalendarView from '@/components/ui/UniversalCalendarView';
import UniversalGanttView from '@/components/ui/UniversalGanttView';
import UniversalWikiView from '@/components/ui/UniversalWikiView';
import { useRegisterCommands } from '@/context/CommandCenterContext';
import { useRouter } from 'next/navigation';

const SUPPORT_VIEWS: ViewType[] = ['grid', 'table', 'list', 'board', 'kanban', 'calendar', 'gantt', 'wiki'];

export default function SupportPage() {
    const { token, user } = useAuth();
    const { addToast } = useToast();
    const router = useRouter();
    const [viewType, setViewType] = useState<ViewType>('table');
    const [tickets, setTickets] = useState<any[]>([]);
    const [selectedTicket, setSelectedTicket] = useState<any>(null);
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isCreateDrawerOpen, setIsCreateDrawerOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [loading, setLoading] = useState(true);
    
    // New ticket form state
    const [newTicket, setNewTicket] = useState({ subject: '', description: '', category: 'General' });
    const [isSubmitting, setIsSubmitting] = useState(false);
    void loading;
    void setLoading;

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
            setIsCreateDrawerOpen(false);
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

    const groupedTickets = useMemo(() => {
        const statuses = ['abierto', 'pendiente', 'en_progreso', 'resuelto', 'cerrado'];
        return statuses.map((status) => ({
            status,
            tickets: filteredTickets.filter((ticket) => (ticket.status || 'abierto') === status),
        })).filter((column) => column.tickets.length > 0 || ['abierto', 'pendiente', 'resuelto'].includes(column.status));
    }, [filteredTickets]);

    const calendarEvents = useMemo(() => filteredTickets.map((ticket) => ({
        id: ticket.id,
        title: ticket.subject,
        date: (ticket.created_at || new Date().toISOString()).slice(0, 10),
        color: ticket.status === 'resuelto' || ticket.status === 'cerrado' ? 'emerald' as const : ticket.priority === 'urgent' ? 'rose' as const : 'blue' as const,
        location: ticket.category,
    })), [filteredTickets]);

    const ganttItems = useMemo(() => filteredTickets.map((ticket) => ({
        id: ticket.id,
        title: ticket.subject,
        subtitle: ticket.category || ticket.status,
        start_date: (ticket.created_at || new Date().toISOString()).slice(0, 10),
        end_date: (ticket.updated_at || ticket.created_at || new Date().toISOString()).slice(0, 10),
        color: ticket.status === 'resuelto' || ticket.status === 'cerrado' ? 'emerald' as const : ticket.priority === 'urgent' ? 'rose' as const : 'blue' as const,
        progress: ticket.status === 'resuelto' || ticket.status === 'cerrado' ? 100 : ticket.status === 'en_progreso' ? 55 : 20,
    })), [filteredTickets]);

    const supportBaseCommands = useMemo(() => [
        { id: 'support-new-ticket', label: 'Crear ticket de soporte', description: 'Reportar incidente o duda', group: 'Soporte', action: () => setIsCreateDrawerOpen(true) },
        { id: 'support-view-table', label: 'Vista tabla', description: 'Gestionar tickets en lista', group: 'Soporte', action: () => setViewType('table') },
        { id: 'support-go-faq', label: 'Ver base de conocimiento', description: 'Guías y manuales', group: 'Soporte', action: () => router.push('/plataforma/support#faq') },
        { id: 'support-dashboard', label: 'Volver al dashboard', group: 'Soporte', action: () => router.push('/plataforma/support') },
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

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#1e1f21] overflow-hidden animate-fade-in">
            <WorkspaceToolbar 
                breadcrumbs={[
                    { label: 'CCF', icon: Layout },
                    { label: 'Soporte y Ayuda', icon: LifeBuoy }
                ]}
                viewType={viewType}
                setViewType={setViewType}
                availableViews={SUPPORT_VIEWS}
                onSearch={setSearch}
                onAdd={() => setIsCreateDrawerOpen(true)}
            />

            <main className="flex-1 overflow-y-auto scrollbar-thin">
                {viewType === 'table' ? (
                    <UniversalTableView
                        data={filteredTickets}
                        columns={[
                            { key: 'id', label: 'ID', type: 'id', width: '80px' },
                            { 
                                key: 'subject', 
                                label: 'Asunto / Descripción', 
                                type: 'text', 
                                width: '400px',
                                render: (val, ticket) => (
                                    <div className="flex flex-col pr-4">
                                        <span className="text-[13px] font-bold text-slate-700 dark:text-slate-200 truncate">{ticket.subject}</span>
                                        <span className="text-[10px] text-slate-400 font-medium truncate">{ticket.description}</span>
                                    </div>
                                )
                            },
                            { 
                                key: 'category', 
                                label: 'Categoría', 
                                type: 'text', 
                                width: '150px',
                                render: (val) => (
                                    <span className="text-[11px] font-bold text-slate-500 flex items-center gap-2">
                                        <Book size={12} className="text-slate-300" />
                                        {val}
                                    </span>
                                )
                            },
                            { key: 'status', label: 'Estado', type: 'status', width: '150px' },
                            { key: 'priority', label: 'Prioridad', type: 'priority', width: '120px' },
                            { key: 'created_at', label: 'Fecha', type: 'date', width: '150px' },
                        ]}
                        groupBy="status"
                        onRowClick={handleOpenTicket}
                    />
                ) : viewType === 'list' ? (
                    <div className="mx-auto max-w-5xl space-y-3 p-3">
                        {filteredTickets.map((ticket) => (
                            <button key={ticket.id} onClick={() => handleOpenTicket(ticket)} className="w-full rounded-lg border border-slate-200 bg-white p-4 text-left transition hover:border-blue-300 dark:border-white/10 dark:bg-white/5">
                                <div className="flex items-center justify-between gap-4">
                                    <div className="min-w-0">
                                        <p className="truncate text-sm font-semibold text-slate-900 dark:text-white">{ticket.subject}</p>
                                        <p className="truncate text-xs font-medium text-slate-400">{ticket.description}</p>
                                    </div>
                                    <span className="shrink-0 rounded-full bg-slate-100 px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500 dark:bg-white/10">{ticket.status || 'abierto'}</span>
                                </div>
                            </button>
                        ))}
                        {filteredTickets.length === 0 && <div className="py-1.5 text-center text-sm font-semibold text-slate-400">Sin tickets para mostrar.</div>}
                    </div>
                ) : viewType === 'board' || viewType === 'kanban' ? (
                    <div className="flex gap-4 overflow-x-auto p-3">
                        {groupedTickets.map((column) => (
                            <section key={column.status} className="w-80 shrink-0 rounded-lg border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
                                <div className="mb-3 flex items-center justify-between px-1">
                                    <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{column.status}</p>
                                    <span className="font-semibold text-slate-400">{column.tickets.length}</span>
                                </div>
                                <div className="space-y-2">
                                    {column.tickets.map((ticket) => (
                                        <button key={ticket.id} onClick={() => handleOpenTicket(ticket)} className="w-full rounded-md border border-slate-200 bg-white p-3 text-left shadow-sm dark:border-white/10 dark:bg-white/5">
                                            <p className="line-clamp-2 text-xs font-semibold text-slate-900 dark:text-white">{ticket.subject}</p>
                                            <p className="mt-2 text-[10px] font-semibold uppercase tracking-wide text-slate-400">{ticket.category || 'General'}</p>
                                        </button>
                                    ))}
                                    {column.tickets.length === 0 && <div className="rounded-md border border-dashed border-slate-200 py-8 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-400 dark:border-white/10">Vacio</div>}
                                </div>
                            </section>
                        ))}
                    </div>
                ) : viewType === 'calendar' ? (
                    <div className="h-[720px] p-3">
                        <UniversalCalendarView events={calendarEvents} title="Calendario de soporte" onEventClick={(event) => {
                            const ticket = filteredTickets.find((item) => item.id === event.id);
                            if (ticket) handleOpenTicket(ticket);
                        }} />
                    </div>
                ) : viewType === 'gantt' ? (
                    <div className="h-[720px] p-3">
                        <UniversalGanttView items={ganttItems} moduleName="Soporte" onItemClick={(item) => {
                            const ticket = filteredTickets.find((entry) => entry.id === item.id);
                            if (ticket) handleOpenTicket(ticket);
                        }} />
                    </div>
                ) : viewType === 'wiki' ? (
                    <div className="p-3">
                        <UniversalWikiView moduleName="Soporte" storageKey="wiki_support" />
                    </div>
                ) : (
 <div className="p-3 w-full space-y-3">
                        {/* User View */}
                        <section className="bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg p-4 text-white shadow-xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 w-64 h-48 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
                            <div className="relative z-10">
                                <h2 className="text-xl font-bold mb-4">¿Cómo podemos ayudarte?</h2>
                                <p className="text-blue-100 font-medium text-lg mb-3 max-w-xl">Nuestro equipo pastoral y técnico está listo para apoyarte en lo que necesites.</p>
                                <button 
                                    onClick={() => setIsCreateDrawerOpen(true)}
                                    className="px-4 py-1.5 bg-white text-blue-600 rounded-lg font-black text-sm uppercase tracking-wide shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all"
                                >
                                    Abrir Nuevo Ticket
                                </button>
                            </div>
                        </section>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="p-4 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-lg shadow-sm space-y-4">
                                <div className="size-7 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-blue-600"><Mail size={24} /></div>
                                <h3 className="text-xl font-bold">Correo Electrónico</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Escríbenos directamente a soporte@ccf.org para consultas institucionales.</p>
                            </div>
                            <div className="p-4 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-lg shadow-sm space-y-4">
                                <div className="size-7 rounded-lg bg-emerald-50 dark:bg-emerald-900/30 flex items-center justify-center text-emerald-600"><MessageSquare size={24} /></div>
                                <h3 className="text-xl font-bold">WhatsApp</h3>
                                <p className="text-slate-500 dark:text-slate-400 text-sm">Respuesta rápida para emergencias pastorales y dudas técnicas.</p>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h3 className="font-semibold text-slate-400 uppercase tracking-wide ml-2">Tus Solicitudes Recientes</h3>
                            {tickets.length === 0 ? (
                                <div className="p-4 text-center border-2 border-dashed border-slate-100 dark:border-white/5 rounded-lg text-slate-400 text-sm font-medium italic">No has abierto tickets recientemente.</div>
                            ) : tickets.map(ticket => (
                                <div key={ticket.id} onClick={() => handleOpenTicket(ticket)} className="p-3 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-lg hover:border-blue-500/30 transition-all cursor-pointer flex items-center justify-between group">
                                    <div className="flex items-center gap-4">
                                        <div className="size-10 rounded-md bg-slate-50 dark:bg-white/5 flex items-center justify-center text-slate-400"><FileText size={20} /></div>
                                        <div>
                                            <h4 className="font-bold text-slate-700 dark:text-white">{ticket.subject}</h4>
                                            <p className="text-xs text-slate-400">{new Date(ticket.created_at).toLocaleDateString()}</p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <div className={clsx(
                                            "px-3 py-1 rounded-full text-[10px] font-semibold uppercase tracking-tight",
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
                        <button className="px-3 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-bold shadow-lg shadow-blue-500/20 active:scale-95 transition-all">Enviar Mensaje</button>
                    </>
                }
            >
                <div className="space-y-3 animate-fade-in">
                    <section className="grid grid-cols-2 gap-4">
                        <DrawerStat label="Estado" value={selectedTicket?.status} icon={CheckCircle} />
                        <DrawerStat label="Prioridad" value={selectedTicket?.priority} icon={AlertCircle} />
                        <DrawerStat label="Creado" value={selectedTicket ? new Date(selectedTicket.created_at).toLocaleDateString() : ''} icon={Clock} />
                        <DrawerStat label="Categoría" value={selectedTicket?.category} icon={Book} />
                    </section>

                    <section className="space-y-4">
                        <div className="flex items-center gap-2">
                            <FileText size={14} className="text-slate-400" />
                            <h4 className="font-semibold text-slate-400 uppercase tracking-wide">Descripción del Problema</h4>
                        </div>
                        <div className="p-3 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-[13px] text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                            {selectedTicket?.description}
                        </div>
                    </section>

                    <section className="space-y-4 pt-6 border-t border-slate-100 dark:border-white/5">
                        <h4 className="font-semibold text-slate-400 uppercase tracking-wide flex items-center gap-2">
                            <History size={14} className="text-blue-500" /> Historial de Resolución
                        </h4>
                        <div className="space-y-3">
                            <div className="flex gap-4 p-4 bg-slate-50 dark:bg-white/5 rounded-md border border-slate-200 dark:border-white/5">
                                <div className="w-8 h-8 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center text-blue-600 shrink-0"><Send size={14} /></div>
                                <div><p className="text-[12px] font-bold text-slate-700 dark:text-slate-200">Ticket Recibido</p><p className="text-[10px] text-slate-400">Asignado automáticamente al departamento correspondiente.</p></div>
                            </div>
                        </div>
                    </section>
                </div>
            </WorkspaceDrawer>

            {/* ─── Drawer: Crear Ticket ─── (NO modal bloqueante) */}
            <WorkspaceDrawer
                isOpen={isCreateDrawerOpen}
                onClose={() => setIsCreateDrawerOpen(false)}
                title="Nuevo Ticket de Soporte"
                subtitle="Reportar un incidente o solicitar ayuda"
                actions={
                    <>
                        <button type="button" onClick={() => setIsCreateDrawerOpen(false)} className="px-4 py-2 text-[11px] font-bold text-slate-500 hover:text-slate-700 transition-colors">
                            Cancelar
                        </button>
                        <button
                            form="create-ticket-form"
                            type="submit"
                            disabled={isSubmitting}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-lg shadow-blue-500/20 hover:bg-blue-700 active:scale-95 transition-all flex items-center gap-2"
                        >
                            {isSubmitting ? <Loader2 size={14} className="animate-spin" /> : null}
                            Enviar Solicitud
                        </button>
                    </>
                }
            >
                <form id="create-ticket-form" onSubmit={handleCreateTicket} className="space-y-5">
                    <div className="space-y-2">
                        <label className="font-semibold text-slate-400 uppercase tracking-wide">Asunto *</label>
                        <input
                            type="text"
                            required
                            value={newTicket.subject}
                            onChange={(e) => setNewTicket({ ...newTicket, subject: e.target.value })}
                            placeholder="Ej: No puedo ver mi certificado"
                            className="w-full px-4 py-3 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500/20 dark:text-white font-medium"
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="font-semibold text-slate-400 uppercase tracking-wide">Categoría</label>
                        <select
                            value={newTicket.category}
                            onChange={(e) => setNewTicket({ ...newTicket, category: e.target.value })}
                            className="w-full px-4 py-3 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500/20 dark:text-white font-medium appearance-none"
                        >
                            <option>General</option>
                            <option>Técnico</option>
                            <option>Académico</option>
                            <option>Pastoral</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="font-semibold text-slate-400 uppercase tracking-wide">Descripción *</label>
                        <textarea
                            required
                            value={newTicket.description}
                            onChange={(e) => setNewTicket({ ...newTicket, description: e.target.value })}
                            placeholder="Describe tu problema con detalle..."
                            className="w-full h-36 px-4 py-3 bg-slate-50 dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500/20 resize-none dark:text-white font-medium"
                        />
                    </div>
                </form>
            </WorkspaceDrawer>
        </div>
    );
}

function DrawerStat({ label, value, icon: Icon }: any) {
    return (
        <div className="p-3 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/5 rounded-md">
            <div className="flex items-center gap-2 mb-1">
                <Icon size={12} className="text-slate-400" />
                <span className="font-semibold text-slate-400 uppercase tracking-wide">{label}</span>
            </div>
            <p className="text-[12px] font-bold text-slate-700 dark:text-slate-200 capitalize">{value || 'N/A'}</p>
        </div>
    );
}

