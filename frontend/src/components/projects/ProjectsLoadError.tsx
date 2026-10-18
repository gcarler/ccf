import clsx from 'clsx';

type ProjectsLoadErrorProps = {
  message: string;
  onRetry?: () => void;
  retrying?: boolean;
  className?: string;
};

export default function ProjectsLoadError({
  message,
  onRetry,
  retrying = false,
  className,
}: ProjectsLoadErrorProps) {
  return (
    <div
      role="alert"
      className={clsx(
        'flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[hsl(var(--warning)/0.3)] bg-[hsl(var(--warning-muted))] p-3 text-[hsl(var(--warning-text))]',
        className,
      )}
    >
      <p className="text-xs font-bold uppercase tracking-wide">{message}</p>
      <div
        data-testid="projects-load-error-pmi-continuity"
        className="w-full text-2xs font-medium text-[hsl(var(--text-secondary))]"
      >
        Protocolo PMI de Continuidad: Los cambios locales y lineas base previas permanecen resguardados.
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          disabled={retrying}
          aria-busy={retrying}
          className="rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] px-3 py-1.5 text-xs font-semibold text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-2))] disabled:cursor-wait disabled:opacity-60"
        >
          {retrying ? 'Reintentando…' : 'Reintentar'}
        </button>
      )}
    </div>
  );
}
