import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { FieldDiffRow, TokenStream } from "./FieldDiff";
import type { FieldDiff } from "@/lib/cms/versionDiff";

describe("FieldDiffRow", () => {
  it("muestra el valor sin cambios en texto plano", () => {
    const diff: FieldDiff = { kind: "unchanged", before: "hola", after: "hola" };
    render(<FieldDiffRow label="Título" diff={diff} />);
    expect(screen.getByText("Título")).toBeInTheDocument();
    expect(screen.getByText("hola")).toBeInTheDocument();
  });

  it("serializa valores no string en unchanged", () => {
    const diff: FieldDiff = { kind: "unchanged", before: { a: 1 }, after: { a: 1 } };
    render(<FieldDiffRow label="Props" diff={diff} />);
    expect(screen.getByText(JSON.stringify({ a: 1 }))).toBeInTheDocument();
  });

  it("usa emptyText cuando el valor es vacío", () => {
    const diff: FieldDiff = { kind: "unchanged", before: "", after: "" };
    render(<FieldDiffRow label="Título" diff={diff} emptyText="—" />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("marca el valor añadido con aria-label y el prefijo + Añadido", () => {
    const diff: FieldDiff = { kind: "added", before: undefined, after: "Nuevo valor" };
    render(<FieldDiffRow label="Título" diff={diff} />);
    const note = screen.getByRole("note", { name: /Valor añadido en la versión B/i });
    expect(note).toHaveTextContent("Nuevo valor");
    expect(screen.getByText("+ Añadido")).toBeInTheDocument();
  });

  it("marca el valor eliminado con tachado", () => {
    const diff: FieldDiff = { kind: "removed", before: "Valor viejo", after: undefined };
    const { container } = render(<FieldDiffRow label="Título" diff={diff} />);
    const note = screen.getByRole("note", { name: /Valor eliminado en la versión B/i });
    expect(note).toHaveTextContent("Valor viejo");
    expect(container.querySelector(".line-through")).toBeInTheDocument();
  });

  it("renderiza changed en side-by-side con dos columnas", () => {
    const diff: FieldDiff = {
      kind: "changed",
      before: "hola mundo",
      after: "hola ccf",
      tokens: [
        { type: "unchanged", value: "hola " },
        { type: "removed", value: "mundo" },
        { type: "added", value: "ccf" },
      ],
    };
    render(<FieldDiffRow label="Título" diff={diff} />);
    // La columna before no debe contener tokens añadidos y viceversa.
    const notes = screen.getAllByRole("note");
    const addedTokens = notes.filter((n) => n.getAttribute("aria-label") === "texto añadido");
    const removedTokens = notes.filter((n) => n.getAttribute("aria-label") === "texto eliminado");
    expect(addedTokens.some((n) => n.textContent === "ccf")).toBe(true);
    expect(removedTokens.some((n) => n.textContent === "mundo")).toBe(true);
    expect(addedTokens.some((n) => n.textContent === "mundo")).toBe(false);
  });

  it("renderiza changed en layout inline como un único stream", () => {
    const diff: FieldDiff = {
      kind: "changed",
      before: "a",
      after: "b",
      tokens: [
        { type: "removed", value: "a" },
        { type: "added", value: "b" },
      ],
    };
    render(<FieldDiffRow label="Título" diff={diff} layout="inline" />);
    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByText("b")).toBeInTheDocument();
  });

  it("renderiza changed sin tokens con los valores crudos", () => {
    const diff: FieldDiff = { kind: "changed", before: 1, after: 2 };
    render(<FieldDiffRow label="Orden" diff={diff} />);
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("aplica multiline whitespace-pre-wrap", () => {
    const diff: FieldDiff = { kind: "added", before: undefined, after: "línea\nlínea2" };
    const { container } = render(<FieldDiffRow label="Cuerpo" diff={diff} multiline />);
    const note = screen.getByRole("note", { name: /Valor añadido/i });
    expect(note.className).toContain("whitespace-pre-wrap");
    expect(container).toBeTruthy();
  });
});

describe("TokenStream", () => {
  it("muestra '—' cuando no hay tokens", () => {
    render(<TokenStream tokens={[]} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("marca tokens añadidos/eliminados con aria-labels", () => {
    render(
      <TokenStream
        tokens={[
          { type: "unchanged", value: "hola " },
          { type: "added", value: "ccf" },
          { type: "removed", value: "mundo" },
        ]}
      />
    );
    expect(screen.getByText("hola")).toBeInTheDocument();
    expect(screen.getByRole("note", { name: "texto añadido" })).toHaveTextContent("ccf");
    expect(screen.getByRole("note", { name: "texto eliminado" })).toHaveTextContent("mundo");
  });
});
