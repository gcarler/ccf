import {
  describe,
  it,
  expect,
  vi,
  beforeEach,
  afterEach,
  type MockInstance,
  type Mock,
} from "vitest";

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

import { toast } from "sonner";
import {
  exportToPng,
  exportToSvg,
  exportToJson,
  copyToClipboard,
  generateFilename,
  exportToPdf,
} from "./whiteboardExport";

const mockToastSuccess = vi.mocked(toast.success);
const mockToastError = vi.mocked(toast.error);

/** Mock mínimo de Canvas de fabric con la superficie usada por whiteboardExport. */
function makeCanvas() {
  const cv = {
    backgroundColor: "transparent" as string | unknown,
    renderAll: vi.fn() as Mock<[], void>,
    toDataURL: vi.fn(() => "data:image/png;base64,AAAA") as Mock<[], string>,
    toSVG: vi.fn(() => "<svg></svg>") as Mock<[], string>,
    toJSON: vi.fn(() => ({ objects: [] })) as Mock<[], { objects: never[] }>,
  };
  return cv as unknown as import("fabric").Canvas;
}

let createdLinks: HTMLAnchorElement[] = [];
let createElementSpy: MockInstance;
let createElementOriginal: (tag: string) => HTMLElement;
let mockBufCtx: { drawImage: Mock; getImageData: Mock };

beforeEach(() => {
  vi.clearAllMocks();
  vi.useFakeTimers();
  createdLinks = [];
  mockBufCtx = {
    drawImage: vi.fn(),
    getImageData: vi.fn(() => ({
      data: new Uint8ClampedArray(8),
    })),
  };

  createElementOriginal = document.createElement.bind(document);
  createElementSpy = vi.spyOn(document, "createElement").mockImplementation((tag: string) => {
    if (tag === "canvas") {
      const buf = {
        width: 0,
        height: 0,
        getContext: vi.fn(() => mockBufCtx),
      };
      return buf as unknown as HTMLCanvasElement;
    }
    const el = createElementOriginal(tag) as HTMLAnchorElement;
    if (tag === "a") {
      const clickSpy = vi.fn();
      el.click = clickSpy;
      createdLinks.push(el);
    }
    return el as HTMLElement;
  });
});

afterEach(() => {
  vi.useRealTimers();
  createElementSpy.mockRestore();
});

describe("whiteboardExport — generateFilename (puro)", () => {
  it("title normal → lowercase + guiones por especiales", () => {
    expect(generateFilename("Mi Diagrama #2", "png")).toBe("mi-diagrama-2.png");
  });
  it("title con espacios y mayúsculas", () => {
    expect(generateFilename("Hello World", "svg")).toBe("hello-world.svg");
  });
  it("title con guiones bajos se convierten a guiones", () => {
    expect(generateFilename("foo_bar_baz", "json")).toBe("foo-bar-baz.json");
  });
  it("title con acentos → quita acentos (no letras)", () => {
    expect(generateFilename("Diagrama Ñúcleo", "pdf")).toBe("diagrama-cleo.pdf");
  });
  it("title vacío → fallback 'whiteboard'", () => {
    expect(generateFilename("", "png")).toBe("whiteboard.png");
  });
  it("title sólo símbolos → fallback (trim de guiones)", () => {
    expect(generateFilename("###!!!???", "svg")).toBe("whiteboard.svg");
  });
  it("title con guiones al inicio/final → se trimean", () => {
    expect(generateFilename("--Hola--", "json")).toBe("hola.json");
  });
  it.each([
    ["png", "png"],
    ["svg", "svg"],
    ["json", "json"],
    ["pdf", "pdf"],
  ])("respects extensión %s", (_ext, expected) => {
    const out = generateFilename("x", expected);
    expect(out).toBe(`x.${expected}`);
  });
});

