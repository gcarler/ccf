"use client";

import React from 'react';

import PaletteSelector from '@/app/theme/PaletteSelector';

export default function ThemeAdminPage() {
    return (
        <div className="p-8">
            <h1 className="text-2xl font-bold mb-4">Administrador de Temas</h1>
            <PaletteSelector />
        </div>
    );
}
