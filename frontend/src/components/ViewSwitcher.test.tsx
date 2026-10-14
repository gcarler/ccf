import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ViewSwitcher from "./ViewSwitcher";

describe("ViewSwitcher", () => {
  it("highlights the active view and makes the other option visibly interactive", () => {
    const setViewType = vi.fn();
    render(<ViewSwitcher viewType="table" setViewType={setViewType} availableViews={["table", "list"]} />);

    const activeView = screen.getByRole("button", { name: "Tabla" });
    const otherView = screen.getByRole("button", { name: "Lista" });

    expect(activeView).toHaveAttribute("aria-pressed", "true");
    expect(activeView).toHaveClass("text-[hsl(var(--primary))]");
    expect(activeView).toHaveClass("bg-[hsl(var(--primary)/0.12)]");
    expect(activeView).toHaveClass("border-[hsl(var(--primary)/0.5)]");

    expect(otherView).toHaveAttribute("aria-pressed", "false");
    expect(otherView).toHaveClass("hover:bg-[hsl(var(--surface-3))]");
    expect(otherView).toHaveClass("hover:text-[hsl(var(--text-primary))]");
    expect(otherView).toHaveClass("hover:border-[hsl(var(--border))]");

    fireEvent.click(otherView);
    expect(setViewType).toHaveBeenCalledWith("list");
  });
});
