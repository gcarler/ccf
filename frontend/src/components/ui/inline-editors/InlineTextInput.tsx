"use client";

import React, { useEffect, useRef, useState } from "react";
import clsx from "clsx";

interface InlineTextInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  inputClassName?: string;
  ariaLabel?: string;
}

export function InlineTextInput({
  value,
  onChange,
  disabled,
  placeholder,
  className,
  inputClassName,
  ariaLabel,
}: InlineTextInputProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) {
      setDraft(value);
      inputRef.current?.focus();
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
      <input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => {
          if (e.key === "Enter") save();
          if (e.key === "Escape") cancel();
        }}
        disabled={disabled}
        placeholder={placeholder}
        aria-label={ariaLabel}
        className={clsx(
          "w-full rounded-md border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] px-2 py-1 text-sm font-bold outline-none transition-all focus:border-[hsl(var(--primary))] focus:ring-1 focus:ring-[hsl(var(--primary))] dark:border-white/10 dark:bg-white/5",
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
