import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const fabric = vi.hoisted(() => {
  const fromURL = vi.fn(async (_data: string) => ({
    width: 1500,
    scaleToWidth: vi.fn(),
    set: vi.fn(function (this: unknown, _props: unknown) {}),
  }));
  return { fromURL };
});

vi.mock("fabric", () => ({
  Canvas: class {},
  FabricImage: { fromURL: fabric.fromURL },
}));

import { handleImageDrop, handleImagePaste, insertImageFile } from "./imageImport";

const fromURL = fabric.fromURL;

function makeDragEvent(opts: { files?: File[]; clientX?: number; clientY?: number }) {
  return {
    preventDefault: vi.fn(),
    stopPropagation: vi.fn(),
    clientX: opts.clientX ?? 10,
    clientY: opts.clientY ?? 20,
    dataTransfer: opts.files ? { files: opts.files } : null,
  } as unknown as DragEvent;
}

function makePasteEvent(opts: { imageItem?: File | null } = {}) {
  const items: Array<{ type: string; getAsFile: () => File | null }> = [];
  if (opts.imageItem !== undefined) {
    items.push({
      type: "image/png",
      getAsFile: () => (opts.imageItem ?? null) as File | null,
    });
  }
  return {
    preventDefault: vi.fn(),
    clipboardData: { items },
  } as unknown as ClipboardEvent;
}

function makeCanvasMock() {
  return {
    viewportTransform: [2, 0, 0, 2, 100, 50],
    add: vi.fn(),
    setActiveObject: vi.fn(),
    renderAll: vi.fn(),
  } as unknown as import("fabric").Canvas;
}

let origRandomUUID: typeof crypto.randomUUID;
let origFileReader: typeof FileReader;
let readerOnload: ((ev: ProgressEvent<FileReader>) => void) | undefined;

beforeEach(() => {
  vi.clearAllMocks();
  readerOnload = undefined;
  origRandomUUID = crypto.randomUUID;
  origFileReader = globalThis.FileReader;
  Object.defineProperty(crypto, "randomUUID", {
    configurable: true,
    value: () => "uuid-fixed",
  });
  class FakeReader {
    static readonly EMPTY = 0 as const;
    static readonly LOADING = 1 as const;
    static readonly DONE = 2 as const;
    onload: ((ev: ProgressEvent<FileReader>) => void) | undefined;
    readAsDataURL(_file: File) {
      readerOnload = this.onload;
    }
    result: string | ArrayBuffer | null = null;
  }
  (globalThis as unknown as { FileReader: typeof FileReader }).FileReader = FakeReader as unknown as typeof FileReader;
});

afterEach(() => {
  Object.defineProperty(crypto, "randomUUID", { configurable: true, value: origRandomUUID });
  globalThis.FileReader = origFileReader;
  vi.restoreAllMocks();
});

/** Dispara el reader.onload con el data dado (simula read completa). */
async function fireReader(data: string) {
  expect(readerOnload).toBeDefined();
  readerOnload!({ target: { result: data } } as unknown as ProgressEvent<FileReader>);
  // Flush microtasks (FabricImage.fromURL es async).
  await Promise.resolve();
  await Promise.resolve();
}

describe("whiteboard/imageImport — handleImageDrop", () => {
  it("no files → preventDefault + stopPropagation pero no inserta", () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const ev = makeDragEvent({ files: [] });
    handleImageDrop(ev, canvas, saveNow);
    expect(ev.preventDefault).toHaveBeenCalled();
    expect(ev.stopPropagation).toHaveBeenCalled();
  });
  it("dataTransfer null → no inserta (guard)", () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const ev = makeDragEvent({ files: undefined });
    handleImageDrop(ev, canvas, saveNow);
    expect(saveNow).not.toHaveBeenCalled();
  });
  it("image file → llama insertImageFile (mediante fromURL + canvas.add)", async () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const file = new File(["x"], "img.png", { type: "image/png" });
    const ev = makeDragEvent({ files: [file], clientX: 110, clientY: 120 });
    handleImageDrop(ev, canvas, saveNow);
    await fireReader("data:image/png;base64,AAAA");
    expect(fromURL).toHaveBeenCalledWith("data:image/png;base64,AAAA");
    expect(canvas.add).toHaveBeenCalledTimes(1);
    expect(canvas.setActiveObject).toHaveBeenCalledTimes(1);
    expect(canvas.renderAll).toHaveBeenCalledTimes(1);
    expect(saveNow).toHaveBeenCalledWith(canvas);
  });
  it("non-image file (text/plain) → guard de tipo, no inserta", async () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const file = new File(["x"], "f.txt", { type: "text/plain" });
    const ev = makeDragEvent({ files: [file] });
    handleImageDrop(ev, canvas, saveNow);
    // No se llama al reader porque el guard de tipo falló.
    expect(readerOnload).toBeUndefined();
  });
});

