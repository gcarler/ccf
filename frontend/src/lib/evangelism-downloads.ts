"use client";

/**
 * Helper de descarga para endpoints que devuelven archivos binarios (PDF, Excel).
 *
 * Usa fetch + blob porque las descargas pasan por Authorization: Bearer headers
 * que window.open / <a download> no pueden inyectar.
 */

import { ApiError, apiFetchBlob } from "@/lib/http";
import { toast } from "sonner";

interface DownloadOptions {
    /** Override filename (default: filename from Content-Disposition header) */
    fallbackFilename?: string;
    /** Show toast on success (default: true) */
    showSuccessToast?: boolean;
    /** Show toast on error (default: true) */
    showErrorToast?: boolean;
}

export async function downloadBinaryFile(
    path: string,
    options: DownloadOptions = {}
): Promise<void> {
    const { fallbackFilename = "descarga", showSuccessToast = true, showErrorToast = true } = options;
    try {
        const blob = await apiFetchBlob(path, { method: "GET" });
        // apiFetchBlob doesn't expose response headers — best-effort naming always uses fallback.
        const objectUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = objectUrl;
        a.download = fallbackFilename;
        a.style.display = "none";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        // Free memory once the browser has had a chance to start the download.
        setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
        if (showSuccessToast) toast.success("Descarga iniciada");
    } catch (e: any) {
        const msg =
            e instanceof ApiError
                ? String((e.detail as { detail?: string })?.detail || e.message || "Error al descargar")
                : e?.message || "Error al descargar";
        if (showErrorToast) toast.error(msg);
        throw e;
    }
}

/** Descarga el PDF de asistencia de un grupo. */
export function downloadGroupAttendancePdf(grupoId: string | number) {
    return downloadBinaryFile(
        `/evangelism/reports/group/${grupoId}/attendance-pdf`,
        { fallbackFilename: `asistencia_grupo_${grupoId}.pdf` }
    );
}

/** Descarga el Excel de asistencia de un grupo. */
export function downloadGroupAttendanceExcel(grupoId: string | number) {
    return downloadBinaryFile(
        `/evangelism/reports/group/${grupoId}/attendance-excel`,
        { fallbackFilename: `asistencia_grupo_${grupoId}.xlsx` }
    );
}
