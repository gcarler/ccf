"use client";

import { useCallback,useEffect,useState } from "react";

export interface CellPosition {
  row: number;
  col: number;
}

export interface UseKeyboardNavOptions {
  rowCount: number;
  colCount: number;
  onCellSelect: (pos: CellPosition) => void;
  onCellEdit: (pos: CellPosition) => void;
  onCopy?: (cells: CellPosition[]) => void;
  onPaste?: (pos: CellPosition, data: string[][]) => void;
  onBulkEdit?: (colId: number, value: any) => void;
}

export function useKeyboardNav({
  rowCount,
  colCount,
  onCellSelect,
  onCellEdit,
  onCopy,
  onPaste,
}: UseKeyboardNavOptions) {
  const [activeCell, setActiveCell] = useState<CellPosition | null>(null);
  const [selectionRange, setSelectionRange] = useState<{ start: CellPosition; end: CellPosition } | null>(null);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!activeCell) return;

    const { row, col } = activeCell;
    let newRow = row;
    let newCol = col;
    let handled = false;

    // Arrow navigation
    if (e.key === "ArrowUp") { newRow = Math.max(0, row - 1); handled = true; }
    else if (e.key === "ArrowDown") { newRow = Math.min(rowCount - 1, row + 1); handled = true; }
    else if (e.key === "ArrowLeft") { newCol = Math.max(0, col - 1); handled = true; }
    else if (e.key === "ArrowRight") { newCol = Math.min(colCount - 1, col + 1); handled = true; }
    // Tab navigation
    else if (e.key === "Tab") {
      if (e.shiftKey) {
        newCol = col - 1;
        if (newCol < 0) { newRow = Math.max(0, row - 1); newCol = colCount - 1; }
      } else {
        newCol = col + 1;
        if (newCol >= colCount) { newRow = row + 1; newCol = 0; }
      }
      if (newRow >= rowCount) { newRow = rowCount - 1; newCol = colCount - 1; }
      handled = true;
    }
    // Enter to edit
    else if (e.key === "Enter") {
      onCellEdit(activeCell);
      handled = true;
    }
    // Escape to deselect
    else if (e.key === "Escape") {
      setActiveCell(null);
      setSelectionRange(null);
      handled = true;
    }
    // Delete to clear
    else if (e.key === "Delete" || e.key === "Backspace") {
      onCellEdit({ ...activeCell });
      handled = true;
    }

    if (handled) {
      e.preventDefault();
      if (newRow !== row || newCol !== col) {
        const newPos = { row: newRow, col: newCol };
        setActiveCell(newPos);
        onCellSelect(newPos);
        // Shift+click extends selection
        if (e.shiftKey) {
          setSelectionRange(prev => prev ? { ...prev, end: newPos } : { start: activeCell, end: newPos });
        } else {
          setSelectionRange(null);
        }
      }
    }
  }, [activeCell, rowCount, colCount, onCellSelect, onCellEdit]);

  // Copy (Ctrl+C)
  useEffect(() => {
    const handleCopy = () => {
      if (!activeCell || !onCopy) return;
      const cells = selectionRange ? getSelectedCells(selectionRange.start, selectionRange.end, rowCount, colCount) : [activeCell];
      onCopy(cells);
    };
    window.addEventListener("copy", handleCopy);
    return () => window.removeEventListener("copy", handleCopy);
  }, [activeCell, selectionRange, rowCount, colCount, onCopy]);

  // Paste (Ctrl+V)
  useEffect(() => {
    const handlePaste = (e: ClipboardEvent) => {
      if (!activeCell || !onPaste) return;
      const text = e.clipboardData?.getData("text/plain");
      if (!text) return;
      e.preventDefault();
      const rows = text.split("\n").map(r => r.split("\t"));
      onPaste(activeCell, rows);
    };
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, [activeCell, onPaste]);

  const getSelectedCells = (start: CellPosition, end: CellPosition, rows: number, cols: number): CellPosition[] => {
    const cells: CellPosition[] = [];
    const r1 = Math.min(start.row, end.row);
    const r2 = Math.max(start.row, end.row);
    const c1 = Math.min(start.col, end.col);
    const c2 = Math.max(start.col, end.col);
    for (let r = r1; r <= Math.min(r2, rows - 1); r++) {
      for (let c = c1; c <= Math.min(c2, cols - 1); c++) {
        cells.push({ row: r, col: c });
      }
    }
    return cells;
  };

  return { activeCell, selectionRange, handleKeyDown };
}
