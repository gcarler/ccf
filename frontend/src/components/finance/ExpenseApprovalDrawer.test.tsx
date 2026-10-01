import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ExpenseApprovalDrawer, { ExpenseReport } from "./ExpenseApprovalDrawer";

vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({
    token: "mock-jwt-token",
    user: { id: "test-user-id", email: "pastor@ccf.org" },
  }),
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { apiFetch } from "@/lib/http";
import { toast } from "sonner";

describe("ExpenseApprovalDrawer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockDraftReport: ExpenseReport = {
    id: "rep-1111-2222",
    description: "Gastos de útiles escolares",
    status: "draft",
    approval_step: "draft",
    total_amount: 85000,
    currency: "COP",
    created_at: "2026-10-01T10:00:00Z",
    items: [
      {
        id: "item-1",
        description: "Cuadernos y marcadores",
        category: "materials",
        amount: 85000,
        currency: "COP",
        expense_date: "2026-10-01",
        vendor: "Papelería del Valle",
      },
    ],
    approval_history: [],
  };

  const mockPastorReviewReport: ExpenseReport = {
    ...mockDraftReport,
    status: "pastor_review",
    approval_step: "pastor_review",
    submitted_at: "2026-10-01T10:30:00Z",
    approval_history: [
      {
        from_status: "draft",
        to_status: "pastor_review",
        actor_name: "Líder Sede",
        timestamp: "2026-10-01T10:30:00Z",
        notes: "Enviado para aval",
      },
    ],
  };

  const mockApprovedReport: ExpenseReport = {
    ...mockDraftReport,
    status: "approved",
    approval_step: "approved",
    approval_history: [
      {
        from_status: "central_authorization",
        to_status: "approved",
        actor_name: "Admin Central",
        timestamp: "2026-10-01T11:00:00Z",
        notes: "Autorizado",
      },
    ],
  };

  it("does not render when closed or report is null", () => {
    render(<ExpenseApprovalDrawer isOpen={false} onClose={() => {}} report={mockDraftReport} />);
    expect(screen.queryByText(/Aprobación de Gastos de Sede/i)).not.toBeInTheDocument();

    render(<ExpenseApprovalDrawer isOpen={true} onClose={() => {}} report={null} />);
    expect(screen.queryByText(/Aprobación de Gastos de Sede/i)).not.toBeInTheDocument();
  });

  it("renders draft expense report with submit action", async () => {
    render(<ExpenseApprovalDrawer isOpen={true} onClose={() => {}} report={mockDraftReport} />);

    expect(screen.getByText(/Aprobación de Gastos de Sede/i)).toBeInTheDocument();
    expect(screen.getByText(/Gastos de útiles escolares/i)).toBeInTheDocument();
    expect(screen.getByText(/Cuadernos y marcadores/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Enviar a Revisión Pastoral/i })).toBeInTheDocument();
  });

  it("handles submission to pastor review", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ status: "pastor_review" });

    render(<ExpenseApprovalDrawer isOpen={true} onClose={() => {}} report={mockDraftReport} />);

    const submitBtn = screen.getByRole("button", { name: /Enviar a Revisión Pastoral/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/finance-suite/expense-reports/rep-1111-2222/submit",
        expect.objectContaining({
          method: "POST",
          token: "mock-jwt-token",
        })
      );
      expect(toast.success).toHaveBeenCalledWith("Informe enviado a revisión pastoral");
    });
  });

  it("renders pastor review state and handles pastor approval", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ status: "central_authorization" });

    render(<ExpenseApprovalDrawer isOpen={true} onClose={() => {}} report={mockPastorReviewReport} />);

    expect(screen.getByText(/Traza de Auditoría Inmutable/i)).toBeInTheDocument();
    expect(screen.getByText(/Líder Sede/i)).toBeInTheDocument();

    const approveBtn = screen.getByRole("button", { name: /Avalar como Pastor de Sede/i });
    fireEvent.click(approveBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/finance-suite/expense-reports/rep-1111-2222/pastor-approve",
        expect.objectContaining({
          method: "POST",
        })
      );
      expect(toast.success).toHaveBeenCalledWith("Informe avalado y remitido a administración central");
    });
  });

  it("handles rejection flow with validation", async () => {
    render(<ExpenseApprovalDrawer isOpen={true} onClose={() => {}} report={mockPastorReviewReport} />);

    const rejectBtn = screen.getByRole("button", { name: /Rechazar/i });
    fireEvent.click(rejectBtn);

    expect(screen.getByText(/Motivo del Rechazo de Fondos/i)).toBeInTheDocument();

    const confirmRejectBtn = screen.getByRole("button", { name: /Confirmar Rechazo/i });
    fireEvent.click(confirmRejectBtn);

    expect(toast.error).toHaveBeenCalledWith(
      "Debe ingresar un motivo detallado de rechazo (mínimo 5 caracteres)"
    );

    const textarea = screen.getByPlaceholderText(/Explique las inconsistencias/i);
    fireEvent.change(textarea, { target: { value: "Falta factura electrónica DIAN legal" } });

    vi.mocked(apiFetch).mockResolvedValueOnce({ status: "rejected" });
    fireEvent.click(confirmRejectBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/finance-suite/expense-reports/rep-1111-2222/reject",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ reason: "Falta factura electrónica DIAN legal" }),
        })
      );
      expect(toast.success).toHaveBeenCalledWith("Informe de gastos rechazado");
    });
  });

  it("handles internal fund disbursement without external gateways", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ status: "disbursed" });

    render(<ExpenseApprovalDrawer isOpen={true} onClose={() => {}} report={mockApprovedReport} />);

    expect(screen.getByText(/Desembolso de Fondos Ministerial/i)).toBeInTheDocument();
    expect(screen.getByText(/Caja Menor/i)).toBeInTheDocument();
    expect(screen.getByText(/Transferencia/i)).toBeInTheDocument();

    const disburseBtn = screen.getByRole("button", { name: /Efectuar Desembolso/i });
    fireEvent.click(disburseBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/finance-suite/expense-reports/rep-1111-2222/disburse",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ payment_method: "caja_menor" }),
        })
      );
      expect(toast.success).toHaveBeenCalledWith(
        "Desembolso efectuado exitosamente vía Caja Menor"
      );
    });
  });
});
