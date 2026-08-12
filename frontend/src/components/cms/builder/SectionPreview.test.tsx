import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  InlineEditorPanel,
  SectionPreview,
  SectionRenderErrorBoundary,
  SectionRenderPreview,
} from "./SectionPreview";
import type { CmsSection } from "@/types/cms-v2";

vi.mock("@/components/public/cms/PublicSectionRenderer", () => ({
  default: ({ section }: { section: CmsSection }) => (
    <div data-testid="public-renderer">{section.type}</div>
  ),
}));

vi.mock("@/components/ui/OptimizedImage", () => ({
  default: ({ alt }: { alt?: string }) => <img alt={alt || "mock"} />,
}));

const updatePropsMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/cms/v2", () => ({ updateCmsSectionProps: updatePropsMock }));

vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

function makeSection(type: string, props: Record<string, unknown> = {}): CmsSection {
  return {
    id: "s1",
    site_id: "site1",
    page_id: "p1",
    type,
    props_json: props,
    sort_order: 1,
    is_visible: true,
    status: "active",
    created_at: "",
    updated_at: "",
  } as unknown as CmsSection;
}

describe("SectionPreview (schema preview por tipo)", () => {
  it("hero: título, body y CTA", () => {
    render(<SectionPreview section={makeSection("hero", { title: "Hero T", body: "Hero B", cta_label: "CTA" })} />);
    expect(screen.getByText("Hero T")).toBeInTheDocument();
    expect(screen.getByText("Hero B")).toBeInTheDocument();
    expect(screen.getByText("CTA")).toBeInTheDocument();
    expect(screen.getByText("Hero Principal")).toBeInTheDocument(); // TypeBadge label
  });

  it("hero sin props: fallbacks por defecto", () => {
    render(<SectionPreview section={makeSection("hero")} />);
    expect(screen.getByText("Título hero")).toBeInTheDocument();
    expect(screen.getByText("Subtítulo o descripción principal")).toBeInTheDocument();
  });

  it("video_hero: indica video de fondo", () => {
    render(<SectionPreview section={makeSection("video_hero")} />);
    expect(screen.getByText(/Video de fondo configurado/)).toBeInTheDocument();
  });

  it("cards: renderiza items, filtra archivados y muestra +N más", () => {
    const items = [
      { title: "A", status: "active" },
      { title: "B", status: "active" },
      { title: "C", status: "archived" },
      { title: "D", status: "active" },
      { title: "E", status: "active" },
    ];
    render(<SectionPreview section={makeSection("cards", { title: "Tarjetas", items })} />);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.queryByText("C")).toBeNull();
    // Tras filtrar quedan 4 items: 3 visibles + 1 "más"
    expect(screen.getByText("+1 más")).toBeInTheDocument();
  });

  it("cards sin items: título por defecto", () => {
    render(<SectionPreview section={makeSection("cards")} />);
    expect(screen.getByText("Bloque de tarjetas")).toBeInTheDocument();
  });

  it("gallery con imagen: renderiza img", () => {
    render(<SectionPreview section={makeSection("gallery", { image_url: "https://img/x.png" })} />);
    expect(screen.getByAltText("gallery")).toBeInTheDocument();
  });

  it("gallery sin imagen: placeholder", () => {
    render(<SectionPreview section={makeSection("gallery")} />);
    expect(screen.getByText("Sin imagen configurada")).toBeInTheDocument();
  });

  it("cta_banner: título, subtítulo y CTA", () => {
    render(
      <SectionPreview section={makeSection("cta_banner", { title: "CTA T", body: "CTA B", cta_label: "Únete" })} />
    );
    expect(screen.getByText("CTA T")).toBeInTheDocument();
    expect(screen.getByText("CTA B")).toBeInTheDocument();
    expect(screen.getByText("Únete")).toBeInTheDocument();
  });

  it("testimonials: título por defecto", () => {
    render(<SectionPreview section={makeSection("testimonials")} />);
    expect(screen.getByText("Sección de Testimonios")).toBeInTheDocument();
  });

  it("stats: renderiza métricas y fallback", () => {
    const { rerender } = render(
      <SectionPreview section={makeSection("stats", { items: [{ value: "42", label: "Iglesias" }] })} />
    );
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Iglesias")).toBeInTheDocument();

    rerender(<SectionPreview section={makeSection("stats")} />);
    expect(screen.getByText("Métrica")).toBeInTheDocument();
  });

  it("team: título por defecto", () => {
    render(<SectionPreview section={makeSection("team")} />);
    expect(screen.getByText("Nuestro Equipo")).toBeInTheDocument();
  });

  it("countdown: unidades y fecha objetivo", () => {
    render(<SectionPreview section={makeSection("countdown", { target_date: "2026-12-31" })} />);
    expect(screen.getByText("DD")).toBeInTheDocument();
    expect(screen.getByText("SS")).toBeInTheDocument();
    expect(screen.getByText(/Hasta: 2026-12-31/)).toBeInTheDocument();
  });

  it("faq: renderiza preguntas y filtra archivadas", () => {
    const items = [
      { q: "¿P1?", status: "active" },
      { q: "¿P2?", status: "archived" },
      { q: "¿P3?", status: "active" },
    ];
    render(<SectionPreview section={makeSection("faq", { items })} />);
    expect(screen.getByText("¿P1?")).toBeInTheDocument();
    expect(screen.getByText("¿P3?")).toBeInTheDocument();
    expect(screen.queryByText("¿P2?")).toBeNull();
  });

  it("embed: muestra la URL o el placeholder", () => {
    const { rerender } = render(<SectionPreview section={makeSection("embed", { embed_url: "https://youtube.com/x" })} />);
    expect(screen.getByText("https://youtube.com/x")).toBeInTheDocument();

    rerender(<SectionPreview section={makeSection("embed")} />);
    expect(screen.getByText("Sin URL configurada")).toBeInTheDocument();
  });

  it("rich_text y fallback: título/body con fallbacks", () => {
    render(<SectionPreview section={makeSection("rich_text")} />);
    expect(screen.getByText("Título")).toBeInTheDocument();
    expect(screen.getByText("Contenido de sección")).toBeInTheDocument();
  });

  it("usa el label del catálogo para el TypeBadge", () => {
    render(<SectionPreview section={makeSection("cta_banner")} />);
    expect(screen.getByText("Banner CTA")).toBeInTheDocument();
  });
});

