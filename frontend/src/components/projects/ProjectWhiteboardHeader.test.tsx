import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ReactNode } from "react";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProjectWhiteboardHeader, { type WhiteboardSaveStatus } from "./ProjectWhiteboardHeader";

const toastError = vi.hoisted(() => vi.fn());

vi.mock("sonner", () => ({ toast: { error: toastError } }));

vi.mock("@/components/ui/RightPanel", () => ({
  RightPanel: ({
    open,
    title,
    description,
    onClose,
    children,
  }: {
    open: boolean;
    title: string;
    description: string;
    onClose: () => void;
    children: ReactNode;
  }) => open ? (
    <section role="dialog" aria-label={title}>
      <p>{description}</p>
      <button type="button" aria-label="Cerrar panel" onClick={onClose}>×</button>
      {children}
    </section>
  ) : null,
}));

interface HarnessProps {
  onClose: () => void;
  initiallyDirty?: boolean;
  initiallySaving?: boolean;
}

function Harness({ onClose, initiallyDirty = true, initiallySaving = false }: HarnessProps) {
  const [saveStatus, setSaveStatus] = useState<WhiteboardSaveStatus>(initiallySaving ? "saving" : "idle");
  const [isDirty, setIsDirty] = useState(initiallyDirty);

  return (
    <>
      <ProjectWhiteboardHeader
        title="Pizarra de prueba"
        saveStatus={saveStatus}
        isDirty={isDirty}
        saveNow={() => setSaveStatus("saving")}
        onClose={onClose}
      />
      <button
        type="button"
        onClick={() => {
          setSaveStatus("saved");
          setIsDirty(false);
        }}
      >
        Simular guardado exitoso
      </button>
    </>
  );
}

