"use client";

import React from 'react';
import { LucideIcon } from 'lucide-react';
import { DSToolbarChip } from '@/design';

type Variant = 'outline' | 'solid' | 'dashed';
type Size = 'sm' | 'md';

interface CommunityToolbarChipProps {
    label: string;
    icon?: LucideIcon;
    active?: boolean;
    variant?: Variant;
    size?: Size;
    className?: string;
    onClick?: () => void;
    title?: string;
}

export default function CommunityToolbarChip({
    label,
    icon,
    active = false,
    variant = 'outline',
    size = 'md',
    className,
    onClick,
    title,
}: CommunityToolbarChipProps) {
    const mappedVariant = variant === 'dashed' ? 'outline' : variant === 'solid' ? 'solid' : 'outline';
    const extraClass = variant === 'dashed' ? 'border-dashed' : '';

    return (
        <DSToolbarChip
            label={label}
            icon={icon}
            active={active}
            variant={mappedVariant as any}
            size={size}
            className={className ? `${extraClass} ${className}` : extraClass}
            onClick={onClick}
            title={title || label}
        />
    );
}
