"use client";

import React, { forwardRef, useImperativeHandle, useRef, useState } from "react";
import type { ICellEditorParams } from "ag-grid-community";

export interface TitleCellEditorRef {
    getValue: () => string;
    afterGuiAttached: () => void;
}

const TitleCellEditor = forwardRef<TitleCellEditorRef, ICellEditorParams>((props, ref) => {
    const originalValue = (props.value ?? "") as string;
    const [value, setValue] = useState<string>(originalValue);
    const inputRef = useRef<HTMLInputElement>(null);
    const cancelledRef = useRef(false);

    useImperativeHandle(ref, () => ({
        getValue: () => (cancelledRef.current ? originalValue.trim() : value.trim()),
        afterGuiAttached: () => {
            inputRef.current?.focus();
            inputRef.current?.select();
        },
    }));

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
            e.preventDefault();
            props.stopEditing();
        } else if (e.key === "Escape") {
            e.preventDefault();
            cancelledRef.current = true;
            props.stopEditing();
        }
    };

    return (
        <input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => props.stopEditing()}
            className="w-full h-full px-2 text-[13px] font-semibold text-[hsl(var(--text-primary))] dark:text-[hsl(var(--text-secondary))] bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] border border-[hsl(var(--primary))] outline-none rounded-sm"
            aria-label="Editar título de tarea"
        />
    );
});

TitleCellEditor.displayName = "TitleCellEditor";

export default TitleCellEditor;
