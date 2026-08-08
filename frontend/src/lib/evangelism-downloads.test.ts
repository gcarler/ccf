import { describe, it, expect, vi, beforeEach, afterEach, type MockInstance } from "vitest";

vi.mock("@/lib/http", () => ({
  apiFetchBlob: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number;
    detail?: unknown;
    constructor(message: string, status: number, detail?: unknown) {
      super(message);
      this.status = status;
      this.detail = detail;
    }
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { apiFetchBlob, ApiError } from "@/lib/http";
import { toast } from "sonner";
import {
  downloadBinaryFile,
  downloadGroupAttendancePdf,
  downloadGroupAttendanceExcel,
} from "./evangelism-downloads";

const mockApiFetchBlob = vi.mocked(apiFetchBlob);
const mockToastSuccess = vi.mocked(toast.success);
const mockToastError = vi.mocked(toast.error);

function makeBlob(content = "blob-content"): Blob {
  return new Blob([content], { type: "application/pdf" });
}

let capturedAnchor: HTMLAnchorElement | null = null;
let appendChildSpy: MockInstance<[Node], Node>;
let appendChildOriginal: (node: Node) => Node;

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
  capturedAnchor = null;

  appendChildOriginal = document.body.appendChild.bind(document.body);
  appendChildSpy = vi.spyOn(document.body, "appendChild").mockImplementation((node: Node) => {
    if (node instanceof HTMLAnchorElement) {
      capturedAnchor = node as HTMLAnchorElement;
    }
    return appendChildOriginal(node);
  });
});

afterEach(() => {
  vi.useRealTimers();
  appendChildSpy.mockRestore();
});

describe("evangelism-downloads — downloadBinaryFile (éxito)", () => {
  it("llama apiFetchBlob con GET, crea <a> con href=objectURL + download=fallback, click → toast", async () => {
    mockApiFetchBlob.mockResolvedValueOnce(makeBlob());
    const createObjectURLSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:fake-url");
    const removeChildSpy = vi.spyOn(document.body, "removeChild");

    await downloadBinaryFile("/evangelism/reports/x");

    expect(mockApiFetchBlob).toHaveBeenCalledWith("/evangelism/reports/x", { method: "GET" });
    expect(createObjectURLSpy).toHaveBeenCalledTimes(1);
    expect(capturedAnchor).not.toBeNull();
    expect(capturedAnchor!.href).toBe("blob:fake-url");
    expect(capturedAnchor!.download).toBe("descarga");
    expect(removeChildSpy).toHaveBeenCalledWith(capturedAnchor);
    expect(mockToastSuccess).toHaveBeenCalledWith("Descarga iniciada");
  });

  it("usa fallbackFilename cuando se pasa", async () => {
    mockApiFetchBlob.mockResolvedValueOnce(makeBlob());
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:x");
    await downloadBinaryFile("/x", { fallbackFilename: "myfile.pdf" });
    expect(capturedAnchor!.download).toBe("myfile.pdf");
  });

  it("showSuccessToast=false no muestra toast éxito", async () => {
    mockApiFetchBlob.mockResolvedValueOnce(makeBlob());
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:x");
    await downloadBinaryFile("/x", { showSuccessToast: false });
    expect(mockToastSuccess).not.toHaveBeenCalled();
  });

  it("revoca el objectUrl después de 2s (setTimeout)", async () => {
    mockApiFetchBlob.mockResolvedValueOnce(makeBlob());
    const createObjectURLSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:revokable");
    const revokeObjectURLSpy = vi.spyOn(URL, "revokeObjectURL");
    await downloadBinaryFile("/x");
    expect(revokeObjectURLSpy).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1999);
    expect(revokeObjectURLSpy).not.toHaveBeenCalled();
    vi.advanceTimersByTime(2);
    expect(revokeObjectURLSpy).toHaveBeenCalledWith("blob:revokable");
    expect(createObjectURLSpy).toHaveBeenCalled();
  });
});

