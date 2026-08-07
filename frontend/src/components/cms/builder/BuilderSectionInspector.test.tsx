import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import type { PageBuilderState } from "@/hooks/usePageBuilder";

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
        items: [{ value: "10K+", label: "Personas" }],
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

  // ── Hero remaining fields ────────────────────────────────────────────────

  it("renders and edits hero title_accent field", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("hero", {
      props_json: { title_accent: "Tu Guía," },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Tu Guía,");
    expect(input).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "Nuestra Misión" } });
    fireEvent.blur(input, { target: { value: "Nuestra Misión" } });
    expect(saveSectionField).toHaveBeenCalledWith("title_accent", "Nuestra Misión");
  });

  it("renders hero description field", () => {
    const section = createMockCmsSection("hero", {
      props_json: { description: "Navegando juntos" },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    const textarea = screen.getByText(/navegando juntos/i);
    expect(textarea).toBeInTheDocument();
  });

  it("renders hero primary_cta and secondary_cta fields", () => {
    const section = createMockCmsSection("hero", {
      props_json: { primary_cta: "Saber más", secondary_cta: "Ver eventos" },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByDisplayValue("Saber más")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Ver eventos")).toBeInTheDocument();
  });

  it("renders hero primary_cta_href and secondary_cta_href fields", () => {
    const section = createMockCmsSection("hero", {
      props_json: { primary_cta_href: "/conocer", secondary_cta_href: "/predicas" },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByDisplayValue("/conocer")).toBeInTheDocument();
    expect(screen.getByDisplayValue("/predicas")).toBeInTheDocument();
  });

  it("renders hero scroll_indicator field", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("hero", {
      props_json: { scroll_indicator: "Descubrir" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Descubrir");
    fireEvent.change(input, { target: { value: "Explorar" } });
    fireEvent.blur(input, { target: { value: "Explorar" } });
    expect(saveSectionField).toHaveBeenCalledWith("scroll_indicator", "Explorar");
  });

  // ── Standard section CTA fields ──────────────────────────────────────────

  it("renders and edits standard section cta_label and cta_href", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("rich_text", {
      props_json: { title: "Título", cta_label: "Ver más", cta_href: "/page" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const ctaInput = screen.getByDisplayValue("Ver más");
    fireEvent.change(ctaInput, { target: { value: "Saber más" } });
    fireEvent.blur(ctaInput, { target: { value: "Saber más" } });
    expect(saveSectionField).toHaveBeenCalledWith("cta_label", "Saber más");

    const hrefInput = screen.getByDisplayValue("/page");
    fireEvent.change(hrefInput, { target: { value: "/nueva-ruta" } });
    fireEvent.blur(hrefInput, { target: { value: "/nueva-ruta" } });
    expect(saveSectionField).toHaveBeenCalledWith("cta_href", "/nueva-ruta");
  });

  // ── Cards additional fields ──────────────────────────────────────────────

  it("calls upsertArrayItem when editing cards item body", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("cards", {
      props_json: { items: [{ title: "A", body: "Desc B" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const textarea = screen.getByDisplayValue("Desc B");
    fireEvent.change(textarea, { target: { value: "Nueva desc" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { body: "Nueva desc" });
  });

  it("calls upsertArrayItem when editing cards item icon and href", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("cards", {
      props_json: { items: [{ title: "A", icon: "🎯", href: "/link" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const iconInput = screen.getByDisplayValue("🎯");
    fireEvent.change(iconInput, { target: { value: "⭐" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { icon: "⭐" });

    // Blur icon field → should call upsertArrayItem + saveSectionProps
    fireEvent.blur(iconInput, { target: { value: "⭐" } });
    expect(saveSectionProps).toHaveBeenCalled();
  });

  // ── FAQ additional fields ────────────────────────────────────────────────

  it("calls upsertArrayItem when editing FAQ question field", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("faq", {
      props_json: { items: [{ q: "¿Qué es?", a: "Respuesta" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("¿Qué es?");
    fireEvent.change(input, { target: { value: "¿Cómo?" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { q: "¿Cómo?" });
  });

  // ── Stats label field ────────────────────────────────────────────────────

  it("calls upsertArrayItem when editing stats label", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("stats", {
      props_json: { items: [{ value: "10K+", label: "Personas" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Personas");
    fireEvent.change(input, { target: { value: "Visitantes" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { label: "Visitantes" });
  });

  // ── Team additional fields ───────────────────────────────────────────────

  it("calls upsertArrayItem when editing team member name", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("team", {
      props_json: { items: [{ name: "Ana", role: "Pastor" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Ana");
    fireEvent.change(input, { target: { value: "María" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { name: "María" });
  });

  it("calls upsertArrayItem when editing team member role", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("team", {
      props_json: { items: [{ name: "Ana", role: "Pastor" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Pastor");
    fireEvent.change(input, { target: { value: "Líder" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { role: "Líder" });
  });

  it("calls upsertArrayItem when editing team member image url", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("team", {
      props_json: { items: [{ name: "Ana", image: "https://img.jpg" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("https://img.jpg");
    fireEvent.change(input, { target: { value: "https://new.jpg" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { image: "https://new.jpg" });
  });

  // ── Pricing additional fields ────────────────────────────────────────────

  it("calls upsertArrayItem when editing pricing plan name", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("pricing", {
      props_json: { items: [{ name: "Básico", price: "$10" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Básico");
    fireEvent.change(input, { target: { value: "Premium" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { name: "Premium" });
  });

  it("calls upsertArrayItem when editing pricing features field", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("pricing", {
      props_json: { items: [{ name: "Básico", features: "Acceso básico" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const textarea = screen.getByDisplayValue("Acceso básico");
    fireEvent.change(textarea, { target: { value: "Acceso completo" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { features: "Acceso completo" });
  });

  it("calls upsertArrayItem when editing pricing btn field", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("pricing", {
      props_json: { items: [{ name: "Básico", btn: "Comprar" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("Comprar");
    fireEvent.change(input, { target: { value: "Suscribir" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { btn: "Suscribir" });
  });

  it("renders pricing featured checkbox and toggles it", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("pricing", {
      props_json: { items: [{ name: "Premium", featured: "true" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const checkbox = screen.getByLabelText(/destacado/i);
    expect(checkbox).toBeInTheDocument();
    expect(checkbox).toBeChecked();

    fireEvent.click(checkbox);
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { featured: "false" });
  });

  // ── Gallery additional fields ────────────────────────────────────────────

  it("calls upsertArrayItem when editing gallery alt and caption", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("gallery", {
      props_json: { items: [{ url: "https://img.jpg", alt: "Alt text", caption: "Caption" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const altInput = screen.getByDisplayValue("Alt text");
    fireEvent.change(altInput, { target: { value: "Nuevo alt" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { alt: "Nuevo alt" });

    const captionInput = screen.getByDisplayValue("Caption");
    fireEvent.change(captionInput, { target: { value: "Nuevo caption" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { caption: "Nuevo caption" });
  });

  // ── Timeline additional fields ───────────────────────────────────────────

  it("calls upsertArrayItem when editing timeline year and body", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("timeline", {
      props_json: { items: [{ year: "2020", title: "Inicio", body: "Desc" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const yearInput = screen.getByDisplayValue("2020");
    fireEvent.change(yearInput, { target: { value: "2021" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { year: "2021" });

    const bodyInput = screen.getByDisplayValue("Desc");
    fireEvent.change(bodyInput, { target: { value: "Nueva desc" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { body: "Nueva desc" });
  });

  // ── Icon_grid additional fields ──────────────────────────────────────────

  it("calls upsertArrayItem when editing icon_grid icon and body", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("icon_grid", {
      props_json: { items: [{ icon: "🎯", title: "Meta", body: "Desc breve" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const iconInput = screen.getByDisplayValue("🎯");
    fireEvent.change(iconInput, { target: { value: "⭐" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { icon: "⭐" });

    const bodyInput = screen.getByDisplayValue("Desc breve");
    fireEvent.change(bodyInput, { target: { value: "Nueva desc" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { body: "Nueva desc" });
  });

  // ── Popup additional fields ──────────────────────────────────────────────

  it("renders popup_banner delay_ms and start_at fields", () => {
    const section = createMockCmsSection("popup_banner", {
      props_json: { delay_ms: 3000, start_at: "2024-01-01T00:00" },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByDisplayValue("3000")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2024-01-01T00:00")).toBeInTheDocument();
  });

  it("calls updateSectionPropsLocal for popup hide_on_paths", () => {
    const updateSectionPropsLocal = vi.fn();
    const section = createMockCmsSection("popup_banner", {
      props_json: { hide_on_paths: ["/login"] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.updateSectionPropsLocal = updateSectionPropsLocal;

    render(<BuilderSectionInspector builder={builder} />);

    const textarea = screen.getByDisplayValue("/login");
    fireEvent.change(textarea, { target: { value: "/login\n/admin" } });
    expect(updateSectionPropsLocal).toHaveBeenCalledWith(
      expect.objectContaining({ hide_on_paths: ["/login", "/admin"] })
    );
  });

  it("renders popup dismiss_days and dismiss_key fields", () => {
    const section = createMockCmsSection("popup_banner", {
      props_json: { dismiss_days: 7, dismiss_key: "popup_1" },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByDisplayValue("7")).toBeInTheDocument();
    expect(screen.getByDisplayValue("popup_1")).toBeInTheDocument();
  });

  // ── Video_hero section ───────────────────────────────────────────────────

  it("renders video_hero section with video_url field", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("video_hero", {
      props_json: { video_url: "https://youtube.com/watch?v=abc" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("https://youtube.com/watch?v=abc");
    expect(input).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "https://new-video.com" } });
    fireEvent.blur(input, { target: { value: "https://new-video.com" } });
    expect(saveSectionField).toHaveBeenCalledWith("video_url", "https://new-video.com");
  });

  // ── Rich_text_columns section ─────────────────────────────────────────────

  it("renders rich_text_columns section with body_2 field", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("rich_text_columns", {
      props_json: { body: "Col 1", body_2: "Col 2" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const textarea = screen.getByDisplayValue("Col 2");
    expect(textarea).toBeInTheDocument();
    fireEvent.change(textarea, { target: { value: "Nueva col 2" } });
    fireEvent.blur(textarea, { target: { value: "Nueva col 2" } });
    expect(saveSectionField).toHaveBeenCalledWith("body_2", "Nueva col 2");
  });

  // ── Newsletter section ───────────────────────────────────────────────────

  it("renders newsletter section with action_url field", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("newsletter", {
      props_json: { action_url: "/api/subscribe" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const input = screen.getByDisplayValue("/api/subscribe");
    expect(input).toBeInTheDocument();
    fireEvent.change(input, { target: { value: "/api/newsletter" } });
    fireEvent.blur(input, { target: { value: "/api/newsletter" } });
    expect(saveSectionField).toHaveBeenCalledWith("action_url", "/api/newsletter");
  });

  // ── CTA Banner section ───────────────────────────────────────────────────

  it("renders cta_banner section with second button fields", () => {
    const saveSectionField = vi.fn();
    const section = createMockCmsSection("cta_banner", {
      props_json: { cta_label_2: "Saber más", cta_href_2: "/info" },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.saveSectionField = saveSectionField;

    render(<BuilderSectionInspector builder={builder} />);

    const labelInput = screen.getByDisplayValue("Saber más");
    fireEvent.change(labelInput, { target: { value: "Ver más" } });
    fireEvent.blur(labelInput, { target: { value: "Ver más" } });
    expect(saveSectionField).toHaveBeenCalledWith("cta_label_2", "Ver más");

    const hrefInput = screen.getByDisplayValue("/info");
    fireEvent.change(hrefInput, { target: { value: "/nuevo" } });
    fireEvent.blur(hrefInput, { target: { value: "/nuevo" } });
    expect(saveSectionField).toHaveBeenCalledWith("cta_href_2", "/nuevo");
  });

  // ── Testimonials section ─────────────────────────────────────────────────

  it("renders testimonials section with manual items", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("testimonials", {
      props_json: {
        items: [{ author: "Juan", content: "Testimonio", role: "Voluntario" }],
      },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    // Testimonials items use: author (not name), content (not quote), role
    const authorInput = screen.getByDisplayValue(/juan/i);
    expect(authorInput).toBeInTheDocument();

    fireEvent.change(authorInput, { target: { value: "Pedro" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { author: "Pedro" });
  });

  // ── Restore archived items ───────────────────────────────────────────────

  it("calls upsertArrayItem to restore an archived cards item", () => {
    const nextProps = { items: [{ title: "A", status: "published" }] };
    const upsertArrayItem = vi.fn(() => nextProps);
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("cards", {
      props_json: { items: [{ title: "A", body: "B", status: "archived" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByText(/archivado/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /restaurar/i }));
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { status: "published" });
    expect(saveSectionProps).toHaveBeenCalledWith(nextProps);
  });

  it("archives a stats item via first archive button", () => {
    const nextProps = { items: [{ value: "10", label: "X", status: "archived" }] };
    const upsertArrayItem = vi.fn(() => nextProps);
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("stats", {
      props_json: { items: [{ value: "10", label: "X" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    // There are 2 archive buttons: one for item archive + one for "Añadir" buttons
    // Use getAllByRole and pick the first archive button
    const archiveButtons = screen.getAllByRole("button", { name: /archivar/i });
    // The first archive button corresponds to the item's archive action
    fireEvent.click(archiveButtons[0]);
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { status: "archived" });
    expect(saveSectionProps).toHaveBeenCalledWith(nextProps);
  });

  // ── AddArrayItem for remaining types ─────────────────────────────────────

  it("calls addArrayItem when adding a stats metric", () => {
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("stats", {
      props_json: { items: [{ value: "10", label: "X" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    // Button text has no accent: "Añadir metrica"
    fireEvent.click(screen.getByRole("button", { name: /añadir metrica/i }));
    expect(addArrayItem).toHaveBeenCalledWith(
      "items",
      expect.objectContaining({ value: "0", label: "Nueva metrica" }),
    );
  });

  it("calls addArrayItem when adding a gallery image", () => {
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("gallery", {
      props_json: { items: [{ url: "https://img.jpg" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /añadir imagen/i }));
    expect(addArrayItem).toHaveBeenCalledWith(
      "items",
      expect.objectContaining({ url: "", alt: "", caption: "" }),
    );
  });

  it("calls addArrayItem when adding a timeline milestone", () => {
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("timeline", {
      props_json: { items: [{ year: "2020", title: "Inicio" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /añadir hito/i }));
    expect(addArrayItem).toHaveBeenCalledWith(
      "items",
      expect.objectContaining({ year: "2024", title: "Nuevo hito" }),
    );
  });

  it("calls addArrayItem when adding an icon_grid item", () => {
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("icon_grid", {
      props_json: { items: [{ icon: "🎯", title: "Meta" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /añadir item/i }));
    expect(addArrayItem).toHaveBeenCalledWith(
      "items",
      expect.objectContaining({ icon: "✨", title: "Nuevo item", body: "Descripción" }),
    );
  });

  // ── Hero bg_image field ──────────────────────────────────────────────────

  it("renders OptimizedImage when hero has bg_image", () => {
    const section = createMockCmsSection("hero", {
      props_json: { bg_image: "https://example.com/bg.jpg" },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    const img = screen.getByAltText("Imagen seleccionada");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/bg.jpg");
  });

  it("opens media picker for image_text section", () => {
    const setMediaPickerTarget = vi.fn();
    const setMediaPickerOpen = vi.fn();
    const section = createMockCmsSection("image_text", { props_json: {} });
    const builder = createMockBuilder({ activeSection: section });
    builder.setMediaPickerTarget = setMediaPickerTarget;
    builder.setMediaPickerOpen = setMediaPickerOpen;

    render(<BuilderSectionInspector builder={builder} />);

    const buttons = screen.getAllByRole("button", { name: /elegir imagen/i });
    fireEvent.click(buttons[0]);
    expect(setMediaPickerTarget).toHaveBeenCalledWith("section");
  });

  it("shows gallery OptimizedImage when gallery item has url", () => {
    const section = createMockCmsSection("gallery", {
      props_json: { items: [{ url: "https://img.jpg", alt: "Gallery img" }] },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    const img = screen.getByAltText("Gallery img");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://img.jpg");
  });

  // ── Empty state for archived item ────────────────────────────────────────

  it("shows archived label for archived card items", () => {
    const section = createMockCmsSection("cards", {
      props_json: { items: [{ title: "A", status: "archived" }] },
    });
    const builder = createMockBuilder({ activeSection: section });

    render(<BuilderSectionInspector builder={builder} />);

    const archivedLabels = screen.getAllByText(/archivado/i);
    expect(archivedLabels.length).toBeGreaterThanOrEqual(1);
  });

  // ── AddArrayItem for team and pricing ────────────────────────────────────

  it("calls addArrayItem when adding a team person", () => {
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("team", {
      props_json: { items: [{ name: "Ana" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /añadir persona/i }));
    expect(addArrayItem).toHaveBeenCalledWith(
      "items",
      expect.objectContaining({ name: "Nombre", role: "Rol" }),
    );
  });

  it("calls addArrayItem when adding a pricing plan", () => {
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("pricing", {
      props_json: { items: [{ name: "Básico" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    fireEvent.click(screen.getByRole("button", { name: /añadir plan/i }));
    expect(addArrayItem).toHaveBeenCalledWith(
      "items",
      expect.objectContaining({ name: "Nuevo plan", price: "$0" }),
    );
  });

  // ── M1 Block Types (animated_counter, video_embed, gallery_masonry, map_embed) ──

  it("renders and edits animated_counter inspector controls", () => {
    const upsertArrayItem = vi.fn(() => ({}));
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("animated_counter", {
      props_json: {
        items: [{ label: "Personas", value: 1200, prefix: "$", suffix: "+", duration_ms: 2000 }],
      },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.upsertArrayItem = upsertArrayItem;
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    expect(screen.getByDisplayValue("Personas")).toBeInTheDocument();
    expect(screen.getByDisplayValue("1200")).toBeInTheDocument();

    const labelInput = screen.getByDisplayValue("Personas");
    fireEvent.change(labelInput, { target: { value: "Usuarios" } });
    expect(upsertArrayItem).toHaveBeenCalledWith("items", 0, { label: "Usuarios" });

    fireEvent.click(screen.getByRole("button", { name: /añadir contador/i }));
    expect(addArrayItem).toHaveBeenCalledWith("items", expect.objectContaining({ label: "Nuevo contador" }));
  });

  it("renders and edits video_embed inspector controls", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionField = vi.fn();
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("video_embed", {
      props_json: { video_url: "https://youtube.com/watch?v=123", caption: "Video intro", autoplay: false },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.updateSectionPropsLocal = updateSectionPropsLocal;
    builder.saveSectionField = saveSectionField;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const urlInput = screen.getByDisplayValue("https://youtube.com/watch?v=123");
    fireEvent.change(urlInput, { target: { value: "https://youtu.be/456" } });
    expect(updateSectionPropsLocal).toHaveBeenCalledWith(expect.objectContaining({ video_url: "https://youtu.be/456" }));

    fireEvent.blur(urlInput, { target: { value: "https://youtu.be/456" } });
    expect(saveSectionField).toHaveBeenCalledWith("video_url", "https://youtu.be/456");

    const checkbox = screen.getByLabelText(/autoplay/i);
    fireEvent.click(checkbox);
    expect(saveSectionProps).toHaveBeenCalledWith(expect.objectContaining({ autoplay: true }));
  });

  it("renders and edits gallery_masonry inspector controls", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionProps = vi.fn();
    const addArrayItem = vi.fn(() => ({}));
    const section = createMockCmsSection("gallery_masonry", {
      props_json: { columns: 3, images: [{ url: "/img1.jpg", alt: "Alt 1", caption: "Cap 1" }] },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.updateSectionPropsLocal = updateSectionPropsLocal;
    builder.saveSectionProps = saveSectionProps;
    builder.addArrayItem = addArrayItem;

    render(<BuilderSectionInspector builder={builder} />);

    const select = screen.getByDisplayValue("3 Columnas");
    fireEvent.change(select, { target: { value: "4" } });
    expect(saveSectionProps).toHaveBeenCalledWith(expect.objectContaining({ columns: 4 }));

    fireEvent.click(screen.getByRole("button", { name: /añadir imagen/i }));
    expect(addArrayItem).toHaveBeenCalledWith("images", expect.objectContaining({ status: "published" }));
  });

  it("renders and edits map_embed inspector controls", () => {
    const updateSectionPropsLocal = vi.fn();
    const saveSectionField = vi.fn();
    const saveSectionProps = vi.fn();
    const section = createMockCmsSection("map_embed", {
      props_json: { address: "Bogotá", lat: 4.6097, lng: -74.0817, zoom: 14, height_px: 400 },
    });
    const builder = createMockBuilder({ activeSection: section });
    builder.updateSectionPropsLocal = updateSectionPropsLocal;
    builder.saveSectionField = saveSectionField;
    builder.saveSectionProps = saveSectionProps;

    render(<BuilderSectionInspector builder={builder} />);

    const addressInput = screen.getByDisplayValue("Bogotá");
    fireEvent.change(addressInput, { target: { value: "Cali" } });
    expect(updateSectionPropsLocal).toHaveBeenCalledWith(expect.objectContaining({ address: "Cali" }));

    fireEvent.blur(addressInput, { target: { value: "Cali" } });
    expect(saveSectionField).toHaveBeenCalledWith("address", "Cali");
  });
});
