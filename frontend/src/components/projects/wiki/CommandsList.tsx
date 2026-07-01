"use client";

import React, { forwardRef, useEffect, useImperativeHandle, useState } from 'react';
import clsx from 'clsx';

export const CommandsList = forwardRef((props: any, ref) => {
    const [selectedIndex, setSelectedIndex] = useState(0);

    const selectItem = (index: number) => {
        const item = props.items[index];
        if (item) {
            props.command(item);
        }
    };

    const upHandler = () => {
        setSelectedIndex(((selectedIndex + props.items.length) - 1) % props.items.length);
    };

    const downHandler = () => {
        setSelectedIndex((selectedIndex + 1) % props.items.length);
    };

    const enterHandler = () => {
        selectItem(selectedIndex);
    };

    useEffect(() => setSelectedIndex(0), [props.items]);

    useImperativeHandle(ref, () => ({
        onKeyDown: ({ event }: any) => {
            if (event.key === 'ArrowUp') {
                upHandler();
                return true;
            }
            if (event.key === 'ArrowDown') {
                downHandler();
                return true;
            }
            if (event.key === 'Enter') {
                enterHandler();
                return true;
            }
            return false;
        },
    }));

    return (
        <div className="bg-[hsl(var(--bg-primary))] dark:bg-[#1e1f21] border border-[hsl(var(--border))] dark:border-white/10 rounded-lg shadow-2xl overflow-hidden p-1.5 min-w-[240px] animate-in fade-in zoom-in-95 duration-100 font-display">
            <div className="px-2 py-1.5 mb-1">
                <span className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Comandos Rápidos</span>
            </div>
            {props.items.length ? (
                props.items.map((item: any, index: number) => (
                    <button
                        key={index}
                        onClick={() => selectItem(index)}
                        className={clsx(
                            "w-full flex items-center gap-3 px-2 py-2 rounded-md transition-all text-left",
                            index === selectedIndex
                                ? "bg-[hsl(var(--primary))] text-white shadow-lg shadow-blue-500/20"
                                : "text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5"
                        )}
                    >
                        <div className={clsx(
                            "size-7 rounded-md flex items-center justify-center",
                            index === selectedIndex ? "bg-white/20" : "bg-[hsl(var(--surface-2))] dark:bg-white/5"
                        )}>
                            <item.icon size={14} />
                        </div>
                        <div>
                            <p className="text-[12px] font-bold leading-none">{item.title}</p>
                            <p className={clsx("text-[10px] mt-0.5 font-medium", index === selectedIndex ? "text-blue-100" : "text-[hsl(var(--text-secondary))]")}>
                                {item.description}
                            </p>
                        </div>
                    </button>
                ))
            ) : (
                <div className="px-3 py-1.5 text-center text-xs text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wide">
                    Sin comandos
                </div>
            )}
        </div>
    );
});

CommandsList.displayName = 'CommandsList';
