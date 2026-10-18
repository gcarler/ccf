"use client";

import { useRef, useState } from 'react';
import { apiFetch } from '@/lib/http';
import type { ProjectTaskRecord, TaskSupplyRecord } from '@/types/projects';
import { Boxes, CheckCircle2, DollarSign, Loader2, Trash2 } from 'lucide-react';

export default function TaskSupplySection({
    task,
    supplies,
    onSuppliesChange,
    deletingSupplyId = null,
    onDeleteRequest = () => {},
    token,
    onActivityCreated,
}: {
    task: ProjectTaskRecord;
    supplies: TaskSupplyRecord[];
    onSuppliesChange: (supplies: TaskSupplyRecord[]) => void;
    deletingSupplyId?: string | null;
    onDeleteRequest?: (supplyId: string) => void;
    token: string | null;
    onActivityCreated?: () => void;
}) {
    const [newSupplyName, setNewSupplyName] = useState('');
    const [newSupplyQuantity, setNewSupplyQuantity] = useState(1);
    const [newSupplyUnitCost, setNewSupplyUnitCost] = useState(0);
    const [autoCreateExpense, setAutoCreateExpense] = useState(true);
    const [creatingSupply, setCreatingSupply] = useState(false);
    const [savingSupplyId, setSavingSupplyId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const persistedSuppliesRef = useRef({ taskId: task.id, items: supplies });
    if (persistedSuppliesRef.current.taskId !== task.id) {
        persistedSuppliesRef.current = { taskId: task.id, items: supplies };
    }

    const computeSupplyTotal = (s: Pick<TaskSupplyRecord, 'quantity' | 'unit_cost' | 'total_cost'>) => {
        if (typeof s.total_cost === 'number' && s.total_cost > 0) return s.total_cost;
        return Math.round((s.quantity || 0) * (s.unit_cost || 0) * 100) / 100;
    };

    const totalSuppliesCost = supplies.reduce((acc, s) => acc + computeSupplyTotal(s), 0);

    const handleAddSupply = async () => {
        if (!token || !newSupplyName.trim()) return;
        setError(null);
        setCreatingSupply(true);
        try {
            const quantityVal = Math.max(1, newSupplyQuantity || 1);
            const unitCostVal = Math.max(0, Number(newSupplyUnitCost) || 0);
            const totalCostVal = Math.round(quantityVal * unitCostVal * 100) / 100;
            const created = await apiFetch<TaskSupplyRecord>(
                `/projects/${task.project_id}/tasks/${task.id}/supplies`,
                {
                    method: 'POST',
                    token,
                    body: {
                        item_name: newSupplyName.trim(),
                        quantity: quantityVal,
                        status: 'pending',
                        unit_cost: unitCostVal,
                        total_cost: totalCostVal,
                        auto_create_expense: autoCreateExpense,
                    },
                }
            );
            const nextSupplies = [...supplies, created];
            persistedSuppliesRef.current.items = [...persistedSuppliesRef.current.items, created];
            onSuppliesChange(nextSupplies);
            onActivityCreated?.();
            setNewSupplyName('');
            setNewSupplyQuantity(1);
            setNewSupplyUnitCost(0);
        } catch {
            setError('No se pudo crear el insumo.');
        } finally { setCreatingSupply(false); }
    };

    const handleUpdateSupply = async (
        supply: TaskSupplyRecord,
        patch: Partial<Pick<TaskSupplyRecord, 'item_name' | 'quantity' | 'status' | 'unit_cost' | 'total_cost' | 'auto_create_expense'>>,
    ) => {
        if (!token) return;
        setError(null);
        const persistedSupply = persistedSuppliesRef.current.items.find(item => item.id === supply.id) ?? supply;
        const optimistic = supplies.map(item => item.id === supply.id ? { ...item, ...patch } : item);
        onSuppliesChange(optimistic);
        setSavingSupplyId(supply.id);
        try {
            const updated = await apiFetch<TaskSupplyRecord>(
                `/projects/${task.project_id}/tasks/${task.id}/supplies/${supply.id}`,
                { method: 'PATCH', token, body: patch }
            );
            persistedSuppliesRef.current.items = persistedSuppliesRef.current.items.map(item => item.id === updated.id ? updated : item);
            onSuppliesChange(optimistic.map(item => item.id === updated.id ? updated : item));
            onActivityCreated?.();
        } catch {
            const rolledBack = supplies.map(item => item.id === persistedSupply.id ? persistedSupply : item);
            onSuppliesChange(rolledBack);
            setError('No se pudo actualizar el insumo.');
        } finally { setSavingSupplyId(null); }
    };

    return (
        <section aria-labelledby="task-supplies-heading" className="px-4 py-3 border-b border-[hsl(var(--border))]">
            {error && (
                <div role="alert" className="mb-2 rounded-md border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning)/0.1)] p-2 text-[hsl(var(--warning))]">
                    <p className="text-2xs font-bold uppercase tracking-wide">{error}</p>
                </div>
            )}

            <div className="mb-3 flex items-center justify-between gap-2 flex-wrap">
                <h3 id="task-supplies-heading" className="flex items-center gap-1.5 text-2xs font-semibold uppercase tracking-wider text-[hsl(var(--muted-foreground))]">
                    <Boxes size={11} /> Insumos
                    <span className="rounded bg-[hsl(var(--surface-2))] px-1.5 py-0.5 text-2xs font-bold text-[hsl(var(--muted-foreground))]">
                        {supplies.length}
                    </span>
                </h3>
                <span className="inline-flex items-center gap-1 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--foreground))]">
                    <DollarSign size={10} className="text-[hsl(var(--primary))]" />
                    Costo Total Insumos: ${totalSuppliesCost.toLocaleString('es-CO')}
                </span>
            </div>

            <div className="space-y-2">
                {supplies.length === 0 && (
                    <p className="text-xs italic text-[hsl(var(--muted-foreground))]">
                        Sin insumos registrados.
                    </p>
                )}

                {supplies.map(supply => {
                    const rowTotal = computeSupplyTotal(supply);
                    const linkedExpenseId = supply.linked_expense_id || supply.expense_id || null;
                    return (
                        <div
                            key={supply.id}
                            className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 space-y-1.5"
                        >
                            <div className="grid grid-cols-[minmax(0,1fr)_56px_84px_104px_32px] items-center gap-1">
                                <input
                                    aria-label={`Nombre del insumo ${supply.item_name}`}
                                    disabled={savingSupplyId === supply.id}
                                    value={supply.item_name}
                                    onChange={event => onSuppliesChange(supplies.map(item => item.id === supply.id ? { ...item, item_name: event.target.value } : item))}
                                    onBlur={event => {
                                        const value = event.target.value.trim();
                                        const original = persistedSuppliesRef.current.items.find(item => item.id === supply.id);
                                        if (value && value !== original?.item_name) handleUpdateSupply(supply, { item_name: value });
                                    }}
                                    className="min-w-0 bg-transparent text-sm font-bold text-[hsl(var(--foreground))] outline-none"
                                />
                                <input
                                    type="number"
                                    aria-label={`Cantidad de ${supply.item_name}`}
                                    disabled={savingSupplyId === supply.id}
                                    min={1}
                                    value={supply.quantity}
                                    onChange={event => {
                                        const quantity = Math.max(1, Number(event.target.value) || 1);
                                        onSuppliesChange(supplies.map(item => item.id === supply.id ? { ...item, quantity } : item));
                                    }}
                                    onBlur={event => {
                                        const quantity = Math.max(1, Number(event.target.value) || 1);
                                        const original = persistedSuppliesRef.current.items.find(item => item.id === supply.id);
                                        if (quantity !== original?.quantity) handleUpdateSupply(supply, { quantity });
                                    }}
                                    className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-xs font-bold text-[hsl(var(--foreground))] outline-none"
                                />
                                <input
                                    type="number"
                                    step="0.01"
                                    min={0}
                                    aria-label={`Costo unitario de ${supply.item_name}`}
                                    disabled={savingSupplyId === supply.id}
                                    value={supply.unit_cost ?? 0}
                                    onChange={event => {
                                        const unit_cost = Math.max(0, Number(event.target.value) || 0);
                                        const total_cost = Math.round((supply.quantity || 1) * unit_cost * 100) / 100;
                                        onSuppliesChange(supplies.map(item => item.id === supply.id ? { ...item, unit_cost, total_cost } : item));
                                    }}
                                    onBlur={event => {
                                        const unit_cost = Math.max(0, Number(event.target.value) || 0);
                                        const original = persistedSuppliesRef.current.items.find(item => item.id === supply.id);
                                        if (unit_cost !== (original?.unit_cost ?? 0)) {
                                            handleUpdateSupply(supply, { unit_cost });
                                        }
                                    }}
                                    className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-xs font-bold text-[hsl(var(--foreground))] outline-none"
                                />
                                <select
                                    aria-label={`Estado de ${supply.item_name}`}
                                    value={supply.status}
                                    disabled={savingSupplyId === supply.id}
                                    onChange={event => handleUpdateSupply(supply, { status: event.target.value })}
                                    className="rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-1.5 text-xs font-bold text-[hsl(var(--foreground))] outline-none"
                                >
                                    <option value="pending">Pendiente</option>
                                    <option value="ready">Listo</option>
                                    <option value="approved">Aprobado</option>
                                    <option value="purchased">Comprado</option>
                                    <option value="received">Recibido</option>
                                    <option value="paid">Pagado</option>
                                    <option value="unavailable">No disponible</option>
                                </select>
                                <button
                                    type="button"
                                    onClick={() => onDeleteRequest(supply.id)}
                                    disabled={!token || deletingSupplyId === supply.id}
                                    title="Eliminar insumo"
                                    aria-label={`Eliminar insumo: ${supply.item_name}`}
                                    className="p-1.5 rounded-md text-[hsl(var(--muted-foreground))] hover:text-[hsl(var(--destructive))] hover:bg-[hsl(var(--destructive)/0.1)] transition-colors disabled:opacity-50"
                                >
                                    {deletingSupplyId === supply.id ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                                </button>
                            </div>
                            <div className="flex items-center justify-between gap-2 text-2xs text-[hsl(var(--muted-foreground))]">
                                <span>
                                    Total insumo: <strong className="text-[hsl(var(--foreground))]">${rowTotal.toLocaleString('es-CO')}</strong>
                                </span>
                                {linkedExpenseId ? (
                                    <span className="inline-flex items-center gap-1 rounded-full border border-[hsl(var(--success)/0.35)] bg-[hsl(var(--success)/0.12)] px-2 py-0.5 text-2xs font-bold text-[hsl(var(--success))]">
                                        <CheckCircle2 size={10} />
                                        Gasto sincronizado ({linkedExpenseId})
                                    </span>
                                ) : (
                                    <span>Sin gasto vinculado</span>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="mt-3 space-y-2">
                <div className="grid grid-cols-[minmax(0,1fr)_64px_92px_auto] gap-2">
                    <input
                        aria-label="Nombre del nuevo insumo"
                        value={newSupplyName}
                        onChange={event => setNewSupplyName(event.target.value)}
                        onKeyDown={event => event.key === 'Enter' && handleAddSupply()}
                        placeholder="Nuevo insumo"
                        className="min-w-0 rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-2 text-sm font-medium text-[hsl(var(--foreground))] placeholder:text-[hsl(var(--muted-foreground))] outline-none"
                    />
                    <input
                        type="number"
                        aria-label="Cantidad del nuevo insumo"
                        min={1}
                        value={newSupplyQuantity}
                        onChange={event => setNewSupplyQuantity(Math.max(1, Number(event.target.value) || 1))}
                        className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-2 text-sm font-bold text-[hsl(var(--foreground))] outline-none"
                    />
                    <input
                        type="number"
                        step="0.01"
                        min={0}
                        aria-label="Costo unitario del nuevo insumo"
                        placeholder="Costo $"
                        value={newSupplyUnitCost}
                        onChange={event => setNewSupplyUnitCost(Math.max(0, Number(event.target.value) || 0))}
                        className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-2 py-2 text-sm font-bold text-[hsl(var(--foreground))] outline-none"
                    />
                    <button
                        type="button"
                        onClick={handleAddSupply}
                        disabled={creatingSupply || !newSupplyName.trim()}
                        aria-busy={creatingSupply}
                        className="rounded-md bg-[hsl(var(--primary))] px-3 py-2 text-2xs font-semibold uppercase tracking-wide text-[hsl(var(--primary-foreground))] disabled:opacity-50"
                    >
                        {creatingSupply ? 'Agregando…' : 'Agregar'}
                    </button>
                </div>
                <div className="flex items-center justify-between gap-2 text-2xs text-[hsl(var(--muted-foreground))]">
                    <label className="inline-flex items-center gap-1.5 cursor-pointer font-medium">
                        <input
                            type="checkbox"
                            aria-label="Sincronizar con gastos del proyecto"
                            checked={autoCreateExpense}
                            onChange={event => setAutoCreateExpense(event.target.checked)}
                            style={{ accentColor: 'hsl(var(--primary))' }}
                        />
                        <span>Sincronizar con gastos del proyecto (AC)</span>
                    </label>
                    <span>
                        Subtotal nuevo: <strong className="text-[hsl(var(--foreground))]">${(Math.max(1, newSupplyQuantity || 1) * (newSupplyUnitCost || 0)).toLocaleString('es-CO')}</strong>
                    </span>
                </div>
            </div>
        </section>
    );
}

