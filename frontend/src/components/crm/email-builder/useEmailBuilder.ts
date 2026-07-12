/** Hook principal del editor de email */
'use client';
import { useCallback, useReducer, useState } from 'react';
import { arrayMove } from '@dnd-kit/sortable';
import { getDefaultProps, type BlockType, type EmailBlock } from './blockTypes';

type Action =
  | { type: 'ADD_BLOCK'; blockType: BlockType; index?: number }
  | { type: 'REMOVE_BLOCK'; id: string }
  | { type: 'MOVE_BLOCK'; activeId: string; overId: string }
  | { type: 'UPDATE_BLOCK_PROPS'; id: string; props: Record<string, unknown> }
  | { type: 'DUPLICATE_BLOCK'; id: string }
  | { type: 'SET_BLOCKS'; blocks: EmailBlock[] }
  | { type: 'UNDO' }
  | { type: 'REDO' };

interface BuilderState { blocks: EmailBlock[]; past: EmailBlock[][]; future: EmailBlock[][] }

function generateId(): string { return `block-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`; }

function reducer(state: BuilderState, action: Action): BuilderState {
  const { blocks, past, future } = state;
  function pushHistory(current: EmailBlock[]): BuilderState { return { blocks: current, past: [...past.slice(-49), blocks], future: [] }; }
  switch (action.type) {
    case 'ADD_BLOCK': { const nb: EmailBlock = { id: generateId(), type: action.blockType, props: getDefaultProps(action.blockType) }; const i = action.index ?? blocks.length; return pushHistory([...blocks.slice(0, i), nb, ...blocks.slice(i)]); }
    case 'REMOVE_BLOCK': return pushHistory(blocks.filter(b => b.id !== action.id));
    case 'MOVE_BLOCK': { const oi = blocks.findIndex(b => b.id === action.activeId); const ni = blocks.findIndex(b => b.id === action.overId); if (oi === -1 || ni === -1) return state; return pushHistory(arrayMove(blocks, oi, ni)); }
    case 'UPDATE_BLOCK_PROPS': return pushHistory(blocks.map(b => b.id === action.id ? { ...b, props: { ...b.props, ...action.props } } : b));
    case 'DUPLICATE_BLOCK': { const idx = blocks.findIndex(b => b.id === action.id); if (idx === -1) return state; const d: EmailBlock = { id: generateId(), type: blocks[idx].type, props: structuredClone(blocks[idx].props) }; return pushHistory([...blocks.slice(0, idx + 1), d, ...blocks.slice(idx + 1)]); }
    case 'SET_BLOCKS': return pushHistory(action.blocks);
    case 'UNDO': { if (past.length === 0) return state; const prev = past[past.length - 1]; return { blocks: prev, past: past.slice(0, -1), future: [blocks, ...future] }; }
    case 'REDO': { if (future.length === 0) return state; const next = future[0]; return { blocks: next, past: [...past, blocks], future: future.slice(1) }; }
    default: return state;
  }
}

export interface UseEmailBuilderReturn {
  blocks: EmailBlock[]; selectedId: string | null; canUndo: boolean; canRedo: boolean;
  addBlock: (type: BlockType, index?: number) => void; removeBlock: (id: string) => void;
  moveBlock: (activeId: string, overId: string) => void; updateBlockProps: (id: string, props: Record<string, unknown>) => void;
  duplicateBlock: (id: string) => void; selectBlock: (id: string | null) => void;
  setBlocks: (blocks: EmailBlock[]) => void; undo: () => void; redo: () => void;
  selectedBlock: EmailBlock | undefined; getBlocksJson: () => EmailBlock[];
}

export function useEmailBuilder(initialBlocks: EmailBlock[] = []): UseEmailBuilderReturn {
  const [state, dispatch] = useReducer(reducer, { blocks: initialBlocks, past: [], future: [] });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const addBlock = useCallback((type: BlockType, index?: number) => dispatch({ type: 'ADD_BLOCK', blockType: type, index }), []);
  const removeBlock = useCallback((id: string) => { dispatch({ type: 'REMOVE_BLOCK', id }); if (selectedId === id) setSelectedId(null); }, [selectedId]);
  const moveBlock = useCallback((a: string, o: string) => dispatch({ type: 'MOVE_BLOCK', activeId: a, overId: o }), []);
  const updateBlockProps = useCallback((id: string, props: Record<string, unknown>) => dispatch({ type: 'UPDATE_BLOCK_PROPS', id, props }), []);
  const duplicateBlock = useCallback((id: string) => dispatch({ type: 'DUPLICATE_BLOCK', id }), []);
  const selectBlock = useCallback((id: string | null) => setSelectedId(id), []);
  const setBlocks = useCallback((blocks: EmailBlock[]) => dispatch({ type: 'SET_BLOCKS', blocks }), []);
  const undo = useCallback(() => dispatch({ type: 'UNDO' }), []);
  const redo = useCallback(() => dispatch({ type: 'REDO' }), []);
  const selectedBlock = state.blocks.find(b => b.id === selectedId);
  const getBlocksJson = useCallback(() => state.blocks, [state.blocks]);
  return { blocks: state.blocks, selectedId, canUndo: state.past.length > 0, canRedo: state.future.length > 0, addBlock, removeBlock, moveBlock, updateBlockProps, duplicateBlock, selectBlock, setBlocks, undo, redo, selectedBlock, getBlocksJson };
}
