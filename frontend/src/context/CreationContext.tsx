"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

interface CreationContextType {
    isModalOpen: boolean;
    openModal: (type?: 'task' | 'event' | 'project' | 'doc' | 'reminder' | 'whiteboard' | 'panel', initialData?: any) => void;
    closeModal: () => void;
    defaultType: 'task' | 'event' | 'project' | 'doc' | 'reminder' | 'whiteboard' | 'panel';
    initialData?: any;
}

const CreationContext = createContext<CreationContextType | undefined>(undefined);

export function CreationProvider({ children }: { children: React.ReactNode }) {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [defaultType, setDefaultType] = useState<'task' | 'event' | 'project' | 'doc' | 'reminder' | 'whiteboard' | 'panel'>('task');
    const [initialData, setInitialData] = useState<any>(undefined);

    const openModal = useCallback((type: 'task' | 'event' | 'project' | 'doc' | 'reminder' | 'whiteboard' | 'panel' = 'task', data?: any) => {
        setDefaultType(type);
        setInitialData(data);
        setIsModalOpen(true);
    }, []);

    const closeModal = useCallback(() => {
        setIsModalOpen(false);
        setInitialData(undefined);
    }, []);

    const value = useMemo(() => ({
        isModalOpen, openModal, closeModal, defaultType, initialData
    }), [isModalOpen, openModal, closeModal, defaultType, initialData]);

    return (
        <CreationContext.Provider value={value}>
            {children}
        </CreationContext.Provider>
    );
}

export function useCreation() {
    const context = useContext(CreationContext);
    if (!context) {
        throw new Error('useCreation must be used within a CreationProvider');
    }
    return context;
}
