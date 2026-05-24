"use client";

import React, { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import CommunityToolbarChip from '@/components/community/ToolbarChip';
import CommunityQuickCommentCard from '@/components/community/QuickCommentCard';
import CommunityListRow from '@/components/community/ListRow';
import { formatDueLabel, getInitials } from '@/lib/community/utils';
import {
    Bell,
    Megaphone,
    MessageSquare,
    Calendar,
    HeartHandshake,
    Heart,
    Users,
    Search,
    Star,
    ArrowUpRight,
    CheckCircle2,
    MessageCircle,
    Tag,
    Clock4,
    Filter,
    SlidersHorizontal,
    RefreshCcw,
    ArrowLeft,
    Share2,
    Zap,
    UserMinus,
    List,
    KanbanSquare,
    GanttChart,
    Table as TableIcon,
    Columns3
} from 'lucide-react';
import { Plus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

type ColumnId = 'canales' | 'cuidado' | 'grupos' | 'generosidad';
type ViewId = 'list' | 'board' | 'calendar' | 'gantt' | 'table';

type BoardItem = {
    id: string;
    name: string;
    stage: string;
    owner: string;
    due: string;
    priority: 'Alta' | 'Media' | 'Baja';
    status: string;
    comments: string;
    link: string;
};

type CommunityApiCard = {
    id: number;
    column_id: ColumnId;
    name: string;
    stage: string;
    owner: string;
    due_date?: string | null;
    priority: BoardItem['priority'];
    status: string;
    comments?: string | null;
    link?: string | null;
};

type NewCardForm = {
    columnId: ColumnId;
    name: string;
    stage: string;
    owner: string;
    due: string;
    priority: BoardItem['priority'];
    status: string;
    comments: string;
};

const initialBoardColumns: { id: ColumnId; title: string; description: string; accent: string; items: BoardItem[] }[] = [
    {
        id: 'canales',
        title: 'Flujo de canales',
        description: 'Notificaciones, anuncios y bandejas que requieren respuesta hoy.',
        accent: 'text-sky-500',
        items: [
            {
                id: 'notif-rollup',
                name: 'Resumen semanal de notificaciones',
                stage: 'Notificaciones',
                owner: 'Equipo Comms',
                due: 'Hoy 6:00 p.m.',
                priority: 'Alta',
                status: 'En curso',
                comments: '12 alertas sin leer',
                link: '/community/notifications'
            },
            {
                id: 'broadcast',
                name: 'Broadcast pastoral “Familias”',
                stage: 'Anuncios',
                owner: 'Ps. Laura',
                due: 'Mañana',
                priority: 'Media',
                status: 'Listo',
                comments: 'Programado en MailerLite',
                link: '/community/announcements'
            },
            {
                id: 'dm-bandeja',
                name: 'Bandeja de mensajes',
                stage: 'Mensajes',
                owner: 'Coordinación',
                due: '—',
                priority: 'Media',
                status: 'Pendiente',
                comments: '8 hilos activos',
                link: '/community/messages'
            }
        ]
    },
    {
        id: 'cuidado',
        title: 'Cuidado pastoral',
        description: 'Seguimiento de oraciones, testimonios y acompañamientos clave.',
        accent: 'text-rose-500',
        items: [
            {
                id: 'prayer-wall',
                name: 'Revisión del muro de oración',
                stage: 'Oración',
                owner: 'Intercesión',
                due: 'Hoy 9:00 p.m.',
                priority: 'Alta',
                status: 'En curso',
                comments: '5 peticiones nuevas',
                link: '/community/prayer'
            },
            {
                id: 'testimonios',
                name: 'Testimonios para el domingo',
                stage: 'Testimonios',
                owner: 'Creative Team',
                due: 'Viernes',
                priority: 'Media',
                status: 'Revisión',
                comments: '3 historias en cola',
                link: '/community/testimonies'
            }
        ]
    },
    {
        id: 'grupos',
        title: 'Grupos & eventos',
        description: 'Coordinación de grupos pequeños, descubrimiento y calendario.',
        accent: 'text-amber-500',
        items: [
            {
                id: 'grupos-lideres',
                name: 'Rotaciones de líderes',
                stage: 'Grupos',
                owner: 'Coaching',
                due: 'Próx. martes',
                priority: 'Media',
                status: 'En curso',
                comments: '18 grupos confirmados',
                link: '/community/groups'
            },
            {
                id: 'discover-labs',
                name: 'Labs “Descubrir tu llamado”',
                stage: 'Descubrir',
                owner: 'RR.HH. Voluntarios',
                due: 'Jueves',
                priority: 'Baja',
                status: 'Planificado',
                comments: '26 registros',
                link: '/community/discover'
            },
            {
                id: 'ensayo-worship',
                name: 'Ensayo Worship Night',
                stage: 'Eventos',
                owner: 'Producción',
                due: 'Sábado',
                priority: 'Alta',
                status: 'Listo',
                comments: 'Calendario sincronizado',
                link: '/community/events'
            }
        ]
    },
    {
        id: 'generosidad',
        title: 'Impacto & generosidad',
        description: 'Campañas de ofrendas, ayudas y reportes de impacto.',
        accent: 'text-emerald-500',
        items: [
            {
                id: 'ofrendas',
                name: 'Campaña “Navidad Generosa”',
                stage: 'Ofrendas',
                owner: 'Finanzas',
                due: '15 Dic',
                priority: 'Alta',
                status: 'En curso',
                comments: '$18.4M recaudados',
                link: '/community/give'
            },
            {
                id: 'ayuda-social',
                name: 'Entrega de despensas Zona Norte',
                stage: 'Impacto social',
                owner: 'Serve Team',
                due: 'Domingo',
                priority: 'Media',
                status: 'Coordinando',
                comments: '40 familias enlistadas',
                link: '/community/give'
            }
        ]
    }
];

const columnIcons: Record<ColumnId, LucideIcon> = {
    canales: Bell,
    cuidado: Heart,
    grupos: Users,
    generosidad: HeartHandshake
};

const featureCards = [
    {
        title: 'Notificaciones',
        description: 'Resumen inteligente de lo que está pasando en tus equipos y ministerios.',
        icon: Bell,
        href: '/community/notifications',
        tone: 'from-primary/15 to-primary/5'
    },
    {
        title: 'Anuncios',
        description: 'Mensajes oficiales del equipo pastoral y de comunicaciones.',
        icon: Megaphone,
        href: '/community/announcements',
        tone: 'from-amber-200/40 to-amber-50/30'
    },
    {
        title: 'Mensajes',
        description: 'Chats privados y grupos para coordinar iniciativas.',
        icon: MessageSquare,
        href: '/community/messages',
        tone: 'from-emerald-200/40 to-emerald-50/30'
    },
    {
        title: 'Eventos',
        description: 'Calendario vivo con reuniones, ensayos y experiencias.',
        icon: Calendar,
        href: '/community/events',
        tone: 'from-blue-200/40 to-blue-50/30'
    },
    {
        title: 'Ofrendas & generosidad',
        description: 'Facilita ofrendas especiales y campañas solidarias.',
        icon: HeartHandshake,
        href: '/community/give',
        tone: 'from-rose-200/40 to-rose-50/30'
    },
    {
        title: 'Muro de oración',
        description: 'Comparte peticiones y celebra respuestas en comunidad.',
        icon: Heart,
        href: '/community/prayer',
        tone: 'from-sky-200/40 to-sky-50/30'
    },
    {
        title: 'Testimonios',
        description: 'Historias reales que inspiran y fortalecen la fe.',
        icon: Star,
        href: '/community/testimonies',
        tone: 'from-yellow-200/40 to-yellow-50/30'
    },
    {
        title: 'Grupos pequeños',
        description: 'Encuentra tu círculo y mantente conectado entre semana.',
        icon: Users,
        href: '/community/groups',
        tone: 'from-slate-200/40 to-slate-50/30'
    },
    {
        title: 'Descubrir',
        description: 'Explora nuevos ministerios, serving teams y oportunidades.',
        icon: Search,
        href: '/community/discover',
        tone: 'from-indigo-200/40 to-indigo-50/30'
    }
];

const priorityTone: Record<'Alta' | 'Media' | 'Baja', string> = {
    Alta: 'bg-rose-100 text-rose-600 border-rose-200',
    Media: 'bg-amber-100 text-amber-600 border-amber-200',
    Baja: 'bg-slate-100 text-slate-500 border-slate-200'
};

const statusTone = 'bg-slate-100 text-slate-600 border-slate-200';

const mapApiCardToBoardItem = (card: CommunityApiCard): BoardItem => ({
    id: `community-card-${card.id}`,
    name: card.name,
    stage: card.stage,
    owner: card.owner,
    due: formatDueLabel(card.due_date),
    priority: card.priority ?? 'Media',
    status: card.status,
    comments: card.comments || 'Sin comentarios',
    link: card.link || `/community/${card.column_id}`
});

const palette = ['bg-primary/10 text-primary', 'bg-emerald-100 text-emerald-600', 'bg-amber-100 text-amber-600'];
const columnAccentDot: Record<ColumnId, string> = {
    canales: 'bg-indigo-400',
    cuidado: 'bg-rose-400',
    grupos: 'bg-amber-400',
    generosidad: 'bg-emerald-400'
};
const listColumnHeaders = ['Nombre', 'Persona asignada', 'Fecha límite', 'Prioridad', 'Estado', 'Comentarios'];
const listGridClass = 'grid grid-cols-[32px_minmax(0,2.4fr)_1.4fr_1.1fr_0.9fr_1fr_0.9fr] items-center gap-4';
const summaryIcons: Record<string, LucideIcon> = {
    Notificaciones: Bell,
    Anuncios: Megaphone,
    Mensajes: MessageSquare,
    Oración: Heart,
    Eventos: Calendar
};
const viewOptions: Array<{ id: ViewId; label: string; icon: LucideIcon; description: string }> = [
    { id: 'list', label: 'Lista', icon: List, description: 'Vista lineal para priorizar rápidamente' },
    { id: 'board', label: 'Tablero', icon: KanbanSquare, description: 'Columnas tipo ClickUp' },
    { id: 'calendar', label: 'Calendario', icon: Calendar, description: 'Agenda visual' },
    { id: 'gantt', label: 'Gantt', icon: GanttChart, description: 'Dependencias y progreso' },
    { id: 'table', label: 'Tabla', icon: TableIcon, description: 'Datos sin distracciones' }
];

export default function CommunityHubPage() {
    const router = useRouter();
    const { token } = useAuth();
    const metrics = [
        { label: 'Equipos activos', value: '32', detail: '+5 esta semana', icon: Users },
        { label: 'Oraciones respondidas', value: '18', detail: 'Últimos 30 días', icon: Heart },
        { label: 'Eventos próximos', value: '11', detail: 'Mes actual', icon: Calendar }
    ];
    const stageSummary = [
        { label: 'Notificaciones', count: 12 },
        { label: 'Anuncios', count: 8 },
        { label: 'Mensajes', count: 5 },
        { label: 'Oración', count: 5 },
        { label: 'Eventos', count: 11 }
    ];
    const filterPills = [
        { label: 'Hoy', icon: Clock4 },
        { label: 'Esta semana', icon: Calendar },
        { label: 'Alta prioridad', icon: Zap },
        { label: 'Sin responsable', icon: UserMinus }
    ];
    const toolbarFilterChips = [
        { label: 'Filtro', icon: Filter },
        { label: 'Cerrada', icon: CheckCircle2 },
        { label: 'Persona asignada', icon: Users }
    ];
    const shareableTeams = ['Líderes', 'Comms', 'Pastoral', 'Campus Norte', 'Innovación'];
    const shareLink = 'https://app.ccf.community/hub';
    const priorityOptions: BoardItem['priority'][] = ['Alta', 'Media', 'Baja'];
    const statusOptions = ['Pendiente', 'En curso', 'Listo'];
    const [sharedTeams, setSharedTeams] = useState<string[]>(shareableTeams.slice(0, 3));
    const [shareOpen, setShareOpen] = useState(false);
    const [toast, setToast] = useState<{ message: string; type: 'success' | 'info' } | null>(null);
    const [isCreatingCard, setIsCreatingCard] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [newCard, setNewCard] = useState<NewCardForm>({
        columnId: initialBoardColumns[0]?.id ?? 'canales',
        name: '',
        stage: '',
        owner: '',
        due: '',
        priority: 'Media',
        status: 'Pendiente',
        comments: ''
    });
    const [columns, setColumns] = useState(initialBoardColumns);
    const [activeView, setActiveView] = useState<ViewId>('board');
    const [loadingCards, setLoadingCards] = useState(false);
    const [isSubmittingCard, setIsSubmittingCard] = useState(false);
    const visibleSharedTeams = sharedTeams.slice(0, 3);
    const extraSharedTeams = Math.max(sharedTeams.length - visibleSharedTeams.length, 0);
    const allItems = columns.flatMap((column) =>
        column.items.map((item, index) => ({ ...item, columnTitle: column.title, index }))
    );

    const hydrateColumns = useCallback((persistedCards: CommunityApiCard[]) => {
        const merged = initialBoardColumns.map((column) => ({
            ...column,
            items: [
                ...column.items,
                ...persistedCards
                    .filter((card) => card.column_id === column.id)
                    .map((card) => mapApiCardToBoardItem(card))
            ]
        }));
        setColumns(merged);
    }, []);

    const refreshBoardCards = useCallback(async () => {
        setLoadingCards(true);
        try {
            const response = await apiFetch<CommunityApiCard[]>(
                '/community/cards',
                token ? { token, cache: 'no-store' } : { cache: 'no-store' }
            );
            hydrateColumns(Array.isArray(response) ? response : []);
        } catch (error) {
            console.error('Error fetching community cards', error);
        } finally {
            setLoadingCards(false);
        }
    }, [token, hydrateColumns]);

    useEffect(() => {
        refreshBoardCards();
    }, [refreshBoardCards]);

    useEffect(() => {
        if (!toast) return;
        const timeout = setTimeout(() => setToast(null), 3500);
        return () => clearTimeout(timeout);
    }, [toast]);

    useEffect(() => {
        if (!shareOpen) return;
        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                setShareOpen(false);
            }
        };
        if (typeof window !== 'undefined') {
            window.addEventListener('keydown', handleKeyDown);
            return () => window.removeEventListener('keydown', handleKeyDown);
        }
    }, [shareOpen]);

    const navigateTo = (path: string) => () => {
        router.push(path);
    };

    const handleShareToggle = () => setShareOpen((prev) => !prev);

    const handleCopyShareLink = async () => {
        try {
            if (typeof navigator !== 'undefined' && navigator.clipboard) {
                await navigator.clipboard.writeText(shareLink);
                setToast({ message: 'Enlace copiado al portapapeles', type: 'success' });
            } else {
                throw new Error('Clipboard no disponible');
            }
        } catch (error) {
            console.warn(error);
            setToast({ message: `Copia manual: ${shareLink}`, type: 'info' });
        }
    };

    const handleTeamToggle = (team: string) => {
        setSharedTeams((prev) =>
            prev.includes(team) ? prev.filter((member) => member !== team) : [...prev, team]
        );
    };

    const resetNewCardForm = () => {
        setNewCard({
            columnId: columns[0]?.id ?? initialBoardColumns[0]?.id ?? 'canales',
            name: '',
            stage: '',
            owner: '',
            due: '',
            priority: 'Media',
            status: 'Pendiente',
            comments: ''
        });
    };

    const handleNewCardField = <K extends keyof NewCardForm>(field: K, value: NewCardForm[K]) => {
        setNewCard((prev) => ({ ...prev, [field]: value }));
    };

    const handleCreateCard = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!newCard.name.trim()) {
            setToast({ message: 'Agrega un nombre a la tarjeta', type: 'info' });
            return;
        }
        if (isSubmittingCard) return;
        const columnIndex = columns.findIndex((column) => column.id === newCard.columnId);
        if (columnIndex === -1) {
            setToast({ message: 'Selecciona una lista válida', type: 'info' });
            return;
        }
        const payload = {
            column_id: newCard.columnId,
            name: newCard.name.trim(),
            stage: newCard.stage.trim() || columns[columnIndex].title,
            owner: newCard.owner.trim() || 'Equipo Comunidad',
            due_date: newCard.due ? new Date(newCard.due).toISOString() : null,
            priority: newCard.priority,
            status: newCard.status.trim() || 'Pendiente',
            comments: newCard.comments.trim() || 'Sin comentarios',
            link: `/community/${newCard.columnId}`
        };
        try {
            setIsSubmittingCard(true);
            await apiFetch<CommunityApiCard>('/community/cards', {
                method: 'POST',
                token: token ?? undefined,
                body: payload
            });
            setToast({ message: 'Tarjeta agregada al tablero', type: 'success' });
            setIsCreatingCard(false);
            resetNewCardForm();
            await refreshBoardCards();
        } catch (error) {
            console.error('Error creating card', error);
            setToast({ message: 'No se pudo crear la tarjeta', type: 'info' });
        } finally {
            setIsSubmittingCard(false);
        }
    };

    const handleExportReport = () => {
        if (isExporting || typeof window === 'undefined') return;
        try {
            setIsExporting(true);
            const headerRow = 'Nombre,Columna,Estado,Prioridad,Responsable,Fecha límite';
            const rows = columns.flatMap((column) =>
                column.items.map((item) =>
                    [item.name, column.title, item.status, item.priority, item.owner, item.due].join(',')
                )
            );
            const csv = [headerRow, ...rows].join('\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'community-board.csv');
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
            setToast({ message: 'Reporte exportado en CSV', type: 'success' });
        } catch (error) {
            console.error(error);
            setToast({ message: 'No se pudo exportar el reporte', type: 'info' });
        } finally {
            setIsExporting(false);
        }
    };

    const renderBoardView = () => (
        <>
            <div className="flex flex-col gap-4 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4">
                <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                    <div className="flex flex-wrap gap-3">
                        {filterPills.map(({ label, icon }) => (
                            <CommunityToolbarChip key={label} label={label} icon={icon} size="md" />
                        ))}
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button className="px-4 h-8 rounded-lg border border-[hsl(var(--border))] text-[10px] font-medium uppercase tracking-wide flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                            <Filter size={14} /> Filtros
                        </button>
                        <button className="px-4 h-8 rounded-lg border border-[hsl(var(--border))] text-[10px] font-medium uppercase tracking-wide flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                            <SlidersHorizontal size={14} /> Columnas
                        </button>
                        <button className="px-4 h-8 rounded-lg border border-[hsl(var(--border))] text-[10px] font-medium uppercase tracking-wide flex items-center gap-2 text-[hsl(var(--text-secondary))]">
                            <RefreshCcw size={14} /> Actualizar
                        </button>
                    </div>
                </div>

                <div className="flex gap-4 overflow-x-auto pb-1">
                    {stageSummary.map((stage) => {
                        const Icon = summaryIcons[stage.label] || Tag;
                        return (
                            <div key={stage.label} className="min-w-[150px] rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] p-4 space-y-2">
                                <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    <Icon size={14} /> {stage.label}
                                </div>
                                <p className="text-lg font-semibold text-[hsl(var(--text-primary))]">{stage.count}</p>
                                <div className="w-full h-1 rounded-full bg-gradient-to-r from-[hsl(var(--primary))] to-transparent"></div>
                            </div>
                        );
                    })}
                </div>
            </div>

            <div className="-mx-4 sm:-mx-6 px-4 sm:px-4 pb-2 overflow-x-auto">
                <div className="flex gap-4 sm:gap-4 min-w-full snap-x snap-mandatory">
                    {columns.map((column) => {
                        const Icon = columnIcons[column.id];
                        return (
                            <div key={column.id} className="min-w-[280px] sm:min-w-[320px] snap-start flex-1">
                                <div className="bg-white dark:bg-slate-900/80 border border-[hsl(var(--border))] rounded-md p-4 shadow-xl flex flex-col h-full transition-transform duration-300 hover:-translate-y-1">
                                    <div className="flex items-start justify-between gap-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`size-9 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-center ${column.accent}`}>
                                                <Icon size={22} />
                                            </div>
                                            <div>
                                                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Lista</p>
                                                <h3 className="text-base font-semibold text-[hsl(var(--text-primary))]">{column.title}</h3>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Total</p>
                                            <p className="text-xl font-semibold text-[hsl(var(--text-primary))]">{column.items.length}</p>
                                        </div>
                                    </div>
                                    <p className="text-sm text-[hsl(var(--text-secondary))] mt-3">{column.description}</p>
                                    <button className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--text-primary))] text-[hsl(var(--surface-1))] text-[10px] font-semibold uppercase tracking-wide">
                                        <ArrowUpRight size={14} /> Crear tarjeta
                                    </button>

                                    <div className="mt-3 space-y-4">
                                        {column.items.map((item, idx) => {
                                            const watchers = [item.owner, 'Equipo Comunidad', 'Coordinación'];
                                            return (
                                                <div key={item.id} className="p-4 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] space-y-4 hover:border-[hsl(var(--primary)/0.4)] transition-colors">
                                                    <div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-[hsl(var(--border))] text-[hsl(var(--text-primary))] text-[9px] font-semibold">
                                                            <Tag size={12} /> {item.stage}
                                                        </span>
                                                        <span className="inline-flex items-center gap-1 font-semibold text-[hsl(var(--text-primary))]">
                                                            <Clock4 size={12} /> {item.due}
                                                        </span>
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-semibold text-[hsl(var(--text-primary))] tracking-tight">{item.name}</p>
                                                        <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium mt-1">{item.comments}</p>
                                                    </div>
                                                    <div className="grid grid-cols-2 gap-3 text-[11px] uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                                        <div>
                                                            <p className="mb-1">Prioridad</p>
                                                            <span className={`inline-flex items-center justify-center px-2 py-1 rounded-md border text-[10px] font-semibold tracking-wide ${priorityTone[item.priority]}`}>
                                                                {item.priority}
                                                            </span>
                                                        </div>
                                                        <div>
                                                            <p className="mb-1">Estado</p>
                                                            <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg border text-[10px] font-semibold tracking-wide ${statusTone}`}>
                                                                <CheckCircle2 size={14} /> {item.status}
                                                            </span>
                                                        </div>
                                                        <div>
                                                            <p className="mb-1">Persona</p>
                                                            <div className="flex items-center gap-2 text-[hsl(var(--text-primary))] font-semibold tracking-normal normal-case">
                                                                <div className="size-8 rounded-full bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] font-semibold text-[11px] flex items-center justify-center">
                                                                    {getInitials(item.owner)}
                                                                </div>
                                                                <span>{item.owner}</span>
                                                            </div>
                                                        </div>
                                                        <div>
                                                            <p className="mb-1">Seguimiento</p>
                                                            <p className="text-[hsl(var(--text-primary))] font-semibold tracking-normal normal-case">{column.title}</p>
                                                        </div>
                                                    </div>
                                                    <div className="flex items-center justify-between pt-1 border-t border-dashed border-[hsl(var(--border))] pt-3">
                                                        <div className="flex -space-x-2">
                                                            {watchers.slice(0, 3).map((person, watcherIdx) => (
                                                                <div key={watcherIdx} className={`size-8 rounded-full border border-white shadow-sm flex items-center justify-center text-[10px] font-semibold ${palette[(idx + watcherIdx) % palette.length]}`}>
                                                                    {getInitials(person)}
                                                                </div>
                                                            ))}
                                                        </div>
                                                        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))]">
                                                            <Link href={item.link} className="hover:underline">Abrir</Link>
                                                            <button className="inline-flex items-center gap-1 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]">
                                                                <MessageCircle size={14} />
                                                                Notas
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>
        </>
    );

    const renderListView = () => (
        <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-3">
            <div className="flex flex-wrap gap-2">
                {['Grupo: Estado', 'Subtareas', 'Columnas'].map((pill) => (
                    <CommunityToolbarChip key={pill} label={pill} size="md" />
                ))}
            </div>

            {columns.map((column) => (
                <div key={`${column.id}-list`} className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-[11px] font-semibold text-[hsl(var(--text-secondary))]">
                            <span className={`size-2 rounded-full ${columnAccentDot[column.id]}`}></span>
                            <span className="uppercase tracking-wide text-[10px] text-[hsl(var(--text-primary))]">{column.title}</span>
                            <span className="px-2 py-0.5 rounded-full bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[10px] font-medium">{column.items.length}</span>
                        </div>
                        <button className="text-[10px] font-medium uppercase tracking-wide text-[hsl(var(--primary))] flex items-center gap-2">
                            <Plus size={12} /> Nuevo
                        </button>
                    </div>

                    <div className="rounded-lg border border-[hsl(var(--border))] overflow-hidden bg-white">
                        <div className={`${listGridClass} text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))] bg-[hsl(var(--surface-2))] px-4 py-1.5`}>
                            <div className="text-center">#</div>
                            {listColumnHeaders.map((header) => (
                                <div key={header}>{header}</div>
                            ))}
                        </div>
                        {column.items.map((item, idx) => (
                            <CommunityListRow
                                key={`${column.id}-${item.id}-row`}
                                index={idx}
                                item={item}
                                accentClass={columnAccentDot[column.id]}
                                priorityClass={priorityTone[item.priority]}
                                statusClass={statusTone}
                            />
                        ))}
                    </div>
                </div>
            ))}

            <button className="text-[10px] font-medium uppercase tracking-wide text-[hsl(var(--text-secondary))] border border-dashed border-[hsl(var(--border))] rounded-lg px-4 py-2">
                + Nuevo estado
            </button>
        </div>
    );

    const renderCalendarView = () => (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {allItems.map((item) => (
                <div key={`${item.columnTitle}-${item.id}-cal`} className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-3 space-y-2">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">{item.due || 'Sin fecha'}</p>
                    <h4 className="text-sm font-semibold text-[hsl(var(--text-primary))]">{item.name}</h4>
                    <p className="text-[12px] text-[hsl(var(--text-secondary))]">{item.columnTitle} · {item.stage}</p>
                    <div className="flex justify-between items-center text-[11px] text-[hsl(var(--text-secondary))]">
                        <span>{item.owner}</span>
                        <span className="px-2 py-1 rounded-full bg-white text-[10px] font-semibold">{item.priority}</span>
                    </div>
                </div>
            ))}
        </div>
    );

    const renderGanttView = () => (
        <div className="space-y-4 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4">
            {allItems.map((item, idx) => {
                const progress = Math.min(100, 30 + (idx / (allItems.length || 1)) * 70);
                return (
                    <div key={`${item.columnTitle}-${item.id}-gantt`} className="space-y-1">
                        <div className="flex justify-between text-[11px] text-[hsl(var(--text-secondary))]">
                            <span>{item.name}</span>
                            <span>{item.due}</span>
                        </div>
                        <div className="h-3 rounded-full bg-[hsl(var(--surface-2))] overflow-hidden">
                            <div
                                className="h-full rounded-full bg-gradient-to-r from-[hsl(var(--primary))] to-[hsl(var(--primary)/0.4)]"
                                style={{ width: `${progress}%` }}
                            ></div>
                        </div>
                    </div>
                );
            })}
        </div>
    );

    const renderTableView = () => (
        <div className="overflow-x-auto rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
            <table className="min-w-full text-sm">
                <thead className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                    <tr>
                        <th className="text-left px-4 py-1.5">Nombre</th>
                        <th className="text-left px-4 py-1.5">Lista</th>
                        <th className="text-left px-4 py-1.5">Persona</th>
                        <th className="text-left px-4 py-1.5">Prioridad</th>
                        <th className="text-left px-4 py-1.5">Estado</th>
                        <th className="text-left px-4 py-1.5">Entrega</th>
                    </tr>
                </thead>
                <tbody>
                    {allItems.map((item) => (
                        <tr key={`${item.columnTitle}-${item.id}-table`} className="border-t border-[hsl(var(--border))]">
                            <td className="px-4 py-1.5 font-semibold text-[hsl(var(--text-primary))]">{item.name}</td>
                            <td className="px-4 py-1.5 text-[hsl(var(--text-secondary))]">{item.columnTitle}</td>
                            <td className="px-4 py-1.5 text-[hsl(var(--text-secondary))]">{item.owner}</td>
                            <td className="px-4 py-1.5">
                                <span className={`px-2 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wide ${priorityTone[item.priority]}`}>{item.priority}</span>
                            </td>
                            <td className="px-4 py-1.5 text-[hsl(var(--text-secondary))]">{item.status}</td>
                            <td className="px-4 py-1.5 text-[hsl(var(--text-secondary))]">{item.due}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );

    const renderActiveView = () => {
        switch (activeView) {
            case 'list':
                return renderListView();
            case 'calendar':
                return renderCalendarView();
            case 'gantt':
                return renderGanttView();
            case 'table':
                return renderTableView();
            default:
                return renderBoardView();
        }
    };

    return (
        <div className="space-y-4 animate-in fade-in duration-500 px-4 sm:px-4 pb-16 w-full">
            <div className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-4 py-1.5 flex flex-col gap-2 md:flex-row md:items-center md:justify-between text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                <div className="flex items-center gap-2">
                    <button type="button" onClick={navigateTo('/')} className="font-medium text-[hsl(var(--text-primary))] hover:text-[hsl(var(--primary))]">
                        CCF
                    </button>
                    <span>/</span>
                    <button type="button" onClick={navigateTo('/crm')} className="font-medium text-[hsl(var(--text-primary))] hover:text-[hsl(var(--primary))]">
                        CRM Pastoral
                    </button>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                    {(['table', 'board'] as ViewId[]).map((view) => (
                        <button
                            key={view}
                            onClick={() => setActiveView(view)}
                            className={`px-3 h-8 rounded-full border text-[9px] uppercase tracking-wide ${activeView === view ? 'bg-[hsl(var(--text-primary))] text-white font-semibold' : 'text-[hsl(var(--text-secondary))] font-normal'}`}
                        >
                            {view === 'table' ? 'Tabla' : 'Grid'}
                        </button>
                    ))}
                    <div className="relative w-[150px] hidden sm:block">
                        <Search size={10} className="absolute left-3 top-1/2 -translate-y-1/2 text-[hsl(var(--text-secondary))]" />
                        <input
                            placeholder="Buscar en esta vista..."
                            className="w-full h-8 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] pl-7 pr-3 text-[9px]"
                        />
                    </div>
                    <button className="p-1.5 rounded-full border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]"><Filter size={10} /></button>
                    <button className="p-1.5 rounded-full border border-[hsl(var(--border))] text-[hsl(var(--text-secondary))]"><Columns3 size={10} /></button>
                    <button className="p-1.5 rounded-full border border-[hsl(var(--text-primary))] text-[hsl(var(--text-primary))]"><SlidersHorizontal size={10} /></button>
                    <button className="px-3 h-8 rounded-full bg-slate-900 text-white text-[9px] font-semibold uppercase tracking-wide">+ Nuevo</button>
                </div>
            </div>
            <header className="rounded-lg border border-[hsl(var(--border))] bg-gradient-to-br from-[hsl(var(--surface-2))] to-[hsl(var(--surface-1))] p-4 md:p-3 space-y-3">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex items-center gap-3 text-[9px] font-medium uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        <button
                            type="button"
                            onClick={() => router.back()}
                            className="size-6 rounded-full border border-[hsl(var(--border))] flex items-center justify-center hover:text-[hsl(var(--primary))]"
                        >
                            <ArrowLeft size={16} />
                        </button>
                        <button type="button" onClick={navigateTo('/')} className="hover:text-[hsl(var(--primary))]">
                            Workspace
                        </button>
                        <span className="opacity-40">/</span>
                        <button type="button" onClick={navigateTo('/community')} className="hover:text-[hsl(var(--primary))]">
                            Comunidad
                        </button>
                        <span className="opacity-40">/</span>
                        <button
                            type="button"
                            onClick={() => setActiveView('board')}
                            className="text-[hsl(var(--primary))] hover:opacity-80"
                        >
                            Tablero
                        </button>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        <div className="flex -space-x-2 items-center">
                            {visibleSharedTeams.map((team, idx) => (
                                <div key={team} className={`size-8 rounded-full border border-white shadow-sm flex items-center justify-center text-[10px] font-semibold ${palette[idx % palette.length]}`}>
                                    {team.slice(0, 2).toUpperCase()}
                                </div>
                            ))}
                            {extraSharedTeams > 0 && (
                                <div className="size-8 rounded-full border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] text-[10px] font-medium flex items-center justify-center text-[hsl(var(--text-secondary))]">
                                    +{extraSharedTeams}
                                </div>
                            )}
                        </div>
                        <div className="relative">
                            <button
                                type="button"
                                onClick={handleShareToggle}
                                aria-expanded={shareOpen}
                                className="px-4 h-9 rounded-lg border border-[hsl(var(--border))] text-[10px] font-medium uppercase tracking-wide flex items-center gap-2 text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))]"
                            >
                                <Share2 size={14} /> Compartir acceso
                            </button>
                            {shareOpen && (
                                <div className="absolute right-0 z-10 mt-3 w-72 rounded-lg border border-[hsl(var(--border))] bg-white dark:bg-slate-900/90 shadow-xl p-4 space-y-4">
                                    <div className="flex items-center justify-between text-[11px] font-semibold text-[hsl(var(--text-primary))]">
                                        <span>Compartir tablero</span>
                                        <button type="button" onClick={() => setShareOpen(false)} className="text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]">
                                            Cerrar
                                        </button>
                                    </div>
                                    <div className="space-y-2">
                                        <p className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))]">Enlace rápido</p>
                                        <div className="flex items-center gap-2">
                                            <code className="flex-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-3 py-1.5 text-[11px] text-[hsl(var(--text-primary))] overflow-hidden text-ellipsis">
                                                {shareLink}
                                            </code>
                                            <button type="button" onClick={handleCopyShareLink} className="px-3 py-1.5 rounded-md bg-[hsl(var(--text-primary))] text-[10px] font-semibold uppercase tracking-wide text-white">
                                                Copiar
                                            </button>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        <p className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))]">Equipos</p>
                                        <div className="space-y-1.5 text-[12px] text-[hsl(var(--text-primary))]">
                                            {shareableTeams.map((team) => (
                                                <label key={team} className="flex items-center justify-between rounded-md border border-[hsl(var(--border))] px-3 py-2">
                                                    <span>{team}</span>
                                                    <input
                                                        type="checkbox"
                                                        className="accent-[hsl(var(--primary))] size-4"
                                                        checked={sharedTeams.includes(team)}
                                                        onChange={() => handleTeamToggle(team)}
                                                    />
                                                </label>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-4 text-[11px] font-semibold text-[hsl(var(--text-secondary))]">
                    <span className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))]">
                        <span className="size-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        En vivo - sincronizado hace 5 min
                    </span>
                    <span className="inline-flex items-center gap-2">
                        <Clock4 size={14} /> Próxima revisión: 6:00 p.m.
                    </span>
                </div>

                <div className="space-y-4">
                    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                        <div>
                            <h1 className="sr-only">Tablero comunitario</h1>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            <button
                                type="button"
                                onClick={handleExportReport}
                                disabled={isExporting}
                                className="px-4 h-9 rounded-lg border border-[hsl(var(--border))] text-[10px] font-semibold uppercase tracking-wide disabled:opacity-60 disabled:cursor-not-allowed"
                            >
                                Exportar reporte
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setIsCreatingCard((prev) => !prev);
                                    if (!isCreatingCard && shareOpen) {
                                        setShareOpen(false);
                                    }
                                    if (isCreatingCard) {
                                        resetNewCardForm();
                                    }
                                }}
                                aria-expanded={isCreatingCard}
                                className="px-4 h-9 rounded-lg bg-[hsl(var(--text-primary))] text-[hsl(var(--surface-1))] text-[10px] font-semibold uppercase tracking-wide"
                            >
                                {isCreatingCard ? 'Cerrar formulario' : 'Nueva tarjeta'}
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {metrics.map(({ label, value, detail, icon: Icon }) => (
                            <div key={label} className="rounded-lg bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] p-3 space-y-2.5">
                                <div className="flex items-center gap-3 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                                    <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--primary))]">
                                        <Icon size={16} />
                                    </div>
                                    <span>{label}</span>
                                </div>
                                <p className="text-lg md:text-xl font-semibold text-[hsl(var(--text-primary))]">{value}</p>
                                <p className="text-xs text-[hsl(var(--text-secondary))] font-medium">{detail}</p>
                                <div className="h-[3px] rounded-full bg-gradient-to-r from-[hsl(var(--primary))] via-transparent to-[hsl(var(--primary)/0.2)]"></div>
                            </div>
                        ))}
                    </div>

                    {isCreatingCard && (
                        <form onSubmit={handleCreateCard} className="space-y-4 rounded-lg border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-3">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <label className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] space-y-2">
                                    Lista destino
                                    <select
                                        value={newCard.columnId}
                                        onChange={(event) => handleNewCardField('columnId', event.target.value as ColumnId)}
                                        className="h-8 w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 text-sm text-[hsl(var(--text-primary))]"
                                    >
                                        {columns.map((column) => (
                                            <option key={column.id} value={column.id} className="text-black">
                                                {column.title}
                                            </option>
                                        ))}
                                    </select>
                                </label>
                                <label className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] space-y-2">
                                    Nombre
                                    <input
                                        value={newCard.name}
                                        onChange={(event) => handleNewCardField('name', event.target.value)}
                                        placeholder="Ej. Seguimiento visitas"
                                        className="h-8 w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 text-sm text-[hsl(var(--text-primary))]"
                                    />
                                </label>
                                <label className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] space-y-2">
                                    Etapa
                                    <input
                                        value={newCard.stage}
                                        onChange={(event) => handleNewCardField('stage', event.target.value)}
                                        placeholder="Mensajes, Oración, etc."
                                        className="h-8 w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 text-sm text-[hsl(var(--text-primary))]"
                                    />
                                </label>
                                <label className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] space-y-2">
                                    Responsable
                                    <input
                                        value={newCard.owner}
                                        onChange={(event) => handleNewCardField('owner', event.target.value)}
                                        placeholder="Equipo o persona"
                                        className="h-8 w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 text-sm text-[hsl(var(--text-primary))]"
                                    />
                                </label>
                                <label className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] space-y-2">
                                    Fecha límite
                                    <input
                                        type="date"
                                        value={newCard.due}
                                        onChange={(event) => handleNewCardField('due', event.target.value)}
                                        className="h-8 w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 text-sm text-[hsl(var(--text-primary))]"
                                    />
                                </label>
                                <label className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] space-y-2">
                                    Prioridad
                                    <select
                                        value={newCard.priority}
                                        onChange={(event) => handleNewCardField('priority', event.target.value as BoardItem['priority'])}
                                        className="h-8 w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 text-sm text-[hsl(var(--text-primary))]"
                                    >
                                        {priorityOptions.map((priority) => (
                                            <option key={priority} value={priority} className="text-black">
                                                {priority}
                                            </option>
                                        ))}
                                    </select>
                                </label>
                                <label className="text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] space-y-2">
                                    Estado
                                    <select
                                        value={newCard.status}
                                        onChange={(event) => handleNewCardField('status', event.target.value)}
                                        className="h-8 w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 text-sm text-[hsl(var(--text-primary))]"
                                    >
                                        {statusOptions.map((status) => (
                                            <option key={status} value={status} className="text-black">
                                                {status}
                                            </option>
                                        ))}
                                    </select>
                                </label>
                                <label className="md:col-span-2 text-[10px] uppercase tracking-wide text-[hsl(var(--text-secondary))] space-y-2">
                                    Comentarios
                                    <textarea
                                        value={newCard.comments}
                                        onChange={(event) => handleNewCardField('comments', event.target.value)}
                                        placeholder="Contexto rápido para el equipo"
                                        className="min-h-[96px] w-full rounded-lg border border-[hsl(var(--border))] bg-transparent px-3 py-2 text-sm text-[hsl(var(--text-primary))]"
                                    />
                                </label>
                            </div>
                            <div className="flex flex-wrap items-center justify-between gap-3">
                                <button
                                    type="button"
                                    onClick={() => {
                                        setIsCreatingCard(false);
                                        resetNewCardForm();
                                    }}
                                    className="px-4 h-10 rounded-lg border border-[hsl(var(--border))] text-[10px] font-medium uppercase tracking-wide text-[hsl(var(--text-secondary))]"
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSubmittingCard}
                                    className="px-4 h-10 rounded-lg bg-[hsl(var(--text-primary))] text-[hsl(var(--surface-1))] text-[10px] font-semibold uppercase tracking-wide disabled:opacity-60 disabled:cursor-not-allowed"
                                >
                                    {isSubmittingCard ? 'Guardando...' : 'Guardar tarjeta'}
                                </button>
                            </div>
                        </form>
                    )}
                </div>
            </header>

            <section className="space-y-2">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Vista tipo ClickUp</p>
                        <h2 className="text-lg font-semibold text-[hsl(var(--text-primary))]">Tablero operativo</h2>
                        <p className="text-[hsl(var(--text-secondary))] text-sm font-medium">Etapa, prioridad, responsables y comentarios agrupados por columna.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <button className="px-3 h-8 rounded-lg border border-[hsl(var(--border))] text-[10px] font-medium uppercase tracking-wide text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] transition-colors">
                            Compartir tablero
                        </button>
                        <button className="px-3 h-8 rounded-lg bg-[hsl(var(--text-primary))] text-[hsl(var(--surface-1))] text-[10px] font-semibold uppercase tracking-wide">
                            Crear nota
                        </button>
                    </div>
                </div>

                <div className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 space-y-4">
                    <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-3" aria-label="Vista toolbar">
                        <CommunityToolbarChip label="Añadir canal" icon={Plus} size="sm" />
                        <div className="flex flex-wrap items-center gap-1">
                            {viewOptions.map(({ id, label, icon }) => (
                                <CommunityToolbarChip
                                    key={id}
                                    label={label}
                                    icon={icon}
                                    active={activeView === id}
                                    variant={activeView === id ? 'solid' : 'outline'}
                                    onClick={() => setActiveView(id)}
                                    title={`Cambiar a ${label}`}
                                />
                            ))}
                            <CommunityToolbarChip label="+ Vista" variant="dashed" />
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        {toolbarFilterChips.map(({ label, icon }) => (
                            <CommunityToolbarChip key={label} label={label} icon={icon} size="sm" />
                        ))}
                        <CommunityToolbarChip label="Personalizar" icon={SlidersHorizontal} size="sm" />
                        <CommunityToolbarChip label="Add tarea" icon={Plus} variant="solid" className="bg-slate-900 text-white border-slate-900" />
                    </div>
                </div>
                    <p className="text-[11px] text-[hsl(var(--text-secondary))] flex items-center gap-3">
                        {viewOptions.find((view) => view.id === activeView)?.description}
                        {loadingCards && (
                            <span className="text-[9px] uppercase tracking-wide text-[hsl(var(--primary))]">
                                Sincronizando…
                            </span>
                        )}
                    </p>
                </div>

                {activeView === 'list' && <CommunityQuickCommentCard />}

                {renderActiveView()}
            </section>

            <section className="space-y-4">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div>
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Atajos rápidos</p>
                        <h2 className="text-lg font-semibold text-[hsl(var(--text-primary))]">Explora los módulos</h2>
                    </div>
                    <div className="text-sm text-[hsl(var(--text-secondary))] font-medium">
                        Selecciona una tarjeta para ir directamente al área correspondiente.
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {featureCards.map(({ title, description, icon: Icon, href, tone }) => (
                        <Link
                            key={title}
                            href={href}
                            className="group relative rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-4 overflow-hidden"
                        >
                            <div className={`absolute inset-0 bg-gradient-to-br ${tone} opacity-0 group-hover:opacity-100 transition-opacity`} />
                            <div className="relative flex items-start gap-4">
                                <div className="size-7 rounded-lg bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-center text-[hsl(var(--primary))] group-hover:scale-105 transition-transform">
                                    <Icon size={24} strokeWidth={2.5} />
                                </div>
                                <div className="flex-1 space-y-2">
                                    <div className="flex items-center gap-2">
                                        <h3 className="text-base font-semibold text-[hsl(var(--text-primary))] group-hover:text-[hsl(var(--primary))] transition-colors">{title}</h3>
                                        <ArrowUpRight size={18} className="text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--primary))]" />
                                    </div>
                                    <p className="text-sm text-[hsl(var(--text-secondary))] font-medium">{description}</p>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            </section>

            <section className="rounded-lg border border-dashed border-[hsl(var(--border))] bg-[hsl(var(--surface-3))] p-3 text-center space-y-4">
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">¿Falta algo?</p>
                <h3 className="text-lg font-semibold text-[hsl(var(--text-primary))]">Súmate al roadmap comunitario</h3>
                <p className="text-[hsl(var(--text-secondary))] max-w-xl mx-auto font-medium">
                    Mándanos tus ideas para mejorar este hub. Puedes proponer nuevos módulos, integraciones o métricas que faciliten la colaboración.
                </p>
                <button className="px-3 h-8 rounded-lg bg-[hsl(var(--text-primary))] text-[hsl(var(--surface-1))] font-semibold uppercase tracking-wide text-[10px]">
                    Enviar propuesta
                </button>
            </section>

            {toast && (
                <div
                    role="status"
                    aria-live="polite"
                    className={`fixed bottom-6 right-6 z-20 rounded-lg px-3 py-1.5 text-sm font-medium text-white shadow-lg ${
                        toast.type === 'success' ? 'bg-emerald-500' : 'bg-slate-600'
                    }`}
                >
                    {toast.message}
                </div>
            )}
        </div>
    );
}

