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
});
