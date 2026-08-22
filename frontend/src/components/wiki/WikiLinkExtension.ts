import { Node, mergeAttributes, InputRule } from '@tiptap/core';
import Suggestion, { SuggestionOptions } from '@tiptap/suggestion';
import { ReactRenderer } from '@tiptap/react';
import tippy, { Instance as TippyInstance } from 'tippy.js';
import { WikiLinkList, WikiLinkItem } from './WikiLinkList';
import { apiFetch } from '@/lib/http';

export interface WikiLinkOptions {
  suggestion: Omit<SuggestionOptions<WikiLinkItem>, 'editor'>;
  token?: string | null;
}

export const WikiLinkExtension = Node.create<WikiLinkOptions>({
  name: 'wikiLink',
  group: 'inline',
  inline: true,
  selectable: true,
  atom: true,

  addAttributes() {
    return {
      pageKey: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-page-key'),
        renderHTML: (attributes) => ({
          'data-page-key': attributes.pageKey,
        }),
      },
      title: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-title') || element.textContent?.replace(/^\[\[|\]\]$/g, ''),
        renderHTML: (attributes) => ({
          'data-title': attributes.title,
        }),
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'span[data-type="wiki-link"]',
      },
      {
        tag: 'a[data-type="wiki-link"]',
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    const pageKey = node.attrs.pageKey || 'wiki_page';
    const title = node.attrs.title || pageKey;

    return [
      'a',
      mergeAttributes(
        {
          href: `/plataforma/wiki/docs/${pageKey}`,
          'data-type': 'wiki-link',
          class:
            'wiki-link inline-flex items-center font-bold text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.08)] hover:bg-[hsl(var(--primary)/0.18)] dark:bg-[hsl(var(--primary)/0.15)] dark:hover:bg-[hsl(var(--primary)/0.25)] px-1.5 py-0.5 rounded-md border border-[hsl(var(--primary)/0.2)] no-underline transition-all cursor-pointer select-none text-xs mx-0.5',
        },
        HTMLAttributes
      ),
      `[[${title}]]`,
    ];
  },

  addInputRules() {
    return [
      new InputRule({
        find: /\[\[([a-zA-Z0-9_\-\s]+)(?:\|([^\]]+))?\]\]$/,
        handler: ({ state, range, match }) => {
          const rawKeyOrTitle = match[1]?.trim();
          const rawLabel = match[2]?.trim() || rawKeyOrTitle;

          if (!rawKeyOrTitle) return;

          const slugKey = rawKeyOrTitle.startsWith('wiki_')
            ? rawKeyOrTitle
            : `wiki_${rawKeyOrTitle.toLowerCase().replace(/ /g, '_').replace(/[^\w_-]/g, '')}`;

          const { tr } = state;
          tr.replaceWith(
            range.from,
            range.to,
            this.type.create({
              pageKey: slugKey,
              title: rawLabel,
            })
          );
        },
      }),
    ];
  },

  addProseMirrorPlugins() {
    return [
      Suggestion({
        editor: this.editor,
        char: '[[',
        allowSpaces: true,
        command: ({ editor, range, props }: { editor: any; range: any; props: WikiLinkItem }) => {
          editor
            .chain()
            .focus()
            .deleteRange(range)
            .insertContent([
              {
                type: this.name,
                attrs: {
                  pageKey: props.page_key,
                  title: props.title,
                },
              },
              {
                type: 'text',
                text: ' ',
              },
            ])
            .run();
        },
        items: async ({ query }: { query: string }) => {
          try {
            const token = (this.options as any).token;
            const searchParam = query ? `?search=${encodeURIComponent(query)}&limit=10` : '?limit=10';
            const docs = await apiFetch<Array<{ id: string; page_key: string; title: string; category?: string }>>(
              `/wiki/pages${searchParam}`,
              { token: token || undefined }
            );

            if (Array.isArray(docs)) {
              return docs.map((d) => ({
                id: d.id,
                page_key: d.page_key,
                title: d.title,
                category: d.category || 'General',
              }));
            }
            return [];
          } catch {
            return [];
          }
        },
        render: () => {
          let component: ReactRenderer;
          let popup: TippyInstance[];

          return {
            onStart: (props: any) => {
              component = new ReactRenderer(WikiLinkList, {
                props,
                editor: props.editor,
              });

              if (!props.clientRect) return;

              popup = tippy('body', {
                getReferenceClientRect: props.clientRect,
                appendTo: () => document.body,
                content: component.element,
                showOnCreate: true,
                interactive: true,
                trigger: 'manual',
                placement: 'bottom-start',
              });
            },
            onUpdate(props: any) {
              component.updateProps(props);
              if (!props.clientRect) return;
              popup[0]?.setProps({
                getReferenceClientRect: props.clientRect,
              });
            },
            onKeyDown(props: any) {
              if (props.event.key === 'Escape') {
                popup[0]?.hide();
                return true;
              }
              return (component.ref as any)?.onKeyDown?.(props) ?? false;
            },
            onExit() {
              popup[0]?.destroy();
              component.destroy();
            },
          };
        },
      }),
    ];
  },
});
