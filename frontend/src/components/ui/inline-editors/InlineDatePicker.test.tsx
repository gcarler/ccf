import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { InlineDatePicker } from "./InlineDatePicker";

afterEach(() => {
  vi.useRealTimers();
});

describe("InlineDatePicker", () => {
  it.each([
    ["ISO timestamp", "2026-10-29T00:00:00Z"],
    ["date-only value", "2026-10-29"],
    ["space-separated timestamp", "2026-10-29 00:00:00"],
  ])("keeps the calendar day and shows synced %s values", (_label, value) => {
    const { rerender } = render(<InlineDatePicker value={value} onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Seleccionar fecha límite" })).not.toHaveTextContent("—");

    rerender(<InlineDatePicker value="2026-10-29T00:00:00Z" onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Seleccionar fecha límite" }));

    expect(screen.getByText("Octubre 2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "29" })).toHaveClass("bg-[hsl(var(--primary))]");
  });

  it("emits a stable date key when the student selects a calendar day", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-01T12:00:00Z"));
    const onChange = vi.fn();
    render(<InlineDatePicker value={null} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Seleccionar fecha límite" }));
    fireEvent.click(screen.getByRole("button", { name: "Mes siguiente" }));
    fireEvent.click(screen.getByRole("button", { name: "29" }));

    expect(onChange).toHaveBeenCalledWith("2026-10-29");
  });
});
