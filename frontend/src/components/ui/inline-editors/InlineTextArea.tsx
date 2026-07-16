"use client";

import React, { useEffect, useRef, useState } from "react";
import clsx from "clsx";

interface InlineTextAreaProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  inputClassName?: string;
  ariaLabel?: string;
  rows?: number;
}

export function InlineTextArea({
  value,
  onChange,
  disabled,
  placeholder,
  className,
  inputClassName,
  ariaLabel,
  rows = 3,
}: InlineTextAreaProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (isEditing) {
      setDraft(value);
      textareaRef.current?.focus();
    }
  }, [isEditing, value]);

  const save = () => {
    setIsEditing(false);
    if (draft.trim() !== value.trim()) {
      onChange(draft.trim());
    }
  };

  const cancel = () => {
    setIsEditing(false);
    setDraft(value);
  };

  if (isEditing) {
    return (
      <textarea
        ref={textareaRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) save();
          if (e.key === "Escape") cancel();
        }}
        disabled={disabled}
        placeholder={placeholder}
        aria-label={ariaLabel}
        rows={rows}
        className={clsx(
          "w-full resize-none rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1 text-sm outline-none transition-all focus:border-[hsl(var(--primary))] focus:ring-1 focus:ring-[hsl(var(--primary))] dark:border-white/10 dark:bg-white/5",
          inputClassName
        )}
      />
    );
  }

  return (
    <button
      onClick={() => setIsEditing(true)}
      disabled={disabled}
      className={clsx(
        "w-full text-left rounded-md px-2 py-1 -ml-2 transition-colors hover:bg-[hsl(var(--surface-1))] dark:hover:bg-white/5",
        className
      )}
      aria-label={ariaLabel}
    >
      <span className={clsx(!value && "text-[hsl(var(--text-secondary))]")}>
        {value || placeholder || "—"}
      </span>
    </button>
  );
}
