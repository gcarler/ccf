import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { VersionsDiffView } from "./VersionsDiffView";
import type { PageVersionDiff, SectionSnapshot } from "@/lib/cms/versionDiff";
import type { CmsPageVersion } from "@/types/cms-v2";

function makeVersion(n: number): CmsPageVersion {
  return {
    id: `v${n}`,
    page_id: "p1",
    version_number: n,
    snapshot_json: {},
    notes: null,
    created_at: "2026-01-01T00:00:00Z",
  };
}

function makeSnapshot(props: Record<string, unknown>): SectionSnapshot {
  return {
    id: "sec",
    type: "hero",
    props_json: props,
    sort_order: 1,
    is_visible: true,
    status: "active",
  } as unknown as SectionSnapshot;
}

const diff: PageVersionDiff = {
  pageMeta: {
    title: {
      kind: "changed",
      before: "Antes",
      after: "Después",
      tokens: [
        { type: "removed", value: "Antes" },
        { type: "added", value: "Después" },
      ],
    },
    slug: { kind: "unchanged", before: "inicio", after: "inicio" },
    status: { kind: "changed", before: "draft", after: "published" },
    seo: { meta_description: { kind: "added", before: undefined, after: "Nueva desc" } },
  },
  sections: [
    { section_key: "s1", type: "hero", status: "added", after: makeSnapshot({ title: "Hero" }) },
    { section_key: "s2", type: "rich_text", status: "removed", before: makeSnapshot({ title: "Viejo" }) },
    {
      section_key: "s3",
      type: "cards",
      status: "modified",
      before: makeSnapshot({ title: "X" }),
      after: makeSnapshot({ title: "Y" }),
      prop_diffs: {
        title: {
          kind: "changed",
          before: "X",
          after: "Y",
          tokens: [
            { type: "removed", value: "X" },
            { type: "added", value: "Y" },
          ],
        },
      },
    },
    { section_key: "s4", type: "faq", status: "reordered", sort_before: 1, sort_after: 3 },
    {
      section_key: "s5",
      type: "stats",
      status: "visibility-changed",
      before: makeSnapshot({}),
      after: makeSnapshot({}),
    },
    {
      section_key: "s6",
      type: "team",
      status: "status-changed",
      before: { ...makeSnapshot({}), status: "draft" },
      after: { ...makeSnapshot({}), status: "published" },
    },
    { section_key: "s7", type: "countdown", status: "unchanged", after: makeSnapshot({}) },
  ],
  summary: {
    sectionsAdded: 1,
    sectionsRemoved: 1,
    sectionsReordered: 1,
    sectionsModified: 1,
    sectionsUnchanged: 1,
    seoFieldsChanged: 1,
    titleChanged: true,
  },
};

