import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import MediaPickerField, { setMediaPickerTrigger } from "./MediaPickerField";

describe("MediaPickerField", () => {
  it("renders label and 'Seleccionar Imagen' button when value is empty", () => {
    const onChange = vi.fn();
    render(<MediaPickerField label="Imagen de Fondo" value="" onChange={onChange} />);

    expect(screen.getByText("Imagen de Fondo")).toBeInTheDocument();
    expect(screen.getByText("Seleccionar Imagen")).toBeInTheDocument();
    expect(screen.queryByAltText("Vista previa")).not.toBeInTheDocument();
    expect(screen.queryByText("Quitar")).not.toBeInTheDocument();
  });

  it("renders preview thumbnail, 'Cambiar Imagen', and 'Quitar' button when value is present", () => {
    const onChange = vi.fn();
    const imageUrl = "https://example.com/test.jpg";
    render(<MediaPickerField label="Imagen de Fondo" value={imageUrl} onChange={onChange} />);

    expect(screen.getByText("Cambiar Imagen")).toBeInTheDocument();
    expect(screen.getByText("Quitar")).toBeInTheDocument();
    expect(screen.getByText(imageUrl)).toBeInTheDocument();

    const img = screen.getByAltText("Vista previa") as HTMLImageElement;
    expect(img).toBeInTheDocument();
    expect(img.src).toBe(imageUrl);
  });

  it("calls onChange('') when clicking 'Quitar'", () => {
    const onChange = vi.fn();
    render(<MediaPickerField label="Imagen" value="https://example.com/pic.png" onChange={onChange} />);

    const removeBtn = screen.getByText("Quitar");
    fireEvent.click(removeBtn);

    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith("");
  });

  it("hides thumbnail on image loading error (onError handling)", () => {
    const onChange = vi.fn();
    render(<MediaPickerField label="Imagen" value="https://example.com/broken.png" onChange={onChange} />);

    const img = screen.getByAltText("Vista previa") as HTMLImageElement;
    expect(img.style.display).not.toBe("none");

    fireEvent.error(img);
    expect(img.style.display).toBe("none");
  });

  it("invokes mediaPickerTrigger when clicking Seleccionar Imagen / Cambiar Imagen button", () => {
    const triggerMock = vi.fn();
    setMediaPickerTrigger(triggerMock);
    const onChange = vi.fn();

    render(<MediaPickerField label="Imagen" value="" onChange={onChange} />);
    fireEvent.click(screen.getByText("Seleccionar Imagen"));

    expect(triggerMock).toHaveBeenCalledWith(onChange, "");
    setMediaPickerTrigger(null);
  });
});
