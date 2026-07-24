"use client";

import { useState } from 'react';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, TaskSupplyRecord } from '@/types/projects';
import { Boxes, Loader2, Trash2 } from 'lucide-react';

export default function TaskSupplySection({
    task,
    supplies,
    onSuppliesChange,
    token,
    onActivityCreated,
}: {
    task: ProjectTaskRecord;
    supplies: TaskSupplyRecord[];
    onSuppliesChange: (supplies: TaskSupplyRecord[]) => void;
    token: string | null;
    onActivityCreated?: () => void;
}) {
    const [newSupplyName, setNewSupplyName] = useState('');
    const [newSupplyQuantity, setNewSupplyQuantity] = useState(1);
    const [creatingSupply, setCreatingSupply] = useState(false);
    const [savingSupplyId, setSavingSupplyId] = useState<string | null>(null);
    const [deletingSupplyId, setDeletingSupplyId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    const handleAddSupply = async () => {
        if (!token || !newSupplyName.trim()) return;
        setCreatingSupply(true);
        try {
            const created = await apiFetch<TaskSupplyRecord>(
                `/projects/${task.project_id}/tasks/${task.id}/supplies`,
                {
                    method: 'POST',
                    token,
                    body: { item_name: newSupplyName.trim(), quantity: Math.max(1, newSupplyQuantity || 1), status: 'pending' },
                }
            );
            const nextSupplies = [...supplies, created];
            onSuppliesChange(nextSupplies);
            onActivityCreated?.();
            setNewSupplyName('');
            setNewSupplyQuantity(1);
        } catch {
            setError('No se pudo crear el insumo.');
        } finally { setCreatingSupply(false); }
    };

    const handleUpdateSupply = async (
        supply: TaskSupplyRecord,
        patch: Partial<Pick<TaskSupplyRecord, 'item_name' | 'quantity' | 'status'>>,
    ) => {
        if (!token) return;
        const optimistic = supplies.map(item => item.id === supply.id ? { ...item, ...patch } : item);
        onSuppliesChange(optimistic);
        setSavingSupplyId(supply.id);
        try {
            const updated = await apiFetch<TaskSupplyRecord>(
                `/projects/${task.project_id}/tasks/${task.id}/supplies/${supply.id}`,
                { method: 'PATCH', token, body: patch }
            );
            onSuppliesChange(optimistic.map(item => item.id === updated.id ? updated : item));
            onActivityCreated?.();
        } catch {
            setError('No se pudo actualizar el insumo.');
        } finally { setSavingSupplyId(null); }
    };

    const handleDeleteSupply = async (supplyId: string) => {
        if (!token) return;
        setDeletingSupplyId(supplyId);
        try {
            await apiFetch(`/projects/${task.project_id}/tasks/${task.id}/supplies/${supplyId}`, { method: 'DELETE', token });
            const nextSupplies = supplies.filter(s => s.id !== supplyId);
            onSuppliesChange(nextSupplies);
            onActivityCreated?.();
        } catch {
            setError('No se pudo eliminar el insumo.');
        } finally { setDeletingSupplyId(null); }
    };

    return (
        <section className="px-4 py-3 border-b border-[hsl(var(--border))] dark:border-white/[0.05]">
            {error && (
                <div className="mb-2 rounded-md border border-[hsl(var(--warning)/25%)] bg-warning-soft p-2 text-warning-text dark:border-[hsl(var(--warning)/100%)]/20 dark:bg-[hsl(var(--warning))]/10 dark:text-[hsl(var(--warning))]">
                    <p className="text-[10px] font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}

            <div className="mb-3 flex items-center justify-between">
                <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                    <Boxes size={11} /> Insumos
                    <span className="rounded bg-[hsl(var(--surface-2))] px-1.5 py-0.5 text-[9px] font-bold text-[hsl(var(--text-secondary))] dark:bg-white/[0.06] dark:text-[hsl(var(--text-secondary))]">
                        {supplies.length}
                    </span>
                </p>
            </div>

            <div className="space-y-2">
                {supplies.length === 0 && (
                    <p className="text-[11px] italic text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))]">
                        Sin insumos registrados.
                    </p>
                )}

                {supplies.map(supply => (
                    <div
                        key={supply.id}
                        className="grid grid-cols-[minmax(0,1fr)_72px_110px] items-center gap-2 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 dark:border-white/[0.06] dark:bg-white/[0.03]"
                    >
                        <input
                            value={supply.item_name}
                            onChange={event => onSuppliesChange(supplies.map(item => item.id === supply.id ? { ...item, item_name: event.target.value } : item))}
                            onBlur={event => {
                                const value = event.target.value.trim();
                                const original = task.supplies?.find(item => item.id === supply.id);
                                if (value && value !== original?.item_name) handleUpdateSupply(supply, { item_name: value });
                            }}
                            className="min-w-0 bg-transparent text-[12px] font-bold text-[hsl(var(--text-primary))] outline-none dark:text-[hsl(var(--text-secondary))]"
                        />
                        <input
                            type="number"
                            min={1}
                            value={supply.quantity}
                            onChange={event => {
                                const quantity = Math.max(1, Number(event.target.value) || 1);
                                onSuppliesChange(supplies.map(item => item.id === supply.id ? { ...item, quantity } : item));
                            }}
                            onBlur={event => {
                                const quantity = Math.max(1, Number(event.target.value) || 1);
                                const original = task.supplies?.find(item => item.id === supply.id);
                                if (quantity !== original?.quantity) handleUpdateSupply(supply, { quantity });
                            }}
                            className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-[11px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
                        />
                        <select
                            value={supply.status}
                            disabled={savingSupplyId === supply.id}
                            onChange={event => handleUpdateSupply(supply, { status: event.target.value })}
                            className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1.5 text-[11px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
                        >
                            <option value="pending">Pendiente</option>
                            <option value="ready">Listo</option>
                            <option value="unavailable">No disponible</option>
                        </select>
                        <button
                            onClick={() => handleDeleteSupply(supply.id)}
                            disabled={deletingSupplyId === supply.id}
                            title="Eliminar insumo"
                            className="p-1.5 rounded-md text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--danger))] hover:bg-danger-soft dark:hover:bg-[hsl(var(--danger))]/10 transition-colors disabled:opacity-50"
                        >
                            {deletingSupplyId === supply.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                        </button>
                    </div>
                ))}
            </div>

            <div className="mt-3 grid grid-cols-[minmax(0,1fr)_72px_auto] gap-2">
                <input
                    value={newSupplyName}
                    onChange={event => setNewSupplyName(event.target.value)}
                    onKeyDown={event => event.key === 'Enter' && handleAddSupply()}
                    placeholder="Nuevo insumo"
                    className="min-w-0 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-3 py-2 text-[12px] font-medium outline-none dark:border-white/10 dark:bg-white/5"
                />
                <input
                    type="number"
                    min={1}
                    value={newSupplyQuantity}
                    onChange={event => setNewSupplyQuantity(Math.max(1, Number(event.target.value) || 1))}
                    className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-2 text-[12px] font-bold outline-none dark:border-white/10 dark:bg-white/5"
                />
                <button
                    onClick={handleAddSupply}
                    disabled={creatingSupply || !newSupplyName.trim()}
                    className="rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-[10px] font-semibold uppercase tracking-wide text-white disabled:opacity-50"
                >
                    {creatingSupply ? '...' : 'Agregar'}
                </button>
            </div>
        </section>
    );
}
