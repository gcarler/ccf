"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import CharacterCount from "@tiptap/extension-character-count";
import Underline from "@tiptap/extension-underline";
import Highlight from "@tiptap/extension-highlight";
import Typography from "@tiptap/extension-typography";
import TaskList from "@tiptap/extension-task-list";
import TaskItem from "@tiptap/extension-task-item";
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
  Image as ImageIcon,
  Undo,
  Redo,
} from "lucide-react";
import clsx from "clsx";

interface RichEditorProps {
  content: string;
  onChange: (html: string) => void;
  placeholder?: string;
  readOnly?: boolean;
  minHeight?: string;
}

export default function RichEditor({
  content,
  onChange,
  placeholder = "Escribe tu contenido aquí...",
  readOnly = false,
  minHeight = "200px",
}: RichEditorProps) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Image,
      Link.configure({
        openOnClick: false,
      }),
      Placeholder.configure({
        placeholder,
      }),
      CharacterCount,
      Underline,
      Highlight,
      Typography,
      TaskList,
      TaskItem.configure({
        nested: true,
      }),
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
          "prose-li:text-[hsl(var(--text-secondary))]"
        ),
        style: `min-height: ${minHeight};`,
      },
    },
  });

  if (!editor) {
    return null;
  }

  const addImage = () => {
    const url = window.prompt("URL de la imagen:");
    if (url) {
      editor.chain().focus().setImage({ src: url }).run();
    }
  };

  const setLink = () => {
    const previousUrl = editor.getAttributes("link").href;
    const url = window.prompt("URL del enlace:", previousUrl);

    if (url === null) {
      return;
    }
    if (url === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
  };

  return (
    <div className="w-full rounded-md border border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--bg-primary))] dark:bg-[hsl(var(--admin-bg-secondary))] overflow-hidden flex flex-col">
      {!readOnly && (
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-1 border-b border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 p-2 shrink-0">
          <div className="flex items-center gap-1 pr-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBold().run()}
              disabled={!editor.can().chain().focus().toggleBold().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("bold") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <Bold size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleItalic().run()}
              disabled={!editor.can().chain().focus().toggleItalic().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("italic") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <Italic size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              disabled={!editor.can().chain().focus().toggleUnderline().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("underline") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <UnderlineIcon size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleStrike().run()}
              disabled={!editor.can().chain().focus().toggleStrike().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("strike") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <Strikethrough size={16} />
            </button>
          </div>

          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("heading", { level: 1 }) ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <Heading1 size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("heading", { level: 2 }) ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <Heading2 size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("heading", { level: 3 }) ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <Heading3 size={16} />
            </button>
          </div>

          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("bulletList") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <List size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("orderedList") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <ListOrdered size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleTaskList().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("taskList") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <CheckSquare size={16} />
            </button>
          </div>

          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("blockquote") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <Quote size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleCode().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("code") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <Code size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().toggleCodeBlock().run()}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("codeBlock") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <FileCode size={16} />
            </button>
          </div>

          <div className="flex items-center gap-1 px-2 border-r border-[hsl(var(--border))] dark:border-white/10">
            <button
              type="button"
              onClick={setLink}
              className={clsx("p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors", editor.isActive("link") ? "bg-[hsl(var(--surface-2))] dark:bg-white/20 text-[hsl(var(--primary))]" : "text-[hsl(var(--text-secondary))]")}
            >
              <LinkIcon size={16} />
            </button>
            <button
              type="button"
              onClick={addImage}
              className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors text-[hsl(var(--text-secondary))]"
            >
              <ImageIcon size={16} />
            </button>
          </div>

          <div className="flex items-center gap-1 pl-2">
            <button
              type="button"
              onClick={() => editor.chain().focus().undo().run()}
              disabled={!editor.can().chain().focus().undo().run()}
              className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors text-[hsl(var(--text-secondary))] disabled:opacity-50"
            >
              <Undo size={16} />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().redo().run()}
              disabled={!editor.can().chain().focus().redo().run()}
              className="p-1.5 rounded hover:bg-[hsl(var(--surface-2))] dark:hover:bg-white/10 transition-colors text-[hsl(var(--text-secondary))] disabled:opacity-50"
            >
              <Redo size={16} />
            </button>
          </div>
        </div>
      )}



      <div className="flex-1 p-3 overflow-y-auto">
        <EditorContent editor={editor} />
      </div>

      <div className="flex items-center justify-end p-2 border-t border-[hsl(var(--border))] dark:border-white/10 bg-[hsl(var(--surface-1))] dark:bg-white/5 text-[hsl(var(--text-secondary))] text-xs">
        {editor.storage.characterCount.words()} palabras
      </div>
    </div>
  );
}
