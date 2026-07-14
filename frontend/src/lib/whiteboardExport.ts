import type { Canvas } from "fabric";
import { toast } from "sonner";

/**
 * Export whiteboard canvas as PNG image
 */
export function exportToPng(
  canvas: Canvas,
  filename: string,
  multiplier = 2
): void {
  const dataUrl = canvas.toDataURL({ format: "png", multiplier });
  const link = document.createElement("a");
  link.download = `${filename}.png`;
  link.href = dataUrl;
  link.click();
  toast.success("Exportado como PNG");
}

/**
 * Export whiteboard canvas as SVG image
 */
export function exportToSvg(canvas: Canvas, filename: string): void {
  const svg = canvas.toSVG();
  const blob = new Blob([svg], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.download = `${filename}.svg`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
  toast.success("Exportado como SVG");
}

/**
 * Export whiteboard canvas as JSON (for backup/restore)
 */
export function exportToJson(
  canvas: Canvas,
  title: string,
  filename?: string
): void {
  const payload = JSON.stringify(
    { title, description: "", canvas: canvas.toJSON() },
    null,
    2
  );
  const blob = new Blob([payload], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.download =
    filename || `${title.toLowerCase().replace(/[^a-z0-9]+/g, "-") || "whiteboard"}.json`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
  toast.success("Exportado como JSON");
}

/**
 * Copy canvas as image to clipboard
 */
export async function copyToClipboard(canvas: Canvas): Promise<boolean> {
  try {
    const dataUrl = canvas.toDataURL({ format: "png", multiplier: 2 });
    const response = await fetch(dataUrl);
    const blob = await response.blob();
    await navigator.clipboard.write([
      new ClipboardItem({ "image/png": blob }),
    ]);
    toast.success("Copiado al portapapeles");
    return true;
  } catch {
    toast.error("No se pudo copiar al portapapeles");
    return false;
  }
}

/**
 * Generate a default filename from title
 */
export function generateFilename(title: string, extension: string): string {
  const sanitized = title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${sanitized || "whiteboard"}.${extension}`;
}