describe("ProjectWhiteboardHeader close safety", () => {
  beforeEach(() => toastError.mockClear());

  it("does not unmount dirty work until an explicit discard or successful save", async () => {
    const onClose = vi.fn();
    render(<Harness onClose={onClose} initiallySaving />);

    fireEvent.click(screen.getByRole("button", { name: "Cerrar pizarra" }));
    expect(screen.getByRole("dialog", { name: "Cerrar pizarra" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Guardar y cerrar" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Guardar y cerrar" }));

    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Simular guardado exitoso" }));

    await waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    expect(screen.queryByRole("dialog", { name: "Cerrar pizarra" })).not.toBeInTheDocument();
  });

  it("keeps the drawer open and offers retry when saving fails", async () => {
    const onClose = vi.fn();
    function FailedSaveHarness() {
      const [saveStatus, setSaveStatus] = useState<WhiteboardSaveStatus>("idle");
      return (
        <>
          <ProjectWhiteboardHeader
            title="Pizarra de prueba"
            saveStatus={saveStatus}
            isDirty={saveStatus !== "saved"}
            saveNow={() => setSaveStatus("error")}
            onClose={onClose}
          />
        </>
      );
    }
    render(<FailedSaveHarness />);

    fireEvent.click(screen.getByRole("button", { name: "Cerrar pizarra" }));
    fireEvent.click(screen.getByRole("button", { name: "Guardar y cerrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudieron guardar los cambios");
    expect(screen.getByRole("dialog", { name: "Cerrar pizarra" })).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
    expect(toastError).toHaveBeenCalledWith("No se pudieron guardar los cambios de la pizarra.");
  });

  it("closes dirty work only after an explicit discard decision", () => {
    const onClose = vi.fn();
    render(<Harness onClose={onClose} />);

    fireEvent.click(screen.getByRole("button", { name: "Cerrar pizarra" }));
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Salir sin guardar" }));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("blocks retry when the server has a newer version and explains how to preserve local changes", () => {
    const onClose = vi.fn();
    render(
      <ProjectWhiteboardHeader
        title="Pizarra de prueba"
        saveStatus="error"
        isDirty
        hasConflict
        saveNow={vi.fn()}
        onClose={onClose}
      />,
    );

    expect(screen.getByRole("button", { name: "Guardar" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Cerrar pizarra" }));
    expect(screen.getByText(/expórtalos antes de cerrar/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recarga para guardar" })).toBeDisabled();
  });

  it("closes immediately when no changes are pending and labels the icon button", async () => {
    const onClose = vi.fn();
    const { container } = render(<Harness onClose={onClose} initiallyDirty={false} />);

    expect((await axe(container)).violations).toEqual([]);
    fireEvent.click(screen.getByRole("button", { name: "Cerrar pizarra" }));

    expect(onClose).toHaveBeenCalledOnce();
    expect(screen.queryByRole("dialog", { name: "Cerrar pizarra" })).not.toBeInTheDocument();
  });

  describe("PMI §5.2 & §10.1 — Gobernanza de Modelado Colaborativo y Sincronización OPA", () => {
    it("cambia el modo de taller PMI desde el selector y refleja el badge activo", () => {
      render(
        <ProjectWhiteboardHeader
          title="Pizarra de prueba"
          saveStatus="idle"
          isDirty={false}
          saveNow={vi.fn()}
          onClose={vi.fn()}
        />,
      );

      expect(screen.getByTestId("whiteboard-header-pmi-strip")).toBeInTheDocument();
      expect(screen.getByTestId("whiteboard-pmi-mode-select")).toHaveAttribute(
        "aria-label",
        "Modo de taller PMI",
      );
      expect(screen.getByTestId("whiteboard-pmi-active-mode")).toHaveTextContent(
        "Modelado WBS / Red PDM",
      );

      fireEvent.change(screen.getByTestId("whiteboard-pmi-mode-select"), {
        target: { value: "risk_ishikawa" },
      });
      expect(screen.getByTestId("whiteboard-pmi-active-mode")).toHaveTextContent(
        "Taller de Riesgos / Ishikawa",
      );

      fireEvent.change(screen.getByTestId("whiteboard-pmi-mode-select"), {
        target: { value: "stakeholder_map" },
      });
      expect(screen.getByTestId("whiteboard-pmi-active-mode")).toHaveTextContent(
        "Mapa de Interesados / Impacto",
      );
    });

    it("muestra el indicador de integridad OPA con la prioridad correcta de estados", () => {
      // Conflicto de concurrencia: prioridad máxima
      const { unmount: unmountConflict } = render(
        <ProjectWhiteboardHeader
          title="Pizarra de prueba"
          saveStatus="error"
          isDirty
          hasConflict
          saveNow={vi.fn()}
          onClose={vi.fn()}
        />,
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveTextContent(
        "Conflicto de Concurrencia OPA",
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveClass(
        "text-[hsl(var(--destructive))]",
      );
      unmountConflict();

      // Sincronizando artefacto
      const { unmount: unmountSaving } = render(
        <ProjectWhiteboardHeader
          title="Pizarra de prueba"
          saveStatus="saving"
          isDirty
          saveNow={vi.fn()}
          onClose={vi.fn()}
        />,
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveTextContent(
        "Sincronizando Artefacto...",
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveClass(
        "text-[hsl(var(--primary))]",
      );
      unmountSaving();

      // Error de sincronización sin conflicto
      const { unmount: unmountError } = render(
        <ProjectWhiteboardHeader
          title="Pizarra de prueba"
          saveStatus="error"
          isDirty
          saveNow={vi.fn()}
          onClose={vi.fn()}
        />,
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveTextContent(
        "Error de Sincronizacion",
      );
      unmountError();

      // Cambios locales pendientes
      const { unmount: unmountDirty } = render(
        <ProjectWhiteboardHeader
          title="Pizarra de prueba"
          saveStatus="idle"
          isDirty
          saveNow={vi.fn()}
          onClose={vi.fn()}
        />,
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveTextContent(
        "Cambios Locales Pendientes",
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveClass(
        "text-[hsl(var(--warning))]",
      );
      unmountDirty();

      // Sincronizado con OPA (estado base)
      render(
        <ProjectWhiteboardHeader
          title="Pizarra de prueba"
          saveStatus="idle"
          isDirty={false}
          saveNow={vi.fn()}
          onClose={vi.fn()}
        />,
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveTextContent(
        "Sincronizado con OPA",
      );
      expect(screen.getByTestId("whiteboard-pmi-opa-status")).toHaveClass(
        "text-[hsl(var(--success))]",
      );
    });
  });
});
