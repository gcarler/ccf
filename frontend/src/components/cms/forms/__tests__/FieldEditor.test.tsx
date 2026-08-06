import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FieldEditor, makeDefaultField, FIELD_TYPES } from "../FieldEditor";
import type { CmsFormField } from "@/types/cms-v2";

function field(overrides: Partial<CmsFormField> & { id: string; label: string }): CmsFormField {
  return { type: "text", required: false, ...overrides } as CmsFormField;
}

function mount(over: Partial<Parameters<typeof FieldEditor>[0]> = {}) {
  const handlers = {
    onChange: vi.fn(),
    onRemove: vi.fn(),
    onMove: vi.fn(),
    onDuplicate: vi.fn(),
  };
  const initial = over.field ?? field({ id: "x", label: "X" });
  function Harness() {
    const [f, setF] = React.useState<CmsFormField>(initial);
    return (
      <FieldEditor
        field={f}
        index={over.index ?? 0}
        total={over.total ?? 1}
        siblings={over.siblings ?? [f]}
        onChange={(next) => {
          setF(next);
          handlers.onChange(next);
        }}
        onRemove={handlers.onRemove}
        onMove={handlers.onMove}
        onDuplicate={handlers.onDuplicate}
      />
    );
  }
  render(<Harness />);
  return handlers;
}

describe("FieldEditor", () => {
  it("renderiza el tipo y etiqueta del campo", () => {
    mount({ field: field({ id: "x", label: "Mi Campo", type: "email" }) });
    expect(screen.getByText(/Campo #1 — Correo electrónico/)).toBeInTheDocument();
  });

  it("expone los 19 tipos en el catálogo FIELD_TYPES", () => {
    expect(FIELD_TYPES).toHaveLength(19);
    expect(FIELD_TYPES.map((t) => t.type)).toContain("select_multiple");
    expect(FIELD_TYPES.map((t) => t.type)).toContain("captcha");
  });

  it("makeDefaultField crea defaults razonables por tipo", () => {
    const select = makeDefaultField("select", 0);
    expect(select.options).toEqual(["Opción 1", "Opción 2"]);
    expect(select.required).toBe(true);

    const rating = makeDefaultField("rating", 1);
    expect(rating.max_value).toBe(5);

    const slider = makeDefaultField("slider", 2);
    expect(slider.min_value).toBe(0);
    expect(slider.max_value).toBe(100);
    expect(slider.step).toBe(1);

    const file = makeDefaultField("file", 3);
    expect(file.max_file_mb).toBe(10);

    const divider = makeDefaultField("divider", 4);
    // divider no es required.
    expect(divider.required).toBe(false);
  });

  it("select: agrega, renombra y elimina opciones por fila", () => {
    const { onChange } = mount({
      field: field({ id: "s", label: "Sel", type: "select", options: ["A", "B"], required: true }),
    });

    // Agregar opción
    fireEvent.click(screen.getByRole("button", { name: /Agregar opción/i }));
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ options: ["A", "B", "Nueva opción"] }),
    );

    // Renombrar la opción 1 ("A" → "Z")
    const inputs = screen.getAllByLabelText(/^Opción \d+$/i);
    fireEvent.change(inputs[0], { target: { value: "Z" } });
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ options: ["Z", "B", "Nueva opción"] }),
    );

    // Eliminar la opción 2 (índice 1 → "B")
    const removeBtns = screen.getAllByRole("button", { name: /Eliminar opción \d+/i });
    fireEvent.click(removeBtns[1]);
    expect(onChange).toHaveBeenLastCalledWith(
      expect.objectContaining({ options: ["Z", "Nueva opción"] }),
    );
  });

  it("el botón duplicar invoca onDuplicate", () => {
    const { onDuplicate } = mount({ field: field({ id: "x", label: "X" }) });
    fireEvent.click(screen.getByRole("button", { name: /Duplicar campo/i }));
    expect(onDuplicate).toHaveBeenCalledTimes(1);
  });

  it("mover arriba/abajo y eliminar invocan sus callbacks", () => {
    const { onMove, onRemove } = mount({
      field: field({ id: "mid", label: "M" }),
      index: 1,
      total: 3,
    });
    fireEvent.click(screen.getByRole("button", { name: /Mover arriba/i }));
    expect(onMove).toHaveBeenCalledWith("up");
    fireEvent.click(screen.getByRole("button", { name: /Mover abajo/i }));
    expect(onMove).toHaveBeenCalledWith("down");
    fireEvent.click(screen.getByRole("button", { name: /Eliminar campo/i }));
    expect(onRemove).toHaveBeenCalledTimes(1);
  });

  it("text: permite editar límites de longitud y patrón regex", () => {
    const { onChange } = mount({
      field: field({ id: "t", label: "Código", type: "text" }),
    });
    const numInputs = document.querySelectorAll<HTMLInputElement>('input[type="number"]');
    fireEvent.change(numInputs[0], { target: { value: "2" } });
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ min_length: 2 }));

    fireEvent.change(numInputs[1], { target: { value: "5" } });
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ max_length: 5 }));

    // Patrón regex (placeholder distinctive)
    const pattern = screen.getByPlaceholderText("^[A-Za-z]+$") as HTMLInputElement;
    fireEvent.change(pattern, { target: { value: "^[A-Z]{3}$" } });
    expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ regex_pattern: "^[A-Z]{3}$" }));
  });
});
