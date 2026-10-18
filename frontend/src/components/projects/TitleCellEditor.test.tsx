import React, { createRef } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ICellEditorParams } from '@/components/ui/AgGridTable';
import TitleCellEditor, { type TitleCellEditorRef } from './TitleCellEditor';

function makeEditorParams(value: string, stopEditing = vi.fn()): ICellEditorParams {
  return {
    value,
    stopEditing,
  } as unknown as ICellEditorParams;
}

describe('TitleCellEditor', () => {
  it('commits trimmed value on Enter key and calls stopEditing', () => {
    const stopEditing = vi.fn();
    const ref = createRef<TitleCellEditorRef>();

    render(<TitleCellEditor ref={ref} {...makeEditorParams('  Tarea Original  ', stopEditing)} />);

    const input = screen.getByTestId('title-cell-editor-input');
    fireEvent.change(input, { target: { value: '  Nuevo Paquete WBS  ' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(stopEditing).toHaveBeenCalledOnce();
    expect(ref.current?.getValue()).toBe('Nuevo Paquete WBS');
  });

  it('cancels editing on Escape key and restores trimmed original value', () => {
    const stopEditing = vi.fn();
    const ref = createRef<TitleCellEditorRef>();

    render(<TitleCellEditor ref={ref} {...makeEditorParams('  Original  ', stopEditing)} />);

    const input = screen.getByTestId('title-cell-editor-input');
    fireEvent.change(input, { target: { value: 'Descartado' } });
    fireEvent.keyDown(input, { key: 'Escape' });

    expect(stopEditing).toHaveBeenCalledOnce();
    expect(ref.current?.getValue()).toBe('Original');
  });

  it('calls stopEditing on blur and focuses/selects on afterGuiAttached', () => {
    const stopEditing = vi.fn();
    const ref = createRef<TitleCellEditorRef>();

    render(<TitleCellEditor ref={ref} {...makeEditorParams('Tarea', stopEditing)} />);

    ref.current?.afterGuiAttached();
    const input = screen.getByTestId('title-cell-editor-input');
    expect(input).toHaveFocus();

    fireEvent.blur(input);
    expect(stopEditing).toHaveBeenCalledOnce();
  });
});
