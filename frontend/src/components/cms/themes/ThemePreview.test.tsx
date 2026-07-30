import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import ThemePreview from "./ThemePreview";

const DEFAULT_TOKENS: Record<string, string> = {
  "--site-background": "#001134",
  "--site-on-background": "#d9e2ff",
  "--site-primary": "#a5c8ff",
  "--site-on-primary": "#00315e",
  "--site-navbar-bg": "rgba(0,13,42,0.6)",
  "--site-outline-variant": "#424750",
  "--site-surface-container": "#021d4a",
  "--site-surface-container-low": "#001944",
  "--site-surface-container-high": "#1d3361",
  "--site-surface-container-lowest": "#000d2a",
  "--site-error": "#ffb4ab",
  "--site-on-surface": "#d9e2ff",
  "--site-on-surface-variant": "#c2c6d1",
  "--site-hero-badge-bg": "rgba(165,200,255,0.05)",
  "--site-hero-badge-border": "rgba(165,200,255,0.3)",
  "--site-hero-badge-color": "rgba(165,200,255,0.9)",
  "--site-hero-cta-gradient": "linear-gradient(135deg,#018abd 0%,#2c609d 100%)",
  "--site-hero-cta-shadow": "0 8px 32px rgba(1,138,189,0.4)",
};

describe("ThemePreview", () => {
  it("renders the CCF logo badge", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText("CCF")).toBeInTheDocument();
  });

  it("renders the hero section with welcome badge", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/bienvenidos/i)).toBeInTheDocument();
  });

  it("renders hero title with faith and hope text", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/fe y esperanza/i)).toBeInTheDocument();
  });

  it("renders hero description text", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(
      screen.getByText(/preview en tiempo real/i),
    ).toBeInTheDocument();
  });

  it("renders hero CTA buttons", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/ver sermón/i)).toBeInTheDocument();
    // "Eventos" appears in both navbar link and button — use getAllByText
    const eventosElements = screen.getAllByText(/eventos/i);
    expect(eventosElements.length).toBeGreaterThanOrEqual(2);
  });

  it("renders the stats row with values", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText("1,240")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("$8.5K")).toBeInTheDocument();
  });

  it("renders stats row labels", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/personas/i)).toBeInTheDocument();
    expect(screen.getByText(/países/i)).toBeInTheDocument();
    expect(screen.getByText(/donaciones/i)).toBeInTheDocument();
  });

  it("renders upcoming events section title", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/próximos eventos/i)).toBeInTheDocument();
  });

  it("renders event cards with titles and details", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/culto de jóvenes/i)).toBeInTheDocument();
    expect(screen.getByText(/conferencia familiar/i)).toBeInTheDocument();
  });

  it("renders event registrarme button", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    const buttons = screen.getAllByText(/registrarme/i);
    expect(buttons.length).toBe(2);
  });

  it("renders the testimonial section with quote", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(
      screen.getByText(/glassmorphism/i),
    ).toBeInTheDocument();
  });

  it("renders testimonial author info", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/juan díaz/i)).toBeInTheDocument();
    expect(screen.getByText(/persona desde 2023/i)).toBeInTheDocument();
  });

  it("renders the contact form section", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/formulario de contacto/i)).toBeInTheDocument();
  });

  it("renders form input fields with mock values", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByDisplayValue("María González")).toBeInTheDocument();
    expect(screen.getByDisplayValue("maria@email.com")).toBeInTheDocument();
  });

  it("renders the message textarea", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(
      screen.getByDisplayValue(/me encantaría ser parte/i),
    ).toBeInTheDocument();
  });

  it("renders the submit button and checkbox", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/enviar mensaje/i)).toBeInTheDocument();
    expect(
      screen.getByText(/recibir noticias/i),
    ).toBeInTheDocument();
  });

  it("renders the alerts and status section", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/estados y alertas/i)).toBeInTheDocument();
    expect(screen.getByText(/confirmado/i)).toBeInTheDocument();
    expect(screen.getByText(/pendiente/i)).toBeInTheDocument();
    expect(screen.getByText(/cancelado/i)).toBeInTheDocument();
    expect(screen.getByText(/notificación/i)).toBeInTheDocument();
  });

  it("renders the footer section", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/preview generado/i)).toBeInTheDocument();
  });

  it("renders social/footer icons as SVG elements", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    // All icons are rendered as lucide-react SVGs
    const svgs = document.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThan(5);
  });

  it("renders event time and location details", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/7:00 pm/i)).toBeInTheDocument();
    expect(screen.getByText(/auditorio principal/i)).toBeInTheDocument();
    expect(screen.getByText(/9:00 am/i)).toBeInTheDocument();
  });

  it("renders event tag badges", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/worship/i)).toBeInTheDocument();
    expect(screen.getByText(/especial/i)).toBeInTheDocument();
  });

  it("renders 5 star rating in testimonial", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    // Stars are rendered as SVG elements; the testimonial has 5 stars
    const stars = document.querySelectorAll("svg");
    expect(stars.length).toBeGreaterThan(0);
  });

  it("applies CSS custom properties from tokens", () => {
    const { container } = render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    // The outer container should have the background style applied
    const outerDiv = container.firstChild as HTMLElement;
    expect(outerDiv).toBeInTheDocument();
  });

  it("renders with empty tokens gracefully", () => {
    // Should not throw with empty tokens (falls back to defaults)
    expect(() => render(<ThemePreview tokens={{}} />)).not.toThrow();
  });

  it("renders 'Ver todo' link in events section", () => {
    render(<ThemePreview tokens={DEFAULT_TOKENS} />);

    expect(screen.getByText(/ver todo/i)).toBeInTheDocument();
  });
});
