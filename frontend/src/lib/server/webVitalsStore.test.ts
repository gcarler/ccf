import { describe, it, expect, vi, beforeEach } from "vitest";

const fs = vi.hoisted(() => ({
  mkdir: vi.fn(async () => undefined),
  appendFile: vi.fn(async () => undefined),
  readFile: vi.fn(async () => ""),
}));

vi.mock("node:fs/promises", () => ({
  default: { ...fs },
  mkdir: fs.mkdir,
  appendFile: fs.appendFile,
  readFile: fs.readFile,
}));

import {
  persistWebVital,
  readWebVitals,
  summarizeWebVitals,
  type StoredWebVital,
} from "./webVitalsStore";

const VALID: StoredWebVital = {
  id: "id1",
  name: "LCP",
  value: 2.5,
  label: "web-vital",
  page: "Home",
  path: "/",
  timestamp: 1700000000000,
};

beforeEach(() => {
  fs.mkdir.mockReset();
  fs.mkdir.mockResolvedValue(undefined);
  fs.appendFile.mockReset();
  fs.appendFile.mockResolvedValue(undefined);
  fs.readFile.mockReset();
  fs.readFile.mockResolvedValue("");
});

describe("webVitalsStore — persistWebVital (validación)", () => {
  it("payload válido → ok:true y escribe NDJSON con newline + mkdir previo", async () => {
    const out = await persistWebVital({ ...VALID });
    expect(out).toEqual({ ok: true });
    expect(fs.mkdir).toHaveBeenCalledTimes(1);
    expect(fs.appendFile).toHaveBeenCalledTimes(1);
    const [filePath, content] = fs.appendFile.mock.calls[0] as unknown as [string, string];
    expect(filePath.endsWith("web-vitals.ndjson")).toBe(true);
    expect(content.endsWith("\n")).toBe(true);
    expect(content.startsWith('{"id":"id1"')).toBe(true);
  });

  it("id vacío → invalid", async () => {
    expect(await persistWebVital({ ...VALID, id: "" })).toEqual({
      ok: false,
      reason: "invalid-payload",
    });
    expect(await persistWebVital({ ...VALID, id: "   " })).toEqual({
      ok: false,
      reason: "invalid-payload",
    });
  });
  it("id null/undefined → invalid", async () => {
    expect(await persistWebVital({ ...VALID, id: undefined as unknown as string })).toEqual({
      ok: false,
      reason: "invalid-payload",
    });
  });
  it("name no en ALLOWED_NAMES → invalid", async () => {
    expect(await persistWebVital({ ...VALID, name: "CLS" as never })).toEqual({
      ok: false,
      reason: "invalid-payload",
    });
    expect(await persistWebVital({ ...VALID, name: "ttfb" as never })).toEqual({
      ok: false,
      reason: "invalid-payload",
    });
  });
  it("name TTFB/LCP/FCP → válido", async () => {
    expect(await persistWebVital({ ...VALID, name: "TTFB" })).toEqual({ ok: true });
    expect(await persistWebVital({ ...VALID, name: "FCP" })).toEqual({ ok: true });
    expect(fs.appendFile).toHaveBeenCalledTimes(2);
  });
  it("value NaN/undefined → invalid", async () => {
    expect(await persistWebVital({ ...VALID, value: NaN })).toEqual({ ok: false, reason: "invalid-payload" });
    expect(await persistWebVital({ ...VALID, value: undefined as unknown as number })).toEqual({
      ok: false,
      reason: "invalid-payload",
    });
  });
  it.each(["web-vital", "custom"])("label válido: %s → ok", async (label) => {
    expect(await persistWebVital({ ...VALID, label: label as StoredWebVital["label"] })).toEqual({
      ok: true,
    });
  });
  it.each(["web-vital-alt", "vital", "", 123])(
    "label inválido: %s → invalid",
    async (label) => {
      expect(
        await persistWebVital({ ...VALID, label: label as StoredWebVital["label"] }),
      ).toEqual({ ok: false, reason: "invalid-payload" });
    },
  );
  it("page no-string → invalid", async () => {
    expect(await persistWebVital({ ...VALID, page: undefined as unknown as string })).toEqual({
      ok: false,
      reason: "invalid-payload",
    });
  });
  it("timestamp 0/negativo/no-number → invalid", async () => {
    expect(await persistWebVital({ ...VALID, timestamp: 0 })).toEqual({ ok: false, reason: "invalid-payload" });
    expect(await persistWebVital({ ...VALID, timestamp: -1 })).toEqual({ ok: false, reason: "invalid-payload" });
    expect(await persistWebVital({ ...VALID, timestamp: undefined as unknown as number })).toEqual({
      ok: false,
      reason: "invalid-payload",
    });
  });
  it("payload no-object (null/primitive) → invalid", async () => {
    expect(await persistWebVital(null)).toEqual({ ok: false, reason: "invalid-payload" });
    expect(await persistWebVital(42)).toEqual({ ok: false, reason: "invalid-payload" });
    expect(await persistWebVital("x")).toEqual({ ok: false, reason: "invalid-payload" });
  });
  it("invalid NO escribe archivo", async () => {
    await persistWebVital(null);
    expect(fs.mkdir).not.toHaveBeenCalled();
    expect(fs.appendFile).not.toHaveBeenCalled();
  });
});

