"use client";

import React, { useState, useEffect, useCallback } from 'react';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import UniversalTableView, { TableColumn } from '@/components/ui/UniversalTableView';
import { Flame } from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/http';
import { useAuth } from '@/context/AuthContext';
import Skeleton from '@/components/ui/Skeleton';
import { useCreation } from '@/context/CreationContext';

export interface EvangelismStrategy {
    id: string;
    title: string;
    description: string;
    status: 'active' | 'pending' | 'done';
    strategy_type: string;
    start_date: string;
    end_date: string;
    created_at: string;
    updated_at: string;
}

export default function EvangelismClient() {
    const { token } = useAuth();
    const { openModal } = useCreation();
    const [data, setData] = useState<EvangelismStrategy[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchStrategies = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const result = await apiFetch<EvangelismStrategy[]>('/evangelism/strategies', { token });
            setData(Array.isArray(result) ? result : []);
        } catch (err) {
            toast.error('Error al cargar estrategias de evangelismo');
            setData([]);
        } finally {
            setLoading(false);
        }
    }, [token]);

    useEffect(() => {
        fetchStrategies();
    }, [fetchStrategies]);

    const columns: TableColumn<EvangelismStrategy>[] = [
        { key: 'id', label: 'ID', type: 'id' },
        { key: 'title', label: 'Estrategia', type: 'text' },
        { key: 'status', label: 'Estado', type: 'status' },
        { key: 'strategy_type', label: 'Tipo', type: 'text' },
        { key: 'start_date', label: 'Inicio', type: 'date' },
        { key: 'end_date', label: 'Fin', type: 'date' },
    ];

    const handleAddItem = () => {
        openModal('evangelism_strategy');
    };

    const handleUpdateItem = async (id: string, field: keyof EvangelismStrategy, value: any) => {
        setData(prev => prev.map(item => item.id === id ? { ...item, [field]: value } : item));
        try {
            await apiFetch(`/evangelism/strategies/${id}`, {
                method: 'PATCH',
                token,
                body: { [field]: value }
            });
            toast.success('Estrategia actualizada');
        } catch {
            toast.error('Error al actualizar');
            fetchStrategies();
        }
    };

    return (
        <EvangelismShell
            breadcrumbs={[
                { label: 'Evangelismo', icon: Flame },
                { label: 'Estrategias' }
            ]}
        >
            <div className="h-full flex flex-col">
                {loading ? (
                    <div className="p-4 space-y-2">
                        {[1, 2, 3].map(i => <Skeleton key={i} className="h-12 w-full rounded-xl" />)}
                    </div>
                ) : (
                    <UniversalTableView
                        data={data}
                        columns={columns}
                        viewName="Todas las Estrategias"
                        onAddItem={handleAddItem}
                        onUpdateItem={handleUpdateItem}
                    />
                )}
            </div>
        </EvangelismShell>
    );
}
