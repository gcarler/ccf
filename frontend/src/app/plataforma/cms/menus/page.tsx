"use client";

import React, { useState, useEffect, useMemo } from 'react';
import { toast } from "sonner";
import { SITE_KEY } from '@/lib/site-config';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Archive, Link2, Plus, RotateCcw, X,
    ExternalLink, ChevronRight, Zap,
    GripVertical, Save
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import SidePanel from '@/components/ui/SidePanel';
import clsx from 'clsx';
import { createCmsMenu, createCmsMenuItem, deleteCmsMenuItem as archiveCmsMenuItem, listCmsMenuItems, listCmsMenus, listCmsSites, patchCmsMenu, patchCmsMenuItem, reorderCmsMenuItems } from '@/lib/cms/v2';
import { CmsMenu, CmsMenuItem, CmsSite } from '@/types/cms-v2';
import { ApiError } from '@/lib/http';
import { canEditCms } from '@/lib/cms/permissions';

interface MenuItem {
    id: string;
    parent_id?: string | null;
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

function sanitizeKey(value: string) {
    return value.toLowerCase().trim().replace(/\s+/g, "-").replace(/[^a-z0-9_-]/g, "");
}

export default function CmsMenusManagement() {
    const { token, user } = useAuth();
    const [sites, setSites] = useState<CmsSite[]>([]);
    const [siteKey, setSiteKey] = useState(SITE_KEY);
    const [menus, setMenus] = useState<CmsMenu[]>([]);
    const [menuKey, setMenuKey] = useState("main");
    const [navConfig, setNavConfig] = useState<NavConfig>({ items: [] });
    const [loading, setLoading] = useState(true);
    const [menuLoading, setMenuLoading] = useState(false);
    const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
    const [newItemLabel, setNewItemLabel] = useState("");
    const [newItemHref, setNewItemHref] = useState("");
    const [newMenuName, setNewMenuName] = useState("");
    const [newMenuKey, setNewMenuKey] = useState("");
    const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
    const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
    const [draggedId, setDraggedId] = useState<string | null>(null);
    const canEdit = canEditCms(user?.role);
    const selectedMenu = useMemo(() => menus.find((menu) => menu.menu_key === menuKey) || null, [menus, menuKey]);

    const wouldCreateCycle = (itemId: string, parentId: string | null) => {
        if (parentId == null) return false;
        if (itemId === parentId) return true;
        const byId = new Map(navConfig.items.map((item) => [item.id, item]));
        let cursor = byId.get(parentId);
        const visited = new Set<string>();
        while (cursor) {
            if (visited.has(cursor.id)) return true;
            visited.add(cursor.id);
            if (cursor.id === itemId) return true;
            cursor = cursor.parent_id ? byId.get(cursor.parent_id) : undefined;
        }
        return false;
    };

    const displayedItems = useMemo(() => {
        const byParent = new Map<string | null, MenuItem[]>();
        navConfig.items.forEach((item) => {
            const key = item.parent_id ?? null;
            const arr = byParent.get(key) || [];
            arr.push(item);
            byParent.set(key, arr);
        });
        byParent.forEach((items) => items.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)));

        const result: Array<{ item: MenuItem; depth: number }> = [];
        const walk = (parentId: string | null, depth: number) => {
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
        loadSites();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token]);

    useEffect(() => {
        loadMenus();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token, siteKey]);

    useEffect(() => {
        fetchNav();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token, siteKey, menuKey]);

    const loadSites = async () => {
        if (!token) return;
        try {
            const rows = await listCmsSites(token);
            const nextSites = Array.isArray(rows) ? rows : [];
            setSites(nextSites);
            if (nextSites.length > 0 && !nextSites.some((site) => site.site_key === siteKey)) {
                setSiteKey(nextSites[0].site_key);
            }
        } catch (error) {
      toast.error("Error al cargar sitios CMS");
        }
    };

