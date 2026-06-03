"use client";

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

interface ErrorBoundaryProps {
  children?: React.ReactNode;
  fallback?: React.ReactNode;
  moduleName?: string;
}

export default class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error(
      `[ErrorBoundary${this.props.moduleName ? `:${this.props.moduleName}` : ''}]`,
      error,
      errorInfo.componentStack,
    );
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="flex items-center justify-center min-h-[400px] p-4">
          <div className="text-center space-y-4 max-w-md">
            <div className="size-8 rounded-lg bg-rose-50 dark:bg-rose-500/10 flex items-center justify-center mx-auto">
              <AlertTriangle size={28} className="text-rose-500" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-800 dark:text-white mb-1">
                Algo sali&oacute; mal
              </h3>
              <p className="text-[13px] text-slate-500 dark:text-slate-400 font-medium">
                {this.props.moduleName
                  ? `El m&oacute;dulo "${this.props.moduleName}" encontr&oacute; un error inesperado.`
                  : 'Un error inesperado ocurri&oacute; en esta secci&oacute;n.'}
              </p>
            </div>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="inline-flex items-center gap-2 px-3 py-2.5 bg-slate-900 dark:bg-[hsl(var(--bg-primary))] text-white dark:text-slate-900 rounded-md text-[11px] font-bold hover:opacity-90 active:scale-95 transition-all"
            >
              <RefreshCw size={14} />
              Reintentar
            </button>
          </div>
        </div>
      );
    }

    return this.props.children ?? null;
  }
}