describe("VersionsDiffView", () => {
  it("renderiza el resumen con los contadores y versiones comparadas", () => {
    render(
      <VersionsDiffView
        before={makeVersion(2)}
        after={makeVersion(3)}
        diff={diff}
        hideUnchanged={false}
      />
    );
    expect(screen.getByText("Resumen del diff")).toBeInTheDocument();
    expect(screen.getByText(/^#2$/)).toBeInTheDocument();
    // #3 aparece en la comparación y en la sección reordenada
    expect(screen.getAllByText(/^#3$/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Añadidas")).toBeInTheDocument();
    expect(screen.getByText("Eliminadas")).toBeInTheDocument();
    expect(screen.getByText("Reordenadas")).toBeInTheDocument();
    expect(screen.getByText("Modificadas")).toBeInTheDocument();
    // "Sin cambios" aparece en el summary y en la sección unchanged
    expect(screen.getAllByText("Sin cambios").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Campos SEO")).toBeInTheDocument();
  });

  it("indica orden inverso cuando after < before", () => {
    render(<VersionsDiffView before={makeVersion(5)} after={makeVersion(3)} diff={diff} hideUnchanged={false} />);
    expect(screen.getByText(/orden inverso/)).toBeInTheDocument();
  });

  it("oculta secciones sin cambios por defecto y muestra el contador", () => {
    render(<VersionsDiffView before={makeVersion(2)} after={makeVersion(3)} diff={diff} />);
    expect(screen.queryByText("s7")).toBeNull();
    expect(screen.getByText(/Secciones \(6 de 7\)/)).toBeInTheDocument();
    expect(screen.getByText("(1 sin cambios ocultas)")).toBeInTheDocument();
  });

  it("muestra todas las secciones con hideUnchanged=false", () => {
    render(<VersionsDiffView before={makeVersion(2)} after={makeVersion(3)} diff={diff} hideUnchanged={false} />);
    expect(screen.getByText("s7")).toBeInTheDocument();
    // Con hideUnchanged=false hay 2: el stat del summary y el badge de la sección
    expect(screen.getAllByText("Sin cambios").length).toBeGreaterThanOrEqual(2);
  });

  it("renderiza los estados de sección: añadida, eliminada, reordenada, visibilidad y status", () => {
    render(<VersionsDiffView before={makeVersion(2)} after={makeVersion(3)} diff={diff} hideUnchanged={false} />);
    expect(screen.getByText("Añadida")).toBeInTheDocument();
    expect(screen.getByText("Eliminada")).toBeInTheDocument();
    expect(screen.getByText("Reordenada")).toBeInTheDocument();
    expect(screen.getByText(/orden #1/)).toBeInTheDocument();
    expect(screen.getAllByText(/^#3$/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Visibilidad")).toBeInTheDocument();
    expect(screen.getByText("Archivado/Activo")).toBeInTheDocument();
  });

  it("muestra los diffs de props de una sección modificada", () => {
    render(<VersionsDiffView before={makeVersion(2)} after={makeVersion(3)} diff={diff} hideUnchanged={false} />);
    // FieldDiffRow con la columna de tokens: el token eliminado 'X' y añadido 'Y'
    expect(screen.getByText("X")).toBeInTheDocument();
    expect(screen.getByText("Y")).toBeInTheDocument();
  });

  it("renderiza los metadatos de la página (Título/Slug/Estado + SEO)", () => {
    render(<VersionsDiffView before={makeVersion(2)} after={makeVersion(3)} diff={diff} hideUnchanged={false} />);
    expect(screen.getByText("Metadatos de la página")).toBeInTheDocument();
    expect(screen.getByText("Título")).toBeInTheDocument();
    expect(screen.getByText("Slug")).toBeInTheDocument();
    expect(screen.getByText("Estado")).toBeInTheDocument();
    expect(screen.getByText("SEO")).toBeInTheDocument();
  });

  it("omite los metadatos cuando no hay cambios en la página", () => {
    const noMeta: PageVersionDiff = {
      ...diff,
      pageMeta: {
        title: { kind: "unchanged", before: "A", after: "A" },
        slug: { kind: "unchanged", before: "b", after: "b" },
        status: { kind: "unchanged", before: "draft", after: "draft" },
        seo: {},
      },
    };
    render(<VersionsDiffView before={makeVersion(2)} after={makeVersion(3)} diff={noMeta} hideUnchanged={false} />);
    expect(screen.queryByText("Metadatos de la página")).toBeNull();
  });

  it("muestra el botón de rollback cuando canRollback y llama con before.id", () => {
    const onRollback = vi.fn();
    render(
      <VersionsDiffView
        before={makeVersion(2)}
        after={makeVersion(3)}
        diff={diff}
        canRollback
        onRollback={onRollback}
        hideUnchanged={false}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /Restaurar v2/i }));
    expect(onRollback).toHaveBeenCalledWith("v2");
  });

  it("no muestra rollback sin permiso", () => {
    render(<VersionsDiffView before={makeVersion(2)} after={makeVersion(3)} diff={diff} hideUnchanged={false} />);
    expect(screen.queryByRole("button", { name: /Restaurar/i })).toBeNull();
  });

  it("el toggle muestra/oculta secciones sin cambios", () => {
    const onToggle = vi.fn();
    render(
      <VersionsDiffView
        before={makeVersion(2)}
        after={makeVersion(3)}
        diff={diff}
        onToggleHideUnchanged={onToggle}
      />
    );
    const toggle = screen.getByRole("button", { name: /Mostrar secciones sin cambios/i });
    fireEvent.click(toggle);
    expect(onToggle).toHaveBeenCalled();
  });

  it("muestra el estado vacío cuando no hay secciones", () => {
    const empty: PageVersionDiff = {
      ...diff,
      sections: [],
      summary: { ...diff.summary, sectionsUnchanged: 0 },
    };
    render(<VersionsDiffView before={makeVersion(2)} after={makeVersion(3)} diff={empty} hideUnchanged={false} />);
    expect(screen.getByText(/Ninguna de las dos versiones contiene secciones/)).toBeInTheDocument();
  });
});
