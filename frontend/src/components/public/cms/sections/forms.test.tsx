import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import type { CmsSection } from "@/types/cms-v2";
import { ContactFormSection, PrayerFormSection } from "./forms";
import { apiFetch } from "@/lib/http";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
  extractErrorMessage: vi.fn((_error: unknown, fallback: string) => fallback),
}));

const mockedApiFetch = vi.mocked(apiFetch);

function section<T extends "contact_form" | "prayer_form">(
  type: T,
  props_json: Record<string, unknown> = {},
): CmsSection<T> {
  const cmsDefaults = type === "contact_form"
    ? {
        title: "Hablemos de Tu Caminar",
        name_label: "Nombre completo",
        name_placeholder: "Tu nombre",
        email_label: "Correo electrónico",
        email_placeholder: "tu@email.com (opcional)",
        phone_label: "WhatsApp",
        phone_placeholder: "+57 300...",
        message_label: "¿En qué podemos ayudarte?",
        message_placeholder: "Cuéntanos un poco sobre ti...",
        submit_label: "Enviar mensaje y conectar",
        success_message: "Gracias. Te contactaremos pronto.",
        reset_label: "Enviar otro mensaje",
        sending_label: "Enviando...",
        error_message: "No se pudo enviar el mensaje.",
      }
    : {
        title: "Pedir oración",
        name_label: "Nombre",
        name_placeholder: "Tu nombre",
        request_label: "Petición de oración",
        request_placeholder: "Comparte tu necesidad...",
        submit_label: "Enviar al equipo pastoral",
        success_message: "Tu petición ha sido enviada.",
        reset_label: "Enviar otra petición",
        sending_label: "Enviando...",
        error_message: "No se pudo enviar la petición.",
      };
  return {
    id: `${type}-1`,
    page_id: "page-1",
    section_key: type,
    type,
    props_json: { ...cmsDefaults, ...props_json } as unknown as CmsSection<T>["props_json"],
    sort_order: 0,
    is_visible: true,
    status: "active",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

describe("public CMS forms", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockedApiFetch.mockResolvedValue({} as never);
  });

  it("submits the contact form to the internal contact endpoint", async () => {
    render(<ContactFormSection section={section("contact_form")} />);

    fireEvent.change(screen.getByLabelText("Nombre completo"), { target: { value: "Ana Gómez" } });
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "ana@example.com" } });
    fireEvent.change(screen.getByLabelText("¿En qué podemos ayudarte?"), { target: { value: "Quiero conocer la iglesia" } });
    fireEvent.submit(screen.getByRole("button", { name: "Enviar mensaje y conectar" }).closest("form")!);

    await waitFor(() => expect(mockedApiFetch).toHaveBeenCalledWith("/public/contact", expect.objectContaining({
      method: "POST",
      body: {
        full_name: "Ana Gómez",
        email: "ana@example.com",
        phone: undefined,
        notes: "Quiero conocer la iglesia",
        source: "cms-contact",
      },
      silent: true,
    })));
    expect(await screen.findByRole("status")).toHaveTextContent("Gracias. Te contactaremos pronto.");
  });

  it("submits the prayer form to the internal prayer endpoint", async () => {
    render(<PrayerFormSection section={section("prayer_form", { category: "Familia" })} />);

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Carlos Ruiz" } });
    fireEvent.change(screen.getByLabelText("Petición de oración"), { target: { value: "Por mi familia" } });
    fireEvent.submit(screen.getByRole("button", { name: "Enviar al equipo pastoral" }).closest("form")!);

    await waitFor(() => expect(mockedApiFetch).toHaveBeenCalledWith("/crm/prayer-requests/public", expect.objectContaining({
      method: "POST",
      body: {
        requester_name: "Carlos Ruiz",
        request_text: "Por mi familia",
        category: "Familia",
      },
      silent: true,
    })));
    expect(await screen.findByRole("status")).toHaveTextContent("Tu petición ha sido enviada.");
  });

  it("does not call the API when the honeypot is filled", async () => {
    render(<ContactFormSection section={section("contact_form")} />);
    const form = screen.getByRole("button", { name: "Enviar mensaje y conectar" }).closest("form")!;
    fireEvent.change(screen.getByLabelText("Nombre completo"), { target: { value: "Bot" } });
    fireEvent.change(screen.getByLabelText("¿En qué podemos ayudarte?"), { target: { value: "Spam" } });
    fireEvent.change(form.querySelector("input[name=website]")!, { target: { value: "https://spam.invalid" } });
    fireEvent.submit(form);

    expect(mockedApiFetch).not.toHaveBeenCalled();
    expect(await screen.findByRole("status")).toHaveTextContent("Gracias. Te contactaremos pronto.");
  });

  it("disables the submit button while a request is pending", async () => {
    let resolveRequest: (() => void) | undefined;
    mockedApiFetch.mockReturnValueOnce(new Promise((resolve) => {
      resolveRequest = () => resolve({} as never);
    }) as never);
    render(<ContactFormSection section={section("contact_form")} />);
    const form = screen.getByRole("button", { name: "Enviar mensaje y conectar" }).closest("form")!;
    fireEvent.change(screen.getByLabelText("Nombre completo"), { target: { value: "Pedro López" } });
    fireEvent.change(screen.getByLabelText("¿En qué podemos ayudarte?"), { target: { value: "Una consulta" } });
    fireEvent.submit(form);

    expect(screen.getByRole("button", { name: "Enviando..." })).toBeDisabled();
    resolveRequest!();
    await screen.findByRole("status");
  });

  it("shows an accessible error and keeps the form available after a failed request", async () => {
    mockedApiFetch.mockRejectedValueOnce(new Error("network"));
    render(<PrayerFormSection section={section("prayer_form")} />);
    const form = screen.getByRole("button", { name: "Enviar al equipo pastoral" }).closest("form")!;
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "Laura Díaz" } });
    fireEvent.change(screen.getByLabelText("Petición de oración"), { target: { value: "Necesito oración" } });
    fireEvent.submit(form);

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo enviar la petición.");
    expect(screen.getByRole("button", { name: "Enviar al equipo pastoral" })).toBeEnabled();
  });
});
