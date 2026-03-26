"use client";

import React from 'react';

export default function DatePicker({ currentDate, onSelect }: { currentDate?: Date | string | null, onSelect: (date: Date) => void }) {
    return (
        <label className="cursor-pointer">
            <input 
                type="date" 
                value={currentDate ? new Date(currentDate).toISOString().split('T')[0] : ''}
                onChange={(e) => {
                    if (e.target.value) onSelect(new Date(e.target.value));
                }}
                className="bg-transparent border-none text-[11px] font-bold text-slate-500 w-24 outline-none cursor-pointer"
            />
        </label>
    );
}
