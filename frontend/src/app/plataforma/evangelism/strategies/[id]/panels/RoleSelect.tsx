import { useEffect, useId, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';

export function RoleSelect({ value, options, colorClass, onChange }: {
  value: string;
  options: { value: string; label: string }[];
  colorClass: string;
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(() => Math.max(0, options.findIndex(o => o.value === value)));
  const instanceId = useId();
  const listboxId = `role-listbox-${instanceId}`;
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const current = options.find(o => o.value === value);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    setActiveIndex(Math.max(0, options.findIndex(o => o.value === value)));
  }, [open, value, options]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setOpen(false);
      e.preventDefault();
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActiveIndex(i => Math.min(options.length - 1, i + 1));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setOpen(true);
      setActiveIndex(i => Math.max(0, i - 1));
      return;
    }
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
      if (!open) {
        e.preventDefault();
        setOpen(true);
        return;
      }
      const opt = options[activeIndex];
      if (opt) {
        e.preventDefault();
        onChange(opt.value);
        setOpen(false);
      }
      return;
    }
    if (e.key === 'Home') {
      e.preventDefault();
      setActiveIndex(0);
      return;
    }
    if (e.key === 'End') {
      e.preventDefault();
      setActiveIndex(options.length - 1);
      return;
    }
  };

  return (
    <div ref={ref} className="relative" onKeyDown={handleKeyDown}>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen(o => !o)}
        role="combobox"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={listboxId}
        aria-activedescendant={open && options[activeIndex] ? `${listboxId}-option-${activeIndex}` : undefined}
        className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded cursor-pointer ${colorClass}`}
      >
        {current?.label ?? value}
        <ChevronDown size={10} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div id={listboxId} role="listbox" className="absolute right-0 top-full mt-1 z-50 min-w-[140px] bg-[hsl(var(--bg-primary))] border border-[hsl(var(--border-primary))] rounded-lg shadow-lg py-1 overflow-hidden">
          {options.map((opt, i) => (
            <button
              key={opt.value}
              id={`${listboxId}-option-${i}`}
              type="button"
              role="option"
              aria-selected={value === opt.value}
              onClick={() => { onChange(opt.value); setOpen(false); triggerRef.current?.focus(); }}
              className={`w-full text-left px-3 py-1.5 text-xs font-semibold hover:bg-[hsl(var(--bg-muted))] transition-colors ${value === opt.value ? 'opacity-60' : ''} ${i === activeIndex ? 'bg-[hsl(var(--bg-muted))] outline-none' : ''}`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
