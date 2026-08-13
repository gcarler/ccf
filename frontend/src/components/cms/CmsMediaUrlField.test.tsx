import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import CmsMediaUrlField from "./CmsMediaUrlField";

vi.mock("@/components/cms/builder/MediaPicker", () => ({
  default: ({ onSelect }: { onSelect: (item: { url: string }) => void }) => (
    <button data-testid="mock-media-picker" onClick={() => onSelect({ url: "/api/static/cms/public-site/photo.webp" })}>
      mock picker
    </button>
  ),
}));

describe("CmsMediaUrlField", () => {
  it("keeps manual URL editing available and opens the CMS picker", () => {
    const onChange = vi.fn();
    render(<CmsMediaUrlField label="Imagen destacada" value="" token="token" onChange={onChange} />);

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "https://example.com/photo.jpg" } });
    expect(onChange).toHaveBeenCalledWith("https://example.com/photo.jpg");

    fireEvent.click(screen.getByRole("button", { name: "Biblioteca" }));
    expect(screen.getByTestId("mock-media-picker")).toBeInTheDocument();
  });

  it("writes the selected CMS media URL", () => {
    const onChange = vi.fn();
    render(<CmsMediaUrlField label="Imagen" value="" token="token" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Biblioteca" }));
    fireEvent.click(screen.getByTestId("mock-media-picker"));

    expect(onChange).toHaveBeenCalledWith("/api/static/cms/public-site/photo.webp");
  });
});
