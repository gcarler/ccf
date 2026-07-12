'use client';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { useEffect } from 'react';
import type { EmailBlock, TextProps } from '../blockTypes';

export default function TextBlock({ block, isEditing, onUpdate }: { block: EmailBlock; isEditing: boolean; onUpdate: (content: string) => void }) {
  const p = block.props as TextProps;
  const editor = useEditor({ extensions: [StarterKit, Placeholder.configure({ placeholder: 'Escribe tu mensaje...' })], content: p.content || '<p>Escribe tu mensaje aqui...</p>', editable: isEditing, onUpdate: ({ editor }) => onUpdate(editor.getHTML()) });
  useEffect(() => { if (editor && editor.getHTML() !== p.content) editor.commands.setContent(p.content || '<p></p>', false); }, [isEditing]);
  return <div className="p-4" style={{ textAlign: (p.textAlign as any) || 'left' }}><EditorContent editor={editor} className="prose prose-sm max-w-none" /></div>;
}
