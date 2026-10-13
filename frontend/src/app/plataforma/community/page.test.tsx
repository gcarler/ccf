import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CommunityHubPage from "./page";

const apiFetchMock = vi.hoisted(() => vi.fn());
const toastMock = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
const authSession = vi.hoisted(() => ({ token: "test-token" }));

vi.mock("@/lib/http", () => ({ apiFetch: apiFetchMock }));
vi.mock("@/context/AuthContext", () => ({ useAuth: () => ({ token: authSession.token }) }));
vi.mock("sonner", () => ({ toast: toastMock }));
vi.mock("@/components/ui/RightPanel", () => ({
  default: ({ open, title, children }: { open: boolean; title: string; children: React.ReactNode }) =>
    open ? <aside role="dialog" aria-label={title}>{children}</aside> : null,
}));

const persistedCard = {
  id: "card-1",
  title: "Jornada de servicio",
  body: "Encuentro para servir juntos.",
  created_at: "2026-10-12T12:00:00Z",
};

describe("CommunityHubPage", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
    authSession.token = "test-token";
    apiFetchMock.mockResolvedValue([]);
  });

  it("loads and displays cards using the backend contract", async () => {
    apiFetchMock.mockResolvedValueOnce([persistedCard]);
    render(<CommunityHubPage />);

    expect(await screen.findByText("Jornada de servicio")).toBeInTheDocument();
    expect(screen.getByText("Encuentro para servir juntos.")).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledWith("/community/cards", {
      token: "test-token",
      cache: "no-store",
    });
  });

  it("shows the loading skeleton while cards are pending", async () => {
    let resolveCards: ((cards: typeof persistedCard[]) => void) | undefined;
    apiFetchMock.mockImplementationOnce(() => new Promise((resolve) => { resolveCards = resolve; }));
    render(<CommunityHubPage />);

    expect(screen.getByLabelText("Cargando tarjetas")).toHaveAttribute("aria-busy", "true");
    await act(async () => resolveCards?.([]));
    expect(await screen.findByText("Aún no hay tarjetas")).toBeInTheDocument();
  });

  it("does not show an old session response after the auth token changes", async () => {
    let resolveOld: ((cards: typeof persistedCard[]) => void) | undefined;
    let resolveCurrent: ((cards: typeof persistedCard[]) => void) | undefined;
    const oldCard = { ...persistedCard, id: "old-session-card", title: "Privado de sesión anterior" };
    apiFetchMock
      .mockImplementationOnce(() => new Promise((resolve) => { resolveOld = resolve; }))
      .mockImplementationOnce(() => new Promise((resolve) => { resolveCurrent = resolve; }));
    const { rerender } = render(<CommunityHubPage />);

    authSession.token = "next-session-token";
    rerender(<CommunityHubPage />);
    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(2));
    await act(async () => resolveCurrent?.([persistedCard]));
    expect(await screen.findByText("Jornada de servicio")).toBeInTheDocument();
    await act(async () => resolveOld?.([oldCard]));

    expect(screen.queryByText("Privado de sesión anterior")).not.toBeInTheDocument();
    expect(screen.getByText("Jornada de servicio")).toBeInTheDocument();
  });

  it("shows a real empty state without demo cards or fabricated metrics", async () => {
    render(<CommunityHubPage />);

    expect(await screen.findByText("Aún no hay tarjetas")).toBeInTheDocument();
    expect(screen.queryByText("Equipos activos")).not.toBeInTheDocument();
    expect(screen.queryByText("Resumen semanal de notificaciones")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Comunidad" })).toBeVisible();
  });

  it("keeps an error visible and retries the GET", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([persistedCard]);
    render(<CommunityHubPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron cargar las tarjetas");
    await user.click(screen.getByRole("button", { name: "Reintentar" }));

    expect(await screen.findByText("Jornada de servicio")).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledTimes(2);
  });

  it("exports only the confirmed cards with a CSV download", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockResolvedValueOnce([persistedCard]);
    const createObjectURL = vi.fn().mockReturnValue("blob:community-cards");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const clickAnchor = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    render(<CommunityHubPage />);

    await user.click(await screen.findByRole("button", { name: "Exportar CSV" }));

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(createObjectURL.mock.calls[0][0]).toBeInstanceOf(Blob);
    expect(clickAnchor).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:community-cards");
    vi.unstubAllGlobals();
  });

  it("creates a card through the Drawer with only title and body", async () => {
    const user = userEvent.setup();
    apiFetchMock.mockResolvedValueOnce([]).mockResolvedValueOnce(persistedCard).mockResolvedValueOnce([persistedCard]);
    render(<CommunityHubPage />);

    await user.click(await screen.findByRole("button", { name: "Nueva tarjeta" }));
    expect(screen.getByRole("dialog", { name: "Nueva tarjeta" })).toBeInTheDocument();
    await user.type(screen.getByRole("textbox", { name: "Título" }), "Jornada de servicio");
    await user.type(screen.getByRole("textbox", { name: /Descripción/ }), "Encuentro para servir juntos.");
    await user.click(screen.getByRole("button", { name: "Publicar tarjeta" }));

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(3));
    expect(apiFetchMock).toHaveBeenNthCalledWith(2, "/community/cards", {
      method: "POST",
      token: "test-token",
      body: { title: "Jornada de servicio", body: "Encuentro para servir juntos." },
    });
    expect(await screen.findByText("Jornada de servicio")).toBeInTheDocument();
    expect(toastMock.success).toHaveBeenCalledWith("Tarjeta creada");
  });

  it("preserves form values after a failed POST so the user can retry", async () => {
    const user = userEvent.setup();
    apiFetchMock
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("forbidden"))
      .mockResolvedValueOnce(persistedCard)
      .mockResolvedValueOnce([persistedCard]);
    render(<CommunityHubPage />);

    await user.click(await screen.findByRole("button", { name: "Nueva tarjeta" }));
    const titleInput = screen.getByRole("textbox", { name: "Título" });
    const bodyInput = screen.getByRole("textbox", { name: /Descripción/ });
    await user.type(titleInput, "Jornada de servicio");
    await user.type(bodyInput, "Encuentro para servir juntos.");
    await user.click(screen.getByRole("button", { name: "Publicar tarjeta" }));

    await waitFor(() => expect(toastMock.error).toHaveBeenCalled());
    expect(titleInput).toHaveValue("Jornada de servicio");
    expect(bodyInput).toHaveValue("Encuentro para servir juntos.");

    await user.click(screen.getByRole("button", { name: "Publicar tarjeta" }));
    await waitFor(() => expect(apiFetchMock).toHaveBeenCalledTimes(4));
    expect(apiFetchMock).toHaveBeenNthCalledWith(3, "/community/cards", {
      method: "POST",
      token: "test-token",
      body: { title: "Jornada de servicio", body: "Encuentro para servir juntos." },
    });
    expect(await screen.findByText("Jornada de servicio")).toBeInTheDocument();
  });

  it("serializes concurrent form submits into one POST", async () => {
    const user = userEvent.setup();
    let resolvePost: ((card: typeof persistedCard) => void) | undefined;
    apiFetchMock
      .mockResolvedValueOnce([])
      .mockImplementationOnce(() => new Promise((resolve) => { resolvePost = resolve; }))
      .mockResolvedValueOnce([persistedCard]);
    render(<CommunityHubPage />);

    await user.click(await screen.findByRole("button", { name: "Nueva tarjeta" }));
    await user.type(screen.getByRole("textbox", { name: "Título" }), "Jornada de servicio");
    const form = screen.getByRole("textbox", { name: "Título" }).closest("form");
    expect(form).not.toBeNull();

    fireEvent.submit(form as HTMLFormElement);
    fireEvent.submit(form as HTMLFormElement);
    expect(apiFetchMock).toHaveBeenCalledTimes(2);

    await act(async () => {
      resolvePost?.(persistedCard);
    });
    expect(await screen.findByText("Jornada de servicio")).toBeInTheDocument();
    expect(apiFetchMock).toHaveBeenCalledTimes(3);
  });
});
