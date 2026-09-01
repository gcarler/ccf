import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CmsJsonMediaField from "./CmsJsonMediaField";

vi.mock("@/components/cms/CmsMediaUrlField", () => ({
  default: ({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) => (
    <div>
      <span>{label}</span>
      <button type="button" onClick={() => onChange("/api/static/cms/public-site/selected.webp")}>
        Seleccionar imagen para {label}
      </button>
      <span>{value}</span>
    </div>
  ),
}));

describe("CmsJsonMediaField", () => {
  it("exposes nested public image fields and updates valid JSON", () => {
    const onChange = vi.fn();
    const value = JSON.stringify({
      hero_image_url: "/images/source.webp",
      cta_images: [{ src: "" }],
      cards: [{ title: "Evento", image_url: "/images/card.png" }],
    }, null, 2);

    render(<CmsJsonMediaField value={value} token="token" onChange={onChange} />);

    expect(screen.getByText("hero_image_url")).toBeInTheDocument();
    expect(screen.getByText("cta_images / 0 / src")).toBeInTheDocument();
    expect(screen.getByText("cards / 0 / image_url")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Seleccionar imagen para hero_image_url/i }));

    const nextJson = onChange.mock.calls.at(-1)?.[0] as string;
    expect(JSON.parse(nextJson)).toMatchObject({
      hero_image_url: "/api/static/cms/public-site/selected.webp",
      cta_images: [{ src: "" }],
    });
  });

  it("exposes founder photos and nested sermon thumbnail overrides through CMS pickers", () => {
    const onChange = vi.fn();
    const value = JSON.stringify({
      founder1_image: "/api/static/cms/pastores/old-one.webp",
      founder2_image: "/api/static/cms/pastores/old-two.webp",
      content: JSON.stringify({ thumbnail_overrides: { "video-abc": "" } }),
    }, null, 2);

    render(<CmsJsonMediaField value={value} token="token" onChange={onChange} />);

    expect(screen.getByText("founder1_image")).toBeInTheDocument();
    expect(screen.getByText("founder2_image")).toBeInTheDocument();
    expect(screen.getByText("Miniaturas de prédicas")).toBeInTheDocument();
    expect(screen.getByDisplayValue("video-abc")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Seleccionar imagen para Imagen de miniatura/i }));

    const nextJson = onChange.mock.calls.at(-1)?.[0] as string;
    const next = JSON.parse(nextJson) as { content: string };
    expect(JSON.parse(next.content)).toMatchObject({
      thumbnail_overrides: { "video-abc": "/api/static/cms/public-site/selected.webp" },
    });
  });

  it("can activate sermon thumbnail overrides when the feed has none yet", () => {
    const onChange = vi.fn();
    const value = JSON.stringify({
      content: JSON.stringify({ hero_eyebrow: "Mensaje semanal" }),
    }, null, 2);

    render(
      <CmsJsonMediaField
        value={value}
        token="token"
        allowThumbnailOverrides
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Activar selector" }));

    const nextJson = onChange.mock.calls.at(-1)?.[0] as string;
    const next = JSON.parse(nextJson) as { content: string };
    expect(JSON.parse(next.content)).toMatchObject({
      hero_eyebrow: "Mensaje semanal",
      thumbnail_overrides: {},
    });
  });

  it("keeps the JSON textarea editable when it is temporarily invalid", () => {
    const onChange = vi.fn();
    render(<CmsJsonMediaField value="{ inválido" token="token" onChange={onChange} />);

    const textarea = screen.getByRole("textbox", { name: "Contenido editable (JSON)" });
    fireEvent.change(textarea, { target: { value: "{}" } });

    expect(onChange).toHaveBeenCalledWith("{}");
  });

  it("exposes and updates editorial fields inside serialized content", () => {
    const onChange = vi.fn();
    const value = JSON.stringify({
      content: JSON.stringify({
        empty_title: "Esperando agenda desde el CMS",
        calendar_description: "Organiza tu tiempo con nuestras actividades comunitarias.",
      }),
    });

    render(<CmsJsonMediaField value={value} token="token" onChange={onChange} />);

    expect(screen.getByDisplayValue("Esperando agenda desde el CMS")).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("Esperando agenda desde el CMS"), {
      target: { value: "Agenda publicada" },
    });

    const next = JSON.parse(onChange.mock.calls.at(-1)?.[0] as string) as { content: string };
    expect(JSON.parse(next.content)).toMatchObject({
      empty_title: "Agenda publicada",
      calendar_description: "Organiza tu tiempo con nuestras actividades comunitarias.",
    });
  });
});
