"use client";

import { useEffect, useState } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import { BubbleMenu } from "@tiptap/react/menus";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Placeholder from "@tiptap/extension-placeholder";
import CharacterCount from "@tiptap/extension-character-count";
import Highlight from "@tiptap/extension-highlight";
import Typography from "@tiptap/extension-typography";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
import { TextStyle } from "@tiptap/extension-text-style";
import { Color } from "@tiptap/extension-color";
import { Table, TableRow, TableHeader, TableCell } from "@tiptap/extension-table";
import * as Popover from "@radix-ui/react-popover";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Strikethrough,
  Heading1,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  CheckSquare,
  Quote,
  Code,
  FileCode,
  Link as LinkIcon,
  Unlink,
  Image as ImageIcon,
  Table as TableIcon,
  Palette,
  Maximize2,
  Minimize2,
  Undo,
  Redo,
  X,
  Plus,
  Trash2,
  Rows,
  Columns,
} from "lucide-react";
import clsx from "clsx";
import { apiFetch } from "@/lib/http";

interface CmsMediaItem {
  id: number;
  url: string;
  filename?: string | null;
  alt_text?: string | null;
  mime_type?: string | null;
}

interface RichEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
  readOnly?: boolean;
  minHeight?: string;
  token?: string;
}

const TEXT_COLORS = [
  { name: "Predeterminado", color: "" },
  { name: "Negro", color: "#000000" },
  { name: "Gris", color: "#6b7280" },
  { name: "Rojo", color: "#ef4444" },
  { name: "Azul", color: "#3b82f6" },
  { name: "Verde", color: "#10b981" },
];