describe("whiteboardExport — exportToPng", () => {
  it("guarda y restaura bg blanco, toDataURL con png+multiplier, click, toast success", () => {
    const canvas = makeCanvas();
    exportToPng(canvas, "my-export", 3);
    expect(canvas.backgroundColor).toBe("transparent");
    expect(canvas.toDataURL).toHaveBeenCalledWith({
      format: "png",
      multiplier: 3,
    });
    expect(canvas.renderAll).toHaveBeenCalledTimes(2);
    expect(createdLinks.length).toBe(1);
    expect(createdLinks[0].download).toBe("my-export.png");
    expect(createdLinks[0].href).toBe("data:image/png;base64,AAAA");
    expect(createdLinks[0].click).toHaveBeenCalled();
    expect(mockToastSuccess).toHaveBeenCalledWith("Exportado como PNG");
  });
  it("multiplier default = 2", () => {
    const canvas = makeCanvas();
    exportToPng(canvas, "x");
    expect(canvas.toDataURL).toHaveBeenCalledWith({
      format: "png",
      multiplier: 2,
    });
  });
  it("restaura el bg original incluso si era 'transparent'", () => {
    const canvas = makeCanvas();
    (canvas as unknown as { backgroundColor: unknown }).backgroundColor = "transparent";
    exportToPng(canvas, "x");
    expect((canvas as unknown as { backgroundColor: unknown }).backgroundColor).toBe("transparent");
  });
});

describe("whiteboardExport — exportToSvg", () => {
  it("toSVG, crea Blob+objectURL, click con filename .svg, toast success", () => {
    const canvas = makeCanvas();
    const urlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:svg");
    exportToSvg(canvas, "my-svg");
    expect(canvas.toSVG).toHaveBeenCalledTimes(1);
    expect(canvas.backgroundColor).toBe("transparent");
    expect(canvas.renderAll).toHaveBeenCalledTimes(2);
    expect(urlSpy).toHaveBeenCalledTimes(1);
    expect(createdLinks[0].download).toBe("my-svg.svg");
    expect(createdLinks[0].href).toBe("blob:svg");
    expect(createdLinks[0].click).toHaveBeenCalled();
    expect(mockToastSuccess).toHaveBeenCalledWith("Exportado como SVG");
  });
  it("revoca el objectUrl después de 1s", () => {
    const canvas = makeCanvas();
    const revokeSpy = vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:svg-rev");
    exportToSvg(canvas, "x");
    expect(revokeSpy).not.toHaveBeenCalled();
    vi.advanceTimersByTime(999);
    expect(revokeSpy).not.toHaveBeenCalled();
    vi.advanceTimersByTime(2);
    expect(revokeSpy).toHaveBeenCalledWith("blob:svg-rev");
  });
});

describe("whiteboardExport — exportToJson", () => {
  it("toJSON,serializa correctamente, click con filename.json, toast success", () => {
    const canvas = makeCanvas();
    const urlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:json");
    exportToJson(canvas, "Mi Diagrama", "custom-name.json");
    expect(canvas.toJSON).toHaveBeenCalledTimes(1);
    expect(urlSpy).toHaveBeenCalledTimes(1);
    expect(createdLinks[0].download).toBe("custom-name.json");
    expect(createdLinks[0].href).toBe("blob:json");
    expect(createdLinks[0].click).toHaveBeenCalled();
    expect(mockToastSuccess).toHaveBeenCalledWith("Exportado como JSON");
    const blobArg = urlSpy.mock.calls[0][0] as Blob;
    expect(blobArg.type).toBe("application/json");
  });
  it("sin filename → usa slug de title + .json", () => {
    const canvas = makeCanvas();
    exportToJson(canvas, "Mi Diagrama");
    expect(createdLinks[0].download).toBe("mi-diagrama.json");
  });
  it("title con acentos → slug sanitizado (guiones por no-alfanuméricos)", () => {
    const canvas = makeCanvas();
    exportToJson(canvas, "Ñúcleo");
    // Nota: el path inline hace toLowerCase().replace(/[^a-z0-9]+/g, "-")
    // — sin trim de guiones (a diferencia de generateFilename), produciendo
    // "_úcleo".toLowerCase() → "úcleo" → "-cleo" con guión al inicio.
    expect(createdLinks[0].download).toBe("-cleo.json");
  });
  it("filename explícito vacío → fallback a slug", () => {
    const canvas = makeCanvas();
    exportToJson(canvas, "Mi Diagrama", "");
    expect(createdLinks[0].download).toBe("mi-diagrama.json");
  });
  it("title vacío → filename 'whiteboard.json'", () => {
    const canvas = makeCanvas();
    exportToJson(canvas, "");
    expect(createdLinks[0].download).toBe("whiteboard.json");
  });
  it("revoca objectUrl tras 1s", () => {
    const canvas = makeCanvas();
    const revokeSpy = vi.spyOn(URL, "revokeObjectURL");
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:json-rev");
    exportToJson(canvas, "x");
    vi.advanceTimersByTime(1001);
    expect(revokeSpy).toHaveBeenCalledWith("blob:json-rev");
  });
});

