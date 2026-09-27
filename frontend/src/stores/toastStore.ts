import { create } from 'zustand';

type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: string;
  message: string;
  description?: string;
  type: ToastType;
}

/**
 * Payload de toast: acepta string simple (retrocompatible) o un objeto
 * estructurado con título, descripción/message y variante semántica.
 */
export type ToastInput = string | {
  title: string;
  description?: string;
  /** Alias de `description`, aceptado por compatibilidad con consumidores existentes */
  message?: string;
  variant?: ToastType | 'destructive' | 'default';
  type?: ToastType;
};

interface ToastState {
  toasts: Toast[];
  addToast: (input: ToastInput, type?: ToastType) => void;
  removeToast: (id: string) => void;
}

const VARIANT_TYPE_MAP: Record<string, ToastType> = {
  success: 'success',
  error: 'error',
  destructive: 'error',
  info: 'info',
  warning: 'warning',
  default: 'info',
};

function normalizeToastInput(input: ToastInput, fallback: ToastType): Omit<Toast, 'id'> {
  if (typeof input === 'string') {
    return { message: input, type: fallback };
  }
  const rawVariant = input.variant ?? input.type;
  const type = (rawVariant && VARIANT_TYPE_MAP[rawVariant]) || fallback;
  return {
    message: input.title,
    description: input.description ?? input.message,
    type,
  };
}

export const useToastStore = create<ToastState>((set, get) => ({
  toasts: [],

  addToast: (input, type = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    const toast = { id, ...normalizeToastInput(input, type) };
    set((state) => ({ toasts: [...state.toasts, toast] }));
    setTimeout(() => {
      get().removeToast(id);
    }, 5000);
  },

  removeToast: (id: string) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },
}));
