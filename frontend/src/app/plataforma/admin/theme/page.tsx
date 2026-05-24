"use client";

import React from 'react';

import PaletteSelector from '@/app/plataforma/theme/PaletteSelector';

export default function ThemeAdminPage() {
    return (
        <div className="p-4">
            <h1 className="text-lg font-bold mb-4">Administrador de Temas</h1>
            <PaletteSelector />
        </div>
    );
}

