import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useAuth } from "@/context/AuthContext";
import { apiFetch } from "@/lib/http";
import { InlineUserPicker } from "./InlineUserPicker";

vi.mock("@/context/AuthContext", () => ({
  useAuth: vi.fn(),
}));

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

const mockApiFetch = vi.mocked(apiFetch);
const mockUseAuth = vi.mocked(useAuth);

const laury = {
  id: "persona-laury",
  nombre_completo: "Laury Méndez",
  first_name: "Laury",
  last_name: "Méndez",
  email: "laury@example.com",
};

async function advanceDebounce() {
  await act(async () => {
    vi.advanceTimersByTime(300);
    await Promise.resolve();
    await Promise.resolve();
  });
}

async function flushRequest() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe("InlineUserPicker", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockApiFetch.mockReset();
    mockApiFetch.mockResolvedValue([]);
    mockUseAuth.mockReturnValue({ token: "test-token" } as ReturnType<typeof useAuth>);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("debounces server search for 300ms and uses the CRM search contract", async () => {
    render(<InlineUserPicker value={null} onChange={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Selector de persona asignada" }));
    await advanceDebounce();

    expect(mockApiFetch).toHaveBeenCalledWith("/crm/personas", {
      method: "GET",
      token: "test-token",
      query: { search: undefined, limit: 50 },
      signal: expect.any(AbortSignal),
    });

    const input = screen.getByPlaceholderText("Buscar usuario...");
    fireEvent.change(input, { target: { value: "Laury Méndez & Ana" } });
    vi.advanceTimersByTime(299);
    expect(mockApiFetch).toHaveBeenCalledTimes(1);

    await advanceDebounce();
    expect(mockApiFetch).toHaveBeenLastCalledWith("/crm/personas", {
      method: "GET",
      token: "test-token",
      query: { search: "Laury Méndez & Ana", limit: 50 },
      signal: expect.any(AbortSignal),
    });
  });

  it("selects a persona and reports its canonical id and display name", async () => {
    mockApiFetch.mockResolvedValueOnce([laury]);
    const onChange = vi.fn();
    render(<InlineUserPicker value={null} onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Selector de persona asignada" }));
    await advanceDebounce();
    fireEvent.click(screen.getByRole("button", { name: /Laury Méndez/ }));

    expect(onChange).toHaveBeenCalledWith("persona-laury", "Laury Méndez");
  });

  it("allows removing an assignment even when the current search has no results", async () => {
    mockApiFetch.mockResolvedValueOnce(laury).mockResolvedValueOnce([]);
    const onChange = vi.fn();
    render(<InlineUserPicker value="persona-laury" onChange={onChange} />);

    fireEvent.click(screen.getByRole("button", { name: "Selector de persona asignada" }));
    await advanceDebounce();
    fireEvent.change(screen.getByPlaceholderText("Buscar usuario..."), {
      target: { value: "sin coincidencias" },
    });
    await advanceDebounce();

    fireEvent.click(screen.getByRole("button", { name: "Quitar asignación" }));
    expect(onChange).toHaveBeenCalledWith(null, null);
  });

  it("preserves the assigned person's name when the selected record is outside the search result", async () => {
    mockApiFetch.mockResolvedValueOnce(laury).mockResolvedValueOnce([]);
    render(<InlineUserPicker value="persona-laury" onChange={vi.fn()} />);

    await flushRequest();
    expect(screen.getByTitle("Asignado a Laury Méndez")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Selector de persona asignada" }));
    await advanceDebounce();
    fireEvent.change(screen.getByPlaceholderText("Buscar usuario..."), {
      target: { value: "otra búsqueda" },
    });
    await advanceDebounce();

    expect(screen.getByTitle("Asignado a Laury Méndez")).toBeInTheDocument();
  });
});
