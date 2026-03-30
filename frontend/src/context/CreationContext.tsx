"use client";

import React, { createContext, useContext, useState } from 'react';

interface CreationContextType {
    isModalOpen: boolean;
    openModal: (type?: 'task' | 'doc' | 'reminder' | 'whiteboard' | 'panel') => void;
    closeModal: () => void;
    defaultType: 'task' | 'doc' | 'reminder' | 'whiteboard' | 'panel';
}

const CreationContext = createContext<CreationContextType | undefined>(undefined);

export function CreationProvider({ children }: { children: React.ReactNode }) {
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [defaultType, setDefaultType] = useState<'task' | 'doc' | 'reminder' | 'whiteboard' | 'panel'>('task');

    const openModal = (type: 'task' | 'doc' | 'reminder' | 'whiteboard' | 'panel' = 'task') => {
        setDefaultType(type);
        setIsModalOpen(true);
    };

    const closeModal = () => setIsModalOpen(false);

    return (
        <CreationContext.Provider value={{ isModalOpen, openModal, closeModal, defaultType }}>
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
