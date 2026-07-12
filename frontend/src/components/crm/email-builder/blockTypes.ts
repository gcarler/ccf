/** Block type definitions for the CRM email builder. */
export type BlockType = 'header' | 'text' | 'button' | 'image' | 'divider' | 'spacer' | 'verse' | 'columns';
export type BlockCategory = 'content' | 'layout';

export interface BlockTypeDefinition {
  type: BlockType;
  label: string;
  icon: string;
  category: BlockCategory;
  defaultProps: Record<string, unknown>;
}

export interface EmailBlock {
  id: string;
  type: BlockType;
  props: Record<string, unknown>;
}

export const BLOCK_DEFINITIONS: BlockTypeDefinition[] = [
  { type: 'header', label: 'Encabezado', icon: 'Type', category: 'content', defaultProps: { title: 'Tu titulo aqui', subtitle: '', textAlign: 'center', titleColor: '', bgColor: '' } },
  { type: 'text', label: 'Texto', icon: 'AlignLeft', category: 'content', defaultProps: { content: '<p>Escribe tu mensaje aqui...</p>', textAlign: 'left' } },
  { type: 'button', label: 'Boton CTA', icon: 'MousePointerClick', category: 'content', defaultProps: { label: 'Haz clic aqui', url: '#', align: 'center', bgColor: '', textColor: '#ffffff', borderRadius: 10 } },
  { type: 'image', label: 'Imagen', icon: 'Image', category: 'content', defaultProps: { src: '', alt: '', width: '100%', href: '' } },
  { type: 'divider', label: 'Divisor', icon: 'Minus', category: 'layout', defaultProps: { color: '#e5e7eb', thickness: 1, style: 'solid', width: '100%' } },
  { type: 'spacer', label: 'Espacio', icon: 'Space', category: 'layout', defaultProps: { height: 24 } },
  { type: 'verse', label: 'Versiculo', icon: 'BookOpen', category: 'content', defaultProps: { text: 'Jeremias 29:11', reference: 'Jeremias 29:11', textAlign: 'center' } },
  { type: 'columns', label: 'Columnas', icon: 'Columns', category: 'layout', defaultProps: { count: 2, columns: [{ blocks: [] }, { blocks: [] }] } },
];

export function getBlockDefinition(type: BlockType): BlockTypeDefinition | undefined {
  return BLOCK_DEFINITIONS.find(b => b.type === type);
}

export function getDefaultProps(type: BlockType): Record<string, unknown> {
  return getBlockDefinition(type)?.defaultProps ?? {};
}
