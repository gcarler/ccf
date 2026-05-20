"use client";

import React, { createContext, useContext, useState } from 'react';

interface CreationContextType {
    isModalOpen: boolean;
    openModal: (type?: 'task' | 'event' | 'doc' | 'reminder' | 'whiteboard' | 'panel' | 'evangelism_strategy', initialData?: any) => void;
    closeModal: () => void;
    defaultType: 'task' | 'event' | 'doc' | 'reminder' | 'whiteboard' | 'panel' | 'evangelism_strategy';
    initialData?: any;
}

const CreationContext = createContext<CreationContextType | undefined>(undefined);

export function CreationProvider({ children }: { children: React.ReactNode }) {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [defaultType, setDefaultType] = useState<'task' | 'event' | 'doc' | 'reminder' | 'whiteboard' | 'panel' | 'evangelism_strategy'>('task');
    const [initialData, setInitialData] = useState<any>(undefined);

    const openModal = (type: 'task' | 'event' | 'doc' | 'reminder' | 'whiteboard' | 'panel' | 'evangelism_strategy' = 'task', data?: any) => {
        setDefaultType(type);
        setInitialData(data);
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
        setInitialData(undefined);
    };

    return (
        <CreationContext.Provider value={{ isModalOpen, openModal, closeModal, defaultType, initialData }}>
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
