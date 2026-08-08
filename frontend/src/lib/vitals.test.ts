import { describe, it, expect, vi, beforeEach, afterEach, type Mock } from "vitest";
import { reportWebVital } from "./vitals";

let payloadJson: string | undefined;
let OriginalBlob: typeof Blob;

beforeEach(() => {
  vi.clearAllMocks();
  OriginalBlob = globalThis.Blob;
  payloadJson = undefined;
  class CapturingBlob extends OriginalBlob implements Blob {
    constructor(parts: BlobPart[], options?: BlobPropertyBag) {
      super(parts, options);
      if (parts.length > 0 && typeof parts[0] === "string") {
        payloadJson = parts[0] as string;
      }
    }
  }
  globalThis.Blob = CapturingBlob as unknown as typeof Blob;
});

afterEach(() => {
  globalThis.Blob = OriginalBlob;
  vi.unstubAllGlobals();
});

describe("vitals — reportWebVital (sendBeacon path)", () => {
  let originalSendBeacon: typeof navigator.sendBeacon;
  let sendBeaconSpy: Mock;
  let fetchSpy: Mock;

  beforeEach(() => {
    originalSendBeacon = navigator.sendBeacon;
    sendBeaconSpy = vi.fn(() => true);
    fetchSpy = vi.fn(() => Promise.resolve() as Promise<void>);
    vi.stubGlobal("fetch", fetchSpy);
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: sendBeaconSpy,
    });
  });

  afterEach(() => {
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: originalSendBeacon,
    });
  });

  it("usa navigator.sendBeacon → URL /api/analytics/web-vitals con Blob JSON contiendo payload", () => {
    reportWebVital({ id: "v1", name: "LCP", value: 2.5, label: "web-vital" });
    expect(sendBeaconSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy).not.toHaveBeenCalled();
    const [url, blob] = sendBeaconSpy.mock.calls[0] as [string, Blob];
    expect(url).toBe("/api/analytics/web-vitals");
    expect(blob.type).toBe("application/json");
    expect(payloadJson).toBeDefined();
    const payload = JSON.parse(payloadJson!);
    expect(payload.id).toBe("v1");
    expect(payload.name).toBe("LCP");
    expect(payload.value).toBe(2.5);
    expect(payload.label).toBe("web-vital");
    expect(payload.page).toBe(document.title);
    expect(payload.path).toBe(window.location.pathname);
    expect(typeof payload.timestamp).toBe("number");
  });

  it("label 'custom' es propagado", () => {
    reportWebVital({ id: "x", name: "custom", value: 1, label: "custom" });
    const payload = JSON.parse(payloadJson!);
    expect(payload.label).toBe("custom");
    expect(payload.id).toBe("x");
  });
});

describe("vitals — reportWebVital (fetch fallback cuando sendBeacon no existe)", () => {
  let fetchSpy: Mock;

  beforeEach(() => {
    fetchSpy = vi.fn(() => Promise.resolve() as Promise<void>);
    vi.stubGlobal("fetch", fetchSpy);
    Object.defineProperty(navigator, "sendBeacon", {
      configurable: true,
      value: undefined as unknown as typeof navigator.sendBeacon,
    });
  });

  it("sin sendBeacon → fetch POST /api/analytics/web-vitals con keepalive + JSON body", () => {
    reportWebVital({ id: "v2", name: "CLS", value: 0.1, label: "web-vital" });
    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, init] = fetchSpy.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/analytics/web-vitals");
    expect(init.method).toBe("POST");
    expect(init.keepalive).toBe(true);
    const headers = init.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
    const blob = init.body as Blob;
    expect(blob.type).toBe("application/json");
    const payload = JSON.parse(payloadJson!);
    expect(payload.name).toBe("CLS");
    expect(payload.value).toBe(0.1);
  });
});