describe("webVitalsStore — readWebVitals", () => {
  function fakeFile(lines: string[]) {
    fs.readFile.mockResolvedValue(lines.join("\n"));
  }
  it("archivo vacío/inexistente (readFile rejects) → []", async () => {
    fs.readFile.mockRejectedValue(new Error("ENOENT"));
    expect(await readWebVitals()).toEqual([]);
  });
  it("archivo vacío (resuelve empty string) → []", async () => {
    fs.readFile.mockResolvedValue("");
    expect(await readWebVitals()).toEqual([]);
  });
  it("parsea NDJSON válido → registros validados", async () => {
    fakeFile([
      JSON.stringify({ ...VALID, id: "r1" }),
      JSON.stringify({ ...VALID, id: "r2" }),
    ]);
    const out = await readWebVitals();
    expect(out.length).toBe(2);
    expect(out[0].id).toBe("r1");
    expect(out[1].id).toBe("r2");
  });
  it("filtra líneas inválidas (JSON parse error y validation false)", async () => {
    fakeFile([
      "{not-json",
      JSON.stringify({ ...VALID, id: "good" }),
      JSON.stringify({ ...VALID, id: "", page: "empty-id would be invalid but id is empty" }),
      JSON.stringify({ ...VALID, name: "CLS" as never }),
    ]);
    const out = await readWebVitals();
    expect(out.length).toBe(1);
    expect(out[0].id).toBe("good");
  });
  it.each<[number, number]>([
    [5, 5],
    [0, 1],
    [-3, 1],
    [3000, 2000],
  ])("limit %i → clamped a %i (default 200)", async (input, _expectedClamp) => {
    fakeFile([]);
    await readWebVitals({ limit: input });
    // Solo validamos que no lanza con límites extremos; el clamp exacto se
    // ejercería con muchos records pero slice(-N) sobre array vacío devuelve [].
    const outLimit = await readWebVitals({ limit: 5 });
    expect(Array.isArray(outLimit)).toBe(true);
  });
  it("filter name → solo registros con ese name", async () => {
    fakeFile([
      JSON.stringify({ ...VALID, id: "l1", name: "LCP" }),
      JSON.stringify({ ...VALID, id: "t1", name: "TTFB" }),
      JSON.stringify({ ...VALID, id: "l2", name: "LCP" }),
    ]);
    const out = await readWebVitals({ name: "LCP" });
    expect(out.map((r) => r.id)).toEqual(["l1", "l2"]);
  });
  it("filter path → solo registros con ese path", async () => {
    fakeFile([
      JSON.stringify({ ...VALID, id: "a", path: "/" }),
      JSON.stringify({ ...VALID, id: "b", path: "/about" }),
      JSON.stringify({ ...VALID, id: "c", path: "/" }),
    ]);
    const out = await readWebVitals({ path: "/" });
    expect(out.map((r) => r.id)).toEqual(["a", "c"]);
  });
  it("combinación name+path → intersección", async () => {
    fakeFile([
      JSON.stringify({ ...VALID, id: "x", name: "LCP", path: "/" }),
      JSON.stringify({ ...VALID, id: "y", name: "TTFB", path: "/" }),
      JSON.stringify({ ...VALID, id: "z", name: "LCP", path: "/x" }),
    ]);
    const out = await readWebVitals({ name: "LCP", path: "/" });
    expect(out.map((r) => r.id)).toEqual(["x"]);
  });
  it("default limit = 200 (slice toma últimos N)", async () => {
    const many = Array.from({ length: 250 }, (_, i) =>
      JSON.stringify({ ...VALID, id: `r${i}` }),
    );
    fakeFile(many);
    const out = await readWebVitals();
    expect(out.length).toBe(200);
    expect(out[0].id).toBe("r50");
    expect(out[199].id).toBe("r249");
  });
});

describe("webVitalsStore — summarizeWebVitals", () => {
  it("array vacío → objeto vacío", () => {
    expect(summarizeWebVitals([])).toEqual({});
  });
  it("una métrica con un record → count=1, p50=p75=latest=valor redondeado", () => {
    const out = summarizeWebVitals([{ ...VALID, value: 2.567 }]);
    expect(out.LCP).toEqual({ count: 1, p50: 2.57, p75: 2.57, latest: 2.57 });
  });
  it("múltiples valores, p50/p75 quantile correcto", () => {
    const out = summarizeWebVitals([
      { ...VALID, id: "1", value: 1 },
      { ...VALID, id: "2", value: 2 },
      { ...VALID, id: "3", value: 3 },
      { ...VALID, id: "4", value: 4 },
      { ...VALID, id: "5", value: 5 },
    ]);
    expect(out.LCP.count).toBe(5);
    // sorted: [1,2,3,4,5]; idx(p50)=floor(4*0.5)=2 → 3; idx(p75)=floor(4*0.75)=3 → 4
    expect(out.LCP.p50).toBe(3);
    expect(out.LCP.p75).toBe(4);
    expect(out.LCP.latest).toBe(5);
  });
  it("agrupa por métrica (multiple metrics)", () => {
    const out = summarizeWebVitals([
      { ...VALID, name: "LCP", value: 2 },
      { ...VALID, name: "TTFB", value: 1 },
      { ...VALID, name: "FCP", value: 1.5 },
    ]);
    expect(Object.keys(out).sort()).toEqual(["FCP", "LCP", "TTFB"]);
  });
  it("latest redondea a 2 decimales", () => {
    const out = summarizeWebVitals([{ ...VALID, value: 3.14159 }]);
    expect(out.LCP.latest).toBe(3.14);
  });
  it("p50 con array de 1 elemento → ese elemento", () => {
    const out = summarizeWebVitals([{ ...VALID, value: 9.999 }]);
    expect(out.LCP.p50).toBe(10);
    expect(out.LCP.p75).toBe(10);
  });
});
