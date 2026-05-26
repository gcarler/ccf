"use client";

import React, { Component, ErrorInfo, ReactNode, useState, useCallback } from 'react';
import { AlertTriangle, RefreshCw, Copy } from 'lucide-react';

interface Props {
  children: ReactNode;
  moduleName: string;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ModuleErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error(`[${this.props.moduleName}] Error caught:`, error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  handleCopyError = () => {
    const { error, errorInfo } = this.state;
    const text = `Module: ${this.props.moduleName}\nError: ${error?.message}\nStack: ${error?.stack}\nComponent Stack: ${errorInfo?.componentStack}`;
    navigator.clipboard.writeText(text);
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="min-h-[400px] flex items-center justify-center bg-slate-50 dark:bg-[#0f1117]">
          <div className="max-w-md w-full p-6 bg-white dark:bg-[#1e1f21] border border-red-200 dark:border-red-900/30 rounded-xl shadow-lg">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-lg bg-red-100 dark:bg-red-900/20 text-red-600 dark:text-red-400">
                <AlertTriangle size={20} />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Módulo no disponible
                </h3>
                <p className="text-[11px] text-slate-400">{this.props.moduleName}</p>
              </div>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400 mb-4">
              Este módulo tiene un error temporal. El resto de la plataforma sigue funcionando normalmente.
            </p>

            {this.state.error && (
              <details className="mb-4 p-3 bg-slate-50 dark:bg-black/20 rounded-lg text-[10px] font-mono text-slate-500 max-h-32 overflow-auto">
                <summary className="cursor-pointer text-xs font-sans text-slate-400 mb-1">Ver detalles técnicos</summary>
                <pre className="whitespace-pre-wrap break-all">{this.state.error.message}</pre>
                <pre className="whitespace-pre-wrap break-all mt-1 opacity-60">{this.state.errorInfo?.componentStack?.slice(0, 500)}</pre>
              </details>
            )}

            <div className="flex gap-2">
              <button
                onClick={this.handleReset}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-xs font-semibold hover:bg-blue-700 transition-colors"
              >
                <RefreshCw size={14} /> Reintentar
              </button>
              <button
                onClick={this.handleCopyError}
                className="flex items-center justify-center gap-2 px-3 py-2 bg-slate-100 dark:bg-white/5 text-slate-600 dark:text-slate-300 rounded-lg text-xs font-medium hover:bg-slate-200 dark:hover:bg-white/10 transition-colors"
                title="Copiar error"
              >
                <Copy size={14} />
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export function useModuleError(moduleName: string) {
  const [error, setError] = useState<Error | null>(null);

  const guard = useCallback(
    <T,>(fn: () => T, fallback?: T): T => {
      try {
        return fn();
      } catch (e) {
        console.error(`[${moduleName}]`, e);
        setError(e as Error);
        return fallback as T;
      }
    },
    [moduleName]
  );

  const reset = useCallback(() => setError(null), []);

  return { error, guard, reset };
}
