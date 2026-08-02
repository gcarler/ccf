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
  // Temporarily set a solid background so the exported PNG is not
  // transparent (the live canvas uses a transparent background so the
  // CSS grid pattern shows through).
  const savedBg = canvas.backgroundColor;
  canvas.backgroundColor = "#ffffff";
  canvas.renderAll();
  const dataUrl = canvas.toDataURL({ format: "png", multiplier });
  canvas.backgroundColor = savedBg;
  canvas.renderAll();
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
  const savedBg = canvas.backgroundColor;
  canvas.backgroundColor = "#ffffff";
  canvas.renderAll();
  const svg = canvas.toSVG();
  canvas.backgroundColor = savedBg;
  canvas.renderAll();
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
    const savedBg = canvas.backgroundColor;
    canvas.backgroundColor = "#ffffff";
    canvas.renderAll();
    const dataUrl = canvas.toDataURL({ format: "png", multiplier: 2 });
    canvas.backgroundColor = savedBg;
    canvas.renderAll();
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

/** Build a minimal single-page PDF embedding a rasterised canvas as an image. */
export async function exportToPdf(
  canvas: Canvas,
  filename: string,
  multiplier = 2
): Promise<void> {
  const savedBg = canvas.backgroundColor;
  canvas.backgroundColor = "#ffffff";
  canvas.renderAll();
  const dataUrl = canvas.toDataURL({ format: "png", multiplier });
  canvas.backgroundColor = savedBg;
  canvas.renderAll();

  const img = new Image();
  img.src = dataUrl;
  await img.decode();
  const dw = img.naturalWidth;
  const dh = img.naturalHeight;

  // Scale to fit an A4 portrait page while preserving aspect ratio.
  const A4W = 595;
  const A4H = 842;
  const M = 24;
  const availW = A4W - M * 2;
  const availH = A4H - M * 2;
  const scale = Math.min(availW / dw, availH / dh, 1);
  const pw = Math.max(1, Math.round(dw * scale));
  const ph = Math.max(1, Math.round(dh * scale));

  // Rasterise into RGB byte array (top-down, PDF expects bottom-up).
  const buf = document.createElement("canvas");
  buf.width = dw;
  buf.height = dh;
  const bctx = buf.getContext("2d");
  if (!bctx) {
    toast.error("No se pudo exportar como PDF");
    return;
  }
  bctx.drawImage(img, 0, 0);
  const px = bctx.getImageData(0, 0, dw, dh).data;
  const rgb = new Uint8Array(dw * dh * 3);
  for (let i = 0; i < dw * dh; i++) {
    rgb[i * 3] = px[i * 4];
    rgb[i * 3 + 1] = px[i * 4 + 1];
    rgb[i * 3 + 2] = px[i * 4 + 2];
  }

  // Compress with CompressionStream 'deflate' (RFC1950 zlib). PDF uses
  // /FlateDecode which accepts zlib-wrapped streams.
  let compressed: Uint8Array;
  try {
    compressed = await compressRaw(rgb);
  } catch {
    compressed = rgb; // fallback: store uncompressed
  }

  const content = `q\n${pw} 0 0 ${ph} ${M} ${M} cm\n/Im0 Do\nQ`;

  const finalParts: (string | Uint8Array)[] = [];
  const offs: number[] = [];
  let c = 0;
  const tick = (b: Uint8Array) => { offs.push(c); c += b.byteLength; finalParts.push(b); };
  const tickStr = (s: string) => tick(new TextEncoder().encode(s));

  const imgHeader = `4 0 obj\n<< /Type /XObject /Subtype /Image /Width ${dw} /Height ${dh} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length ${compressed.byteLength} >>\nstream\n`;
  const contentHeader = `5 0 obj\n<< /Length ${new TextEncoder().encode(content).byteLength} >>\nstream\n`;

  tickStr("%PDF-1.4\n%\u00E2\u00E3\u00CF\u00D3\n");
  tickStr("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n");
  tickStr("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n");
  tickStr(`3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${A4W} ${A4H}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>\nendobj\n`);
  tickStr(imgHeader);
  tick(compressed);
  tickStr("\nendstream\nendobj\n");
  tickStr(contentHeader);
  tickStr(content);
  tickStr("\nendstream\nendobj\n");

  const xrefOffsets = c;
  let xref = `xref\n0 ${offs.length + 1}\n0000000000 65535 f \n`;
  for (const o of offs) xref += `${String(o).padStart(10, "0")} 00000 n \n`;
  const trailer = `trailer\n<< /Size ${offs.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffsets}\n%%EOF\n`;
  finalParts.push(new TextEncoder().encode(xref));
  finalParts.push(new TextEncoder().encode(trailer));

  const blob = new Blob(finalParts as BlobPart[], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.download = `${filename}.pdf`;
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
  toast.success("Exportado como PDF");
}

/** Compress a Uint8Array using the platform CompressionStream (deflate). */
async function compressRaw(data: Uint8Array): Promise<Uint8Array> {
  const cs = new CompressionStream("deflate");
  const writer = cs.writable.getWriter();
  writer.write(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength) as ArrayBuffer);
  writer.close();
  const reader = cs.readable.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    chunks.push(value);
    total += value.byteLength;
  }
  const out = new Uint8Array(total);
  let o = 0;
  for (const ch of chunks) {
    out.set(ch, o);
    o += ch.byteLength;
  }
  return out;
}