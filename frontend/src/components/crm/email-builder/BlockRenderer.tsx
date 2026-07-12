/** BlockRenderer — dispatcher de bloques. */
'use client';
import type { EmailBlock } from './blockTypes';
import { HeaderBlock, TextBlock, ButtonBlock, ImageBlock, DividerBlock, SpacerBlock, VerseBlock, ColumnsBlock } from './blocks';

interface Props { block: EmailBlock; isEditing: boolean; onUpdate?: (props: Record<string, unknown>) => void; }

export default function BlockRenderer({ block, isEditing, onUpdate }: Props) {
  const handleTextUpdate = (content: string) => onUpdate?.({ content });
  switch (block.type) {
    case 'header': return <HeaderBlock block={block} />;
    case 'text': return <TextBlock block={block} isEditing={isEditing} onUpdate={handleTextUpdate} />;
    case 'button': return <ButtonBlock block={block} />;
    case 'image': return <ImageBlock block={block} />;
    case 'divider': return <DividerBlock block={block} />;
    case 'spacer': return <SpacerBlock block={block} />;
    case 'verse': return <VerseBlock block={block} />;
    case 'columns': return <ColumnsBlock block={block} />;
    default: return <div className="p-4 text-center text-xs text-[hsl(var(--text-secondary))]">Bloque desconocido: {block.type}</div>;
  }
}
