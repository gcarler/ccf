"use client";

import React, { useState, useEffect, useRef } from 'react';
import clsx from 'clsx';

interface InlineEditProps {
    value: string;
    onSave: (newValue: string) => void;
    className?: string;
    textClassName?: string;
    inputClassName?: string;
}

export default function InlineEdit({
    value,
    onSave,
    className,
    textClassName,
    inputClassName
}: InlineEditProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [tempValue, setTempValue] = useState(value);
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (isEditing && inputRef.current) {
            inputRef.current.focus();
            inputRef.current.select();
        }
    }, [isEditing]);

    const handleSave = () => {
        if (tempValue.trim() !== value) {
            onSave(tempValue.trim());
        }
        setIsEditing(false);
    };

    const handleCancel = () => {
        setTempValue(value);
        setIsEditing(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') handleSave();
        if (e.key === 'Escape') handleCancel();
    };

    if (isEditing) {
        return (
            <div className={clsx("flex items-center gap-1 w-full", className)}>
                <input
                    ref={inputRef}
                    type="text"
                    value={tempValue}
                    onChange={(e) => setTempValue(e.target.value)}
                    onBlur={handleSave}
                    onKeyDown={handleKeyDown}
                    className={clsx(
                        "w-full bg-[hsl(var(--bg-primary))] dark:bg-slate-800 border border-blue-500 rounded px-2 py-0.5 text-sm outline-none shadow-[0_0_0_2px_rgba(59,130,246,0.1)]",
                        inputClassName
                    )}
                />
            </div>
        );
    }

    return (
        <div 
            onClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
            }}
            className={clsx(
                "group/inline cursor-text rounded hover:bg-slate-100 dark:hover:bg-white/5 px-1 -ml-1 transition-colors min-h-[1.5em] flex items-center",
                className
            )}
        >
            <span className={clsx("truncate", textClassName)}>{value}</span>
        </div>
    );
}
