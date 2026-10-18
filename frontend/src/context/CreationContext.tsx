"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

export type CreationType = 'task' | 'event' | 'project' | 'doc' | 'reminder' | 'whiteboard' | 'panel';

/** Datos iniciales libres que cada modal interpreta según su tipo. */
export interface CreationInitialData {
    initialDate?: string;
    preset?: string;
    [key: string]: unknown;
}

interface CreationContextType {
    isModalOpen: boolean;
    openModal: (type?: CreationType, initialData?: CreationInitialData) => void;
    closeModal: () => void;
    defaultType: CreationType;
    initialData?: CreationInitialData;
}

const CreationContext = createContext<CreationContextType | undefined>(undefined);

export function CreationProvider({ children }: { children: React.ReactNode }) {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [defaultType, setDefaultType] = useState<CreationType>('task');
    const [initialData, setInitialData] = useState<CreationInitialData | undefined>(undefined);

    const openModal = useCallback((type: CreationType = 'task', data?: CreationInitialData) => {
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
