import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import CmsFormRenderer, { type CmsFormRendererApi } from "../CmsFormRenderer";
import { ApiError } from "@/lib/http";
import type { CmsFormField, CmsFormPublicRead } from "@/types/cms-v2";

function field(overrides: Partial<CmsFormField> & { id: string; label: string }): CmsFormField {
  return {
    type: "text",
    required: false,
    ...overrides,
  } as CmsFormField;
}

function form(overrides: Partial<CmsFormPublicRead> = {}): CmsFormPublicRead {
  return {
    id: "f",
    name: "Form",
    description: null,
    fields: [],
    submit_button_text: "Enviar",
    success_message: "¡Gracias!",
    captcha_enabled: false,
    captcha_provider: "hcaptcha",
    captcha_site_key: null,
    honeypot_enabled: false,
    settings_json: {
      public_ui: {
        captcha_required: "Debes completar el captcha para continuar.",
        invalid_value: "Valor inválido",
        submit_error: "Ocurrió un error al enviar el formulario.",
        reset_label: "Enviar otra respuesta",
        review_title: "Revisa tus respuestas",
        step_label: "Paso",
        of_label: "de",
        review_description: "Confirma antes de enviar.",
        review_empty: "No hay campos completados.",
        previous_label: "Anterior",
        review_button_label: "Revisar",
        next_label: "Continuar",
      },
    },
    is_active: true,
    ...overrides,
  };
}

const labelOf = (id: string) => `El campo "${id}" es obligatorio`;

