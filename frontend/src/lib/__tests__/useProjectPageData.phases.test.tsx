/**
 * PEND-QUALITY-PHASE-SYNC-001 (cierre 2026-07-16) — vitest focalizado.
 *
 * Valida que ``useProjectPageData.loadProject`` reescribe el state
 * ``phases`` con el resultado del round-trip **siempre** (incluso cuando
 * el API responde ``[]``), evitando arrastrar columnas stale del
 * proyecto anterior.
 *
 * Estrategia:
 * - ``apiFetch`` mockeado por ``id`` de proyecto: dos cargas
 *   consecutivas con sets de fases distintos.
 * - ``Wrapper`` minúsculo expone el resultado del hook vía tests
 *   (``data-*`` attrs) para evitar mockear el Consumer real.
 * - No tocar el ``ProjectUpdateProvider``: este test es del SOT de
 *   fetching, no de propagaci\u00f3n cross-view (esa cobertura vive en
 *   ``projects-views-integration.test.tsx``).
 *
 * Ejecutar: ``cd /root/ccf/frontend && npx vitest run \
 *   src/lib/__tests__/useProjectPageData.phases.test.tsx``.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup, fireEvent } from "@testing-library/react";
import React from "react";
import type { PhaseDef } from "@/context/ProjectUpdateContext";

// Mocks que ``useProjectPageData`` toca al montar.
vi.mock("@/lib/http", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/context/AuthContext", () => ({
  useAuth: () => ({ token: "test-token", user: { id: "u1" }, loading: false, hasPermission: () => true }),
}));

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

interface PhaseSeed {
  id: string;
  slug: string;
  name: string;
  color: string;
  order_index: number;
}

interface PageDataSnapshotShape {
  phases: PhaseDef[];
  projectId: string | null;
}

import { apiFetch } from "@/lib/http";
import { useProjectPageData } from "@/hooks/useProjectPageData";

function Snapshot({ data }: { data: PageDataSnapshotShape }) {
  // Renderiza la fase-slug de cada PhaseDef + el projectId actual.
  // Usamos data-* para que el assertion no dependa de estilos.
  return (
    <div>
      <span data-testid="project-id">{data.projectId ?? ""}</span>
      <span data-testid="phases-slugs" data-slugs={data.phases.map((p) => p.slug).join(",")} />
      <span data-testid="phases-len" data-len={String(data.phases.length)} />
    </div>
  );
}

function Harness() {
  const pageData = useProjectPageData("__placeholder__");
  return (
    <>
      {/* El id real lo mutamos via reload key en cada test */}
      <button type="button" onClick={() => pageData.reloadProject()}>reload</button>
      <Snapshot data={{ phases: pageData.phases, projectId: pageData.project?.id ?? null }} />
    </>
  );
}

const FAKE_PHASES_A: PhaseSeed[] = [
  { id: "00000000-0000-0000-0000-000000000001", slug: "todo", name: "Por hacer", color: "#94a3b8", order_index: 0 },
  { id: "00000000-0000-0000-0000-000000000002", slug: "in_progress", name: "En progreso", color: "#3b82f6", order_index: 1 },
  { id: "00000000-0000-0000-0000-000000000003", slug: "completed", name: "Completada", color: "#22c55e", order_index: 2 },
];

describe("useProjectPageData — phase sync reset (PEND-QUALITY-PHASE-SYNC-001)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  afterEach(() => {
    cleanup();
  });

  it("A) carga inicial del proyecto A → phases se hidratan correctamente", async () => {
    (apiFetch as ReturnType<typeof vi.fn>).mockImplementation(async (url: string) => {
      if (url === "/projects/__placeholder__") {
        return { id: "__placeholder__", title: "Proyecto A" };
      }
      if (url === "/projects/__placeholder__/phases") {
        return FAKE_PHASES_A;
      }
      if (url === "/projects/__placeholder__/tasks") return [];
      if (url.startsWith("/projects/activities")) return [];
      return [];
    });

    render(<Harness />);
    // Esperar a que el effect corra la carga inicial.
    await screen.findByTestId("phases-slugs");
    expect(screen.getByTestId("phases-slugs").getAttribute("data-slugs"))
      .toBe("todo,in_progress,completed");
    expect(screen.getByTestId("phases-len").getAttribute("data-len")).toBe("3");
  });

  it("B) recarga con [] reemplaza estado (no conserva el anterior)", async () => {
    // 1ra carga: 3 fases; 2da carga: 0 fases.
    let phasesCalls = 0;
    (apiFetch as ReturnType<typeof vi.fn>).mockImplementation(async (url: string) => {
      if (url === "/projects/__placeholder__") {
        return { id: "__placeholder__", title: "Proyecto A" };
      }
      if (url === "/projects/__placeholder__/phases") {
        phasesCalls += 1;
        if (phasesCalls === 1) return FAKE_PHASES_A;
        return []; // <= la siguiente respuesta es [] (caso crítico)
      }
      if (url === "/projects/__placeholder__/tasks") return [];
      if (url.startsWith("/projects/activities")) return [];
      return [];
    });

    render(<Harness />);
    // Hidratamos primero las 3 fases del proyecto A.
    await screen.findByTestId("phases-slugs");
    expect(screen.getByTestId("phases-len").getAttribute("data-len")).toBe("3");

    // Disparamos reloadProject() manualmente: el round-trip devolver\u00e1 [] y
    // el state de phases debe pasar a [] (no quedarse en 3 stale).
    await act(async () => {
      fireEvent.click(screen.getByText("reload"));
    });

    // Re-leer el render tras el reload.
    expect(screen.getByTestId("phases-len").getAttribute("data-len")).toBe("0");
    expect(screen.getByTestId("phases-slugs").getAttribute("data-slugs")).toBe("");
    expect(phasesCalls).toBeGreaterThanOrEqual(2);
  });
});