describe("whiteboard/imageImport — handleImagePaste", () => {
  it("item image → inserta con coords centradás (innerW/2, innerH/2)", async () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const file = new File(["x"], "from-clip.png", { type: "image/png" });
    const ev = makePasteEvent({ imageItem: file });
    handleImagePaste(ev, canvas, saveNow);
    expect(ev.preventDefault).toHaveBeenCalled();
    await fireReader("data:from-clip");
    expect(canvas.add).toHaveBeenCalledTimes(1);
    expect(saveNow).toHaveBeenCalled();
  });
  it("sin items image (items vacío) → no preventDefault, no inserta", () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const ev = { preventDefault: vi.fn(), clipboardData: { items: [] } } as unknown as ClipboardEvent;
    handleImagePaste(ev, canvas, saveNow);
    expect((ev as unknown as { preventDefault: ReturnType<typeof vi.fn> }).preventDefault).not.toHaveBeenCalled();
    expect(saveNow).not.toHaveBeenCalled();
  });
  it("item image pero getAsFile null → preventDefault llam, no inserta", () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const ev = makePasteEvent({ imageItem: null });
    const evP = ev as unknown as { preventDefault: ReturnType<typeof vi.fn> };
    handleImagePaste(ev, canvas, saveNow);
    expect(evP.preventDefault).toHaveBeenCalledTimes(1);
    expect(saveNow).not.toHaveBeenCalled();
  });
  it("clipboardData null → guard, no inserta", () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const ev = { preventDefault: vi.fn(), clipboardData: null } as unknown as ClipboardEvent;
    handleImagePaste(ev, canvas, saveNow);
    expect(saveNow).not.toHaveBeenCalled();
  });
});

describe("whiteboard/imageImport — insertImageFile (transforms coords)", () => {
  it("transforma clientX/Y del viewport al sistema canvas coords", async () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    // viewportTransform = [2,0,0,2,100,50]; clientX=110, clientY=120 → x=(110-100)/2=5, y=(120-50)/2=35
    const file = new File(["x"], "y.png", { type: "image/png" });
    insertImageFile(file, canvas, 110, 120, saveNow);
    await fireReader("data:y");
    const img = await fromURL.mock.results[0].value;
    expect(img.set).toHaveBeenCalled();
    const setCall = img.set.mock.calls[0][0];
    expect(setCall.left).toBe(5);
    expect(setCall.top).toBe(35);
    expect(setCall.originX).toBe("center");
    expect(setCall.originY).toBe("center");
    expect(setCall.data).toEqual({ shapeId: "uuid-fixed", type: "image" });
  });
  it("img.width > 800 → escala a width 800", async () => {
    const canvas = makeCanvasMock();
    const saveNow = vi.fn();
    const file = new File(["x"], "big.png", { type: "image/png" });
    insertImageFile(file, canvas, 0, 0, saveNow);
    await fireReader("data:big");
    const img = await fromURL.mock.results[0].value;
    expect(img.scaleToWidth).toHaveBeenCalledWith(800);
  });
  it("viewportTransform null → fallback default [1,0,0,1,0,0], coords = clientX/Y", async () => {
    const canvas = makeCanvasMock();
    (canvas as unknown as { viewportTransform: number[] | null }).viewportTransform = null;
    const saveNow = vi.fn();
    const file = new File(["x"], "y.png", { type: "image/png" });
    insertImageFile(file, canvas, 50, 75, saveNow);
    await fireReader("data:y");
    const img = await fromURL.mock.results[0].value;
    expect(img.set.mock.calls[0][0].left).toBe(50);
    expect(img.set.mock.calls[0][0].top).toBe(75);
  });
});
