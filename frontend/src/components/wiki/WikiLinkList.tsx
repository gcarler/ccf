import React, { forwardRef, useEffect, useImperativeHandle, useState } from 'react';
import { BookOpen, Plus, FileText, Sparkles } from 'lucide-react';
import type { SuggestionKeyDownProps } from '@tiptap/suggestion';

export interface WikiLinkItem {
  id?: string;
  page_key: string;
  title: string;
  category?: string | null;
}

export interface WikiLinkListProps {
  items: WikiLinkItem[];
  query: string;
  command: (item: WikiLinkItem) => void;
}

export const WikiLinkList = forwardRef((props: WikiLinkListProps, ref) => {
  const [selectedIndex, setSelectedIndex] = useState(0);

  const selectItem = (index: number) => {
    const item = props.items[index];
    if (item) {
      props.command(item);
    } else if (props.query.trim()) {
      // Create new page option
      const slugKey = `wiki_${props.query.trim().toLowerCase().replace(/ /g, '_').replace(/[^\w_-]/g, '')}`;
      props.command({
        page_key: slugKey,
        title: props.query.trim(),
        category: 'General',
      });
    }
  };

  const upHandler = () => {
    setSelectedIndex((selectedIndex + props.items.length) % (props.items.length || 1));
  };

  const downHandler = () => {
    setSelectedIndex((selectedIndex + 1) % (props.items.length || 1));
  };

  const enterHandler = () => {
    selectItem(selectedIndex);
  };

  useEffect(() => setSelectedIndex(0), [props.items]);

  useImperativeHandle(ref, () => ({
    onKeyDown: ({ event }: SuggestionKeyDownProps) => {
      if (event.key === 'ArrowUp') {
        upHandler();
        return true;
      }
      if (event.key === 'ArrowDown') {
        downHandler();
        return true;
      }
      if (event.key === 'Enter' || event.key === 'Tab') {
        enterHandler();
        return true;
      }
      return false;
    },
  }));

  return (
    <div className="z-50 min-w-[260px] max-w-[340px] overflow-hidden rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--bg-primary))] p-1.5 shadow-2xl dark:border-white/10 dark:bg-[#1c1d22]">
      <div className="flex items-center gap-1.5 border-b border-[hsl(var(--border))] px-2.5 py-1.5 text-[10px] font-extrabold uppercase tracking-wider text-[hsl(var(--text-secondary))] dark:border-white/5">
        <Sparkles size={11} className="text-[hsl(var(--primary))]" />
        <span>Vincular Documento Wiki [[...]]</span>
      </div>

      <div className="max-h-56 overflow-y-auto py-1 space-y-0.5">
        {props.items.length > 0 ? (
          props.items.map((item, index) => (
            <button
              key={item.page_key || index}
              type="button"
              onClick={() => selectItem(index)}
              className={`flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left text-xs font-semibold transition-all ${
                index === selectedIndex
                  ? 'bg-[hsl(var(--primary))] text-white shadow-sm'
                  : 'text-[hsl(var(--text-primary))] hover:bg-[hsl(var(--surface-1))] dark:text-zinc-200 dark:hover:bg-white/5'
              }`}
            >
              <div className="flex items-center gap-2 min-w-0">
                <FileText size={14} className={index === selectedIndex ? 'text-white' : 'text-[hsl(var(--primary))]'} />
                <span className="truncate">{item.title}</span>
              </div>
              {item.category && (
                <span
                  className={`shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold uppercase ${
                    index === selectedIndex
                      ? 'bg-white/20 text-white'
                      : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] dark:bg-white/10'
                  }`}
                >
                  {item.category}
                </span>
              )}
            </button>
          ))
        ) : (
          <div className="px-3 py-2 text-center text-xs text-[hsl(var(--text-secondary))]">
            {props.query ? (
              <button
                type="button"
                onClick={() => selectItem(-1)}
                className="flex w-full items-center justify-center gap-1.5 rounded-lg bg-[hsl(var(--primary)/0.1)] px-3 py-2 text-xs font-bold text-[hsl(var(--primary))] hover:bg-[hsl(var(--primary)/0.2)] transition-all"
              >
                <Plus size={13} />
                Crear página: &quot;{props.query}&quot;
              </button>
            ) : (
              <div className="flex items-center justify-center gap-1.5 py-2">
                <BookOpen size={14} className="opacity-40" />
                <span>Escribe para buscar o crear...</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
});

WikiLinkList.displayName = 'WikiLinkList';
