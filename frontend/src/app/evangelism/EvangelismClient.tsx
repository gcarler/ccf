"use client";

import React, { useState } from 'react';
import EvangelismShell from '@/components/evangelism/EvangelismShell';
import UniversalTableView, { TableColumn } from '@/components/ui/UniversalTableView';
import { Flame } from 'lucide-react';
// Import eliminado
import { toast } from 'sonner';

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

const MOCK_DATA: EvangelismStrategy[] = [
    {
        id: 'EVG-001',
        title: 'Campaña "Un Amigo Más"',
        description: 'Estrategia de alcance 1 a 1 para invitar amigos a Faros en Casa.',
        status: 'active',
        strategy_type: 'Faro en Casa',
        start_date: '2026-06-01T00:00:00Z',
        end_date: '2026-07-31T00:00:00Z',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
    },
    {
        id: 'EVG-002',
        title: 'Cosecha de Verano 2026',
        description: 'Evento masivo de impacto en la ciudad con campañas de sanidad.',
        status: 'pending',
        strategy_type: 'Evento Masivo',
        start_date: '2026-08-15T00:00:00Z',
        end_date: '2026-08-20T00:00:00Z',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
    }
];

export default function EvangelismClient() {
    const [data, setData] = useState<EvangelismStrategy[]>(MOCK_DATA);
    // const { openModal } = useCreation(); // Omitido hasta que se implemente el modal

    const columns: TableColumn<EvangelismStrategy>[] = [
        { key: 'id', label: 'ID', type: 'id' },
        { key: 'title', label: 'Estrategia', type: 'text' },
        { key: 'status', label: 'Estado', type: 'status' },
        { key: 'strategy_type', label: 'Tipo', type: 'text' },
        { key: 'start_date', label: 'Inicio', type: 'date' },
        { key: 'end_date', label: 'Fin', type: 'date' },
    ];

    const handleAddItem = () => {
        // Here we could open the UniversalCreationModal, but for now we'll just mock it or show a toast
        toast.info("Función en desarrollo: Abre el formulario de nueva estrategia de evangelismo.");
    };

    const handleUpdateItem = (id: string, field: keyof EvangelismStrategy, value: any) => {
        setData(prev => prev.map(item => item.id === id ? { ...item, [field]: value } : item));
    };

    return (
        <EvangelismShell
            breadcrumbs={[
                { label: 'Evangelismo', icon: Flame },
                { label: 'Estrategias' }
            ]}
        >
            <div className="h-full flex flex-col -mx-4 -my-6 lg:-mx-6">
                <UniversalTableView
                    data={data}
                    columns={columns}
                    viewName="Todas las Estrategias"
                    onAddItem={handleAddItem}
                    onUpdateItem={handleUpdateItem}
                />
            </div>
        </EvangelismShell>
    );
}