    const loadMenus = async () => {
        if (!token || !siteKey) return;
        setMenuLoading(true);
        setSelectedItem(null);
        setSelectedIndex(null);
        try {
            const rows = await listCmsMenus(siteKey, token);
            const nextMenus = Array.isArray(rows) ? rows : [];
            setMenus(nextMenus);
            if (nextMenus.length === 0) {
                setMenuKey("");
                setNavConfig({ items: [] });
                return;
            }
            if (!nextMenus.some((menu) => menu.menu_key === menuKey)) {
                const mainMenu = nextMenus.find((menu) => menu.menu_key === "main");
                setMenuKey((mainMenu || nextMenus[0]).menu_key);
            }
        } catch (error) {
      toast.error("Error al cargar menús CMS");
            setMenus([]);
            setMenuKey("");
            setNavConfig({ items: [] });
        } finally {
            setMenuLoading(false);
        }
    };

    const fetchNav = async () => {
        if (!token || !siteKey || !menuKey) {
            setLoading(false);
            setNavConfig({ items: [] });
            return;
        }
        setLoading(true);
        try {
            const items = await listCmsMenuItems(siteKey, menuKey, token);
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
            if (!(error instanceof ApiError && error.status === 404)) {
      toast.error("Error al cargar items del menú");
            }
            setNavConfig({ items: [] });
        } finally {
            setLoading(false);
        }
    };

