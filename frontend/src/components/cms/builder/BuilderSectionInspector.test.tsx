import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import type { PageBuilderState } from "@/hooks/usePageBuilder";
import type { CmsSection } from "@/types/cms-v2";
import BuilderSectionInspector from "./BuilderSectionInspector";
import { createMockCmsSection } from "@/test-utils/factories";

vi.mock("@/components/ui/OptimizedImage", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}));

function createMockBuilder(overrides: Partial<PageBuilderState> = {}): PageBuilderState {
  const base: Partial<PageBuilderState> = {
    activeSection: null,
    canEdit: true,
    saving: false,
    saveSectionField: vi.fn(),
    saveSectionProps: vi.fn(),
    updateSectionPropsLocal: vi.fn(),
    setSections: vi.fn(),
    setMediaPickerTarget: vi.fn(),
    setMediaPickerOpen: vi.fn(),
    upsertArrayItem: vi.fn(),
    addArrayItem: vi.fn(),
    setSectionVisibility: vi.fn(),
    toggleSectionArchive: vi.fn(),
    duplicateSection: vi.fn(),
  };
  return { ...base, ...overrides } as unknown as PageBuilderState;
}

describe("BuilderSectionInspector", () => {
  it("renders empty state when no section is selected", () => {
    const builder = createMockBuilder();
    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByText(/selecciona una sección del canvas/i)).toBeInTheDocument();
  });

  it("renders hero-specific fields when active section is hero", () => {
    const section = createMockCmsSection("hero", {
      props_json: { eyebrow: " eyebrow", title_lead: "Lead" },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByPlaceholderText(/una comunidad que ilumina/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/ccf:/i)).toBeInTheDocument();
  });

  it("calls saveSectionField on blur for standard title field", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("rich_text", {
      props_json: { title: "Título", body: "Cuerpo" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByPlaceholderText(/título/i);
    fireEvent.change(input, { target: { value: "Nuevo título" } });
    fireEvent.blur(input, { target: { value: "Nuevo título" } });
    expect(saveSectionField).toHaveBeenCalledWith("title", "Nuevo título");
  });

  it("calls saveSectionField on blur for body field", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("rich_text", {
      props_json: { body: "Contenido" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const textarea = screen.getByPlaceholderText(/contenido/i);
    fireEvent.change(textarea, { target: { value: "Nuevo contenido" } });
    fireEvent.blur(textarea, { target: { value: "Nuevo contenido" } });
    expect(saveSectionField).toHaveBeenCalledWith("body", "Nuevo contenido");
  });

  it("calls saveSectionField with correct embed_url for embed sections", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("embed", {
      props_json: { embed_url: "https://example.com" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByPlaceholderText(/youtube, vimeo/i);
    fireEvent.change(input, { target: { value: "https://new-url.com" } });
    fireEvent.blur(input, { target: { value: "https://new-url.com" } });
    expect(saveSectionField).toHaveBeenCalledWith("embed_url", "https://new-url.com");
  });

  it("opens media picker when choosing an image for hero section", () => {
    const setMediaPickerTarget = vi.fn();
    const setMediaPickerOpen = vi.fn();
    const section = createMockCmsSection("hero", { props_json: {} });
    const builder = createMockBuilder({ activeSection: section });
    builder.setMediaPickerTarget = setMediaPickerTarget;
    builder.setMediaPickerOpen = setMediaPickerOpen;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /elegir de media/i }));
    expect(setMediaPickerTarget).toHaveBeenCalledWith("section");
    expect(setMediaPickerOpen).toHaveBeenCalledWith(true);
  });

  it("calls addArrayItem when adding a new card", () => {
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("cards", {
      props_json: { title: "Tarjetas", items: [{ title: "A", body: "B" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /añadir tarjeta/i }));
    expect(addArrayItem).toHaveBeenCalledWith(
      "items",
      expect.objectContaining({ title: "Nueva tarjeta", body: "Descripción" }),
    );
  });

  it("calls addArrayItem when adding a new FAQ item", () => {
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("faq", {
      props_json: { title: "Preguntas", items: [{ q: "A", a: "B" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /añadir pregunta/i }));
    expect(addArrayItem).toHaveBeenCalledWith(
      "items",
      expect.objectContaining({ q: "Nueva pregunta", a: "Respuesta" }),
    );
  });

  it("disables fields when canEdit is false", () => {
    const section = createMockCmsSection("rich_text", {
      props_json: { title: "Título", body: "Cuerpo" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.canEdit = false;

    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByPlaceholderText(/título/i)).toBeDisabled();
    expect(screen.getByPlaceholderText(/contenido/i)).toBeDisabled();
  });

  it("calls updateSectionPropsLocal and saveSectionField for countdown target_date", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("countdown", {
      props_json: { target_date: "2024-12-31T23:59" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.updateSectionPropsLocal = updateSectionPropsLocal;
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("2024-12-31T23:59");
    fireEvent.change(input, { target: { value: "2025-01-01T00:00" } });
    expect(updateSectionPropsLocal).toHaveBeenCalledWith(
      expect.objectContaining({ target_date: "2025-01-01T00:00" })
    );

    fireEvent.blur(input, { target: { value: "2025-01-01T00:00" } });
    expect(saveSectionField).toHaveBeenCalledWith("target_date", "2025-01-01T00:00");
  });

  it("parses and saves popup_banner show_on_paths on blur", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("popup_banner", {
      props_json: { show_on_paths: ["/"] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.updateSectionPropsLocal = updateSectionPropsLocal;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const textarea = screen.getByTestId("popup-show-on-paths");
    fireEvent.change(textarea, { target: { value: "/\n/nosotros\n/cursos" } });
    expect(updateSectionPropsLocal).toHaveBeenCalledWith(
      expect.objectContaining({ show_on_paths: ["/", "/nosotros", "/cursos"] })
    );

    fireEvent.blur(textarea, { target: { value: "/\n/nosotros\n/cursos" } });
    expect(saveSectionProps).toHaveBeenCalledWith(
      expect.objectContaining({ show_on_paths: ["/", "/nosotros", "/cursos"] })
    );
  });

  it("calls upsertArrayItem and saveSectionProps when archiving a team member", () => {
    const nextProps = { items: [{ name: "Ana", role: "Pastor", status: "archived" }] };
    const upsertArrayItem = vi.fn(() => nextProps);
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("team", {
      props_json: {
        items: [{ name: "Ana", role: "Pastor" }],
      },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /archivar persona/i }));
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { status: "archived" });
    expect(saveSectionProps).toHaveBeenCalledWith(nextProps);
  });

  it("calls updateSectionPropsLocal and saveSectionField when image_side changes", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("image_text", {
      props_json: { image_side: "right" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.updateSectionPropsLocal = updateSectionPropsLocal;
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const select = screen.getByDisplayValue("Imagen a la derecha");
    fireEvent.change(select, { target: { value: "left" } });
    expect(updateSectionPropsLocal).toHaveBeenCalledWith(
      expect.objectContaining({ image_side: "left" })
    );
    expect(saveSectionField).toHaveBeenCalledWith("image_side", "left");
  });

  it("calls upsertArrayItem and saveSectionProps when editing a pricing plan price", () => {
    const nextProps = { items: [{ name: "Plan", price: "$20" }] };
    const upsertArrayItem = vi.fn(() => nextProps);
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("pricing", {
      props_json: {
        items: [{ name: "Plan", price: "$10" }],
      },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("$10");
    fireEvent.change(input, { target: { value: "$20" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { price: "$20" });

    fireEvent.blur(input, { target: { value: "$20" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { price: "$20" });
    expect(saveSectionProps).toHaveBeenCalledWith(nextProps);
  });

  it("calls upsertArrayItem and saveSectionProps when editing a stats item value", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("stats", {
      props_json: {
        items: [{ value: "10K+", label: "Miembros" }],
      },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("10K+");
    fireEvent.change(input, { target: { value: "20K+" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { value: "20K+" });

    fireEvent.blur(input, { target: { value: "20K+" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { value: "20K+" });
    expect(saveSectionProps).toHaveBeenCalled();
  });

  it("calls upsertArrayItem and saveSectionProps when editing a gallery image URL", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("gallery", {
      props_json: {
        items: [{ url: "https://old.jpg", alt: "Old", caption: "Old caption" }],
      },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("https://old.jpg");
    fireEvent.change(input, { target: { value: "https://new.jpg" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { url: "https://new.jpg" });

    fireEvent.blur(input, { target: { value: "https://new.jpg" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { url: "https://new.jpg" });
    expect(saveSectionProps).toHaveBeenCalled();
  });

  it("calls upsertArrayItem and saveSectionProps when editing a timeline milestone title", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("timeline", {
      props_json: {
        items: [{ year: "2020", title: "Inicio", body: "Descripción" }],
      },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Inicio");
    fireEvent.change(input, { target: { value: "Lanzamiento" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { title: "Lanzamiento" });

    fireEvent.blur(input, { target: { value: "Lanzamiento" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { title: "Lanzamiento" });
    expect(saveSectionProps).toHaveBeenCalled();
  });

  it("calls upsertArrayItem and saveSectionProps when editing an icon_grid item title", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("icon_grid", {
      props_json: {
        items: [{ icon: "🎯", title: "Meta", body: "Descripción breve" }],
      },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Meta");
    fireEvent.change(input, { target: { value: "Objetivo" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { title: "Objetivo" });

    fireEvent.blur(input, { target: { value: "Objetivo" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { title: "Objetivo" });
    expect(saveSectionProps).toHaveBeenCalled();
  });

  it("calls updateSectionPropsLocal and saveSectionField when popup_banner dismiss_mode changes", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("popup_banner", {
      props_json: { dismiss_mode: "local" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.updateSectionPropsLocal = updateSectionPropsLocal;
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const select = screen.getByDisplayValue("Persistente (localStorage)");
    fireEvent.change(select, { target: { value: "session" } });
    expect(updateSectionPropsLocal).toHaveBeenCalledWith(
      expect.objectContaining({ dismiss_mode: "session" })
    );
    expect(saveSectionField).toHaveBeenCalledWith("dismiss_mode", "session");
  });
});
