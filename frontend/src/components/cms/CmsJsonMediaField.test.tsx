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

  it("keeps the JSON textarea editable when it is temporarily invalid", () => {
    const onChange = vi.fn();
    render(<CmsJsonMediaField value="{ inválido" token="token" onChange={onChange} />);

    const textarea = screen.getByRole("textbox", { name: "Contenido editable (JSON)" });
    fireEvent.change(textarea, { target: { value: "{}" } });

    expect(onChange).toHaveBeenCalledWith("{}");
  });
});