describe("CmsFormRenderer (componente)", () => {
  it("marca campo obligatorio vacío y muestra error inline al intentar enviar", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CmsFormRenderer
        form={form({ fields: [field({ id: "a", label: "Nombre", required: true })] })}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Enviar/i }));

    expect(await screen.findByText(labelOf("Nombre"))).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("no envía si el campo tiene error; sí envía con datos válidos", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CmsFormRenderer
        form={form({ fields: [field({ id: "e", label: "Correo", type: "email", required: true })] })}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Correo/), { target: { value: "no-es-email" } });
    fireEvent.click(screen.getByRole("button", { name: /Enviar/i }));
    expect(await screen.findByText("Ingresa un correo electrónico válido")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText(/Correo/), { target: { value: "a@b.com" } });
    fireEvent.click(screen.getByRole("button", { name: /Enviar/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({ data: { e: "a@b.com" }, captchaToken: null, hp: null });
  });

  it("valida el paso actual antes de avanzar en un formulario multi-paso", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CmsFormRenderer
        form={form({
          fields: [
            field({ id: "a", label: "Paso A", required: true }),
            field({ id: "p", label: "Salto", type: "page" }),
            field({ id: "b", label: "Paso B", required: true }),
          ],
        })}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByText("Paso 1 de 2")).toBeInTheDocument();

    // Sin llenar el paso 1, no avanza.
    fireEvent.click(screen.getByRole("button", { name: /Continuar/i }));
    expect(await screen.findByText(labelOf("Paso A"))).toBeInTheDocument();
    expect(screen.getByText("Paso 1 de 2")).toBeInTheDocument();

    // Llena y avanza.
    fireEvent.change(screen.getByLabelText(/Paso A/), { target: { value: "ok" } });
    fireEvent.click(screen.getByRole("button", { name: /Continuar/i }));

    await waitFor(() => expect(screen.getByText("Paso 2 de 2")).toBeInTheDocument());
    expect(screen.getByLabelText(/Paso B/)).toBeInTheDocument();
  });

  it("multi-paso: muestra revisión final con resumen antes de enviar", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CmsFormRenderer
        form={form({
          fields: [
            field({ id: "a", label: "Nombre", required: true }),
            field({ id: "p", label: "Salto", type: "page" }),
            field({ id: "n", label: "Edad", type: "number", required: true }),
          ],
        })}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Nombre/), { target: { value: "Ana" } });
    fireEvent.click(screen.getByRole("button", { name: /Continuar/i }));
    fireEvent.change(screen.getByLabelText(/Edad/), { target: { value: 30 } });

    // El último paso ofrece "Revisar" en vez de "Enviar".
    const revisarBtn = screen.getByRole("button", { name: /Revisar/i });
    fireEvent.click(revisarBtn);

    expect(screen.getByText("Revisa tus respuestas")).toBeInTheDocument();
    expect(screen.getByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("30")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Enviar/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({ data: { a: "Ana", n: 30 }, captchaToken: null, hp: null });
  });

  it("los indicadores de paso permiten volver a pasos anteriores", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CmsFormRenderer
        form={form({
          fields: [
            field({ id: "a", label: "Paso A", required: true }),
            field({ id: "p", label: "Salto", type: "page" }),
            field({ id: "b", label: "Paso B", required: true }),
          ],
        })}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Paso A/), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: /Continuar/i }));
    await waitFor(() => expect(screen.getByText("Paso 2 de 2")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /Ir al paso 1/i }));
    await waitFor(() => expect(screen.getByText("Paso 1 de 2")).toBeInTheDocument());
    expect(screen.getByLabelText(/Paso A/)).toHaveValue("x");
  });

  it("incluye el honeypot en el payload solo si está rellenado", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const api: { current: CmsFormRendererApi | null } = { current: null };

    render(
      <CmsFormRenderer
        form={form({ honeypot_enabled: true, fields: [field({ id: "a", label: "Nombre" })] })}
        onSubmit={onSubmit}
        onReady={(a) => (api.current = a)}
      />,
    );

    fireEvent.change(screen.getByLabelText(/Nombre/), { target: { value: "Ana" } });
    const hp = document.querySelector<HTMLInputElement>('input[name="_hp"]')!;
    fireEvent.change(hp, { target: { value: "soy-un-bot" } });

    fireEvent.click(screen.getByRole("button", { name: /Enviar/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit).toHaveBeenCalledWith({ data: { a: "Ana" }, captchaToken: null, hp: "soy-un-bot" });
  });

  it("error de backend con field_id se mapea inline y salta al paso del campo", async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError("bad", 422, { code: "INVALID_FIELD", detail: "Correo ya registrado", field_id: "e" }),
    );
    render(
      <CmsFormRenderer
        form={form({
          fields: [
            field({ id: "a", label: "Paso A", required: true }),
            field({ id: "p", label: "Salto", type: "page" }),
            field({ id: "e", label: "Correo", type: "email", required: true }),
          ],
        })}
        onSubmit={onSubmit}
      />,
    );

    // Llena ambos pasos y revisa.
    fireEvent.change(screen.getByLabelText(/Paso A/), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: /Continuar/i }));
    fireEvent.change(screen.getByLabelText(/Correo/), { target: { value: "a@b.com" } });
    fireEvent.click(screen.getByRole("button", { name: /Revisar/i }));
    fireEvent.click(screen.getByRole("button", { name: /Enviar/i }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    // Vuelve al paso del campo con el error inline.
    await waitFor(() => expect(screen.getByText("Paso 2 de 2")).toBeInTheDocument());
    expect(screen.getByText("Correo ya registrado")).toBeInTheDocument();
  });

  it("honeypot activado → éxito silencioso (respuesta 200 al bot)", async () => {
    const onSubmit = vi.fn().mockRejectedValue(
      new ApiError("bot", 422, { code: "HONEYPOT_TRIGGERED", detail: "bot detectado" }),
    );
    render(
      <CmsFormRenderer
        form={form({ fields: [field({ id: "a", label: "Nombre" })] })}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Nombre/), { target: { value: "Ana" } });
    fireEvent.click(screen.getByRole("button", { name: /Enviar/i }));

    await waitFor(() =>
      expect(screen.getByText("¡Gracias!")).toBeInTheDocument(),
    );
  });

  it("captcha requerido bloquea el envío si no hay token", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(
      <CmsFormRenderer
        form={form({ captcha_enabled: true, captcha_site_key: "test-key", fields: [field({ id: "a", label: "Nombre", required: true })] })}
        onSubmit={onSubmit}
      />,
    );
    fireEvent.change(screen.getByLabelText(/Nombre/), { target: { value: "Ana" } });
    fireEvent.click(screen.getByRole("button", { name: /Enviar/i }));

    await waitFor(() =>
      expect(screen.getByText("Debes completar el captcha para continuar.")).toBeInTheDocument(),
    );
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