describe("evangelism-downloads — downloadBinaryFile (errores)", () => {
  it("ApiError con detail.detail → toast.error con ese mensaje", async () => {
    const err = new ApiError("Network", 500, { detail: "falló el backend" });
    mockApiFetchBlob.mockRejectedValueOnce(err);
    await expect(downloadBinaryFile("/x")).rejects.toBe(err);
    expect(mockToastError).toHaveBeenCalledWith("falló el backend");
  });
  it("ApiError sin detail.detail → toast.error con e.message", async () => {
    const err = new ApiError("msg alternativo", 500, { other: "x" });
    mockApiFetchBlob.mockRejectedValueOnce(err);
    await expect(downloadBinaryFile("/x")).rejects.toBe(err);
    expect(mockToastError).toHaveBeenCalledWith("msg alternativo");
  });
  it("ApiError sin detail ni message → toast.error con fallback 'Error al descargar'", async () => {
    const err = new ApiError("", 500);
    mockApiFetchBlob.mockRejectedValueOnce(err);
    await expect(downloadBinaryFile("/x")).rejects.toBe(err);
    expect(mockToastError).toHaveBeenCalledWith("Error al descargar");
  });
  it("Error genérico (no ApiError) con message → toast.error con message", async () => {
    mockApiFetchBlob.mockRejectedValueOnce(new Error("algo"));
    await expect(downloadBinaryFile("/x")).rejects.toThrow("algo");
    expect(mockToastError).toHaveBeenCalledWith("algo");
  });
  it("Error sin message → toast.error con fallback", async () => {
    mockApiFetchBlob.mockRejectedValueOnce(new Error());
    await expect(downloadBinaryFile("/x")).rejects.toThrow();
    expect(mockToastError).toHaveBeenCalledWith("Error al descargar");
  });
  it("showErrorToast=false no muestra toast error", async () => {
    mockApiFetchBlob.mockRejectedValueOnce(new Error("x"));
    await expect(downloadBinaryFile("/x", { showErrorToast: false })).rejects.toThrow("x");
    expect(mockToastError).not.toHaveBeenCalled();
  });
  it("siempre re-lanza el error (incluso con toast)", async () => {
    const err = new ApiError("boom", 500);
    mockApiFetchBlob.mockRejectedValueOnce(err);
    await expect(downloadBinaryFile("/x")).rejects.toBe(err);
  });
});

describe("evangelism-downloads — downloadGroupAttendancePdf", () => {
  it("llama apiFetchBlob con path correcto + usa filename PDF en el <a>", async () => {
    mockApiFetchBlob.mockResolvedValueOnce(makeBlob());
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:x");
    await downloadGroupAttendancePdf(42);
    expect(mockApiFetchBlob).toHaveBeenCalledWith(
      "/evangelism/reports/group/42/attendance-pdf",
      { method: "GET" },
    );
    expect(capturedAnchor!.download).toBe("asistencia_grupo_42.pdf");
  });
  it("acepta grupoId como string", async () => {
    mockApiFetchBlob.mockResolvedValueOnce(makeBlob());
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:x");
    await downloadGroupAttendancePdf("abc-1");
    expect(mockApiFetchBlob).toHaveBeenCalledWith(
      "/evangelism/reports/group/abc-1/attendance-pdf",
      { method: "GET" },
    );
    expect(capturedAnchor!.download).toBe("asistencia_grupo_abc-1.pdf");
  });
});

describe("evangelism-downloads — downloadGroupAttendanceExcel", () => {
  it("llama apiFetchBlob con path correcto + usa filename XLSX en el <a>", async () => {
    mockApiFetchBlob.mockResolvedValueOnce(makeBlob());
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:x");
    await downloadGroupAttendanceExcel(7);
    expect(mockApiFetchBlob).toHaveBeenCalledWith(
      "/evangelism/reports/group/7/attendance-excel",
      { method: "GET" },
    );
    expect(capturedAnchor!.download).toBe("asistencia_grupo_7.xlsx");
  });
});
