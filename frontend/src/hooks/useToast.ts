"use client";

import { toast as sonnerToast } from 'sonner';

export function useToast() {
    return (message: string, type: 'success' | 'error' | 'info' = 'info') => {
        if (type === 'success') sonnerToast.success(message);
        else if (type === 'error') sonnerToast.error(message);
        else sonnerToast.info(message);
    };
}
