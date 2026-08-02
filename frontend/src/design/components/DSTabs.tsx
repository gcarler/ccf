"use client";

import React, { useRef, useState, useCallback } from 'react';
import clsx from 'clsx';
import type { AppIcon } from '@/types/icons';

interface Tab {
    id: string;
    label: string;
    icon?: AppIcon;
    disabled?: boolean;
}

interface DSTabsProps {
    tabs: Tab[];
    defaultTab?: string;
    onChange?: (tabId: string) => void;
    panels?: Record<string, React.ReactNode>;
    renderPanel?: (tabId: string) => React.ReactNode;
    /**
     * @previo — anterior API. Usar `panels` o `renderPanel` en su lugar.
     */
    children?: React.ReactNode;
}

export function DSTabs({
    tabs,
    defaultTab,
    onChange,
    panels,
    renderPanel,
    children,
}: DSTabsProps) {
    const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id);
    const tabRefs = useRef<Map<string, HTMLButtonElement>>(new Map());

    const setTabRef = useCallback((id: string) => (el: HTMLButtonElement | null) => {
        if (el) {
            tabRefs.current.set(id, el);
        } else {
            tabRefs.current.delete(id);
        }
    }, []);

    const focusTab = useCallback((tabId: string) => {
        const tab = tabRefs.current.get(tabId);
        tab?.focus();
    }, []);

    const activateTab = useCallback((tabId: string) => {
        setActiveTab(tabId);
        onChange?.(tabId);
    }, [onChange]);

    const handleTabClick = (tabId: string) => {
        activateTab(tabId);
    };

    const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
        const enabledTabs = tabs.filter((tab) => !tab.disabled);
        const currentIndex = enabledTabs.findIndex((tab) => tab.id === activeTab);
        let nextIndex = currentIndex;

        switch (event.key) {
            case 'ArrowRight':
            case 'ArrowDown':
                event.preventDefault();
                nextIndex = (currentIndex + 1) % enabledTabs.length;
                break;
            case 'ArrowLeft':
            case 'ArrowUp':
                event.preventDefault();
                nextIndex = (currentIndex - 1 + enabledTabs.length) % enabledTabs.length;
                break;
            case 'Home':
                event.preventDefault();
                nextIndex = 0;
                break;
            case 'End':
                event.preventDefault();
                nextIndex = enabledTabs.length - 1;
                break;
            default:
                return;
        }

        if (nextIndex !== currentIndex && enabledTabs[nextIndex]) {
            const nextTab = enabledTabs[nextIndex];
            activateTab(nextTab.id);
            focusTab(nextTab.id);
        }
    };

    const resolvePanel = (tabId: string): React.ReactNode => {
        if (panels && panels[tabId] !== undefined) return panels[tabId];
        if (renderPanel) return renderPanel(tabId);
        return children;
    };

    return (
        <div className="flex flex-col">
            <div
                className="flex items-center gap-1 border-b border-[hsl(var(--border))] dark:border-[hsl(var(--border))]"
                role="tablist"
                aria-orientation="horizontal"
                onKeyDown={handleKeyDown}
            >
                {tabs.map((tab) => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;

                    return (
                        <button
                            key={tab.id}
                            ref={setTabRef(tab.id)}
                            id={`tab-${tab.id}`}
                            role="tab"
                            tabIndex={isActive ? 0 : -1}
                            aria-selected={isActive}
                            aria-controls={`panel-${tab.id}`}
                            disabled={tab.disabled}
                            onClick={() => handleTabClick(tab.id)}
                            className={clsx(
                                'flex items-center gap-1.5 px-3 py-2 text-2xs font-semibold uppercase tracking-wide font-sans',
                                'border-b-2 -mb-[1px] transition-all',
                                isActive
                                    ? 'text-[hsl(var(--primary))] border-[hsl(var(--primary))]'
                                    : 'text-[hsl(var(--text-secondary))] border-transparent hover:text-[hsl(var(--text-primary))] hover:border-[hsl(var(--border))]',
                                tab.disabled && 'opacity-50 cursor-not-allowed'
                            )}
                        >
                            {Icon && <Icon className="size-3.5" aria-hidden="true" />}
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Tab Panels — only the active tab's content is rendered */}
            <div className="py-3">
                {tabs.map((tab) => {
                    const isActive = activeTab === tab.id;
                    return (
                        <div
                            key={tab.id}
                            role="tabpanel"
                            id={`panel-${tab.id}`}
                            aria-labelledby={`tab-${tab.id}`}
                            hidden={!isActive}
                            className={clsx(
                                'focus:outline-none',
                                isActive ? 'block' : 'hidden'
                            )}
                        >
                            {isActive && resolvePanel(tab.id)}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