    const handleCreateMenu = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!token || !siteKey || !canEdit) return;
        const key = sanitizeKey(newMenuKey || newMenuName);
        const name = newMenuName.trim() || key;
        if (!key || !name) return;
        try {
            const created = await createCmsMenu(siteKey, { menu_key: key, name, is_active: true }, token);
            setMenus((prev) => [...prev.filter((menu) => menu.menu_key !== created.menu_key), created]);
            setMenuKey(created.menu_key);
            setNewMenuName("");
            setNewMenuKey("");
            setNavConfig({ items: [] });
        } catch (error) {
      toast.error("Error al crear menú");
        }
    };

    const handleToggleMenuActive = async () => {
        if (!token || !canEdit || !siteKey || !selectedMenu) return;
        try {
            const updated = await patchCmsMenu(siteKey, selectedMenu.menu_key, { is_active: !selectedMenu.is_active }, token);
            setMenus((prev) => prev.map((menu) => menu.id === updated.id ? updated : menu));
        } catch (error) {
      toast.error("Error al actualizar menú");
        }
    };

    const handleAddItem = async (e?: React.FormEvent) => {
        if (e) e.preventDefault();
        if (!newItemLabel.trim() || !newItemHref.trim() || !canEdit || !siteKey || !menuKey) return;

        try {
            await createCmsMenuItem(
                siteKey,
                menuKey,
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
            toast.error('Error al crear item');
        }
    };

    const handleToggleItemVisibility = async (index: number) => {
        if (!canEdit || !siteKey || !menuKey) return;
        const target = navConfig.items[index];
        if (!target) return;
        try {
            if (target.visibility === "hidden") {
                await patchCmsMenuItem(siteKey, menuKey, target.id, { visibility: "public" }, token);
            } else {
                await archiveCmsMenuItem(siteKey, menuKey, target.id, token);
            }
            fetchNav();
        } catch (error) {
            toast.error('Error al actualizar visibilidad');
        }
        if (selectedIndex === index) {
            setSelectedItem(null);
            setSelectedIndex(null);
        }
    };

    const handleUpdateItem = async (index: number, updatedItem: MenuItem) => {
        if (!canEdit || !siteKey || !menuKey) return;
        const target = navConfig.items[index];
        if (!target) return;
        try {
            await patchCmsMenuItem(
                siteKey,
                menuKey,
                target.id,
                {
                    label: updatedItem.label,
                    href: updatedItem.href,
                    is_external: !!updatedItem.is_external,
                    parent_id: updatedItem.parent_id ?? null,
                    visibility: updatedItem.visibility || "public",
                    sort_order: updatedItem.sort_order,
                },
                token,
            );
            setSelectedItem(updatedItem);
            fetchNav();
        } catch (error) {
            toast.error('Error al actualizar item');
        }
    };

    const moveItem = async (index: number, direction: 'up' | 'down') => {
        if (!canEdit || !siteKey || !menuKey) return;
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
                siteKey,
                menuKey,
                normalized.map((item) => ({ id: item.id, parent_id: item.parent_id ?? null, sort_order: item.sort_order ?? 0 })),
                token,
            );
            fetchNav();
        } catch (error) {
            toast.error('Error al reordenar');
        }
    };

    const applyMenuReorder = async (items: MenuItem[]) => {
        if (!canEdit || !siteKey || !menuKey) return;
        const normalized = items.map((item, index) => ({ ...item, sort_order: index }));
        setNavConfig({ items: normalized });
        try {
            await reorderCmsMenuItems(
                siteKey,
                menuKey,
                normalized.map((item) => ({ id: item.id, parent_id: item.parent_id ?? null, sort_order: item.sort_order ?? 0 })),
                token,
            );
            fetchNav();
        } catch (error) {
            toast.error('Error al aplicar orden');
        }
    };

    const moveToRoot = async (itemId: string) => {
        if (!canEdit) return;
        const next = navConfig.items.map((item) => item.id === itemId ? { ...item, parent_id: null } : item);
        await applyMenuReorder(next);
    };

    const makeChildOf = async (itemId: string, parentId: string) => {
        if (!canEdit) return;
        if (itemId === parentId) return;
        if (wouldCreateCycle(itemId, parentId)) return;
        const next = navConfig.items.map((item) => item.id === itemId ? { ...item, parent_id: parentId } : item);
        await applyMenuReorder(next);
    };

    const moveRelativeTo = async (itemId: string, targetId: string, position: 'before' | 'after') => {
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
        <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-primary))]">
            {/* TOOLBAR */}
            <header className="min-h-8 border-b border-[hsl(var(--border))] dark:border-white/5 flex flex-wrap items-center px-3 py-3 gap-3 shrink-0">
                <div className="flex items-center gap-2 flex-1">
                    <Link2 size={16} className="text-[hsl(var(--primary))]" />
                    <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">
                        NAVEGACION CMS
                    </h2>
                </div>
                
                <div className="flex flex-wrap items-center gap-2">
                    <select
                        value={siteKey}
                        onChange={(event) => setSiteKey(event.target.value)}
                        className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] px-3 py-1.5 text-[11px] font-bold"
                    >
                        {sites.length === 0 && <option value={siteKey}>{siteKey}</option>}
                        {sites.map((site) => (
                            <option key={site.site_key} value={site.site_key}>{site.name} ({site.site_key})</option>
                        ))}
                    </select>
                    <select
                        value={menuKey}
                        onChange={(event) => setMenuKey(event.target.value)}
                        disabled={menus.length === 0 || menuLoading}
                        className="rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] px-3 py-1.5 text-[11px] font-bold disabled:opacity-50"
                    >
                        {menus.length === 0 && <option value="">Sin menus</option>}
                        {menus.map((menu) => (
                            <option key={menu.id} value={menu.menu_key}>
                                {menu.name} ({menu.menu_key}){menu.is_active ? "" : " - inactivo"}
                            </option>
                        ))}
                    </select>
                    {selectedMenu && (
                        <button
                            onClick={handleToggleMenuActive}
                            disabled={!canEdit}
                            className="inline-flex items-center gap-2 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50"
                            title={selectedMenu.is_active ? "Desactivar menu publico" : "Activar menu publico"}
                        >
                            {selectedMenu.is_active ? <Archive size={14} /> : <RotateCcw size={14} />}
                            {selectedMenu.is_active ? "Desactivar" : "Activar"}
                        </button>
                    )}
                    <button 
                        onClick={() => setIsQuickAddOpen(!isQuickAddOpen)}
                        disabled={!canEdit || !menuKey}
                        className="bg-[hsl(var(--primary))] text-white px-4 py-1.5 rounded-lg text-[11px] font-semibold uppercase tracking-wide shadow-xl shadow-blue-500/20 hover:bg-[hsl(var(--primary))] active:scale-95 transition-all flex items-center gap-2 disabled:opacity-50"
                    >
                        <Plus size={14} />
                        Añadir Enlace
                    </button>
                </div>
            </header>

            <form
                onSubmit={handleCreateMenu}
                className="border-b border-[hsl(var(--border))] dark:border-white/5 px-3 py-3 flex flex-wrap items-center gap-3 bg-[hsl(var(--surface-1))]/60 dark:bg-white/[0.02]"
            >
                <p className="text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Nuevo menu</p>
                <input
                    value={newMenuName}
                    onChange={(event) => {
                        setNewMenuName(event.target.value);
                        if (!newMenuKey.trim()) setNewMenuKey(sanitizeKey(event.target.value));
                    }}
                    placeholder="Nombre del menu"
                    disabled={!canEdit}
                    className="min-w-48 flex-1 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] px-3 py-2 text-xs disabled:opacity-50"
                />
                <input
                    value={newMenuKey}
                    onChange={(event) => setNewMenuKey(sanitizeKey(event.target.value))}
                    placeholder="menu_key"
                    disabled={!canEdit}
                    className="w-40 rounded-lg border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] px-3 py-2 text-xs disabled:opacity-50"
                />
                <button
                    type="submit"
                    disabled={!canEdit || !siteKey || !sanitizeKey(newMenuKey || newMenuName)}
                    className="rounded-lg border border-blue-200 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--primary))] disabled:opacity-50"
                >
                    Crear menu
                </button>
            </form>

            {/* QUICK ADD BAR (VIOLET) */}
            <AnimatePresence>
                {isQuickAddOpen && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="bg-blue-50 dark:bg-blue-900/10 border-b-2 border-blue-300 dark:border-blue-500/30 overflow-hidden shrink-0"
                    >
                        <form 
                            onSubmit={handleAddItem}
                            className="px-3 py-1.5 flex items-center gap-4"
                        >
                            <div className="size-8 rounded-lg bg-[hsl(var(--primary))] text-white flex items-center justify-center shrink-0">
                                <Zap size={16} />
                            </div>
                            <div className="flex-1 flex gap-3">
                                <input 
                                    autoFocus
                                    value={newItemLabel}
                                    onChange={(e) => setNewItemLabel(e.target.value)}
                                    placeholder="Nombre del enlace..."
                                    disabled={!canEdit}
                                    className="flex-1 bg-transparent border-none text-sm font-bold text-blue-900 dark:text-blue-200 placeholder:text-[hsl(var(--primary))] focus:ring-0"
                                />
                                <input 
                                    value={newItemHref}
                                    onChange={(e) => setNewItemHref(e.target.value)}
                                    placeholder="URL (ej: /contacto o https://...)"
                                    disabled={!canEdit}
                                    className="flex-1 bg-transparent border-none text-sm font-medium text-[hsl(var(--primary))] dark:text-blue-300 placeholder:text-[hsl(var(--primary))] focus:ring-0"
                                />
                            </div>
                            <div className="flex items-center gap-2">
                                <button 
                                    type="submit"
                                    disabled={!canEdit || !menuKey}
                                    className="bg-[hsl(var(--primary))] text-white px-3 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wide disabled:opacity-50"
                                >
                                    GUARDAR
                                </button>
                                <button 
                                    type="button"
                                    onClick={() => setIsQuickAddOpen(false)}
                                    className="p-1.5 hover:bg-blue-200 dark:hover:bg-blue-800/30 rounded-lg text-[hsl(var(--primary))] transition-all"
                                >
                                    <X size={14} />
                                </button>
                            </div>
                        </form>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* LIST AREA */}
 <div className="flex-1 overflow-y-auto custom-scrollbar p-3 w-full">
                {loading ? (
                    <div className="space-y-4">
                        {[1, 2, 3].map(i => (
                            <div key={i} className="h-8 bg-[hsl(var(--surface-1))] dark:bg-white/5 rounded-lg animate-pulse" />
                        ))}
                    </div>
                ) : !menuKey ? (
                    <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-60">
                        <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
                            <Link2 size={32} />
                        </div>
                        <div>
                            <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white">Sin menu seleccionado</p>
                            <p className="text-sm text-[hsl(var(--text-secondary))]">Crea un menu para este sitio y luego agrega enlaces.</p>
                        </div>
                    </div>
                ) : navConfig.items.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-center space-y-4 opacity-50">
                        <div className="size-8 rounded-lg bg-[hsl(var(--surface-2))] dark:bg-white/5 flex items-center justify-center text-[hsl(var(--text-secondary))]">
                            <Link2 size={32} />
                        </div>
                        <div>
                            <p className="font-bold text-[hsl(var(--text-primary))] dark:text-white">Menú vacío</p>
                            <p className="text-sm text-[hsl(var(--text-secondary))]">Comienza a construir la navegación de tu sitio.</p>
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
                            className="rounded-md border border-dashed border-[hsl(var(--border))] dark:border-white/20 px-4 py-2 text-[10px] font-semibold uppercase tracking-wide text-[hsl(var(--text-secondary))]"
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
                                    className="h-2 rounded-md border border-dashed border-transparent hover:border-blue-300 dark:hover:border-blue-500/40"
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
                                    className={clsx(
                                        "group rounded-lg border p-4 shadow-sm hover:shadow-md transition-all cursor-pointer flex items-center gap-4",
                                        item.visibility === "hidden"
                                            ? "bg-[hsl(var(--surface-1))] dark:bg-white/[0.03] border-dashed border-[hsl(var(--border))] dark:border-white/10 opacity-75"
                                            : "bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border-[hsl(var(--border))]/70 dark:border-white/5"
                                    )}
                                    style={{ marginLeft: `${depth * 16}px` }}
                                >
                                    <div className="p-2 text-[hsl(var(--text-secondary))] group-hover:text-[hsl(var(--text-secondary))] transition-colors">
                                        <GripVertical size={16} />
                                    </div>
                                    
                                    <div className="flex-1 min-w-0">
                                        <h3 className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white">
                                            {item.label}
                                        </h3>
                                        <p className="text-[11px] text-[hsl(var(--text-secondary))] font-medium">
                                            {item.href}
                                        </p>
                                    </div>

                                    {item.is_external && (
                                        <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold bg-[hsl(var(--surface-2))] dark:bg-white/5 text-[hsl(var(--text-secondary))] uppercase tracking-wide">
                                            EXTERNO
                                        </span>
                                    )}
                                    {item.visibility === "hidden" && (
                                        <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold bg-amber-50 dark:bg-amber-500/10 text-amber-700 uppercase tracking-wide">
                                            OCULTO
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
                                            className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-all"
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
                                            className="p-2 hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-secondary))] transition-all"
                                            title="Bajar"
                                        >
                                            <ChevronRight size={14} className="rotate-90" />
                                        </button>
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                const sourceIndex = navConfig.items.findIndex((entry) => entry.id === item.id);
                                                handleToggleItemVisibility(sourceIndex);
                                            }}
                                            disabled={!canEdit}
                                            title={item.visibility === "hidden" ? "Restaurar enlace" : "Ocultar enlace"}
                                            className="p-2 hover:bg-amber-50 dark:hover:bg-amber-500/10 rounded-md text-[hsl(var(--text-secondary))] hover:text-amber-700 transition-all"
                                        >
                                            {item.visibility === "hidden" ? <RotateCcw size={16} /> : <Archive size={16} />}
                                        </button>
                                    </div>
                                    <ChevronRight size={16} className="text-[hsl(var(--text-secondary))]" />
                                </motion.div>
                                <div
                                    onDragOver={(e) => e.preventDefault()}
                                    onDrop={async () => {
                                        if (!draggedId || draggedId === item.id) return;
                                        await moveRelativeTo(draggedId, item.id, 'after');
                                        setDraggedId(null);
                                    }}
                                    className="h-2 rounded-md border border-dashed border-transparent hover:border-blue-300 dark:hover:border-blue-500/40"
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
                    <div className="space-y-3">
                        <section className="space-y-4">
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                                    TEXTO DEL ENLACE
                                </label>
                                <input 
                                    type="text"
                                    value={selectedItem.label}
                                    onChange={(e) => handleUpdateItem(selectedIndex, { ...selectedItem, label: e.target.value })}
                                    disabled={!canEdit}
                                    className="w-full px-3 py-2.5 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md focus:ring-2 focus:ring-[hsl(var(--primary))]/30 transition-all font-bold"
                                />
                            </div>
                            
                            <div className="space-y-1.5">
                                <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                                    DESTINO (URL)
                                </label>
                                <input 
                                    type="text"
                                    value={selectedItem.href}
                                    onChange={(e) => handleUpdateItem(selectedIndex, { ...selectedItem, href: e.target.value })}
                                    disabled={!canEdit}
                                    className="w-full px-3 py-2.5 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md focus:ring-2 focus:ring-[hsl(var(--primary))]/30 transition-all"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                                    PADRE (SUBMENÚ)
                                </label>
                                <select
                                    value={selectedItem.parent_id ?? ''}
                                    onChange={(e) => handleUpdateItem(selectedIndex, {
                                        ...selectedItem,
                                        parent_id: e.target.value || null,
                                    })}
                                    disabled={!canEdit}
                                    className="w-full px-3 py-2.5 text-[13px] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--border))] dark:border-white/10 rounded-md focus:ring-2 focus:ring-[hsl(var(--primary))]/30 transition-all"
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

                        <section className="pt-6 border-t border-[hsl(var(--border))] dark:border-white/5 space-y-3">
                            <p className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                                VISIBILIDAD
                            </p>
                            <div className="grid grid-cols-2 gap-2">
                                <button
                                    type="button"
                                    onClick={() => handleUpdateItem(selectedIndex, { ...selectedItem, visibility: "public" })}
                                    disabled={!canEdit}
                                    className={clsx(
                                        "rounded-md border px-3 py-2 text-[10px] font-semibold uppercase tracking-wide transition-all",
                                        selectedItem.visibility !== "hidden"
                                            ? "border-blue-200 bg-blue-50 text-[hsl(var(--primary))] dark:border-blue-500/30 dark:bg-blue-500/10"
                                            : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] dark:border-white/10"
                                    )}
                                >
                                    Publico
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleUpdateItem(selectedIndex, { ...selectedItem, visibility: "hidden" })}
                                    disabled={!canEdit}
                                    className={clsx(
                                        "rounded-md border px-3 py-2 text-[10px] font-semibold uppercase tracking-wide transition-all",
                                        selectedItem.visibility === "hidden"
                                            ? "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-500/30 dark:bg-amber-500/10"
                                            : "border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] dark:border-white/10"
                                    )}
                                >
                                    Oculto
                                </button>
                            </div>
                        </section>

                        <section className="pt-6 border-t border-[hsl(var(--border))] dark:border-white/5">
                            <button 
                                onClick={() => handleUpdateItem(selectedIndex, { ...selectedItem, is_external: !selectedItem.is_external })}
                                disabled={!canEdit}
                                className={clsx(
                                    "w-full flex items-center justify-between p-4 rounded-lg border transition-all",
                                    selectedItem.is_external 
                                        ? "bg-blue-50 dark:bg-blue-500/10 border-blue-200 dark:border-blue-500/30" 
                                        : "bg-[hsl(var(--surface-1))] dark:bg-white/5 border-transparent"
                                )}
                            >
                                <div className="flex items-center gap-3 text-left">
                                    <div className={clsx(
                                        "size-10 rounded-md flex items-center justify-center transition-all",
                                        selectedItem.is_external ? "bg-[hsl(var(--primary))] text-white" : "bg-[hsl(var(--surface-3))] dark:bg-white/10 text-[hsl(var(--text-secondary))]"
                                    )}>
                                        <ExternalLink size={18} />
                                    </div>
                                    <div>
                                        <p className="text-[13px] font-bold text-[hsl(var(--text-primary))] dark:text-white">Abrir en nueva pestaña</p>
                                        <p className="text-[11px] text-[hsl(var(--text-secondary))]">Marcar como enlace externo</p>
                                    </div>
                                </div>
                                <div className={clsx(
                                    "size-6 rounded-full border-2 flex items-center justify-center transition-all",
                                    selectedItem.is_external ? "border-blue-600" : "border-[hsl(var(--border))] dark:border-white/10"
                                )}>
                                    {selectedItem.is_external && <div className="size-3 bg-[hsl(var(--primary))] rounded-full" />}
                                </div>
                            </button>
                        </section>

                        <div className="pt-8 space-y-3">
                            <button 
                                onClick={() => {
                                    setSelectedItem(null);
                                    setSelectedIndex(null);
                                }}
                                className="w-full bg-[hsl(var(--bg-muted))] dark:bg-[hsl(var(--bg-primary))] text-white dark:text-[hsl(var(--text-primary))] py-3 rounded-md text-[11px] font-semibold uppercase tracking-wide shadow-xl hover:opacity-90 active:scale-95 transition-all flex items-center justify-center gap-2"
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