describe("whiteboardExport — copyToClipboard", () => {
  it("éxito: clipboard.write con ClipboardItem PNG → true, toast success", async () => {
    const canvas = makeCanvas();
    const blob = new Blob(["x"], { type: "image/png" });
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      blob: vi.fn(async () => blob),
    } as unknown as Response);
    const writeSpy = vi.fn(async () => {});
    vi.stubGlobal("navigator", {
      clipboard: { write: writeSpy },
    });
    vi.stubGlobal("ClipboardItem", class {
      constructor(_items: Record<string, Blob>) {}
    });
    const out = await copyToClipboard(canvas);
    expect(out).toBe(true);
    expect(canvas.toDataURL).toHaveBeenCalledWith({ format: "png", multiplier: 2 });
    expect(fetchSpy).toHaveBeenCalledWith("data:image/png;base64,AAAA");
    expect(writeSpy).toHaveBeenCalledTimes(1);
    expect(mockToastSuccess).toHaveBeenCalledWith("Copiado al portapapeles");
    vi.unstubAllGlobals();
  });
  it("falla: catch → false, toast error", async () => {
    const canvas = makeCanvas();
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("fail"));
    vi.stubGlobal("navigator", { clipboard: { write: vi.fn() } });
    vi.stubGlobal("ClipboardItem", class {
      constructor(_items: unknown) {}
    });
    const out = await copyToClipboard(canvas);
    expect(out).toBe(false);
    expect(mockToastError).toHaveBeenCalledWith("No se pudo copiar al portapapeles");
    vi.unstubAllGlobals();
  });
  it("restaura bg original incluso ante error", async () => {
    const canvas = makeCanvas();
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("fail"));
    vi.stubGlobal("navigator", { clipboard: { write: vi.fn() } });
    vi.stubGlobal("ClipboardItem", class {
      constructor(_items: unknown) {}
    });
    await copyToClipboard(canvas);
    expect((canvas as unknown as { backgroundColor: unknown }).backgroundColor).toBe("transparent");
    vi.unstubAllGlobals();
  });
});

describe("whiteboardExport — exportToPdf (estructura básica)", () => {
  it("genera PDF Blob con type application/pdf, link.click con filename.pdf, toast success", async () => {
    const canvas = makeCanvas();
    const urlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:pdf");
    // Mock Image con decode() síncrono y naturalWidth/Height.
    class MockImage {
      src = "";
      naturalWidth = 100;
      naturalHeight = 100;
      async decode() {}
    }
    vi.stubGlobal("Image", MockImage);
    // Mock CompressionStream necesario
    const compressible = new Uint8Array([1, 2, 3]);
    vi.stubGlobal("CompressionStream", class {
      writable = {
        getWriter: () => ({
          write: vi.fn(),
          close: vi.fn(),
        }),
      };
      readable = {
        getReader: () => {
          let done = false;
          return {
            read: async () => {
              if (done) return { value: undefined, done: true };
              done = true;
              return { value: compressible, done: false };
            },
          };
        },
      };
    });

    await exportToPdf(canvas, "doc-name", 1);
    expect(canvas.toDataURL).toHaveBeenCalledWith({ format: "png", multiplier: 1 });
    expect(createdLinks[0].download).toBe("doc-name.pdf");
    expect(createdLinks[0].click).toHaveBeenCalled();
    const blobArg = urlSpy.mock.calls[0][0] as Blob;
    expect(blobArg.type).toBe("application/pdf");
    expect(mockToastSuccess).toHaveBeenCalledWith("Exportado como PDF");
    vi.unstubAllGlobals();
  });
  it("restaura bg en finally incluso si toDataURL lanza", async () => {
    const canvas = makeCanvas();
    canvas.toDataURL = vi.fn(() => {
      throw new Error("broken");
    });
    class MockImage {
      src = "";
      naturalWidth = 100;
      naturalHeight = 100;
      async decode() {}
    }
    vi.stubGlobal("Image", MockImage);
    await expect(exportToPdf(canvas, "x", 1)).rejects.toThrow("broken");
    expect((canvas as unknown as { backgroundColor: unknown }).backgroundColor).toBe("transparent");
    vi.unstubAllGlobals();
  });
});