describe("SectionRenderPreview", () => {
  it("renderiza el renderer público dentro del preview", () => {
    render(
      <SectionRenderPreview
        section={makeSection("hero", { title: "H" })}
        mobile={false}
      />
    );
    expect(screen.getByTestId("section-render-preview")).toBeInTheDocument();
    expect(screen.getByTestId("public-renderer")).toHaveTextContent("hero");
  });

  it("abre el inline editor con doble clic en modo wysiwyg", () => {
    const builder = {
      siteKey: "ccf",
      activeSlug: "inicio",
      token: "tok",
      updateSectionPropsLocal: vi.fn(),
    } as unknown as Parameters<typeof SectionRenderPreview>[0]["builder"];
    render(
      <SectionRenderPreview
        section={makeSection("hero", { title: "H" })}
        mobile={false}
        canvasMode="wysiwyg"
        builder={builder}
      />
    );
    fireEvent.doubleClick(screen.getByTestId("section-render-preview"));
    expect(screen.getByText(/Inline Editor · hero/)).toBeInTheDocument();
  });

  it("no abre el inline editor fuera del modo wysiwyg", () => {
    render(<SectionRenderPreview section={makeSection("hero")} mobile={false} canvasMode="esquema" />);
    fireEvent.doubleClick(screen.getByTestId("section-render-preview"));
    expect(screen.queryByText(/Inline Editor/)).toBeNull();
  });
});

describe("SectionRenderErrorBoundary", () => {
  it("renderiza los children sin error", () => {
    render(
      <SectionRenderErrorBoundary>
        <div>ok</div>
      </SectionRenderErrorBoundary>
    );
    expect(screen.getByText("ok")).toBeInTheDocument();
  });

  it("muestra el fallback cuando un hijo lanza error", () => {
    const errSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    function Boom(): React.ReactElement {
      throw new Error("boom");
    }
    render(
      <SectionRenderErrorBoundary>
        <Boom />
      </SectionRenderErrorBoundary>
    );
    expect(screen.getByText(/No se pudo renderizar esta sección/)).toBeInTheDocument();
    errSpy.mockRestore();
  });
});

describe("InlineEditorPanel", () => {
  const builder = {
    siteKey: "ccf",
    activeSlug: "inicio",
    token: "tok",
    updateSectionPropsLocal: vi.fn(),
  } as unknown as Parameters<typeof InlineEditorPanel>[0]["builder"];

  beforeEach(() => {
    vi.clearAllMocks();
    updatePropsMock.mockResolvedValue({});
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renderiza los campos según el tipo de sección", () => {
    render(
      <InlineEditorPanel section={makeSection("hero", { title: "H", subtitle: "S", cta_text: "C" })} builder={builder} onClose={() => {}} />
    );
    expect(screen.getByText("Título")).toBeInTheDocument();
    expect(screen.getByText("Texto CTA")).toBeInTheDocument();
    expect(screen.getByDisplayValue("H")).toBeInTheDocument();
  });

  it("cierra con Escape", () => {
    const onClose = vi.fn();
    render(<InlineEditorPanel section={makeSection("hero")} builder={builder} onClose={onClose} />);
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("guarda con debounce al editar un campo (800ms)", async () => {
    vi.useFakeTimers();
    render(<InlineEditorPanel section={makeSection("hero", { title: "H" })} builder={builder} onClose={() => {}} />);
    fireEvent.change(screen.getByDisplayValue("H"), { target: { value: "Nuevo" } });
    expect(builder.updateSectionPropsLocal).toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(800);
      await Promise.resolve();
    });

    expect(updatePropsMock).toHaveBeenCalledWith("ccf", "inicio", "s1", expect.objectContaining({ title: "Nuevo" }), "tok");
    vi.useRealTimers();
  });

  it("guarda de inmediato con el botón ✓ Guardar y cierra", async () => {
    render(<InlineEditorPanel section={makeSection("hero", { title: "H" })} builder={builder} onClose={() => {}} />);
    fireEvent.click(screen.getByTitle("Guardar cambios"));
    await act(async () => { await Promise.resolve(); });
    expect(updatePropsMock).toHaveBeenCalled();
  });
});