export default function RichEditor({
  content,
  onChange,
  placeholder = "Escribe tu contenido aquí...",
  readOnly = false,
  minHeight = "200px",
  token,
}: RichEditorProps) {
  // ── States ────────────────────────────────────────────────────────────────
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showImagePicker, setShowImagePicker] = useState(false);
  const [showLinkPopover, setShowLinkPopover] = useState(false);
  const [linkUrl, setLinkUrl] = useState("");
  const [customImageUrl, setCustomImageUrl] = useState("");
  const [mediaItems, setMediaItems] = useState<CmsMediaItem[]>([]);
  const [mediaLoading, setMediaLoading] = useState(false);
  const [showColorPicker, setShowColorPicker] = useState(false);

  // ── TipTap Editor Setup ───────────────────────────────────────────────────
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        link: {
          openOnClick: false,
        },
      }),
      Image,
      Placeholder.configure({
        placeholder,
      }),
      CharacterCount,
      Highlight,
      Typography,
      TaskList,
      TaskItem.configure({
        nested: true,
      }),
      TextStyle,
      Color,
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content,
    editable: !readOnly,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML());
    },
    editorProps: {
      attributes: {
        class: clsx(
          "prose prose-sm sm:prose lg:prose-lg xl:prose-2xl mx-auto focus:outline-none max-w-none",
          "prose-headings:text-[hsl(var(--text-primary))] dark:prose-headings:text-white",
          "prose-p:text-[hsl(var(--text-secondary))] dark:prose-p:text-[hsl(var(--text-secondary))]",
          "prose-a:text-[hsl(var(--primary))] prose-a:no-underline hover:prose-a:underline",
          "prose-blockquote:border-l-[hsl(var(--primary))] prose-blockquote:bg-[hsl(var(--surface-2))]/50 dark:prose-blockquote:bg-white/5 prose-blockquote:py-1 prose-blockquote:px-4",
          "prose-code:text-[hsl(var(--info))] prose-code:bg-[hsl(var(--info))]/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded",
          "prose-pre:bg-[hsl(var(--surface-2))] dark:prose-pre:bg-[#1a1b1e] prose-pre:text-[hsl(var(--text-primary))] dark:prose-pre:text-white",
          "prose-li:text-[hsl(var(--text-secondary))]",
          "[&_table]:w-full [&_table]:border-collapse [&_table]:my-4 [&_td]:border [&_td]:border-[hsl(var(--border))] dark:[&_td]:border-zinc-700 [&_td]:p-2 [&_th]:border [&_th]:border-[hsl(var(--border))] dark:[&_th]:border-zinc-700 [&_th]:p-2 [&_th]:bg-[hsl(var(--surface-2))] dark:[&_th]:bg-zinc-800 [&_th]:font-semibold"
        ),
        style: `min-height: ${minHeight};`,
      },
    },
  });

  useEffect(() => {
    if (editor && editor.getHTML() !== content) {
      editor.commands.setContent(content || "");
    }
  }, [content, editor]);

  useEffect(() => {
    if (editor) {
      editor.setEditable(!readOnly);
    }
  }, [readOnly, editor]);

  // ESC key for fullscreen mode
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen]);

  // Fetch Media Library items
  const fetchMediaLibrary = async () => {
    setMediaLoading(true);
    try {
      const response = await apiFetch<{ items?: CmsMediaItem[] } | CmsMediaItem[]>(
        "/cms/media?type=image&limit=12",
        {
          token,
          cache: "no-store",
        }
      );
      if (Array.isArray(response)) {
        setMediaItems(response);
      } else if (response && Array.isArray(response.items)) {
        setMediaItems(response.items);
      } else {
        setMediaItems([]);
      }
    } catch {
      setMediaItems([]);
    } finally {
      setMediaLoading(false);
    }
  };

  const openImagePicker = () => {
    setShowImagePicker(true);
    fetchMediaLibrary();
  };

  const insertImage = (url: string, alt?: string) => {
    if (!url || !editor) return;
    editor.chain().focus().setImage({ src: url, alt: alt || "" }).run();
    setShowImagePicker(false);
    setCustomImageUrl("");
  };

  const handleOpenLinkPopover = () => {
    if (!editor) return;
    setLinkUrl(editor.getAttributes("link").href || "");
    setShowLinkPopover(true);
  };

  const saveLink = () => {
    if (!editor) return;
    if (!linkUrl.trim()) {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
    } else {
      editor.chain().focus().extendMarkRange("link").setLink({ href: linkUrl.trim() }).run();
    }
    setShowLinkPopover(false);
  };

  const removeLink = () => {
    if (!editor) return;
    editor.chain().focus().extendMarkRange("link").unsetLink().run();
    setShowLinkPopover(false);
  };

  if (!editor) {
    return null;
  }

  return (
    <div
      className={clsx(
        "w-full bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] flex flex-col transition-all",
        isFullscreen
          ? "fixed inset-0 z-50 rounded-none h-screen w-screen overflow-hidden"
          : "rounded-md border border-[hsl(var(--border))] dark:border-white/10 overflow-hidden"
      )}
    >
      {/* ── Floating Bubble Menu for Selected Text (R1) ── */}
      {editor && !readOnly && (
        <BubbleMenu
          editor={editor}
          className="flex items-center gap-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 shadow-xl rounded-lg p-1.5 z-30"
        >
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleBold().run()}
            className={clsx(
              "p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-200",
              editor.isActive("bold") && "text-[hsl(var(--primary))] bg-zinc-100 dark:bg-zinc-800 font-bold"
            )}
            title="Negrita"
          >
            <Bold size={15} />
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleItalic().run()}
            className={clsx(
              "p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-200",
              editor.isActive("italic") && "text-[hsl(var(--primary))] bg-zinc-100 dark:bg-zinc-800"
            )}
            title="Cursiva"
          >
            <Italic size={15} />
          </button>
          <button
            type="button"
            onClick={() => editor.chain().focus().toggleUnderline().run()}
            className={clsx(
              "p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-200",
              editor.isActive("underline") && "text-[hsl(var(--primary))] bg-zinc-100 dark:bg-zinc-800"
            )}
            title="Subrayado"
          >
            <UnderlineIcon size={15} />
          </button>
          <button
            type="button"
            onClick={handleOpenLinkPopover}
            className={clsx(
              "p-1.5 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-700 dark:text-zinc-200",
              editor.isActive("link") && "text-[hsl(var(--primary))] bg-zinc-100 dark:bg-zinc-800"
            )}
            title="Enlace"
          >
            <LinkIcon size={15} />
          </button>
        </BubbleMenu>
      )}

      {/* ── Editor Main Toolbar ── */}
      {!readOnly && (
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-1 border-b border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-2 shrink-0">
          {/* Format Group */}
          <div className="flex items-center gap-1 pr-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBold().run()}
              disabled={!editor.can().chain().focus().toggleBold().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("bold")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Negrita"
            >
              <Bold size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleItalic().run()}
              disabled={!editor.can().chain().focus().toggleItalic().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("italic")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Cursiva"
            >
              <Italic size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              disabled={!editor.can().chain().focus().toggleUnderline().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("underline")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Subrayado"
            >
              <UnderlineIcon size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleStrike().run()}
              disabled={!editor.can().chain().focus().toggleStrike().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("strike")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Tachado"
            >
              <Strikethrough size={16} />
            </button>
          </div>

          {/* Headings */}
          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("heading", { level: 1 })
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Título 1"
            >
              <Heading1 size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("heading", { level: 2 })
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Título 2"
            >
              <Heading2 size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("heading", { level: 3 })
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Título 3"
            >
              <Heading3 size={16} />
            </button>
          </div>

          {/* 6 Color Swatches Palette (R4) */}
          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <Popover.Root open={showColorPicker} onOpenChange={setShowColorPicker}>
              <Popover.Trigger asChild>
                <button
                  type="button"
                  className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 text-[hsl(var(--text-secondary))]"
                  title="Color de texto"
                >
                  <Palette size={16} />
                </button>
              </Popover.Trigger>
              <Popover.Content className="z-50 p-2.5 rounded-lg bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shadow-xl flex items-center gap-1.5">
                {TEXT_COLORS.map((c) => (
                  <button
                    key={c.name}
                    type="button"
                    title={c.name}
                    onClick={() => {
                      if (c.color) {
                        editor.chain().focus().setColor(c.color).run();
                      } else {
                        editor.chain().focus().unsetColor().run();
                      }
                      setShowColorPicker(false);
                    }}
                    className={clsx(
                      "size-6 rounded-full border border-zinc-300 dark:border-zinc-600 transition-transform hover:scale-110 flex items-center justify-center",
                      !c.color && "relative overflow-hidden bg-white dark:bg-zinc-900"
                    )}
                    style={{ backgroundColor: c.color || undefined }}
                  >
                    {!c.color && (
                      <span className="w-full h-0.5 bg-red-500 transform -rotate-45 block" />
                    )}
                  </button>
                ))}
              </Popover.Content>
            </Popover.Root>
          </div>

          {/* Lists & Blockquote */}
          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("bulletList")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Lista con viñetas"
            >
              <List size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("orderedList")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Lista numerada"
            >
              <ListOrdered size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleTaskList().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("taskList")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Lista de tareas"
            >
              <CheckSquare size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("blockquote")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Cita"
            >
              <Quote size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleCode().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("code")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Código inline"
            >
              <Code size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleCodeBlock().run()}
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("codeBlock")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Bloque de código"
            >
              <FileCode size={16} />
            </button>
          </div>

          {/* Table Insertion & Contextual Controls (R4) */}
          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={() =>
                editor
                  .chain()
                  .focus()
                  .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
                  .run()
              }
              className={clsx(
                "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                editor.isActive("table")
                  ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                  : "text-[hsl(var(--text-secondary))]"
              )}
              title="Insertar Tabla (3x3)"
            >
              <TableIcon size={16} />
            </button>
            {editor.isActive("table") && (
              <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800 rounded p-0.5 ml-1">
                <button
                  type="button"
                  onClick={() => editor.chain().focus().addColumnAfter().run()}
                  className="px-1.5 py-0.5 text-2xs font-medium rounded hover:bg-white dark:hover:bg-zinc-700 flex items-center gap-0.5 text-zinc-700 dark:text-zinc-200"
                  title="Agregar Columna"
                >
                  <Plus size={12} /> <Columns size={12} />
                </button>
                <button
                  type="button"
                  onClick={() => editor.chain().focus().addRowAfter().run()}
                  className="px-1.5 py-0.5 text-2xs font-medium rounded hover:bg-white dark:hover:bg-zinc-700 flex items-center gap-0.5 text-zinc-700 dark:text-zinc-200"
                  title="Agregar Fila"
                >
                  <Plus size={12} /> <Rows size={12} />
                </button>
                <button
                  type="button"
                  onClick={() => editor.chain().focus().deleteTable().run()}
                  className="p-1 rounded text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40"
                  title="Eliminar Tabla"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            )}
          </div>

          {/* Links & Images Integration (R1) */}
          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            {/* Inline Link Popover */}
            <Popover.Root open={showLinkPopover} onOpenChange={setShowLinkPopover}>
              <Popover.Trigger asChild>
                <button
                  type="button"
                  onClick={handleOpenLinkPopover}
                  className={clsx(
                    "p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors",
                    editor.isActive("link")
                      ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]"
                      : "text-[hsl(var(--text-secondary))]"
                  )}
                  title="Insertar/Editar Enlace"
                >
                  <LinkIcon size={16} />
                </button>
              </Popover.Trigger>
              <Popover.Content className="z-50 p-3 rounded-lg bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 shadow-xl w-80 space-y-2.5">
                <div className="text-xs font-semibold text-zinc-700 dark:text-zinc-200">
                  URL del Enlace
                </div>
                <input
                  type="url"
                  value={linkUrl}
                  onChange={(e) => setLinkUrl(e.target.value)}
                  placeholder="https://ejemplo.com"
                  className="w-full px-2.5 py-1.5 text-sm rounded border border-zinc-300 dark:border-zinc-600 bg-transparent outline-none focus:border-[hsl(var(--primary))]"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      saveLink();
                    }
                  }}
                />
                <div className="flex items-center justify-end gap-2 pt-1">
                  {editor.isActive("link") && (
                    <button
                      type="button"
                      onClick={removeLink}
                      className="px-2.5 py-1 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 rounded flex items-center gap-1"
                    >
                      <Unlink size={13} /> Quitar
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={saveLink}
                    className="px-3 py-1 text-xs bg-[hsl(var(--primary))] text-white rounded font-medium shadow-sm hover:opacity-90 transition-opacity"
                  >
                    Guardar
                  </button>
                </div>
              </Popover.Content>
            </Popover.Root>

            {/* Image Picker Trigger */}
            <button
              type="button"
              onClick={openImagePicker}
              className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors text-[hsl(var(--text-secondary))]"
              title="Insertar Imagen"
            >
              <ImageIcon size={16} />
            </button>
          </div>

          {/* History & Fullscreen Controls (R4) */}
          <div className="flex items-center gap-1 pl-2 ml-auto">
            <button
              type="button"
              onClick={() => editor.chain().focus().undo().run()}
              disabled={!editor.can().chain().focus().undo().run()}
              className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors text-[hsl(var(--text-secondary))] disabled:opacity-50"
              title="Deshacer"
            >
              <Undo size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().redo().run()}
              disabled={!editor.can().chain().focus().redo().run()}
              className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors text-[hsl(var(--text-secondary))] disabled:opacity-50"
              title="Rehacer"
            >
              <Redo size={16} />
            </button>
            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors text-[hsl(var(--text-secondary))]"
              title={isFullscreen ? "Salir de pantalla completa (ESC)" : "Pantalla completa"}
            >
              {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
          </div>
        </div>
      )}

      {/* Editor Content Area */}
      <div className="flex-1 p-4 overflow-y-auto">
        <EditorContent editor={editor} />
      </div>

      {/* Footer / Word Count */}
      <div className="flex items-center justify-between p-2 border-t border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] text-xs">
        <div>
          {isFullscreen && (
            <span className="text-2xs font-semibold uppercase tracking-wider text-zinc-400">
              Modo Pantalla Completa (Presiona ESC para salir)
            </span>
          )}
        </div>
        <div>{editor.storage.characterCount.words()} palabras</div>
      </div>

      {/* ── Image Library & URL Modal UI (R1) ── */}
      {showImagePicker && (
        <div
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setShowImagePicker(false)}
        >
          <div
            className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[85vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-200 dark:border-zinc-800">
              <h3 className="font-semibold text-base text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                <ImageIcon size={18} className="text-[hsl(var(--primary))]" /> Insertar Imagen
              </h3>
              <button
                type="button"
                onClick={() => setShowImagePicker(false)}
                className="p-1 rounded text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-4 space-y-5 overflow-y-auto flex-1">
              {/* Direct URL Input */}
              <div className="space-y-2">
                <label className="text-2xs font-semibold uppercase tracking-wider text-zinc-500">
                  URL Directa de Imagen
                </label>
                <div className="flex gap-2">
                  <input
                    type="url"
                    value={customImageUrl}
                    onChange={(e) => setCustomImageUrl(e.target.value)}
                    placeholder="https://ejemplo.com/imagen.jpg"
                    className="flex-1 px-3 py-1.5 text-sm rounded border border-zinc-300 dark:border-zinc-700 bg-transparent text-zinc-900 dark:text-zinc-100 outline-none focus:border-[hsl(var(--primary))]"
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && customImageUrl.trim()) {
                        e.preventDefault();
                        insertImage(customImageUrl.trim());
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => insertImage(customImageUrl.trim())}
                    disabled={!customImageUrl.trim()}
                    className="px-4 py-1.5 text-sm bg-[hsl(var(--primary))] text-white rounded font-medium disabled:opacity-50 hover:opacity-90 transition-opacity"
                  >
                    Insertar URL
                  </button>
                </div>
              </div>

              {/* CMS Media Library Grid */}
              <div className="border-t border-zinc-200 dark:border-zinc-800 pt-4">
                <label className="text-2xs font-semibold uppercase tracking-wider text-zinc-500 mb-3 block">
                  Biblioteca CMS (`/cms/media?type=image&limit=12`)
                </label>
                {mediaLoading ? (
                  <div className="py-10 text-center text-sm font-medium text-zinc-500">
                    Cargando biblioteca de imágenes...
                  </div>
                ) : mediaItems.length === 0 ? (
                  <div className="py-10 text-center text-sm text-zinc-500">
                    No se encontraron imágenes en la biblioteca.
                  </div>
                ) : (
                  <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                    {mediaItems.map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => insertImage(item.url, item.alt_text || item.filename || "")}
                        className="group relative aspect-video rounded-lg border border-zinc-200 dark:border-zinc-700 overflow-hidden hover:border-[hsl(var(--primary))] transition-all focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))]"
                      >
                        <img
                          src={item.url}
                          alt={item.alt_text || item.filename || "Imagen CMS"}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                        />
                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
