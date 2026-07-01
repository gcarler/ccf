"use client";

import React, { useState } from 'react';
import clsx from 'clsx';
import { typography } from '../tokens';

interface Tab {
    id: string;
    label: string;
    icon?: React.ComponentType<{ className?: string }>;
    disabled?: boolean;
}

interface DSTabsProps {
    tabs: Tab[];
    defaultTab?: string;
    onChange?: (tabId: string) => void;
    children: React.ReactNode;
}

export function DSTabs({
    tabs,
    defaultTab,
    onChange,
    children,
}: DSTabsProps) {
    const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);

    const handleTabClick = (tabId: string) => {
        setActiveTab(tabId);
        onChange?.(tabId);
    };

    return (
        <div className="flex flex-col">
            {/* Tab List */}
            <div
                className="flex items-center gap-1 border-b border-[hsl(var(--border))] dark:border-white/5"
                role="tablist"
                aria-orientation="horizontal"
            >
                {tabs.map((tab) => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;

                    return (
                        <button
                            key={tab.id}
                            role="tab"
                            aria-selected={isActive}
                            aria-controls={`panel-${tab.id}`}
                            disabled={tab.disabled}
                            onClick={() => handleTabClick(tab.id)}
                            className={clsx(
                                'flex items-center gap-1.5 px-3 py-2 text-[10px] font-semibold uppercase tracking-wide',
                                'border-b-2 -mb-[1px] transition-all',
                                isActive
                                    ? 'text-[hsl(var(--primary))] border-[hsl(var(--primary))]'
                                    : 'text-[hsl(var(--text-secondary))] border-transparent hover:text-[hsl(var(--text-primary))] hover:border-[hsl(var(--border))]',
                                tab.disabled && 'opacity-50 cursor-not-allowed'
                            )}
                            style={{ fontFamily: typography.family }}
                        >
                            {Icon && <Icon className="size-3.5" />}
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Tab Panels */}
            <div className="py-3">
                {tabs.map((tab) => (
                    <div
                        key={tab.id}
                        role="tabpanel"
                        id={`panel-${tab.id}`}
                        aria-labelledby={`tab-${tab.id}`}
                        hidden={activeTab !== tab.id}
                        className={clsx(
                            'focus:outline-none',
                            activeTab === tab.id ? 'block' : 'hidden'
                        )}
                    >
                        {activeTab === tab.id && children}
                    </div>
                ))}
            </div>
        </div>
    );
}
