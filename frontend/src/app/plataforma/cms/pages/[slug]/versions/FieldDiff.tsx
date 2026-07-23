"use client";

import React from "react";
import clsx from "clsx";
import type { DiffToken, FieldDiff as FieldDiffT } from "@/lib/cms/versionDiff";

/**
 * Renders a single field's diff.
 *
 *   - "unchanged"     → muted mono-text span (no highlights).
 *   - "added"         → single right-aligned value in emerald.
 *   - "removed"       → single left-aligned value in rose (struck through).
 *   - "changed"       → two columns with word-level tokens highlighted.
 *
 * ``layout="inline"`` collapses to a single column with red/green
 * tokens inline (useful for very narrow sidebars). Default is
 * ``"side-by-side"`` for the main diff surface.
 */
export function FieldDiffRow({
  label,
  diff,
  layout = "side-by-side",
  multiline = false,
  emptyText = "—",
}: {
  label: string;
  diff: FieldDiffT;
  layout?: "side-by-side" | "inline";
  multiline?: boolean;
  emptyText?: string;
}) {
  const isString = typeof diff.before === "string" || typeof diff.after === "string";

  return (
    <div className="grid gap-3 md:grid-cols-[160px_1fr]">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
        {label}
      </div>
      <div className="min-w-0">
        {diff.kind === "unchanged" && (
          <span className="text-[12px] text-[hsl(var(--text-secondary))]">
            {isString ? (diff.after as string) || emptyText : JSON.stringify(diff.after) || emptyText}
          </span>
        )}
        {diff.kind === "added" && (
          <span
            role="note"
            aria-label="Valor añadido en la versión B"
            className={clsx(
              "block text-[12px] text-success-text dark:text-success-text bg-success-soft dark:bg-[hsl(var(--success))]/10 border border-[hsl(var(--success)/25%)] dark:border-[hsl(var(--success)/100%)]/30 rounded-md px-2.5 py-1.5",
              multiline && "whitespace-pre-wrap break-words",
            )}
          >
            <span aria-hidden="true" className="mr-1 text-[10px] font-semibold uppercase tracking-wider">+ Añadido</span>
            {renderValue(diff.after, emptyText)}
          </span>
        )}
        {diff.kind === "removed" && (
          <span
            role="note"
            aria-label="Valor eliminado en la versión B"
            className={clsx(
              "block text-[12px] text-danger-text dark:text-danger-text bg-danger-soft dark:bg-[hsl(var(--danger))]/10 border border-[hsl(var(--danger)/25%)] dark:border-[hsl(var(--danger)/100%)]/30 rounded-md px-2.5 py-1.5 line-through",
              multiline && "whitespace-pre-wrap break-words",
            )}
          >
            <span aria-hidden="true" className="mr-1 text-[10px] font-semibold uppercase tracking-wider no-underline">− Eliminado</span>
            {renderValue(diff.before, emptyText)}
          </span>
        )}
        {diff.kind === "changed" && (
          layout === "inline" ? (
            <span
              className={clsx(
                "block text-[12px] text-[hsl(var(--text-primary))] dark:text-white",
                multiline && "whitespace-pre-wrap break-words",
              )}
            >
              <TokenStream tokens={diff.tokens ?? []} />
            </span>
          ) : (
            <div className="grid gap-2 md:grid-cols-2">
              <DiffColumn
                side="before"
                tokens={diff.tokens}
                fallbackText={isString ? (diff.before as string) : undefined}
                rawFallback={!isString ? diff.before : undefined}
                multiline={multiline}
                emptyText={emptyText}
              />
              <DiffColumn
                side="after"
                tokens={diff.tokens}
                fallbackText={isString ? (diff.after as string) : undefined}
                rawFallback={!isString ? diff.after : undefined}
                multiline={multiline}
                emptyText={emptyText}
              />
            </div>
          )
        )}
      </div>
    </div>
  );
}

/**
 * Inline token stream with red/green highlights. Public so the
 * summary header can render a compact "diff preview" without the
 * full two-column layout.
 */
export function TokenStream({ tokens, className }: { tokens: DiffToken[]; className?: string }) {
  if (tokens.length === 0) {
    return <span className="text-[hsl(var(--text-secondary))]">—</span>;
  }
  return (
    <span className={clsx("whitespace-pre-wrap break-words", className)}>
      {tokens.map((token, i) => {
        if (token.type === "unchanged") {
          return (
            <span key={i} className="text-[hsl(var(--text-primary))] dark:text-white">
              {token.value}
            </span>
          );
        }
        if (token.type === "added") {
          return (
            <span
              key={i}
              role="note"
              aria-label="texto añadido"
              className="bg-[hsl(var(--success-muted))] dark:bg-[hsl(var(--success))]/25 text-success-text dark:text-[hsl(var(--success))] rounded-sm px-0.5"
            >
              {token.value}
            </span>
          );
        }
        return (
          <span
            key={i}
            role="note"
            aria-label="texto eliminado"
            className="bg-[hsl(var(--danger-muted))] dark:bg-[hsl(var(--danger))]/25 text-danger-text dark:text-[hsl(var(--danger))] line-through rounded-sm px-0.5"
          >
            {token.value}
          </span>
        );
      })}
    </span>
  );
}

// ── Internals ──────────────────────────────────────────────────────────

function DiffColumn({
  side,
  tokens,
  fallbackText,
  rawFallback,
  multiline,
  emptyText,
}: {
  side: "before" | "after";
  tokens: DiffToken[] | undefined;
  fallbackText?: string;
  rawFallback?: unknown;
  multiline: boolean;
  emptyText: string;
}) {
  const columnTokens = (tokens ?? []).filter((t) =>
    side === "before" ? t.type !== "added" : t.type !== "removed",
  );
  const isBefore = side === "before";

  return (
    <div
      className={clsx(
        "rounded-md border px-2.5 py-1.5 text-[12px]",
        isBefore
          ? "bg-danger-soft/60 dark:bg-[hsl(var(--danger))]/5 border-[hsl(var(--danger)/25%)]/70 dark:border-[hsl(var(--danger)/100%)]/20"
          : "bg-success-soft/60 dark:bg-[hsl(var(--success))]/5 border-[hsl(var(--success)/25%)]/70 dark:border-[hsl(var(--success)/100%)]/20",
        multiline && "whitespace-pre-wrap break-words",
      )}
    >
      {columnTokens.length > 0 ? (
        <TokenStream tokens={columnTokens} />
      ) : fallbackText !== undefined ? (
        <span className={clsx(isBefore && "line-through text-danger-text/80 dark:text-[hsl(var(--danger)/80%)]")}>
          {fallbackText || <span className="text-[hsl(var(--text-secondary))]">{emptyText}</span>}
        </span>
      ) : (
        <span className={clsx(isBefore && "line-through", "text-[hsl(var(--text-primary))] dark:text-white")}>
          {renderValue(rawFallback, emptyText)}
        </span>
      )}
    </div>
  );
}

function renderValue(v: unknown, emptyText: string): React.ReactNode {
  if (v == null) return <span className="text-[hsl(var(--text-secondary))]">{emptyText}</span>;
  if (typeof v === "string") return v || <span className="text-[hsl(var(--text-secondary))]">{emptyText}</span>;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return <code className="text-[11px]">{JSON.stringify(v)}</code>;
}
