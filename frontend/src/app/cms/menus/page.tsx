"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Link2, Search, Plus, Trash2, 
    ExternalLink, ChevronRight, Zap,
    GripVertical, Settings2, Save
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import SidePanel from '@/components/ui/SidePanel';
import clsx from 'clsx';
import { createCmsMenu, createCmsMenuItem, deleteCmsMenuItem, listCmsMenuItems, patchCmsMenuItem, reorderCmsMenuItems } from '@/lib/cms/v2';
import { CmsMenuItem } from '@/types/cms-v2';
import { ApiError } from '@/lib/http';
import { canEditCms } from '@/lib/cms/permissions';

interface MenuItem {
    id: number;
    parent_id?: number | null;
    label: string;
    href: string;
    is_external?: boolean;
    target?: string;
    visibility?: string;
    sort_order?: number;
}

interface NavConfig {
    items: MenuItem[];
}

export default function CmsMenusManagement() {
    const { token, user } = useAuth();
    const SITE_KEY = 'faro';
    const MENU_KEY = 'main';
    const [navConfig, setNavConfig] = useState<NavConfig>({ items: [] });
    const [loading, setLoading] = useState(true);
    const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
    const [newItemLabel, setNewItemLabel] = useState("");
    const [newItemHref, setNewItemHref] = useState("");
    const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
    const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
    const [draggedId, setDraggedId] = useState<number | null>(null);
    const canEdit = canEditCms(user?.role);

    const wouldCreateCycle = (itemId: number, parentId: number | null) => {
        if (parentId == null) return false;
        if (itemId === parentId) return true;
        const byId = new Map(navConfig.items.map((item) => [item.id, item]));
        let cursor = byId.get(parentId);
        const visited = new Set<number>();
        while (cursor) {
            if (visited.has(cursor.id)) return true;
            visited.add(cursor.id);
            if (cursor.id === itemId) return true;
            cursor = cursor.parent_id ? byId.get(cursor.parent_id) : undefined;
        }
        return false;
    };

    const displayedItems = useMemo(() => {
        const byParent = new Map<number | null, MenuItem[]>();
        navConfig.items.forEach((item) => {
            const key = item.parent_id ?? null;
            const arr = byParent.get(key) || [];
            arr.push(item);
            byParent.set(key, arr);
        });
        byParent.forEach((items) => items.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)));

        const result: Array<{ item: MenuItem; depth: number }> = [];
        const walk = (parentId: number | null, depth: number) => {
            const children = byParent.get(parentId) || [];
            children.forEach((child) => {
                result.push({ item: child, depth });
                walk(child.id, depth + 1);
            });
        };
        walk(null, 0);
        return result;
    }, [navConfig.items]);

    useEffect(() => {
        fetchNav();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    const fetchNav = async () => {
        if (!token) return;
        try {
            const items = await listCmsMenuItems(SITE_KEY, MENU_KEY, token);
            const sorted = (Array.isArray(items) ? items : [])
                .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
                .map((item: CmsMenuItem) => ({
                    id: item.id,
                    parent_id: item.parent_id,
                    label: item.label,
                    href: item.href,
                    is_external: item.is_external,
                    target: item.target,
                    visibility: item.visibility,
                    sort_order: item.sort_order,
                }));
            setNavConfig({ items: sorted });
        } catch (error) {
            if (error instanceof ApiError && error.status === 404) {
                try {
                    await createCmsMenu(SITE_KEY, { menu_key: MENU_KEY, name: 'Menu principal', is_active: true }, token);
                    const items = await listCmsMenuItems(SITE_KEY, MENU_KEY, token);
                    const sorted = (Array.isArray(items) ? items : [])
                        .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
                        .map((item: CmsMenuItem) => ({
                            id: item.id,
                            parent_id: item.parent_id,
                            label: item.label,
                            href: item.href,
                            is_external: item.is_external,
                            target: item.target,
                            visibility: item.visibility,
                            sort_order: item.sort_order,
                        }));
                    setNavConfig({ items: sorted });
                } catch (nestedError) {
                    console.error('Error creating default menu:', nestedError);
                }
            } else {
                console.error("Error fetching nav:", error);
            }
        } finally {
            setLoading(false);
        }
    };

    const handleAddItem = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!newItemLabel.trim() || !newItemHref.trim() || !canEdit) return;

        try {
            await createCmsMenuItem(
                SITE_KEY,
                MENU_KEY,
                {
                    label: newItemLabel,
                    href: newItemHref,
                    is_external: newItemHref.startsWith('http'),
                    sort_order: navConfig.items.length,
                    parent_id: null,
                },
                token,
            );
            setNewItemLabel("");
            setNewItemHref("");
            setIsQuickAddOpen(false);
            fetchNav();
        } catch (error) {
            console.error('Error creating menu item:', error);
        }
    };

    const handleDeleteItem = async (index: number) => {
        if (!canEdit) return;
        const target = navConfig.items[index];
        if (!target) return;
        try {
            await deleteCmsMenuItem(SITE_KEY, MENU_KEY, target.id, token);
            fetchNav();
        } catch (error) {
            console.error('Error deleting menu item:', error);
        }
        if (selectedIndex === index) {
            setSelectedItem(null);
            setSelectedIndex(null);
        }
    };

    const handleUpdateItem = async (index: number, updatedItem: MenuItem) => {
        if (!canEdit) return;
        const target = navConfig.items[index];
        if (!target) return;
        try {
            await patchCmsMenuItem(
                SITE_KEY,
                MENU_KEY,
                target.id,
                {
                    label: updatedItem.label,
                    href: updatedItem.href,
                    is_external: !!updatedItem.is_external,
                    parent_id: updatedItem.parent_id ?? null,
                    sort_order: updatedItem.sort_order,
                },
                token,
            );
            setSelectedItem(updatedItem);
            fetchNav();
        } catch (error) {
            console.error('Error updating menu item:', error);
        }
    };

    const moveItem = async (index: number, direction: 'up' | 'down') => {
        if (!canEdit) return;
        const targetIndex = direction === 'up' ? index - 1 : index + 1;
        if (targetIndex < 0 || targetIndex >= navConfig.items.length) return;
        const reordered = [...navConfig.items];
        const current = reordered[index];
        reordered[index] = reordered[targetIndex];
        reordered[targetIndex] = current;
        const normalized = reordered.map((item, idx) => ({ ...item, sort_order: idx }));
        setNavConfig({ items: normalized });
        try {
            await reorderCmsMenuItems(
                SITE_KEY,
                MENU_KEY,
                normalized.map((item) => ({ id: item.id, parent_id: item.parent_id ?? null, sort_order: item.sort_order ?? 0 })),
                token,
            );
            fetchNav();
        } catch (error) {
            console.error('Error reordering menu items:', error);
        }
    };

    const applyMenuReorder = async (items: MenuItem[]) => {
        if (!canEdit) return;
        const normalized = items.map((item, index) => ({ ...item, sort_order: index }));
        setNavConfig({ items: normalized });
        try {
            await reorderCmsMenuItems(
                SITE_KEY,
                MENU_KEY,
                normalized.map((item) => ({ id: item.id, parent_id: item.parent_id ?? null, sort_order: item.sort_order ?? 0 })),
                token,
            );
            fetchNav();
        } catch (error) {
            console.error('Error applying menu reorder:', error);
        }
    };

    const moveToRoot = async (itemId: number) => {
        if (!canEdit) return;
        const next = navConfig.items.map((item) => item.id === itemId ? { ...item, parent_id: null } : item);
        await applyMenuReorder(next);
    };

    const makeChildOf = async (itemId: number, parentId: number) => {
        if (!canEdit) return;
        if (itemId === parentId) return;
        if (wouldCreateCycle(itemId, parentId)) return;
        const next = navConfig.items.map((item) => item.id === itemId ? { ...item, parent_id: parentId } : item);
        await applyMenuReorder(next);
    };

    const moveRelativeTo = async (itemId: number, targetId: number, position: 'before' | 'after') => {
        if (!canEdit) return;
        if (itemId === targetId) return;
        const current = navConfig.items.find((item) => item.id === itemId);
        const target = navConfig.items.find((item) => item.id === targetId);
        if (!current || !target) return;

        const parentId = target.parent_id ?? null;
        if (wouldCreateCycle(itemId, parentId)) return;

        const withoutCurrent = navConfig.items.filter((item) => item.id !== itemId);
        const targetIndex = withoutCurrent.findIndex((item) => item.id === targetId);
        if (targetIndex < 0) return;
        const nextCurrent = { ...current, parent_id: parentId };
        const insertIndex = position === 'before' ? targetIndex : targetIndex + 1;
        const next = [
            ...withoutCurrent.slice(0, insertIndex),
            nextCurrent,
            ...withoutCurrent.slice(insertIndex),
        ];
        await applyMenuReorder(next);
    };

    return (
        <div className="flex flex-col h-full bg-white dark:bg-[#141517]">
            {/* TOOLBAR */}
            <header className="h-14 border-b border-slate-100 dark:border-white/5 flex items-center px-6 gap-4 shrink-0">
                <div className="flex items-center gap-2 flex-1">
                    <Link2 size={16} className="text-violet-600" />
                    <h2 className="text-[11px] font-black uppercase tracking-widest text-slate-400">
                        NAVEGACIÓN PRINCIPAL
                    </h2>
                </div>
                
                <div className="flex items-center gap-2">
                    <button 
                        onClick={() => setIsQuickAddOpen(!isQuickAddOpen)}
                        disabled={!canEdit}
                        className="bg-violet-600 text-white px-4 py-1.5 rounded-lg text-[11px] font-black uppercase tracking-widest shadow-xl shadow-violet-500/20 hover:bg-violet-700 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50"
                    >
                        <Plus size={14} />
                        Añadir Enlace
                    </button>
                </div>
            </header>

            {/* QUICK ADD BAR (VIOLET) */}
            <AnimatePresence>
                {isQuickAddOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-violet-50 dark:bg-violet-900/10 border-b-2 border-violet-300 dark:border-violet-500/30 overflow-hidden shrink-0"
                    >
                        <form 
                            onSubmit={handleAddItem}
                            className="px-6 py-4 flex items-center gap-4"
                        >
                            <div className="size-8 rounded-lg bg-violet-600 text-white flex items-center justify-center shrink-0">
                                <Zap size={16} />
                            </div>
                            <div className="flex-1 flex gap-3">
                                <input 
                                    autoFocus
                                    value={newItemLabel}
                                    onChange={(e) => setNewItemLabel(e.target.value)}
                                    placeholder="Nombre del enlace..."
                                    disabled={!canEdit}
                                    className="flex-1 bg-transparent border-none text-[15px] font-bold text-violet-900 dark:text-violet-200 placeholder:text-violet-400 focus:ring-0"
                                />
                                <input 
                                    value={newItemHref}
                                    onChange={(e) => setNewItemHref(e.target.value)}
                                    placeholder="URL (ej: /contacto o https://...)"
                                    disabled={!canEdit}
                                    className="flex-1 bg-transparent border-none text-[15px] font-medium text-violet-700 dark:text-violet-300 placeholder:text-violet-400 focus:ring-0"
                                />
                            </div>
                            <div className="flex items-center gap-2">
                                <button 
                                    type="submit"
                                    disabled={!canEdit}
                                    className="bg-violet-600 text-white px-3 py-1 rounded-lg text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
                                >
                                    GUARDAR
                                </button>
                                <button 
                                    type="button"
                                    onClick={() => setIsQuickAddOpen(false)}
                                    className="p-1.5 hover:bg-violet-200 dark:hover:bg-violet-800/30 rounded-lg text-violet-500 transition-all"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </form>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* LIST AREA */}
            <div className="flex-1 overflow-y-auto custom-scrollbar p-6 max-w-4xl mx-auto w-full">
                {loading ? (
                    <div className="space-y-4">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-16 bg-slate-50 dark:bg-white/5 rounded-2xl animate-pulse" />
                        ))}
                    </div>
                ) : navConfig.items.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
                        <div className="size-16 rounded-[2rem] bg-slate-100 dark:bg-white/5 flex items-center justify-center text-slate-400">
                            <Link2 size={32} />
                        </div>
                        <div>
                            <p className="font-bold text-slate-900 dark:text-white">Menú vacío</p>
                            <p className="text-sm text-slate-500">Comienza a construir la navegación de tu sitio.</p>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-3">
                        <div
                            onDragOver={(e) => e.preventDefault()}
                            onDrop={async () => {
                                if (!draggedId) return;
                                await moveToRoot(draggedId);
                                setDraggedId(null);
                            }}
                            className="rounded-xl border border-dashed border-slate-300 dark:border-white/20 px-4 py-2 text-[10px] font-black uppercase tracking-widest text-slate-400"
                        >
                            Soltar aquí para mover a nivel raíz
                        </div>
                        {displayedItems.map(({ item, depth }, index) => (
                            <React.Fragment key={item.id}>
                                <div
                                    onDragOver={(e) => e.preventDefault()}
                                    onDrop={async () => {
                                        if (!draggedId || draggedId === item.id) return;
                                        await moveRelativeTo(draggedId, item.id, 'before');
                                        setDraggedId(null);
                                    }}
                                    className="h-2 rounded-md border border-dashed border-transparent hover:border-violet-300 dark:hover:border-violet-500/40"
                                    style={{ marginLeft: `${depth * 16}px` }}
                                />
                                <motion.div
                                    initial={{ opacity: 0, x: -16 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.04 }}
                                    onClick={() => {
                                        const sourceIndex = navConfig.items.findIndex((entry) => entry.id === item.id);
                                        setSelectedItem(item);
                                        setSelectedIndex(sourceIndex);
                                    }}
                                    draggable={canEdit}
                                    onDragStart={() => setDraggedId(item.id)}
                                    onDragOver={(e) => e.preventDefault()}
                                    onDrop={async () => {
                                        if (!draggedId || draggedId === item.id) return;
                                        await makeChildOf(draggedId, item.id);
                                        setDraggedId(null);
                                    }}
                                    onDragEnd={() => setDraggedId(null)}
                                    className="group bg-white dark:bg-[#252528] rounded-2xl border border-slate-200/70 dark:border-white/5 p-4 shadow-sm hover:shadow-md transition-all cursor-pointer flex items-center gap-4"
                                    style={{ marginLeft: `${depth * 16}px` }}
                                >
                                    <div className="p-2 text-slate-300 group-hover:text-slate-500 transition-colors">
                                        <GripVertical size={16} />
                                    </div>
                                    
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-[13px] font-bold text-slate-900 dark:text-white">
                                            {item.label}
                                        </h3>
                                        <p className="text-[11px] text-slate-400 font-medium">
                                            {item.href}
                                        </p>
                                    </div>

                                    {item.is_external && (
                                        <span className="px-2 py-0.5 rounded-full text-[9px] font-black bg-slate-100 dark:bg-white/5 text-slate-500 uppercase tracking-widest">
                                            EXTERNO
                                        </span>
                                    )}

                                    <div className="opacity-0 group-hover:opacity-100 transition-all flex items-center gap-1">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                const sourceIndex = navConfig.items.findIndex((entry) => entry.id === item.id);
                                                moveItem(sourceIndex, 'up');
                                            }}
                                            disabled={!canEdit}
                                            className="p-2 hover:bg-slate-100 dark:hover:bg-white/10 rounded-xl text-slate-400 hover:text-slate-600 transition-all"
                                            title="Subir"
                                        >
                                            <ChevronRight size={14} className="-rotate-90" />
                                        </button>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                const sourceIndex = navConfig.items.findIndex((entry) => entry.id === item.id);
                                                moveItem(sourceIndex, 'down');
                                            }}
                                            disabled={!canEdit}
                                            className="p-2 hover:bg-slate-100 dark:hover:bg-white/10 rounded-xl text-slate-400 hover:text-slate-600 transition-all"
                                            title="Bajar"
                                        >
                                            <ChevronRight size={14} className="rotate-90" />
                                        </button>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                const sourceIndex = navConfig.items.findIndex((entry) => entry.id === item.id);
                                                handleDeleteItem(sourceIndex);
                                            }}
                                            disabled={!canEdit}
                                            className="p-2 hover:bg-rose-50 dark:hover:bg-rose-500/10 rounded-xl text-slate-400 hover:text-rose-600 transition-all"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                    <ChevronRight size={16} className="text-slate-300" />
                                </motion.div>
                                <div
                                    onDragOver={(e) => e.preventDefault()}
                                    onDrop={async () => {
                                        if (!draggedId || draggedId === item.id) return;
                                        await moveRelativeTo(draggedId, item.id, 'after');
                                        setDraggedId(null);
                                    }}
                                    className="h-2 rounded-md border border-dashed border-transparent hover:border-violet-300 dark:hover:border-violet-500/40"
                                    style={{ marginLeft: `${depth * 16}px` }}
                                />
                            </React.Fragment>
                        ))}
                    </div>
                )}
            </div>

            {/* SIDE PANEL DETAILS */}
            <SidePanel
                isOpen={!!selectedItem}
                onClose={() => {
                    setSelectedItem(null);
                    setSelectedIndex(null);
                }}
                title={selectedItem?.label || "Editar Enlace"}
                subtitle="Configuración de navegación"
            >
                {selectedItem && selectedIndex !== null && (
                    <div className="space-y-6">
                        <section className="space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">
                                    TEXTO DEL ENLACE
                                </label>
                                <input 
                                    type="text"
                                    value={selectedItem.label}
                                    onChange={(e) => handleUpdateItem(selectedIndex, { ...selectedItem, label: e.target.value })}
                                    disabled={!canEdit}
                                    className="w-full px-3 py-2.5 text-[13px] bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-violet-500/30 transition-all font-bold"
                                />
                            </div>
                            
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">
                                    DESTINO (URL)
                                </label>
                                <input 
                                    type="text"
                                    value={selectedItem.href}
                                    onChange={(e) => handleUpdateItem(selectedIndex, { ...selectedItem, href: e.target.value })}
                                    disabled={!canEdit}
                                    className="w-full px-3 py-2.5 text-[13px] bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-violet-500/30 transition-all"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-black uppercase tracking-[0.15em] text-slate-400">
                                    PADRE (SUBMENÚ)
                                </label>
                                <select
                                    value={selectedItem.parent_id ?? ''}
                                    onChange={(e) => handleUpdateItem(selectedIndex, {
                                        ...selectedItem,
                                        parent_id: e.target.value && !wouldCreateCycle(selectedItem.id, Number(e.target.value))
                                            ? Number(e.target.value)
                                            : null,
                                    })}
                                    disabled={!canEdit}
                                    className="w-full px-3 py-2.5 text-[13px] bg-white dark:bg-[#252528] border border-slate-200 dark:border-white/10 rounded-xl focus:ring-2 focus:ring-violet-500/30 transition-all"
                                >
                                    <option value="">Sin padre (nivel raíz)</option>
                                    {navConfig.items
                                        .filter((item) => item.id !== selectedItem.id)
                                        .map((item) => (
                                            <option key={item.id} value={item.id}>{item.label}</option>
                                        ))}
                                </select>
                            </div>
                        </section>

                        <section className="pt-6 border-t border-slate-100 dark:border-white/5">
                            <button 
                                onClick={() => handleUpdateItem(selectedIndex, { ...selectedItem, is_external: !selectedItem.is_external })}
                                disabled={!canEdit}
                                className={clsx(
                                    "w-full flex items-center justify-between p-4 rounded-2xl border transition-all",
                                    selectedItem.is_external 
                                        ? "bg-violet-50 dark:bg-violet-500/10 border-violet-200 dark:border-violet-500/30" 
                                        : "bg-slate-50 dark:bg-white/5 border-transparent"
                                )}
                            >
                                <div className="flex items-center gap-3 text-left">
                                    <div className={clsx(
                                        "size-10 rounded-xl flex items-center justify-center transition-all",
                                        selectedItem.is_external ? "bg-violet-600 text-white" : "bg-slate-200 dark:bg-white/10 text-slate-400"
                                    )}>
                                        <ExternalLink size={18} />
                                    </div>
                                    <div>
                                        <p className="text-[13px] font-bold text-slate-900 dark:text-white">Abrir en nueva pestaña</p>
                                        <p className="text-[11px] text-slate-500">Marcar como enlace externo</p>
                                    </div>
                                </div>
                                <div className={clsx(
                                    "size-6 rounded-full border-2 flex items-center justify-center transition-all",
                                    selectedItem.is_external ? "border-violet-600" : "border-slate-300 dark:border-white/10"
                                )}>
                                    {selectedItem.is_external && <div className="size-3 bg-violet-600 rounded-full" />}
                                </div>
                            </button>
                        </section>

                        <div className="pt-8 space-y-3">
                            <button 
                                onClick={() => {
                                    setSelectedItem(null);
                                    setSelectedIndex(null);
                                }}
                                className="w-full bg-slate-900 dark:bg-white text-white dark:text-slate-900 py-3 rounded-xl text-[11px] font-black uppercase tracking-widest shadow-xl hover:opacity-90 active:scale-95 transition-all flex items-center justify-center gap-2"
                            >
                                <Save size={14} />
                                CERRAR Y LISTO
                            </button>
                        </div>
                    </div>
                )}
            </SidePanel>
        </div>
    );
}

